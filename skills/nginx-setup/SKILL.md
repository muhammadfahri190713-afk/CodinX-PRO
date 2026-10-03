---
name: nginx-setup
description: Konfigurasi Nginx: situs statis atau reverse proxy, uji konfigurasi, reload aman.
---
# Nginx
1. Backup: `cp /etc/nginx/sites-available/<site> /root/<site>.bak` (jika ada).
2. Reverse proxy minimal:
```nginx
server {
    listen 80;
    server_name contoh.com;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
3. Aktifkan: `ln -s /etc/nginx/sites-available/<site> /etc/nginx/sites-enabled/` -> **`nginx -t`** (wajib lulus) -> `systemctl reload nginx`.
4. Verifikasi: `curl -I http://127.0.0.1 -H 'Host: contoh.com'`; log: `/var/log/nginx/error.log`.
HTTPS: skill `ssl-letsencrypt`. Jangan reload sebelum `nginx -t` sukses.
