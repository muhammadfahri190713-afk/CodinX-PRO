"""Paket FREE / PRO / MAX, katalog model, trial, dan limit harian Dinar (user FREE)."""
import json
import math
import os

from . import config, geo

ORDER = {"FREE": 0, "PRO": 1, "MAX": 2}
DAILY_LIMIT = 1300      # Dinar per hari untuk user FREE
DINAR_PER_REQUEST = 65  # 1 request = 65 Dinar  (=> 20 request/hari)
USAGE_FILE = os.path.join(config.HOME, "usage.json")
CATALOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models.json")

_catalog = None


def catalog():
    global _catalog
    if _catalog is None:
        try:
            with open(CATALOG_FILE, encoding="utf-8") as f:
                _catalog = json.load(f)
        except (OSError, ValueError):
            _catalog = []
    return _catalog


def find(model_id):
    for m in catalog():
        if m["id"] == model_id:
            return m
    return None


def trial_mode(cfg):
    """Masa uji coba: SEMUA model gratis (tanpa kunci paket, tanpa uji-coba terbatas, Dinar tidak dipotong)."""
    return bool(cfg.get("trial_mode", True))


def plan_label(cfg):
    return "UJI COBA · semua model gratis" if trial_mode(cfg) else tier_of(cfg)


def tier_of(cfg):
    t = str(cfg.get("tier", "free")).upper()
    return t if t in ORDER else "FREE"


def _load_usage(cfg):
    day = geo.day_key(cfg)
    try:
        with open(USAGE_FILE) as f:
            u = json.load(f)
    except (OSError, ValueError):
        u = {}
    u.setdefault("trials", {})
    if u.get("day") != day:      # reset tengah malam waktu setempat
        u["day"] = day
        u["dinar"] = 0
        u["requests"] = 0
    u.setdefault("dinar", 0)
    u.setdefault("requests", 0)
    return u


def _save_usage(u):
    config.ensure_dirs()
    with open(USAGE_FILE, "w") as f:
        json.dump(u, f)
    os.chmod(USAGE_FILE, 0o600)


def status(cfg):
    u = _load_usage(cfg)
    return {"tier": tier_of(cfg), "trial": trial_mode(cfg), "dinar": u["dinar"], "limit": DAILY_LIMIT, "requests": u["requests"],
            "trials": u["trials"], "reset_in": geo.remaining_str(cfg)}


def can_use_model(cfg, model_id):
    """(allowed, via_trial, message)."""
    if trial_mode(cfg):
        return True, False, ""
    m = find(model_id)
    role = m["role"] if m else "FREE"
    tier = tier_of(cfg)
    if ORDER[role] <= ORDER[tier]:
        return True, False, ""
    if m and m.get("trial") and tier == "FREE":
        used = _load_usage(cfg)["trials"].get(model_id, 0)
        if used < m["trial"]:
            return True, True, f"uji coba {used + 1}/{m['trial']} untuk {m['name']}"
        return False, False, f"Uji coba {m['name']} sudah habis ({m['trial']} request). Butuh paket {role}."
    return False, False, f"Model {m['name'] if m else model_id} butuh paket {role}. Paket kamu: {tier}. Ubah dengan /tier."


def precheck(cfg, model_id):
    """Dipanggil sebelum setiap request ke API. Returns (ok, via_trial, message)."""
    ok, via_trial, msg = can_use_model(cfg, model_id)
    if not ok:
        return False, False, msg
    if tier_of(cfg) == "FREE" and not trial_mode(cfg):
        u = _load_usage(cfg)
        if u["dinar"] + DINAR_PER_REQUEST > DAILY_LIMIT:
            return False, False, (f"Limit harian habis ({u['dinar']}/{DAILY_LIMIT} Dinar). "
                                  f"Reset jam 00:00 ({geo.tz_name(cfg)}) dalam {geo.remaining_str(cfg)}.")
    return True, via_trial, msg


def record(cfg, model_id, tokens, via_trial):
    """Catat pemakaian. 1 request = 65 Dinar, tiap kelipatan `dinar_token_unit` token menambah 1 request."""
    u = _load_usage(cfg)
    if trial_mode(cfg):                                  # gratis: hanya hitung jumlah request
        u["requests"] += 1
        _save_usage(u)
        return 0
    units = max(1, math.ceil(max(tokens, 1) / max(int(cfg.get("dinar_token_unit", 8000)), 1)))
    if tier_of(cfg) == "FREE":
        u["dinar"] += DINAR_PER_REQUEST * units
    u["requests"] += 1
    if via_trial:
        u["trials"][model_id] = u["trials"].get(model_id, 0) + 1
    _save_usage(u)
    return DINAR_PER_REQUEST * units
