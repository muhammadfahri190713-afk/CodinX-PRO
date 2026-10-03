---
name: security-audit
description: Audit keamanan kode/server: injeksi, secret, izin, dependensi, konfigurasi; laporan berseverity.
---
# Audit keamanan
Cakupan: (1) secret di kode/riwayat git -> skill `secret-scan`; (2) injeksi: shell (`shell=True`, backtick), SQL, path traversal, XSS;
(3) autentikasi/otorisasi & CORS/CSRF; (4) izin file (`find / -xdev -perm -0002 -type f` untuk world-writable) dan SUID tak wajar;
(5) dependensi usang/rentan (`pip list --outdated`, `npm audit`); (6) konfigurasi layanan (SSH, Nginx, Docker socket terbuka).
Laporan tabel `| severity | lokasi | temuan | perbaikan |`. Jangan mencetak secret utuh. Jangan "memperbaiki" otomatis hal berisiko tanpa izin.
