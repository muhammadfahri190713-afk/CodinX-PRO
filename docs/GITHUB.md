# Mempublikasikan ke GitHub dengan aman

1. `.env` berisi key asli dan **sudah di `.gitignore`**; yang di-commit hanya `.env.example` (nilai palsu).
2. Pasang pemindai: `bash scripts/install-git-hooks.sh` (blokir commit berisi rahasia) dan jalankan `python3 scripts/secret_scan.py .`.
3. Cek sebelum commit: `git status --short` — tidak boleh ada `.env`, `.seed`, `*.enc`. Verifikasi: `git check-ignore -v .env`.
4. Buat repo **private** dulu: `gh repo create <nama> --private --source=. --push` (atau `git remote add origin …`).
5. CI (`.github/workflows/ci.yml`) menjalankan test + pemindai rahasia pada tiap push.
6. Pengguna lain: `cp .env.example .env`, isi key milik **mereka** sendiri (jangan berbagi key Anda).
7. Bila key pernah ter-commit/ter-push: anggap bocor → **rotate** di penyedia, lalu `git rm --cached .env`.
