---
name: web-check
description: Menjalankan server lokal (mis. localhost:3000) lalu memverifikasi lewat webfetch/curl.
---
# Cek aplikasi web lokal
1. Mulai server dengan `bash` background=true (mis. `npm run dev`, `python3 -m http.server 3000`).
2. Tunggu 2-5 detik, lalu `webfetch` ke `http://localhost:3000` (butuh izin `localhost`).
3. Periksa status HTTP + isi; untuk API pakai method/headers/body.
4. Jika gagal: baca log file dari hasil background, perbaiki, ulangi.
5. Setelah selesai, hentikan proses: `kill <PID>` (izin bash).
