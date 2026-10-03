---
name: backup-restore
description: Backup & restore dengan rsync/tar disertai verifikasi dan uji restore.
---
# Backup & restore
- Snapshot file: `tar --zstd -cpf /backup/<nama>-$(date +%F).tar.zst -C / <path>` lalu verifikasi `tar --zstd -tf <file> | head`.
- Sinkron inkremental: `rsync -aHAX --delete --dry-run <src>/ <dst>/` dulu; jalankan tanpa `--dry-run` setelah hasilnya benar.
- Database: PostgreSQL `pg_dump -Fc db > db.dump`; MySQL `mysqldump --single-transaction db > db.sql`; SQLite `sqlite3 db.sqlite ".backup out.sqlite"`.
- Checksum: `sha256sum <file> > <file>.sha256`; simpan salinan di mesin lain (aturan 3-2-1).
- UJI RESTORE di folder sementara, bukan di atas data produksi. Backup yang belum pernah diuji restore belum dianggap backup.
- Jangan menimpa data produksi tanpa izin eksplisit; selalu `--dry-run` untuk operasi `--delete`.
