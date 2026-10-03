"""Location -> timezone, so the daily Dinar reset happens at the user's local midnight."""
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta

from . import config

GEO_FILE = os.path.join(config.HOME, "geo.json")


def _system_tz():
    try:
        with open("/etc/timezone") as f:
            v = f.read().strip()
        if v:
            return v
    except OSError:
        pass
    try:
        p = os.path.realpath("/etc/localtime")
        i = p.find("zoneinfo/")
        if i >= 0:
            return p[i + 9:]
    except OSError:
        pass
    return ""


def _read_cache():
    try:
        with open(GEO_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def lookup(force=False, timeout=3):
    """Province/city/timezone from the public IP (ipwho.is), cached 24h. Falls back to system tz."""
    cached = _read_cache()
    if cached and not force and time.time() - cached.get("ts", 0) < 86400:
        return cached
    info = None
    try:
        req = urllib.request.Request("https://ipwho.is/", headers={"User-Agent": "CodinX"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
        if d.get("success", True) and d.get("timezone", {}).get("id"):
            info = {"province": d.get("region", ""), "city": d.get("city", ""),
                    "country": d.get("country", ""), "tz": d["timezone"]["id"], "source": "ip"}
    except Exception:
        pass
    if info is None:
        if cached:
            return cached
        info = {"province": "", "city": "", "country": "", "tz": _system_tz() or "UTC", "source": "system"}
    info["ts"] = time.time()
    try:
        with open(GEO_FILE, "w") as f:
            json.dump(info, f)
        os.chmod(GEO_FILE, 0o600)
    except OSError:
        pass
    return info


def tz_name(cfg):
    return cfg.get("timezone") or lookup().get("tz") or "UTC"


def now(cfg):
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz_name(cfg)))
    except Exception:
        return datetime.now().astimezone()


def day_key(cfg):
    return now(cfg).strftime("%Y-%m-%d")


def next_reset(cfg):
    n = now(cfg)
    return (n + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def remaining_str(cfg):
    secs = int((next_reset(cfg) - now(cfg)).total_seconds())
    return f"{secs // 3600}j {secs % 3600 // 60}m"
