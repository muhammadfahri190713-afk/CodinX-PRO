# Perintah

> Dihasilkan otomatis dari kode oleh `scripts/gen_docs.py` — jangan edit manual.

## Slash command (di dalam CodinX)

| Perintah | Fungsi |
|---|---|
| `/help` | daftar perintah |
| `/new` | sesi baru |
| `/sessions` | lanjutkan sesi lama |
| `/skills` | daftar skill + jalankan (pilih nomor) |
| `/skill` | jalankan skill: /skill <nama> [tugas]  ·  atau /<nama>  ·  atau $nama |
| `/agents` | daftar sub-agent khusus |
| `/mcp` | server MCP: status / reload |
| `/hooks` | daftar hooks aktif |
| `/diff` | git diff berwarna  (/diff --stat) |
| `/debug` | on | off | tail — log debug |
| `/models` | pilih model  (/models pro · /models claude) |
| `/connect` | atur endpoint + API key |
| `/doctor` | diagnosa proxy: riwayat percakapan + tool (otomatis) |
| `/toolmode` | auto|native|text|none |
| `/historymode` | auto|native|flat |
| `/remember` | simpan sesuatu ke memori |
| `/forget` | hapus memori (id | all) |
| `/memory` | lihat/cari/tambah/hapus memori |
| `/permissions` | pengaturan izin tool (web, kamera, terminal…) |
| `/tier` | lihat/ubah paket FREE·PRO·MAX |
| `/status` | paket, Dinar, mode, konteks |
| `/plan` | mode plan (read-only) |
| `/build` | mode build (bisa edit) |
| `/auto` | auto-izinkan semua (hard-deny tetap) |
| `/compact` | ringkas konteks |
| `/undo` | batalkan giliran terakhir |
| `/redo` | ulangi yang di-undo |
| `/init` | buat AGENTS.md |
| `/theme` | ganti tema warna |
| `/details` | tampil/sembunyi detail tool |
| `/thinking` | tampil/sembunyi proses berpikir |
| `/export` | simpan percakapan ke .md |
| `/share` | ekspor lokal untuk dibagikan |
| `/location` | provinsi + zona waktu (reset Dinar) |
| `/clear` | bersihkan layar |
| `/exit` | keluar |

## Perintah custom bawaan (`commands/*.md`)

| Perintah | Fungsi |
|---|---|
| `/changelog` | Susun CHANGELOG dan catatan rilis dari riwayat git |
| `/commit` | Buat commit git dengan pesan yang baik |
| `/deps` | Periksa dan perbarui dependensi dengan aman |
| `/doc` | Tulis atau rapikan dokumentasi untuk sebuah file/modul ($ARGUMENTS) |
| `/explain-error` | Jelaskan akar masalah sebuah pesan error dan cara memperbaikinya |
| `/explain` | Jelaskan file/fungsi ($1) |
| `/fix` | Perbaiki error/bug yang dijelaskan |
| `/optimize` | Profil dan optimalkan performa bagian yang lambat |
| `/pr` | Buat judul + deskripsi Pull Request dari perubahan saat ini |
| `/publish` | Persiapkan dan publikasikan proyek ke GitHub dengan aman |
| `/refactor` | Refactor tanpa mengubah perilaku |
| `/review` | Review perubahan git saat ini |
| `/scan` | Pindai rahasia (API key/token) di proyek sebelum commit/push |
| `/security` | Audit keamanan proyek ini (secret, injeksi, izin, dependensi) |
| `/standup` | Ringkasan pekerjaan terakhir untuk standup harian |
| `/test` | Jalankan test proyek dan perbaiki yang gagal |
| `/todo` | Kumpulkan semua TODO/FIXME di proyek jadi daftar prioritas |
| `/translate` | Terjemahkan teks/file ke bahasa lain ($1 = bahasa target) |
| `/web` | Jalankan proyek web dan cek di localhost |

Buat sendiri: `~/.codinx/commands/<nama>.md` atau `<proyek>/.codinx/commands/<nama>.md` (placeholder `$ARGUMENTS`, `$1`…`$9`, `` !`cmd` ``, `@file`).

## Input khusus

- `@path` melampirkan file/folder · `!perintah` menjalankan shell · akhiri baris dengan `\` untuk multi-baris · `$nama` memuat skill.

## Subcommand CLI

| Perintah | Fungsi |
|---|---|
| `codinx` | mode interaktif |
| `codinx run "pesan"` | satu prompt non-interaktif (`-c`, `--auto`, `--plan`, `--format json`, `--no-probe`, `-m model`; pesan `-` = stdin; boleh `/skill …`) |
| `codinx connect` | atur endpoint + API key |
| `codinx doctor` | diagnosa proxy |
| `codinx models [filter]` | daftar model & paket |
| `codinx sessions` | daftar sesi |
| `codinx logs [-n N]` | log debug terbaru |
