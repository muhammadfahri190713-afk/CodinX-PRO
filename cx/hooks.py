"""Hooks (mirip Claude Code): perintah shell pada event PreToolUse / PostToolUse / UserPromptSubmit / Stop.

Konfigurasi: ~/.codinx/hooks.json (+ <proyek>/.codinx/hooks.json bila config `trust_project` = true). Contoh: examples/hooks.json.
Perintah menerima JSON di stdin. Exit 0 = lanjut (stdout jadi konteks), exit 2 = BLOKIR (stderr dikirim ke model),
exit lain = peringatan non-blokir.
"""
import json
import os
import re
import subprocess

from . import config, log

EVENTS = ("PreToolUse", "PostToolUse", "UserPromptSubmit", "Stop")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    h = data.get("hooks", data) if isinstance(data, dict) else {}
    return {k: v for k, v in h.items() if k in EVENTS and isinstance(v, list)}


def load(cwd, cfg):
    files = [os.path.join(config.HOME, "hooks.json")]
    if cfg.get("trust_project"):
        files.append(os.path.join(cwd, ".codinx", "hooks.json"))
    merged = {e: [] for e in EVENTS}
    for f in files:
        for ev, items in _read(f).items():
            merged[ev] += [i for i in items if isinstance(i, dict) and i.get("command")]
    return merged


def _match(matcher, tool):
    if not matcher or matcher == "*":
        return True
    try:
        return re.fullmatch(matcher, tool or "", re.I) is not None
    except re.error:
        return False


def run(event, cwd, cfg, payload, tool=None):
    """-> {'blocked': bool, 'message': str, 'output': str}"""
    res = {"blocked": False, "message": "", "output": ""}
    for item in load(cwd, cfg).get(event, []):
        if event in ("PreToolUse", "PostToolUse") and not _match(item.get("matcher", "*"), tool):
            continue
        data = dict(payload, event=event, cwd=cwd)
        try:
            p = subprocess.run(item["command"], shell=True, input=json.dumps(data, ensure_ascii=False, default=str),
                               capture_output=True, text=True, timeout=int(item.get("timeout", 30)), cwd=cwd,
                               env=dict(os.environ, CODINX_HOOK_EVENT=event, CODINX_PROJECT_DIR=cwd))
        except subprocess.TimeoutExpired:
            res["message"] += f"[hook timeout: {item['command'][:60]}]\n"
            continue
        except OSError as e:
            res["message"] += f"[hook error: {e}]\n"
            continue
        log.debug("hook", event=event, cmd=item["command"][:80], rc=p.returncode)
        if p.returncode == 2:
            res["blocked"] = True
            res["message"] += (p.stderr or p.stdout or "diblokir oleh hook").strip() + "\n"
        elif p.returncode == 0:
            if p.stdout.strip():
                res["output"] += p.stdout.strip() + "\n"
        else:
            res["message"] += f"[hook gagal rc={p.returncode}: {(p.stderr or '').strip()[:200]}]\n"
    res["message"], res["output"] = res["message"].strip(), res["output"].strip()
    return res
