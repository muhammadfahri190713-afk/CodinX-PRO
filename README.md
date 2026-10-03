# CodinX — agent coding di terminal

Agent coding berbasis terminal yang **menulis, menjalankan, dan memverifikasi** kode untukmu — terinspirasi opencode, Codex CLI, dan Claude Code.
Python murni (stdlib) + Pygments untuk warna sintaks. Berjalan di Linux, container, dan **Termux tanpa root**.
Versi 1.2.0 · lisensi MIT.

## Mulai cepat
```bash
unzip CodinX.zip && cd CodinX
cp .env.example .env && chmod 600 .env      # isi CODINX_API_KEY (atau letakkan file .env yang sudah jadi di folder ini)
npm run -s codinx-agents                    # atau: python3 bin/codinx
# pasang permanen (perintah `codinx`):  bash install.sh
# Termux: install.sh memakai $PREFIX secara otomatis; tanpa instalasi pun bisa: python3 bin/codinx
```
Non-interaktif: `codinx run "buat web todo" --auto` · `codinx run -c "lanjutkan"` · `codinx run "/skill debug-fix error x"` · `--format json`.
Endpoint bawaan `https://inttelix.vercel.app/api/v1`; ganti dengan `/connect` atau lewat `.env`. Semua variabel: [docs/CONFIG.md](docs/CONFIG.md).

## Masa uji coba: semua model gratis
Selama uji coba (`trial_mode`, **bawaan aktif**) seluruh **170 model** terbuka tanpa kunci paket dan **Dinar tidak dipotong**.
Matikan dengan `CODINX_TRIAL=0` untuk kembali ke aturan paket FREE/PRO/MAX (FREE: 1300 Dinar/hari, 1 request = 65 Dinar, reset 00:00 zona waktu lokal).

## Fitur
- **UI**: banner, Markdown berwarna (judul, tabel yang membungkus teks, daftar), **syntax highlighting** (Pygments), 11 tema.
- **Izin kuning** "Apakah anda ingin izinkan ini?" → *Iya / Tidak / Selalu izinkan*; *Tidak* → agent mencoba cara lain. Perintah destruktif selalu diblokir. [docs/PERMISSIONS.md](docs/PERMISSIONS.md)
- **Tool (17)**: read, write, edit, multiedit, list, glob, grep, bash (+background), webfetch (termasuk `localhost:3000`), websearch, todo, task (sub-agent), skill, memory, table, camera + server MCP.
- **Skills (42)** bisa dijalankan langsung: `/skills`, `/skill <nama>`, `/<nama>`, `$nama` di pesan, atau otomatis. [docs/SKILLS.md](docs/SKILLS.md)
- **Memori**: sesi tersimpan & dilanjutkan otomatis; memori jangka panjang ("ingat bahwa…", "nama saya…", `/remember`).
- **Sub-agent** khusus (6 bawaan). [docs/SUBAGENTS.md](docs/SUBAGENTS.md) · **Hooks** [docs/HOOKS.md](docs/HOOKS.md) · **MCP** [docs/MCP.md](docs/MCP.md)
- `/plan` read-only, `/undo` `/redo` file, `/diff`, `/init` (AGENTS.md), `@file`, `!shell`, `/compact`, `/export`, log debug. Daftar lengkap: [docs/COMMANDS.md](docs/COMMANDS.md)

## Kompatibilitas proxy (agent tidak lupa percakapan, skill & tool selalu jalan)
Proxy "OpenAI-compatible" sering tidak persis kompatibel. Pada pesan pertama tiap model, CodinX **mendiagnosis sendiri** (`/doctor`):
bila gateway hanya membaca pesan terakhir → mode riwayat **flat**; bila tanpa function-calling → tool lewat teks (`<tool_call>`); bila tak bisa tool sama sekali →
chat + `/skill` + `!perintah`. Detail dan cara memaksa mode: [docs/PROXY_COMPAT.md](docs/PROXY_COMPAT.md). Masalah umum: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Keamanan & GitHub
`.env` (rahasia) sudah di `.gitignore`; yang di-commit hanya `.env.example`. Sebelum push: `python3 scripts/secret_scan.py .` dan `bash scripts/install-git-hooks.sh`.
API key tidak pernah ditulis ke log/config. Panduan lengkap & rotasi key: [docs/GITHUB.md](docs/GITHUB.md), [SECURITY.md](SECURITY.md).
Pembatasan paket/Dinar hanya di sisi klien — penegakan sungguhan harus ada di proxy.

## Pengembangan
`make test` (232 test, tanpa jaringan, ±20 detik) · `make scan` · `make docs` · `make zip`. Arsitektur: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Kontribusi: [CONTRIBUTING.md](CONTRIBUTING.md).

## Dokumentasi
| Topik | File |
|---|---|
| Arsitektur | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Perintah | [docs/COMMANDS.md](docs/COMMANDS.md) |
| Konfigurasi & env | [docs/CONFIG.md](docs/CONFIG.md) |
| Kompatibilitas proxy | [docs/PROXY_COMPAT.md](docs/PROXY_COMPAT.md) |
| Izin | [docs/PERMISSIONS.md](docs/PERMISSIONS.md) |
| Skills | [docs/SKILLS.md](docs/SKILLS.md) |
| Sub-agent | [docs/SUBAGENTS.md](docs/SUBAGENTS.md) |
| Hooks | [docs/HOOKS.md](docs/HOOKS.md) |
| MCP | [docs/MCP.md](docs/MCP.md) |
| Pemecahan masalah | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Publish ke GitHub | [docs/GITHUB.md](docs/GITHUB.md) |
| Contoh konfigurasi | [examples/README.md](examples/README.md) |

Pygments disertakan di `cx/vendor` (BSD-2) — lihat [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Lisensi: [LICENSE](LICENSE).
