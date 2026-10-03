"""Memori jangka panjang (global + per-proyek), disuntik ke system prompt + penangkapan otomatis."""
import json
import os
import re
import time

from . import config

MEM_FILE = os.path.join(config.HOME, "memory.json")

_REMEMBER = re.compile(
    r"^\s*(?:tolong\s+|please\s+)?(?:ingat(?:lah)?|simpan|catat|jangan\s+lupa|remember)"
    r"(?:\s+(?:bahwa|ya|ini|that))?\s*[:,]?\s+(.{4,400})$", re.I | re.S)
_NAME = re.compile(
    r"(?i:\b(?:nama\s+(?:saya|aku)|namaku|panggil\s+(?:saya|aku))\s+(?:adalah\s+|itu\s+)?)"
    r"([A-Za-z][\w'\-]{1,30}(?:\s+[A-Z][\w'\-]{1,30})?)")


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
    """Tambah ingatan. Teks yang sama (tanpa beda huruf besar/kecil) tidak diduplikasi."""
    text = " ".join(text.split())
    items = load()
    for i in items:
        if i["text"].casefold() == text.casefold() and i["scope"] == scope:
            return i["id"]
    nid = (max([i["id"] for i in items]) + 1) if items else 1
    items.append({"id": nid, "text": text, "scope": scope, "cwd": cwd if scope == "project" else "", "time": int(time.time())})
    _save(items)
    return nid


def remove(mem_id):
    items = load()
    keep = [i for i in items if i["id"] != int(mem_id)]
    _save(keep)
    return len(items) - len(keep)


def clear():
    _save([])


def relevant(cwd, query=""):
    items = [i for i in load() if i["scope"] == "global" or i.get("cwd") == cwd]
    if query:
        q = query.casefold()
        items = [i for i in items if q in i["text"].casefold()]
    return items


def prompt_block(cwd, limit=3500):
    items = relevant(cwd)
    if not items:
        return ""
    text = "\n".join(f"- [{i['id']}] ({i['scope']}) {i['text']}" for i in items)
    return text[-limit:] if len(text) > limit else text


def auto_capture(text, cwd=""):
    """Tangkap fakta eksplisit dari ucapan user ('ingat bahwa ...', 'nama saya ...'). -> daftar fakta baru."""
    if text.startswith("[SKILL AKTIF"):
        return []
    facts = []
    m = _REMEMBER.match(text)
    if m:
        facts.append(" ".join(m.group(1).split()).rstrip("."))
    n = _NAME.search(text)
    if n:
        facts.append("Nama user: " + n.group(1).strip())
    new = []
    before = {i["text"].casefold() for i in load()}
    for f in facts:
        if f.casefold() not in before:
            add(f, "global", cwd)
            new.append(f)
    return new
