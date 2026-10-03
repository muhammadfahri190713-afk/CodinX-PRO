---
name: network-diagnose
description: Diagnosis jaringan: DNS, port, rute, firewall, layanan yang mendengarkan.
---
# Diagnosis jaringan
1. Layanan mendengarkan: `ss -ltnp`. Antarmuka/IP: `ip -br a`, rute: `ip r`.
2. DNS: `getent hosts contoh.com`, `dig +short contoh.com` (jika ada).
3. Port jarak jauh: `python3 {SKILLDIR}/scripts/portcheck.py contoh.com:443 127.0.0.1:3000`.
4. HTTP: `curl -sS -o /dev/null -w '%{http_code} %{time_total}s\n' https://contoh.com`.
5. Firewall: `ufw status verbose` / `iptables -S`. Jejak: `traceroute -n host` atau `mtr -rwc 5 host`.
Urutan menyempit: DNS -> TCP connect -> TLS -> HTTP -> aplikasi. Laporkan lapisan pertama yang gagal.
