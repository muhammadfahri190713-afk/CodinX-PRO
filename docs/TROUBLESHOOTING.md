# Pemecahan masalah

| Masalah | Solusi |
|---|---|
| Path data salah setelah memakai `su` | Jalankan sebagai user Termux biasa. Jika perlu, set `export CODINX_HOME="$HOME/.codinx"` sebelum menjalankan. |
| Agent lupa percakapan | `/doctor` (otomatis memilih mode riwayat); cek `/status` → mode riwayat; paksa `/historymode flat` |
| Skill / tool tidak jalan | `/doctor`; bila tool "tidak ada", pakai `/skill <nama>` (tidak butuh tool) dan `!perintah`; coba model lain (`/models`) |
| HTTP 401/403 | API key salah: periksa `.env`/`/connect`; `/status` → sumber API key |
| HTTP 400 aneh | `CODINX_DEBUG=1` lalu `codinx logs -n 80`; coba `/toolmode text` atau `/historymode flat` |
| "Limit harian habis" | paket FREE: 1300 Dinar/hari, reset 00:00 zona waktu (`/location`); `/tier` untuk paket lain |
| Model terkunci 🔒 | model butuh paket lebih tinggi / trial sudah habis (`/models`) |
| Zona waktu salah | isi `"timezone": "Asia/Jakarta"` di `~/.codinx/config.json` |
| Warna/garis aneh | `NO_COLOR=1` atau `--no-color`; tema lain `/theme` |
| `.env` tidak terbaca | harus di folder CodinX atau `~/.codinx/.env`, variabel berawalan `CODINX_`; cek `/status` |
| Prompt izin tak muncul di skrip | non-interaktif otomatis menolak; pakai `codinx run --auto` |
