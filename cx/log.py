"""Log debug JSONL (~/.codinx/logs). Aktifkan: CODINX_DEBUG=1 (atau di .env) atau /debug on. Rahasia otomatis disamarkan."""
import json
import os
import re
import time

from . import config

LOG_DIR = os.path.join(config.HOME, "logs")
_state = {"on": None}
_SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9_\-\.]{8,}|(?i:api[_-]?key[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9_\-\.]{12,})")


def enabled():
    if _state["on"] is None:
        _state["on"] = config.env("CODINX_DEBUG").lower() not in ("", "0", "false", "no", "off")
    return _state["on"]


def set_enabled(v):
    _state["on"] = bool(v)


def redact(s):
    return _SECRET.sub("[REDACTED]", s)


def _path():
    return os.path.join(LOG_DIR, "codinx-" + time.strftime("%Y%m%d") + ".log")


def debug(_ev, **kw):
    """Catat satu kejadian. Nama parameter pertama sengaja `_ev` agar kw bebas memakai kunci `event=`."""
    if not enabled():
        return
    try:
        os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
        rec = {"t": time.strftime("%H:%M:%S"), "ev": _ev}
        rec.update(kw)
        with open(_path(), "a", encoding="utf-8") as f:
            f.write(redact(json.dumps(rec, ensure_ascii=False, default=str)) + "\n")
        os.chmod(_path(), 0o600)
    except OSError:
        pass


def tail(n=40):
    try:
        with open(_path(), encoding="utf-8") as f:
            return f.read().splitlines()[-n:]
    except OSError:
        return []
