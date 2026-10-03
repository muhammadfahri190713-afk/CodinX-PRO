---
name: log-analysis
description: Menganalisis log: error teratas, pola waktu, korelasi; dengan skrip ringkasan.
---
# Analisis log
1. Cari file: `ls -lhS /var/log | head`, `journalctl --disk-usage`.
2. Ringkas error teratas dengan skrip bawaan: `python3 {SKILLDIR}/scripts/top_errors.py /var/log/<file> -n 15`.
3. Lacak waktu: `grep -n 'ERROR' file | head`, lalu lihat konteks `sed -n '<a>,<b>p' file`.
4. Korelasikan antar-layanan menurut timestamp; cari kejadian pertama (akar), bukan yang paling sering.
5. Laporkan: kronologi singkat, penyebab paling mungkin, bukti (baris log), saran.
Jangan menyalin data sensitif (token, email) ke laporan; samarkan.
