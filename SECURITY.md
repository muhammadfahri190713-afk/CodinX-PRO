# Kebijakan keamanan

## Melaporkan kerentanan
Jangan membuka issue publik untuk celah keamanan. Kirim laporan privat ke pemilik repo (GitHub Security Advisories) dengan langkah reproduksi.

## Model ancaman singkat
- CodinX berjalan sebagai **root**: setiap tool sensitif meminta izin; perintah destruktif (`rm -rf /`, `mkfs`, `dd of=/dev/…`, reboot) diblokir tanpa syarat.
- API key dibaca dari environment / `.env` / brankas terenkripsi `~/.codinx/.key.enc` dan **tidak pernah** ditulis ke log (disamarkan) atau konfigurasi.
- Konfigurasi dari repo asing dibatasi: `<proyek>/.codinx/config.json` tidak boleh mengubah `base_url`, izin, atau `trust_project`;
  hooks dan server MCP proyek baru dimuat bila `trust_project` diaktifkan secara eksplisit di konfigurasi global.
- Pembatasan paket/Dinar berjalan di sisi klien dan hanya bersifat panduan; penegakan sungguhan harus ada di proxy.

## Praktik untuk pengguna
`chmod 600 .env`, jangan commit `.env`, jalankan `python3 scripts/secret_scan.py .` sebelum push, dan putar key yang pernah bocor.
