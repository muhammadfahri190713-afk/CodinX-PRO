"""Skills (SKILL.md + frontmatter), progressive disclosure: hanya nama+deskripsi masuk prompt."""
import os
import re

from . import config

PKG_SKILLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")


def roots(cwd):
    return [PKG_SKILLS, os.path.join(config.HOME, "skills"), os.path.join(cwd, ".codinx", "skills")]


def parse(text):
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        for ln in m.group(1).splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                meta[k.strip().lower()] = v.strip().strip("'\"")
        body = m.group(2)
    return meta, body


def discover(cwd):
    found = {}
    for root in roots(cwd):
        if not os.path.isdir(root):
            continue
        for d in sorted(os.listdir(root)):
            f = os.path.join(root, d, "SKILL.md")
            if os.path.isfile(f):
                try:
                    with open(f, encoding="utf-8") as fh:
                        meta, _ = parse(fh.read())
                except OSError:
                    continue
                name = meta.get("name") or d
                found[name] = {"name": name, "description": meta.get("description", ""), "path": f, "dir": os.path.join(root, d)}
    return found


def load(name, cwd):
    sk = discover(cwd).get(name)
    if not sk:
        return None
    with open(sk["path"], encoding="utf-8") as fh:
        _, body = parse(fh.read())
    body = body.replace("{SKILLDIR}", sk["dir"])          # skrip pendukung dirujuk lewat path absolut
    extra = [x for x in sorted(os.listdir(sk["dir"])) if x != "SKILL.md"]
    tail = ("\n\n[File pendukung di %s: %s]" % (sk["dir"], ", ".join(extra))) if extra else ""
    return body.strip() + tail


def index_block(cwd):
    sk = discover(cwd)
    if not sk:
        return ""
    return "\n".join(f"- {s['name']}: {s['description']}" for s in sk.values())


# ---------------------------------------------------------------- resolve + pencocokan otomatis
STOP = set("""yang dan dengan untuk dari pada atau ini itu saya aku kamu tolong bisa mau akan agar supaya
the and for with that this from into your you please can will make buat bikin jalankan jalanin lakukan kerjakan
file kode code proyek project secara lalu setelah sebelum juga lebih sudah belum harus dalam atas oleh""".split())
SYN = {"tabel": ["table"], "kamera": ["camera"], "foto": ["camera"], "cek": ["check"], "periksa": ["check"],
       "bug": ["debug", "fix"], "perbaiki": ["fix", "debug"], "error": ["debug", "fix"], "galat": ["debug"],
       "ulas": ["review"], "commit": ["git"], "cabang": ["git"], "laporan": ["report", "data"],
       "kerangka": ["scaffold", "project"], "proyek": ["project"], "situs": ["web"], "website": ["web"]}


def resolve(name, cwd, exact=False):
    found = discover(cwd)
    n = (name or "").strip().lower()
    for k, v in found.items():
        if k.lower() == n:
            return v
    if exact or not n:
        return None
    pref = [v for k, v in found.items() if k.lower().startswith(n)]
    return pref[0] if len(pref) == 1 else None


def _toks(s):
    return {w for w in re.findall(r"[a-zA-Z]{3,}", (s or "").lower()) if w not in STOP}


def match(text, cwd):
    """-> [(skor, skill)] terurut. Nama skill berbobot 2, kata deskripsi berbobot 1."""
    q = set()
    for w in _toks(text):
        q.add(w)
        q.update(SYN.get(w, []))
    out = []
    for sk in discover(cwd).values():
        name_t = set(re.split(r"[-_ ]+", sk["name"].lower()))
        desc_t = _toks(sk["description"])
        score = 2 * len(q & name_t) + len(q & (desc_t - name_t))
        if score:
            out.append((score, sk))
    return sorted(out, key=lambda x: -x[0])
