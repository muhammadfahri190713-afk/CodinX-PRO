#!/usr/bin/env bash
# Pemakai disk terbesar di bawah sebuah direktori (baca-saja). Pakai: du_top.sh [dir=/] [jumlah=15]
set -u
dir="${1:-/}"; n="${2:-15}"
du -xh --max-depth=1 "$dir" 2>/dev/null | sort -rh | head -n "$n"
