# Berkontribusi

1. Fork & buat branch: `git checkout -b fitur/nama-singkat`.
2. Pasang hook anti-bocor: `bash scripts/install-git-hooks.sh`.
3. Jalankan test: `make test` (atau `python3 -m unittest discover -s tests -t . -v`). Semua harus hijau.
4. Tambahkan test untuk perilaku baru; perbarui `docs/` bila ada perubahan fitur/konfigurasi (`make docs` meregenerasi `COMMANDS.md`/`CONFIG.md`).
5. Pesan commit gaya Conventional Commits (`feat:`, `fix:`, `docs:` …). Jangan commit rahasia (`make scan`).
6. Buka Pull Request dengan deskripsi: apa, mengapa, cara menguji.

Gaya kode: stdlib saja (kecuali `cx/vendor`), Python >= 3.9, fungsi kecil, pesan UI dalam Bahasa Indonesia.
