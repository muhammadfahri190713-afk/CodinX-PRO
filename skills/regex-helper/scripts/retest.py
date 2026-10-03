#!/usr/bin/env python3
"""Uji regex: retest.py PATTERN [teks ...] [-f file] [-i]  — tampilkan cocok/tidak + grup."""
import argparse
import re
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pattern")
    ap.add_argument("texts", nargs="*")
    ap.add_argument("-f", "--file")
    ap.add_argument("-i", action="store_true", help="abaikan huruf besar/kecil")
    a = ap.parse_args()
    try:
        rx = re.compile(a.pattern, re.I if a.i else 0)
    except re.error as e:
        print(f"regex tidak valid: {e}")
        return 2
    lines = list(a.texts)
    if a.file:
        with open(a.file, errors="replace") as f:
            lines += f.read().splitlines()
    ok = 0
    for t in lines:
        m = rx.search(t)
        ok += bool(m)
        print(("COCOK  " if m else "tidak  ") + repr(t) + (f"  -> {m.group(0)!r} grup={m.groups()}" if m else ""))
    print(f"{ok}/{len(lines)} cocok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
