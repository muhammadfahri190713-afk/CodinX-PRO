---
name: documentation-writer
description: Menulis README, docstring, dan panduan yang akurat berdasarkan kode nyata.
---
# Dokumentasi
- README: apa itu (1 kalimat), instalasi, contoh pakai yang BENAR-BENAR dijalankan, konfigurasi (tabel env/opsi), pengujian, lisensi.
- Verifikasi tiap perintah di dokumen dengan menjalankannya; jangan menulis fitur yang tidak ada di kode.
- Docstring: apa & mengapa (bukan mengulang kode), parameter, return, error, contoh singkat.
- Catatan keputusan (ADR): konteks, keputusan, konsekuensi — 1 halaman.
- Bahasa & gaya mengikuti dokumen yang sudah ada. Gunakan sub-agent `doc-writer` untuk dokumentasi besar.
