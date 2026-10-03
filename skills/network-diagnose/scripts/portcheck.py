#!/usr/bin/env python3
"""Cek koneksi TCP ke daftar host:port. Pakai: portcheck.py host:port [host:port ...] [-t detik]"""
import argparse
import socket
import time


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("targets", nargs="+")
    ap.add_argument("-t", type=float, default=3.0)
    a = ap.parse_args()
    bad = 0
    for t in a.targets:
        host, _, port = t.rpartition(":")
        t0 = time.time()
        try:
            with socket.create_connection((host or "127.0.0.1", int(port)), timeout=a.t):
                print(f"OK     {t}  ({(time.time() - t0) * 1000:.0f} ms)")
        except (OSError, ValueError) as e:
            bad += 1
            print(f"GAGAL  {t}  ({e})")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
