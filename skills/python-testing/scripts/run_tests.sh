#!/usr/bin/env bash
# Jalankan test proyek Python: pytest bila ada, jika tidak unittest. Pakai: run_tests.sh [argumen tambahan]
set -u
if python3 -c "import pytest" 2>/dev/null; then
  exec python3 -m pytest -q "$@"
elif [ -d tests ]; then
  exec python3 -m unittest discover -s tests -v "$@"
else
  echo "Tidak menemukan pytest maupun folder tests/." >&2; exit 2
fi
