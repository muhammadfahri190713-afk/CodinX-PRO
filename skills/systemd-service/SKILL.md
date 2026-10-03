---
name: systemd-service
description: Membuat, mengaktifkan, dan men-debug unit systemd untuk aplikasi.
---
# Unit systemd
Template `/etc/systemd/system/<nama>.service`:
```ini
[Unit]
Description=<deskripsi>
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/<nama>
EnvironmentFile=-/etc/<nama>.env
ExecStart=/usr/bin/python3 /opt/<nama>/app.py
Restart=on-failure
RestartSec=3
User=<user-non-root>

[Install]
WantedBy=multi-user.target
```
Langkah: tulis file -> `systemd-analyze verify /etc/systemd/system/<nama>.service` -> `systemctl daemon-reload` ->
`systemctl enable --now <nama>` -> `systemctl status <nama> --no-pager` -> `journalctl -u <nama> -n 50 --no-pager`.
Jalankan sebagai user non-root bila memungkinkan; simpan secret di EnvironmentFile (chmod 600), bukan di ExecStart.
