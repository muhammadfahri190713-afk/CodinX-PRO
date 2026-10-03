# Changelog
Format mengikuti Keep a Changelog; versi mengikuti Semantic Versioning.

## [1.2.0] - 2026-10-02
### Ditambahkan
- **Diagnosa proxy otomatis** (`/doctor`): mendeteksi apakah proxy meneruskan riwayat percakapan dan apakah tool bisa dipanggil;
  mode `flat` (riwayat digabung satu pesan) dan mode tool `text` (`<tool_call>`) untuk gateway yang tidak mendukungnya.
- **Skills bisa dijalankan langsung**: `/skills`, `/skill <nama>`, `/<nama>`, `$nama` di pesan; pencocokan skill otomatis. 42 skill bawaan (sysadmin, dev, keamanan).
- **Memori**: penangkapan otomatis ("ingat bahwa…", "nama saya…"), `/remember`, `/forget`, tanpa duplikat.
- Syntax highlighting (Pygments disertakan), tabel yang membungkus teks, `/diff`.
- Hooks (PreToolUse/PostToolUse/UserPromptSubmit/Stop), klien MCP (stdio), sub-agent khusus (6 bawaan), tool `websearch` dan `multiedit`.
- Konfigurasi proyek `.codinx/config.json` (kunci terbatas), log debug (`CODINX_DEBUG=1`, `/debug`, `codinx logs`), dukungan `.env`.
- Suite test (`make test`), CI GitHub Actions, pemindai rahasia + pre-commit hook, completions bash/zsh, Dockerfile.
- **Mode uji coba** (bawaan aktif): semua 170 model gratis — tanpa kunci paket/trial terbatas dan Dinar tidak dipotong. Matikan: `CODINX_TRIAL=0`.
### Diperbaiki
- Nilai dari env/`.env` tidak lagi ikut tersimpan permanen ke `config.json`; `load()` memakai salinan dalam (dict bersarang tidak dipakai bersama).
- Agent lupa percakapan pada gateway yang hanya membaca pesan terakhir / menolak role `tool`.
- Skill tidak bisa dijalankan pada proxy tanpa function-calling.
- Tabel memotong teks panjang; penangkapan nama menyimpan kata tambahan.

## [1.0.0] - 2026-09-30
- Rilis awal: agent terminal root-only, izin Iya/Tidak/Selalu, tier FREE/PRO/MAX + Dinar, sesi, memori, skills, tema.
