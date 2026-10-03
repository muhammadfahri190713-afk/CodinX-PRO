---
name: ssl-letsencrypt
description: Memasang sertifikat HTTPS gratis dengan certbot dan memastikan pembaruan otomatis.
---
# Let's Encrypt
Prasyarat: DNS A/AAAA mengarah ke server, port 80/443 terbuka (skill `firewall-ufw`), Nginx sudah melayani domain (skill `nginx-setup`).
1. `apt-get install -y certbot python3-certbot-nginx`
2. Uji dulu: `certbot --nginx -d contoh.com -d www.contoh.com --dry-run`
3. Terbitkan: `certbot --nginx -d contoh.com -d www.contoh.com --redirect -m <email> --agree-tos -n`
4. Pembaruan: `systemctl list-timers | grep certbot`, uji `certbot renew --dry-run`.
5. Verifikasi: `curl -I https://contoh.com`, `echo | openssl s_client -connect contoh.com:443 -servername contoh.com 2>/dev/null | openssl x509 -noout -dates`.
Batas laju LE ketat — gunakan `--dry-run`/`--staging` saat bereksperimen.
