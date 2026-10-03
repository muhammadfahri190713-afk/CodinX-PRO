# Konfigurasi

> Dihasilkan otomatis dari kode oleh `scripts/gen_docs.py`.

Prioritas: **variabel lingkungan nyata > `api.py` > `.env` legacy > brankas/`config.json`** (untuk koneksi); `<proyek>/.codinx/config.json` hanya boleh mengubah: `agent`, `context_limit`, `history_mode`, `max_steps`, `model`, `show_details`, `show_thinking`, `temperature`, `theme`, `tool_mode`.

## `~/.codinx/config.json`

| Kunci | Bawaan | Arti |
|---|---|---|
| `base_url` | `'https://inttelix.vercel.app/api/v1'` | Endpoint OpenAI-compatible (otomatis ditambah /v1 bila belum ada). |
| `model` | `'deepseek-v4-flash'` | Model aktif (id seperti di /models). |
| `tier` | `'free'` | Paket: free | pro | max (menentukan model yang boleh dipakai & batas Dinar). |
| `trial_mode` | `True` | Masa uji coba: SEMUA model gratis (tanpa kunci paket, Dinar tidak dipotong). false = aturan paket FREE/PRO/MAX + Dinar. |
| `timezone` | `''` | Zona waktu IANA untuk reset harian Dinar (kosong = deteksi dari IP). |
| `dinar_token_unit` | `8000` | Tiap kelipatan token ini dalam 1 request dihitung +1 request (65 Dinar). |
| `tool_policy` | `{}` | Kebijakan per tool: ask | allow | deny | off (diatur lewat /permissions). |
| `trust_project` | `False` | Izinkan hooks.json & mcp.json dari folder proyek (hanya dari konfigurasi global). |
| `tool_mode` | `'auto'` | auto | native | text | none — cara memanggil tool (auto = hasil /doctor per model). |
| `history_mode` | `'auto'` | auto | native | flat — cara mengirim riwayat (flat = digabung jadi 1 pesan). |
| `auto_probe` | `True` | Diagnosa otomatis sekali per model. |
| `conv_field` | `''` | Nama field body untuk id percakapan, mis. conversation_id / chat_id (kosong = tidak dikirim). |
| `conv_source` | `'client'` | client = id sesi CodinX | server = pakai id yang diberikan server. |
| `theme` | `'codinx'` | Tema warna (lihat /theme). |
| `agent` | `'build'` | build | plan. |
| `context_limit` | `128000` | Batas konteks (token) untuk kompaksi otomatis pada 80%. |
| `temperature` | `None` | Suhu sampling (null = default model). |
| `max_steps` | `60` | Maksimum langkah model per pesan user. |
| `show_thinking` | `False` | Tampilkan proses berpikir model. |
| `show_details` | `True` | Tampilkan output tool. |
| `insecure_tls` | `False` | Lewati verifikasi sertifikat TLS (hanya untuk proxy lokal bersertifikat sendiri). |
| `permission` | `{}` | Aturan pola lanjutan per tool (lihat docs/PERMISSIONS.md). |

## `api.py` (koneksi lokal)

Salin `api.example.py` menjadi `api.py`, lalu isi `API_KEY`. File ini hanya dibaca sebagai konstanta teks, diberi mode 600, dan masuk `.gitignore`; jangan pernah commit API key ke repository publik. `BASE_URL` opsional, default: `https://inttelix.vercel.app/api/v1`.

## Variabel lingkungan / `.env` legacy (hanya awalan `CODINX_`)

| Variabel | Menentukan |
|---|---|---
| `CODINX_BASE_URL` | base_url |
| `CODINX_API_KEY` | (rahasia; tidak pernah disimpan ke config.json) |
| `CODINX_MODEL` | model |
| `CODINX_TRIAL` | trial_mode (1 = uji coba, semua model gratis | 0 = aturan paket) |
| `CODINX_TIER` | tier |
| `CODINX_TOOL_MODE` | tool_mode |
| `CODINX_HISTORY_MODE` | history_mode |
| `CODINX_AUTO_PROBE` | auto_probe (0/1) |
| `CODINX_CONV_FIELD` | conv_field |
| `CODINX_CONV_SOURCE` | conv_source |
| `CODINX_DEBUG` | log debug (1 = aktif) |

## File data di `~/.codinx/`

`config.json` · `.key.enc` (kunci terenkripsi) · `api.py` · `.env` legacy · `sessions/` · `memory.json` · `usage.json` · `geo.json` · `caps.json` (hasil diagnosa) · `history` · `skills/` · `commands/` · `agents/` · `hooks.json` · `mcp.json` · `logs/` · `shares/` · `bg/`
