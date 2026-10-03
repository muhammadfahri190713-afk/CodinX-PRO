#!/usr/bin/env python3
"""Bangun rilis zip yang deterministik & aman: tanpa rahasia (.env/.seed/*.enc), tanpa __pycache__/.git, mode file benar.

  python3 scripts/build_zip.py --out dist/CodinX.zip [--prefix CodinX]
"""
import argparse
import os
import stat
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"__pycache__", ".git", ".codinx", "dist", ".pytest_cache", "node_modules"}
SKIP_FILES = {".env", ".seed", ".key.enc", ".DS_Store"}
SKIP_SUFFIX = (".pyc", ".pyo", ".log", ".tmp", ".enc")
STAMP = (2026, 10, 2, 0, 0, 0)


def files():
    out = []
    for r, dirs, fs in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(fs):
            if f in SKIP_FILES or f.endswith(SKIP_SUFFIX):
                continue
            if f.startswith(".env.") and f != ".env.example":
                continue
            out.append(os.path.join(r, f))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "CodinX.zip"))
    ap.add_argument("--prefix", default="CodinX")
    ap.add_argument("--no-scan", action="store_true")
    a = ap.parse_args()
    if not a.no_scan:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "secret_scan.py"), ROOT], capture_output=True, text=True)
        if r.returncode:
            print(r.stdout + r.stderr)
            print("✗ build dibatalkan: ada rahasia terdeteksi.")
            return 1
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    n = 0
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files():
            rel = os.path.relpath(p, ROOT)
            zi = zipfile.ZipInfo(os.path.join(a.prefix, rel).replace(os.sep, "/"), STAMP)
            zi.compress_type = zipfile.ZIP_DEFLATED
            exe = os.stat(p).st_mode & stat.S_IXUSR
            zi.external_attr = ((0o755 if exe else 0o644) | stat.S_IFREG) << 16
            with open(p, "rb") as fh:
                z.writestr(zi, fh.read(), compresslevel=9)
            n += 1
    size = os.path.getsize(a.out)
    print(f"✓ {a.out}: {n} file, {size / 1e6:.2f} MB ({size} byte)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
