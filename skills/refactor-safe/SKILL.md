---
name: refactor-safe
description: Refactor tanpa mengubah perilaku: kunci dengan test, langkah kecil, verifikasi tiap langkah.
---
# Refactor aman
1. Pastikan ada test yang menangkap perilaku sekarang (skill `python-testing`); bila tidak ada, tulis test karakterisasi dulu.
2. Jalankan test: harus hijau SEBELUM mulai.
3. Satu perubahan kecil per langkah (rename, extract function, hapus duplikasi), jalankan test tiap langkah; commit/`/undo` mudah bila gagal.
4. Jangan campur refactor dengan perubahan fitur/perbaikan bug.
5. Akhiri dengan `git diff --stat` dan ringkasan: apa yang berubah, apa yang sengaja tidak.
