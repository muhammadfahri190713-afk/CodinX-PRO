import json
import os
import re

from . import vault

HOME = os.path.expanduser("~/.codinx")
CONFIG = os.path.join(HOME, "config.json")
KEYFILE = os.path.join(HOME, ".key.enc")
SESSIONS = os.path.join(HOME, "sessions")
HISTORY = os.path.join(HOME, "history")

DEFAULT_BASE_URL = "https://inttelix.vercel.app/api/v1"
DEFAULT_MODEL = "deepseek-v4-flash"

DEFAULTS = {
    "base_url": DEFAULT_BASE_URL,
    "model": DEFAULT_MODEL,
    "tier": "free",
    "timezone": "",
    "dinar_token_unit": 8000,
    "tool_policy": {},
    "theme": "codinx",
    "agent": "build",
    "context_limit": 128000,
    "temperature": None,
    "max_steps": 60,
    "show_thinking": False,
    "show_details": True,
    "insecure_tls": False,
    "permission": {},
}


def ensure_dirs():
    for d in (HOME, SESSIONS, os.path.join(HOME, "commands")):
        os.makedirs(d, mode=0o700, exist_ok=True)


def normalize_url(u):
    u = (u or "").strip().rstrip("/")
    if u and not re.search(r"/v\d+$", u):
        u += "/v1"
    return u


def load():
    ensure_dirs()
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG) as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    if os.environ.get("CODINX_BASE_URL"):
        cfg["base_url"] = os.environ["CODINX_BASE_URL"]
    if os.environ.get("CODINX_MODEL"):
        cfg["model"] = os.environ["CODINX_MODEL"]
    cfg["base_url"] = normalize_url(cfg["base_url"])
    return cfg


def save(cfg):
    ensure_dirs()
    keep = {k: v for k, v in cfg.items() if k in DEFAULTS}
    tmp = CONFIG + ".tmp"
    with open(tmp, "w") as f:
        json.dump(keep, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, CONFIG)


def get_key():
    if os.environ.get("CODINX_API_KEY"):
        return os.environ["CODINX_API_KEY"]
    try:
        with open(KEYFILE, "rb") as f:
            return vault.decrypt(f.read())
    except (OSError, ValueError):
        return ""


def set_key(key):
    ensure_dirs()
    fd = os.open(KEYFILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(vault.encrypt(key))
      
