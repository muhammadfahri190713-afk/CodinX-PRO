"""Klien MCP (Model Context Protocol) via stdio — stdlib saja.

Konfigurasi: ~/.codinx/mcp.json (+ <proyek>/.codinx/mcp.json bila `trust_project` = true)
  {"mcpServers": {"nama": {"command": "npx", "args": ["-y", "paket-server"], "env": {"KEY": "v"}}}}
Tool tampil ke model sebagai  mcp__<server>__<tool>  dan selalu melewati sistem izin.
"""
import atexit
import itertools
import json
import os
import re
import subprocess
import threading
import time

from . import __version__, config, log


class MCPError(Exception):
    pass


class Server:
    def __init__(self, name, spec):
        self.name, self.spec = name, spec
        self.proc, self.tools, self.error, self.started = None, [], "", False
        self._ids, self._resp, self._cv, self._dead = itertools.count(1), {}, threading.Condition(), False

    def start(self, timeout=15):
        spec = self.spec
        cmd = [str(spec["command"])] + [str(a) for a in spec.get("args", [])]
        env = dict(os.environ)
        env.update({k: str(v) for k, v in (spec.get("env") or {}).items()})
        try:
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                         text=True, bufsize=1, env=env, cwd=spec.get("cwd") or None)
        except OSError as e:
            self.error = str(e)
            return False
        threading.Thread(target=self._reader, daemon=True).start()
        try:
            self.request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                        "clientInfo": {"name": "CodinX", "version": __version__}}, timeout)
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            self.tools = self.request("tools/list", {}, timeout).get("tools", [])
            self.started = True
        except MCPError as e:
            self.error = str(e)
            self.stop()
            return False
        log.debug("mcp_started", server=self.name, tools=len(self.tools))
        return True

    def _reader(self):
        try:
            for line in self.proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(msg, dict):
                    continue
                if "id" in msg and ("result" in msg or "error" in msg):
                    with self._cv:
                        self._resp[msg["id"]] = msg
                        self._cv.notify_all()
                elif msg.get("method") == "ping" and "id" in msg:
                    self._send({"jsonrpc": "2.0", "id": msg["id"], "result": {}})
        except (ValueError, OSError):
            pass
        with self._cv:
            self._dead = True
            self._cv.notify_all()

    def _send(self, obj):
        try:
            self.proc.stdin.write(json.dumps(obj) + "\n")
            self.proc.stdin.flush()
        except (OSError, ValueError, AttributeError):
            raise MCPError("server tidak merespons (pipa tertutup)")

    def request(self, method, params, timeout=30):
        rid = next(self._ids)
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        end = time.time() + timeout
        with self._cv:
            while rid not in self._resp:
                if self._dead:
                    raise MCPError("server berhenti")
                left = end - time.time()
                if left <= 0:
                    raise MCPError(f"timeout pada {method}")
                self._cv.wait(min(left, 0.5))
            msg = self._resp.pop(rid)
        if "error" in msg:
            e = msg["error"]
            raise MCPError(str(e.get("message", e) if isinstance(e, dict) else e)[:300])
        return msg.get("result") or {}

    def call(self, tool, args, timeout=120):
        r = self.request("tools/call", {"name": tool, "arguments": args or {}}, timeout)
        parts = [c.get("text", "") if c.get("type") == "text" else f"[{c.get('type', 'konten')}]" for c in r.get("content") or []]
        text = "\n".join(parts) or json.dumps(r.get("structuredContent", r), ensure_ascii=False)
        return ("Error: " if r.get("isError") else "") + text

    def stop(self):
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=3)
            for pipe in (self.proc.stdin, self.proc.stdout):
                try:
                    pipe.close()
                except (OSError, ValueError, AttributeError):
                    pass
        except (OSError, AttributeError):
            pass


def _safe(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)[:64]


def _params(schema):
    if not isinstance(schema, dict) or schema.get("type") != "object":
        return {"type": "object", "properties": {}}
    sc = {k: v for k, v in schema.items() if k != "$schema"}
    sc.setdefault("properties", {})
    return sc


class Manager:
    def __init__(self):
        self.specs, self.servers, self.map, self.loaded = {}, {}, {}, False

    def load(self, cwd, cfg):
        self.specs = {}
        files = [os.path.join(config.HOME, "mcp.json")]
        if cfg.get("trust_project"):
            files.append(os.path.join(cwd, ".codinx", "mcp.json"))
        for f in files:
            try:
                with open(f, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                continue
            for name, spec in (data.get("mcpServers", data) if isinstance(data, dict) else {}).items():
                if isinstance(spec, dict) and spec.get("command") and not spec.get("disabled"):
                    self.specs[name] = spec

    def ensure_started(self, ui=None):
        if self.loaded or not self.specs:
            self.loaded = True
            return
        self.loaded = True
        for name, spec in self.specs.items():
            srv = Server(name, spec)
            ok = srv.start()
            self.servers[name] = srv
            if ui:
                (ui.info if ok else ui.warn)(f"MCP {name}: " + (f"{len(srv.tools)} tool" if ok else f"gagal ({srv.error[:80]})"))
        self.map = {}
        for sname, srv in self.servers.items():
            for t in srv.tools:
                full = _safe(f"mcp__{sname}__{t.get('name', '')}")
                while full in self.map:
                    full = full[:60] + "_x"
                self.map[full] = (srv, t)

    def has(self, full):
        return full in self.map

    def schemas(self):
        return [{"type": "function", "function": {"name": full, "description": f"[MCP:{srv.name}] {t.get('description', '')}"[:900],
                                                  "parameters": _params(t.get("inputSchema"))}} for full, (srv, t) in self.map.items()]

    def call(self, full, args):
        srv, t = self.map[full]
        return srv.call(t["name"], args)

    def status(self):
        rows = []
        for name in self.specs:
            srv = self.servers.get(name)
            rows.append([name, "✓ aktif" if srv and srv.started else ("✗ " + srv.error[:50] if srv else "belum dimulai"),
                         ", ".join(t.get("name", "") for t in (srv.tools if srv else []))[:60]])
        return rows

    def stop_all(self):
        for srv in self.servers.values():
            srv.stop()
        self.servers, self.map, self.loaded = {}, {}, False

    def reload(self, cwd, cfg):
        self.stop_all()
        self.load(cwd, cfg)


manager = Manager()
atexit.register(manager.stop_all)
