---
name: regex-helper
description: Menyusun dan menguji regex dengan contoh nyata menggunakan skrip penguji.
---
# Regex
1. Kumpulkan contoh cocok & tidak cocok dari user.
2. Uji cepat: `python3 {SKILLDIR}/scripts/retest.py '<regex>' 'teks 1' 'teks 2'` (atau `-f file`); tampilkan grup tertangkap.
3. Iterasi: mulai sederhana, tambah jangkar `^$` / `\b`, hindari `.*` serakah (pakai `.*?` atau kelas karakter), waspadai backtracking katastrofik.
4. Tulis hasil akhir lengkap dengan flag, penjelasan per bagian, dan 3+ contoh uji.
Regex bukan parser: untuk HTML/JSON/CSV gunakan parser sungguhan.
