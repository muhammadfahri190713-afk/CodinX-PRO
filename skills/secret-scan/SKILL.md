---
name: secret-scan
description: Memindai rahasia (API key/token/private key) sebelum push ke GitHub dan memandu rotasi.
---
# Secret scan
1. Pindai: `python3 {SKILLDIR}/scripts/secret_scan.py .` (atau `--staged` untuk yang akan di-commit). Nilai selalu disamarkan.
2. Pastikan `.env` ada di `.gitignore` dan TIDAK ter-track: `git ls-files | grep -E '(^|/)\.env$'` (harus kosong); `git check-ignore -v .env`.
3. Bila terlanjur ter-commit: `git rm --cached .env`, commit; lalu **putar (rotate) key** di penyedia — menghapus dari riwayat tidak cukup
   karena key sudah dianggap bocor (git filter-repo/BFG hanya langkah tambahan).
4. Pasang hook: `bash scripts/install-git-hooks.sh` (blokir commit berisi rahasia). Simpan contoh di `.env.example` dengan nilai palsu.
