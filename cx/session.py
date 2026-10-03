"""Sesi percakapan (persisten, 1 percakapan = 1 id), undo/redo perubahan file."""
import json
import os
import time
import uuid

from . import config, fsutil


class Session:
    def __init__(self, cwd):
        self.id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        self.cwd = cwd
        self.created = time.time()
        self.title = ""
        self.messages = []
        self.todos = []
        self.last_prompt_tokens = 0
        self.tokens_total = 0
        self.remote_id = None       # id respons terakhir dari server (chatcmpl-...)
        self.remote_conv = None     # id percakapan yang diberikan server (jika ada)
        self.turns = []        # in-memory: {"index","user","backups"}
        self.redo_stack = []

    # ---- persistence
    @property
    def path(self):
        return os.path.join(config.SESSIONS, self.id + ".json")

    def save(self):
        if not self.messages:
            return
        if not self.title:
            for m in self.messages:
                if m["role"] == "user":
                    self.title = str(m["content"]).strip().splitlines()[0][:70]
                    break
        data = {"id": self.id, "cwd": self.cwd, "created": self.created, "title": self.title,
                "messages": self.messages, "todos": self.todos,
                "last_prompt_tokens": self.last_prompt_tokens, "tokens_total": self.tokens_total,
                "remote_id": self.remote_id, "remote_conv": self.remote_conv}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    @classmethod
    def load(cls, sid):
        with open(os.path.join(config.SESSIONS, sid + ".json"), encoding="utf-8") as f:
            d = json.load(f)
        s = cls(d.get("cwd", os.getcwd()))
        s.id, s.created, s.title = d["id"], d.get("created", time.time()), d.get("title", "")
        s.messages, s.todos = d.get("messages", []), d.get("todos", [])
        s.last_prompt_tokens, s.tokens_total = d.get("last_prompt_tokens", 0), d.get("tokens_total", 0)
        s.remote_id, s.remote_conv = d.get("remote_id"), d.get("remote_conv")
        return s

    @staticmethod
    def list_all():
        out = []
        try:
            names = os.listdir(config.SESSIONS)
        except OSError:
            return out
        for n in names:
            if not n.endswith(".json"):
                continue
            try:
                with open(os.path.join(config.SESSIONS, n), encoding="utf-8") as f:
                    d = json.load(f)
                out.append({"id": d["id"], "cwd": d.get("cwd", ""), "title": d.get("title", ""),
                            "created": d.get("created", 0), "n": len(d.get("messages", []))})
            except (OSError, ValueError, KeyError):
                pass
        return sorted(out, key=lambda x: x["created"], reverse=True)

    @classmethod
    def latest_for(cls, cwd):
        for i in cls.list_all():
            if i["cwd"] == cwd and i["n"] > 0:
                return cls.load(i["id"])
        return None

    # ---- turns / undo / redo
    def begin_turn(self, user_text):
        t = {"index": len(self.messages), "user": user_text, "backups": {}}
        self.turns.append(t)
        return t

    def drop_turn(self):
        if self.turns:
            t = self.turns.pop()
            del self.messages[t["index"]:]

    def undo(self):
        if not self.turns:
            return None
        t = self.turns.pop()
        after = {}
        for p, orig in t["backups"].items():
            after[p] = fsutil.read_bytes(p) if os.path.isfile(p) else None
            if orig is None:
                if os.path.isfile(p):
                    os.remove(p)
            else:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                fsutil.write_bytes(p, orig)
        removed = self.messages[t["index"]:]
        del self.messages[t["index"]:]
        self.redo_stack.append({"turn": t, "after": after, "removed": removed})
        self.save()
        return t

    def redo(self):
        if not self.redo_stack:
            return None
        r = self.redo_stack.pop()
        for p, data in r["after"].items():
            if data is None:
                if os.path.isfile(p):
                    os.remove(p)
            else:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                fsutil.write_bytes(p, data)
        r["turn"]["index"] = len(self.messages)
        self.messages.extend(r["removed"])
        self.turns.append(r["turn"])
        self.save()
        return r["turn"]

    # ---- export
    def export_md(self):
        lines = [f"# {self.title or 'Sesi CodinX'}", f"_id: {self.id} · folder: {self.cwd}_", ""]
        for m in self.messages:
            if m["role"] == "user":
                lines += ["## 🧑 User", str(m["content"]), ""]
            elif m["role"] == "assistant":
                if m.get("content"):
                    lines += ["## 🤖 CodinX", m["content"], ""]
                for tc in m.get("tool_calls") or []:
                    lines += [f"> ⚙ `{tc['function']['name']}` {tc['function']['arguments'][:200]}", ""]
            elif m["role"] == "tool":
                lines += ["```", str(m["content"])[:800], "```", ""]
        return "\n".join(lines)
