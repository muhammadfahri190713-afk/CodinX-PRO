#!/usr/bin/env python3
"""Pretty-print JSON, opsional ambil kunci bersarang. Pakai: jsonpp.py file.json [a.b.c]   (atau stdin dengan '-')"""
import json
import sys


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = sys.stdin if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8")
    try:
        data = json.load(src)
    except ValueError as e:
        print(f"JSON tidak valid: {e}")
        return 1
    for key in (sys.argv[2].split(".") if len(sys.argv) > 2 else []):
        try:
            data = data[int(key)] if isinstance(data, list) else data[key]
        except (KeyError, IndexError, ValueError, TypeError):
            print(f"kunci '{key}' tidak ditemukan")
            return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
