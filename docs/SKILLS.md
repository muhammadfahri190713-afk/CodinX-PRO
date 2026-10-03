# Skills

Skill = folder berisi `SKILL.md` (frontmatter `name` + `description`, lalu instruksi). Hanya nama+deskripsi masuk prompt (progressive disclosure); isi dimuat saat dipakai.

## Cara menjalankan

| Cara | Contoh |
|---|---|
| Menu interaktif | `/skills` lalu pilih nomor |
| Perintah langsung | `/skill web-check cek port 3000` atau `/web-check cek port 3000` |
| Di dalam kalimat | `tolong $secret-scan sebelum push` |
| Otomatis | permintaan yang cocok → isi skill disuntik ke prompt |
| Oleh model | tool `skill` (jika proxy mendukung tool) |
| Mode `run` | `codinx run "/skill debug-fix error x"` |

## Membuat skill

`~/.codinx/skills/<nama>/SKILL.md` (global) atau `<proyek>/.codinx/skills/<nama>/SKILL.md`. Skrip pendukung di `scripts/`; rujuk dengan `{SKILLDIR}/scripts/x.py` (otomatis diganti path absolut).

## Skill bawaan (42)

| Skill | Deskripsi | Skrip |
|---|---|---|
| `api-client` | Membangun klien API HTTP (curl/Python): auth, retry, timeout, paginasi, pengujian. |  |
| `backup-restore` | Backup & restore dengan rsync/tar disertai verifikasi dan uji restore. |  |
| `camera-capture` | Mengambil foto dari kamera server dengan tool camera (butuh izin camera + fswebcam/ffmpeg). |  |
| `changelog-release` | Menyusun CHANGELOG dan rilis semver: kategori, tag git, catatan rilis. |  |
| `code-review` | Review kode terstruktur: bug, keamanan, performa, keterbacaan, test. |  |
| `commit-message` | Menulis pesan commit yang jelas (Conventional Commits) dari diff nyata. |  |
| `cron-jobs` | Menjadwalkan tugas dengan cron atau systemd timer, dan men-debug job yang tidak jalan. |  |
| `data-report` | Membuat laporan ringkas dari CSV/JSON: statistik, tabel, temuan utama. |  |
| `debug-fix` | Metode debugging sistematis: reproduksi, isolasi, perbaiki akar masalah, verifikasi. |  |
| `dependency-update` | Memperbarui dependensi dengan aman: audit, naikkan bertahap, uji, lockfile. |  |
| `disk-cleanup` | Menemukan pemakai disk terbesar dan membersihkan dengan aman (tanpa menghapus sembarangan). | du_top.sh |
| `docker-compose` | Menulis dan men-debug docker-compose: service, volume, jaringan, healthcheck, env. |  |
| `docker-image` | Menulis Dockerfile yang kecil, cepat di-build, dan aman (multi-stage, non-root, cache layer). |  |
| `documentation-writer` | Menulis README, docstring, dan panduan yang akurat berdasarkan kode nyata. |  |
| `file-builder` | Membuat file/proyek baru dengan benar (struktur, isi lengkap, verifikasi) memakai write/bash. |  |
| `firewall-ufw` | Mengatur firewall UFW dengan urutan aman agar SSH tidak terputus. |  |
| `git-workflow` | Alur git aman: status, diff, commit bermakna, branch; tanpa merusak riwayat. |  |
| `github-publish` | Mempublikasikan proyek ke GitHub dengan aman: .gitignore, tanpa secret, remote, push, CI. |  |
| `json-yaml-tools` | Mengolah JSON/YAML: pretty-print, ekstrak kunci, validasi, konversi (jq/python). | jsonpp.py |
| `linux-troubleshoot` | Diagnosis server Linux sistematis: CPU, memori, disk, service gagal, log, jaringan. |  |
| `log-analysis` | Menganalisis log: error teratas, pola waktu, korelasi; dengan skrip ringkasan. | top_errors.py |
| `markdown-format` | Format jawaban agar dirender rapi dan berwarna di terminal CodinX (judul, tabel, kode, daftar). |  |
| `network-diagnose` | Diagnosis jaringan: DNS, port, rute, firewall, layanan yang mendengarkan. | portcheck.py |
| `nginx-setup` | Konfigurasi Nginx: situs statis atau reverse proxy, uji konfigurasi, reload aman. |  |
| `node-api` | Membuat API Node.js (Express/Fastify): rute, validasi, env, error handling, test. |  |
| `performance-profile` | Mengukur dan mengoptimalkan performa: profiling, hot path, benchmark sebelum/sesudah. |  |
| `project-scaffold` | Membuat kerangka proyek baru (Node, Python, web statis) lengkap dengan README dan cara menjalankan. |  |
| `python-project` | Menyiapkan proyek Python modern: venv, struktur, pyproject, lint, test. |  |
| `python-testing` | Menulis dan menjalankan test Python (pytest/unittest): fixture, mock, parametrisasi, cakupan. | run_tests.sh |
| `refactor-safe` | Refactor tanpa mengubah perilaku: kunci dengan test, langkah kecil, verifikasi tiap langkah. |  |
| `regex-helper` | Menyusun dan menguji regex dengan contoh nyata menggunakan skrip penguji. | retest.py |
| `secret-scan` | Memindai rahasia (API key/token/private key) sebelum push ke GitHub dan memandu rotasi. | secret_scan.py |
| `security-audit` | Audit keamanan kode/server: injeksi, secret, izin, dependensi, konfigurasi; laporan berseverity. |  |
| `shell-scripting` | Menulis skrip bash yang aman dan portabel: strict mode, quoting, trap, argumen, shellcheck. |  |
| `sql-database` | Merancang skema SQL, migrasi, kueri, indeks, dan debugging performa (SQLite/Postgres/MySQL). |  |
| `ssh-hardening` | Mengeraskan SSH dengan aman (tanpa mengunci diri): kunci, nonaktifkan password, uji sebelum reload. |  |
| `ssl-letsencrypt` | Memasang sertifikat HTTPS gratis dengan certbot dan memastikan pembaruan otomatis. |  |
| `static-website` | Membuat situs statis (HTML/CSS/JS) responsif dan mengujinya di localhost. | serve.sh |
| `systemd-service` | Membuat, mengaktifkan, dan men-debug unit systemd untuk aplikasi. |  |
| `table-maker` | Menampilkan data sebagai tabel berwarna dan menyimpannya ke .csv/.md/.json lewat tool table. |  |
| `user-management` | Mengelola user, grup, sudo, dan kunci SSH dengan aman. |  |
| `web-check` | Menjalankan server lokal (mis. localhost:3000) lalu memverifikasi lewat webfetch/curl. |  |

## Sub-agent bawaan (6) — lihat `docs/SUBAGENTS.md`

- `doc-writer`: Menulis/merapikan dokumentasi (README, docstring, panduan) berdasarkan kode sebenarnya.
- `explore`: Penelusur read-only: memetakan codebase dan menjawab pertanyaan dengan path:baris.
- `planner`: Perencana: memecah tugas besar menjadi langkah kecil yang bisa diverifikasi.
- `reviewer`: Reviewer kode read-only: bug, keamanan, performa, keterbacaan, test yang hilang.
- `security-auditor`: Audit keamanan read-only: secret bocor, injeksi, izin file, dependensi berisiko.
- `tester`: Menjalankan test proyek, menganalisis kegagalan, melaporkan akar masalah.
