#!/usr/bin/env python3
"""Ringkas baris error teratas dari log (angka/uuid/timestamp dinormalisasi agar baris serupa terhitung sama)."""
import argparse, collections, re, sys

LEVEL = re.compile(r"\b(ERROR|CRITICAL|FATAL|Exception|Traceback|panic|failed|denied|timeout)\b", re.I)
NORMS = [(re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<ts>"),
         (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<uuid>"),
         (re.compile(r"\b0x[0-9a-f]+\b", re.I), "<hex>"), (re.compile(r"\b\d+\b"), "<n>")]


def norm(line):
    for rx, rep in NORMS:
        line = rx.sub(rep, line)
    return " ".join(line.split())[:200]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("-n", type=int, default=10)
    a = ap.parse_args()
    cnt, total = collections.Counter(), 0
    for f in a.files:
        try:
            with open(f, errors="replace") as fh:
                for line in fh:
                    total += 1
                    if LEVEL.search(line):
                        cnt[norm(line)] += 1
        except OSError as e:
            print(f"! {f}: {e}", file=sys.stderr)
    print(f"{total} baris dibaca, {sum(cnt.values())} baris bermasalah, {len(cnt)} pola unik")
    for msg, n in cnt.most_common(a.n):
        print(f"{n:>6}  {msg}")


if __name__ == "__main__":
    main()
