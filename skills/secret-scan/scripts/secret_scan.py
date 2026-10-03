#!/usr/bin/env python3
"""Pindai rahasia (API key, token, private key) sebelum kamu push ke GitHub. Exit 1 bila ada temuan.

  python3 scripts/secret_scan.py [path ...]      # pindai folder/file (default: folder saat ini)
  python3 scripts/secret_scan.py --staged        # hanya file yang di-stage git (dipakai pre-commit)
Nilai yang ditemukan SELALU disamarkan di keluaran. Folder tests/, vendor/, node_modules/, .git/ dilewati.
"""
import argparse
import os
import re
import subprocess
import sys

PATTERNS = [
    ("Anthropic key", r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    ("API key bergaya sk-", r"\bsk-[A-Za-z0-9_\-]{20,}"),
    ("AWS access key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    ("Slack token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    ("Google API key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("Private key", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    ("JWT", r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    # nama variabel mengandung kata kunci (DB_PASSWORD, secret_token, AWS_SECRET_ACCESS_KEY, ...) dan nilai acak (>=16 char, ada angka)
    ("Assignment rahasia", r"(?i)(?:api[_-]?key|secret|token|passwd|password|private[_-]?key|access[_-]?key)[A-Za-z0-9_]*[\"']?\s*[:=]\s*[\"']?(?=[A-Za-z0-9_\-\./+=]*\d)[A-Za-z0-9_\-\./+=]{16,}"),
]
ALLOW = ("isi_api_key", "your_", "your-", "example", "xxxx", "changeme", "placeholder", "<", "dummy", "contoh", "redacted",
         "secret_scan.py", "test-key", "testkey")
# tests/ dilewati: fixture di sana sengaja berisi kunci palsu. vendor/ = kode pihak ketiga.
SKIP_DIRS = {".git", "node_modules", "__pycache__", "vendor", ".venv", "venv", "dist", "tests"}
SECRET_FILES = (".env", ".seed", ".key.enc")


def mask(s):
    return s[:4] + "…(" + str(len(s)) + " char)"


def scan_text(text, name):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(a in low for a in ALLOW):
            continue
        for label, rx in PATTERNS:
            m = re.search(rx, line)
            if m:
                hits.append((name, i, label, mask(m.group(0))))
                break
    return hits


def scan_file(path):
    try:
        if os.path.getsize(path) > 1_000_000:
            return []
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return []
    if b"\0" in raw[:2048]:
        return []
    return scan_text(raw.decode("utf-8", "replace"), path)


def walk(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                yield os.path.join(root, f)


def staged():
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], capture_output=True, text=True)
    hits = []
    for name in out.stdout.split():
        if any(part in SKIP_DIRS for part in name.split("/")[:-1]) and os.path.basename(name) not in SECRET_FILES:
            continue
        if os.path.basename(name) in SECRET_FILES or os.path.basename(name).startswith(".env.") and not name.endswith(".example"):
            hits.append((name, 0, "File rahasia di-stage", os.path.basename(name)))
            continue
        blob = subprocess.run(["git", "show", ":" + name], capture_output=True)
        if b"\0" not in blob.stdout[:2048]:
            hits += scan_text(blob.stdout.decode("utf-8", "replace"), name)
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--staged", action="store_true")
    a = ap.parse_args()
    if a.staged:
        hits = staged()
    else:
        hits = []
        for f in walk(a.paths):
            hits += scan_file(f)
    for name, line, label, val in hits:
        print(f"{name}:{line}: {label}: {val}")
    if hits:
        print(f"\n✗ {len(hits)} temuan. Hapus/ganti, pindahkan ke .env (yang di-ignore), dan putar (rotate) key yang sudah terlanjur bocor.")
        return 1
    print("✓ tidak ada rahasia terdeteksi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
