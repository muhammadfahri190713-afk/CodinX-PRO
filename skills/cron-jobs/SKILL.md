---
name: cron-jobs
description: Menjadwalkan tugas dengan cron atau systemd timer, dan men-debug job yang tidak jalan.
---
# Cron / timer
- Lihat: `crontab -l`, `ls /etc/cron.d`, `systemctl list-timers`.
- Tambah (aman): `(crontab -l 2>/dev/null; echo '*/15 * * * * /opt/job.sh >> /var/log/job.log 2>&1') | crontab -`.
- Jebakan umum: PATH minimal (pakai path absolut), tidak ada env user, `%` harus di-escape `\%`, skrip tanpa `chmod +x`, zona waktu server.
- Uji perintah persis seperti cron: `env -i /bin/sh -c '<perintah>'`.
- Log: `journalctl -u cron -n 50 --no-pager` atau `grep CRON /var/log/syslog | tail`.
- Alternatif modern: systemd timer (`OnCalendar=`, `Persistent=true`) — lihat skill `systemd-service`. Gunakan `flock -n /tmp/job.lock` agar tidak tumpang tindih.
