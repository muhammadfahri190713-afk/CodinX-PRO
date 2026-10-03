import copy
import json
import os
import re

import subprocess

from . import vault

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# CODINX_HOME menghindari masalah saat aplikasi dijalankan lewat `su` atau
# launcher Android yang mengubah HOME ke lokasi yang tidak writable.
HOME = os.path.abspath(os.path.expanduser(os.environ.get("CODINX_HOME", "~/.codinx")))
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
    "trial_mode": True,        # masa uji coba: semua model gratis (matikan: CODINX_TRIAL=0)
    "timezone": "",
    "dinar_token_unit": 8000,
    "tool_policy": {},
    "trust_project": False,    # izinkan hooks.json / mcp.json dari folder proyek (default: hanya global)
    "tool_mode": "auto",       # auto | native | text | none
    "history_mode": "auto",    # auto | native | flat
    "auto_probe": True,        # diagnosa otomatis sekali per model
    "conv_field": "",          # nama field body untuk id percakapan (mis. conversation_id / chat_id)
    "conv_source": "client",   # client = id sesi CodinX | server = pakai id yang diberikan server
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


# ---------------------------------------------------------------- .env support
# Dibaca (hanya variabel berawalan CODINX_): ~/.codinx/.env, folder instalasi,
# lalu folder kerja aktif (yang paling akhir menang). Ini memudahkan Termux/Acode.
# Prioritas: variabel lingkungan nyata > .env > brankas/config.json.
_dotenv = None


def _parse_env(path):
    out = {}
    try:
        with open(path, encoding="utf-8-sig") as f:      # utf-8-sig: buang BOM dari editor Windows
            text = f.read()
    except OSError:
        return out
    for raw in text.splitlines():                         # splitlines + strip: aman untuk CRLF
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        q = re.match(r"""^(["'])(.*?)\1\s*(?:#.*)?$""", v)      # "nilai" / 'nilai' (boleh diikuti komentar)
        if q:
            v = q.group(2)
        else:
            v = re.split(r"\s+#", v, maxsplit=1)[0].strip()
        if k.startswith("CODINX_"):
            out[k] = v
    return out


def env_paths():
    paths = [os.path.join(HOME, ".env"), os.path.join(ROOT, ".env"), os.path.join(os.getcwd(), ".env")]
    return list(dict.fromkeys(paths))


def dotenv():
    global _dotenv
    if _dotenv is None:
        data = {}
        for p in env_paths():
            if os.path.isfile(p):
                try:
                    if os.stat(p).st_mode & 0o077:        # rahasia: hanya boleh dibaca pemiliknya
                        os.chmod(p, 0o600)
                except OSError:
                    pass
                data.update(_parse_env(p))
        _dotenv = data
    return _dotenv


def env(name):
    return os.environ.get(name) or dotenv().get(name) or ""


def key_source():
    if os.environ.get("CODINX_API_KEY"):
        return "variabel lingkungan"
    if dotenv().get("CODINX_API_KEY"):
        return ".env"
    return "brankas terenkripsi" if get_key() else "(belum ada)"


def env_leak_warning():
    """Peringatan bila .env berada di repo git tetapi TIDAK di-ignore (risiko ke-push ke GitHub)."""
    p = os.path.join(ROOT, ".env")
    if not os.path.isfile(p):
        return ""
    try:
        inside = subprocess.run(["git", "-C", ROOT, "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, timeout=3)
        if inside.stdout.strip() != "true":
            return ""
        ignored = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", ".env"], timeout=3)
        tracked = subprocess.run(["git", "-C", ROOT, "ls-files", "--error-unmatch", ".env"], capture_output=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return ""
    if tracked.returncode == 0:
        return ".env SUDAH ter-track git! Jalankan: git rm --cached .env  lalu commit, dan GANTI API key."
    if ignored.returncode != 0:
        return ".env belum masuk .gitignore — tambahkan baris `.env` sebelum git add/push."
    return ""


def ensure_dirs():
    for d in (HOME, SESSIONS, os.path.join(HOME, "commands")):
        os.makedirs(d, mode=0o700, exist_ok=True)


def normalize_url(u):
    u = (u or "").strip().rstrip("/")
    if u and not re.search(r"/v\d+$", u):
        u += "/v1"
    return u


# Kunci yang boleh di-override oleh <proyek>/.codinx/config.json. SENGAJA tidak termasuk base_url / conv_field /
# insecure_tls / tool_policy / permission / trust_project: repo asing tidak boleh mengalihkan API key atau memberi izin.
PROJECT_KEYS = {"model", "theme", "agent", "show_details", "show_thinking", "tool_mode", "history_mode",
                "max_steps", "context_limit", "temperature"}


def load(cwd=None):
    ensure_dirs()
    cfg = copy.deepcopy(DEFAULTS)          # salinan DALAM: dict bersarang (tool_policy, permission) tidak boleh dipakai bersama
    try:
        with open(CONFIG) as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    over = {}
    try:
        with open(os.path.join(cwd or os.getcwd(), ".codinx", "config.json"), encoding="utf-8") as f:
            pdata = json.load(f)
        for k in PROJECT_KEYS:
            if k in pdata and pdata[k] != cfg.get(k):
                over[k] = (cfg.get(k), pdata[k])
                cfg[k] = pdata[k]
    except (OSError, ValueError, AttributeError):
        pass
    cfg["__proj"] = over
    before = {k: cfg.get(k) for k in ("base_url", "model", "tier", "trial_mode", "tool_mode", "history_mode", "conv_field", "conv_source", "auto_probe")}
    if env("CODINX_BASE_URL"):
        cfg["base_url"] = env("CODINX_BASE_URL")
    if env("CODINX_MODEL"):
        cfg["model"] = env("CODINX_MODEL")
    if env("CODINX_TIER"):
        cfg["tier"] = env("CODINX_TIER").lower()
    for var, k in (("CODINX_TOOL_MODE", "tool_mode"), ("CODINX_HISTORY_MODE", "history_mode"),
                   ("CODINX_CONV_FIELD", "conv_field"), ("CODINX_CONV_SOURCE", "conv_source")):
        if env(var):
            cfg[k] = env(var).lower() if k != "conv_field" else env(var)
    if env("CODINX_AUTO_PROBE"):
        cfg["auto_probe"] = env("CODINX_AUTO_PROBE").lower() not in ("0", "false", "no", "off")
    if env("CODINX_TRIAL"):
        cfg["trial_mode"] = env("CODINX_TRIAL").lower() not in ("0", "false", "no", "off")
    if cfg.get("tool_mode") not in ("auto", "native", "text", "none"):
        cfg["tool_mode"] = "auto"
    if cfg.get("history_mode") not in ("auto", "native", "flat"):
        cfg["history_mode"] = "auto"
    cfg["base_url"] = normalize_url(cfg["base_url"])
    # nilai yang berasal dari env/.env tidak boleh ikut tersimpan ke config.json (hanya berlaku selama env itu ada)
    cfg["__env"] = {k: (before[k], cfg.get(k)) for k in before if cfg.get(k) != before[k]}
    return cfg


def save(cfg):
    ensure_dirs()
    keep = {k: v for k, v in cfg.items() if k in DEFAULTS}
    for src in ("__proj", "__env"):                            # override proyek / env tidak ikut tersimpan global
        for k, (gv, ov) in (cfg.get(src) or {}).items():
            if cfg.get(k) == ov:
                keep[k] = gv
    tmp = CONFIG + ".tmp"
    with open(tmp, "w") as f:
        json.dump(keep, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, CONFIG)


def get_key():
    if env("CODINX_API_KEY"):
        return env("CODINX_API_KEY")
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
