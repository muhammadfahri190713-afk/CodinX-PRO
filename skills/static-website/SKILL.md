---
name: static-website
description: Membuat situs statis (HTML/CSS/JS) responsif dan mengujinya di localhost.
---
# Situs statis
- File: `index.html`, `style.css`, `app.js`; pakai `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- CSS: variabel `:root`, flex/grid, mobile-first, `@media (prefers-color-scheme: dark)`.
- Aksesibilitas: `alt` gambar, label form, kontras cukup, fokus terlihat, urutan heading logis.
- Jalankan: `bash {SKILLDIR}/scripts/serve.sh 8080` lalu `webfetch http://localhost:8080` (izin localhost).
- Tanpa dependensi eksternal bila bisa (CDN = titik gagal & privasi). Validasi HTML dengan membaca hasil webfetch.
