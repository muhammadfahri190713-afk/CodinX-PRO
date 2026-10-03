---
name: dependency-update
description: Memperbarui dependensi dengan aman: audit, naikkan bertahap, uji, lockfile.
---
# Update dependensi
1. Lihat yang usang: `pip list --outdated` / `npm outdated`. Audit: `pip-audit` (jika ada) / `npm audit`.
2. Naikkan bertahap: patch -> minor -> major (baca changelog major). Satu kelompok per commit.
3. Setelah tiap langkah: install bersih, jalankan test & build. Perbarui lockfile (`package-lock.json`, `requirements.txt` pin).
4. Jika gagal, kembalikan ke versi sebelumnya dan catat penyebab. Jangan `npm audit fix --force` tanpa izin (bisa melompat major).
