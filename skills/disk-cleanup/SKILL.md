---
name: disk-cleanup
description: Menemukan pemakai disk terbesar dan membersihkan dengan aman (tanpa menghapus sembarangan).
---
# Disk cleanup
1. `df -hT` dan inode: `df -i`.
2. Pemakai terbesar (baca-saja): `bash {SKILLDIR}/scripts/du_top.sh / 15` lalu telusuri turun: `bash {SKILLDIR}/scripts/du_top.sh /var 10`.
3. Kandidat aman (tetap minta izin sebelum menghapus): `journalctl --vacuum-time=7d`, `apt-get clean`, `docker system df` lalu `docker image prune`,
   cache `~/.cache`, log lama berputar `/var/log/*.gz`.
4. File dihapus tapi disk tetap penuh: `lsof +L1` (proses menahan file) -> restart proses itu.
ATURAN: tampilkan apa yang akan dihapus + ukuran, minta konfirmasi; jangan `rm -rf` path berisi variabel kosong; jangan sentuh `/var/lib/*` (database, docker) tanpa alasan jelas.
