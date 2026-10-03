---
name: performance-profile
description: Mengukur dan mengoptimalkan performa: profiling, hot path, benchmark sebelum/sesudah.
---
# Performa
1. Ukur dulu, jangan menebak: `time <cmd>`; Python `python3 -X importtime`, `python3 -m cProfile -s cumtime script.py | head -30`.
2. Temukan hot path (fungsi dengan cumtime terbesar), perbaiki satu per satu: algoritma/struktur data -> I/O batching -> caching -> baru mikro-optimasi.
3. Benchmark berulang (min dari beberapa run) sebelum & sesudah; laporkan dalam tabel `| skenario | sebelum | sesudah | selisih |`.
4. Pastikan hasil tetap benar (jalankan test). Optimasi tanpa bukti ukur tidak diterima.
