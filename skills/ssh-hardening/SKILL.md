---
name: ssh-hardening
description: Mengeraskan SSH dengan aman (tanpa mengunci diri): kunci, nonaktifkan password, uji sebelum reload.
---
# SSH hardening (HATI-HATI: salah langkah = terkunci)
1. Pastikan login pakai kunci SUDAH berhasil dari sesi lain. Backup: `cp /etc/ssh/sshd_config /root/sshd_config.bak`.
2. Ubah di `/etc/ssh/sshd_config.d/99-hardening.conf`: `PasswordAuthentication no`, `PermitRootLogin prohibit-password`, `MaxAuthTries 3`, `X11Forwarding no`.
3. **`sshd -t`** harus tanpa error. Lalu `systemctl reload ssh` (BUKAN restart) dan JANGAN menutup sesi yang sedang terbuka.
4. Buka sesi SSH baru untuk membuktikan masih bisa masuk; bila gagal, kembalikan backup.
5. Tambahan: `fail2ban`, ganti port hanya bila perlu (update firewall dulu — skill `firewall-ufw`).
