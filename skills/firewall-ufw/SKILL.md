---
name: firewall-ufw
description: Mengatur firewall UFW dengan urutan aman agar SSH tidak terputus.
---
# UFW
Urutan WAJIB: izinkan SSH dulu -> baru aktifkan.
```
ufw status verbose
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp          # atau port SSH kamu
ufw allow 80,443/tcp      # bila web
ufw --force enable
ufw status numbered
```
Hapus aturan: `ufw delete <nomor>`. Batasi brute force: `ufw limit 22/tcp`.
Docker melewati UFW untuk port yang dipublikasikan — periksa `iptables -S DOCKER-USER`. Jangan `ufw reset` tanpa izin eksplisit.
