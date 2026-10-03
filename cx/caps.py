"""Kemampuan per model/proxy (hasil diagnosa): mode tool + mode riwayat. Disimpan di ~/.codinx/caps.json."""
import json
import os
import time

from . import config

FILE = os.path.join(config.HOME, "caps.json")


def _load():
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def get(model):
    return dict(_load().get(model, {}))


def set(model, **kw):
    d = _load()
    e = d.setdefault(model, {})
    e.update(kw)
    e["ts"] = int(time.time())
    config.ensure_dirs()
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.chmod(FILE, 0o600)


def clear(model=None):
    d = _load()
    if model:
        d.pop(model, None)
    else:
        d = {}
    config.ensure_dirs()
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(d, f)
