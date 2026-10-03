# Pemberitahuan pihak ketiga

## Pygments (disertakan di `cx/vendor/pygments`)
Dipakai untuk syntax highlighting blok kode di terminal. Subset lexer disalin apa adanya (tanpa modifikasi isi lexer);
hanya `lexers/_mapping.py` dibuat ulang agar sesuai modul yang disertakan (lihat `scripts/vendor_pygments.py`).

- Proyek: https://pygments.org
- Lisensi: BSD-2-Clause — teks lengkap di `cx/vendor/PYGMENTS_LICENSE`, daftar penulis di `cx/vendor/PYGMENTS_AUTHORS`.
- Versi: lihat `cx/vendor/PYGMENTS_VERSION`.

Bila Pygments tidak bisa dimuat, CodinX otomatis jatuh ke teks polos tanpa warna sintaks.
