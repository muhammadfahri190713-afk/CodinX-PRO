---
name: linux-troubleshoot
description: Diagnosis server Linux sistematis: CPU, memori, disk, service gagal, log, jaringan.
---
# Troubleshoot Linux
Urutan baca-saja (aman, tanpa mengubah sistem):
1. Ringkasan: `uptime`, `free -h`, `df -hT`, `ps aux --sort=-%cpu | head`, `ps aux --sort=-%mem | head`.
2. Service gagal: `systemctl --failed`, lalu `systemctl status <svc> --no-pager -l` dan `journalctl -u <svc> -n 100 --no-pager`.
3. Kernel/OOM/disk: `dmesg -T | tail -50`, `journalctl -p err -b --no-pager | tail -50`.
4. Disk penuh: skill `disk-cleanup`. Jaringan: skill `network-diagnose`. Log: skill `log-analysis`.
5. Laporkan sebagai tabel `| gejala | bukti (perintah+keluaran singkat) | dugaan penyebab | perbaikan |`.
Perbaikan yang mengubah sistem (restart service, hapus file, ubah config) HARUS dijelaskan dulu dan memakai izin; backup config sebelum diubah.
