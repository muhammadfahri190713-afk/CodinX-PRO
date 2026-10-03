---
name: github-publish
description: Mempublikasikan proyek ke GitHub dengan aman: .gitignore, tanpa secret, remote, push, CI.
---
# Publish ke GitHub
1. Cek rahasia: skill `secret-scan` (harus bersih). `.env` di `.gitignore`; sediakan `.env.example`.
2. `git init -b main` (jika belum) -> `git add -A` -> `git status --short` (pastikan TIDAK ada `.env`/`.seed`/`*.enc`) -> `git commit -m "feat: rilis awal"`.
3. Remote: `gh repo create <nama> --private --source=. --remote=origin --push` (butuh `gh auth login`), atau buat repo di web lalu
   `git remote add origin git@github.com:<user>/<repo>.git && git push -u origin main`. Mulai dengan **private**; publikkan setelah audit.
4. CI: `.github/workflows/ci.yml` menjalankan test + secret scan. Tambahkan LICENSE dan README.
5. Bila key pernah ter-commit: anggap bocor — rotate segera (lihat `secret-scan`).
