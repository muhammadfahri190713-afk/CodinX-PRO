---
name: table-maker
description: Menampilkan data sebagai tabel berwarna dan menyimpannya ke .csv/.md/.json lewat tool table.
---
# Tabel
- Tampilkan tabel ke user dengan tool `table` (columns, rows, title). Isi `save_as` (mis. `laporan.csv`) bila user ingin file.
- Data dari file: baca dengan `read`/`bash` (mis. `python3 -c`), rapikan, lalu panggil `table`.
- Batasi tampilan <=30 baris; sisanya simpan ke file dan beri tahu path-nya.
- Kolom angka: konsisten desimalnya; tanggal: YYYY-MM-DD.
