---
name: code-review
description: Review kode terstruktur: bug, keamanan, performa, keterbacaan, test.
---
# Review
Periksa `git diff` (atau file yang ditunjuk). Laporkan sebagai tabel: | severity | lokasi | masalah | saran |.
Urutan prioritas: kebenaran/bug -> keamanan (injeksi, secret, path traversal) -> error handling -> performa -> gaya.
Sebut `path:baris`. Puji hal yang sudah baik secara singkat. Jangan mengubah file kecuali diminta.
