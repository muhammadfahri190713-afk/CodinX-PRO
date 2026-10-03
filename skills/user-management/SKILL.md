---
name: user-management
description: Mengelola user, grup, sudo, dan kunci SSH dengan aman.
---
# User & sudo
- Tambah user: `adduser <u>` (interaktif) atau `useradd -m -s /bin/bash <u>`; grup: `usermod -aG sudo <u>`.
- Kunci SSH: `install -d -m700 -o <u> -g <u> /home/<u>/.ssh` lalu tulis `authorized_keys` (`chmod 600`, pemilik user itu).
- Sudoers: edit hanya dengan `visudo -f /etc/sudoers.d/<nama>` (validasi sintaks otomatis); jangan beri `NOPASSWD: ALL` tanpa alasan.
- Kunci/hapus: `passwd -l <u>`, `usermod -L -e 1 <u>`; hapus `userdel -r` HANYA setelah backup home dan izin eksplisit.
- Audit: `last -n 20`, `lastb | head`, `awk -F: '$3==0' /etc/passwd` (UID 0 selain root = curiga).
