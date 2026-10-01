"""Memori jangka panjang (global + per-proyek). Disuntik ke system prompt tiap sesi."""
import json
import os
import time

from . import config

MEM_FILE = os.path.join(config.HOME, "memory.json")


def load():
    try:
        with open(MEM_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(items):
    config.ensure_dirs()
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.chmod(MEM_FILE, 0o600)


def add(text, scope="global", cwd=""):
    items = load()
    nid = (max([i["id"] for i in items]) + 1) if items else 1
    items.append({"id": nid, "text": text.strip(), "scope": scope, "cwd": cwd if scope == "project" else "",
                  "time": int(time.time())})
    _save(items)
    return nid


def remove(mem_id):
    items = load()
    keep = [i for i in items if i["id"] != int(mem_id)]
    _save(keep)
    return len(items) - len(keep)


def clear():
    _save([])


def relevant(cwd):
    return [i for i in load() if i["scope"] == "global" or i.get("cwd") == cwd]


def prompt_block(cwd, limit=3500):
    items = relevant(cwd)
    if not items:
        return ""
    lines = [f"- [{i['id']}] ({i['scope']}) {i['text']}" for i in items]
    text = "\n".join(lines)
    return text[-limit:] if len(text) > limit else text
