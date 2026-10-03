# Kompatibilitas proxy

Proxy "OpenAI-compatible" sering tidak sepenuhnya kompatibel. CodinX mendeteksi dan beradaptasi otomatis.

| Gejala | Penyebab | Yang dilakukan CodinX |
|---|---|---|
| Agent lupa pesan sebelumnya | gateway hanya membaca pesan terakhir | mode riwayat **flat**: seluruh riwayat digabung ke 1 pesan |
| HTTP 400 saat ada `tools` | model/proxy tanpa function-calling | mode tool **text**: `<tool_call>{json}</tool_call>` di teks biasa |
| HTTP 400 "unsupported role: tool" | proxy menolak pesan `role=tool` | mode **text** (hasil tool dikirim sebagai pesan user) |
| Model tidak pernah memanggil tool | model tidak mendukung | mode **none**: chat saja; skill via `/skill`, tindakan via `!perintah` |
| `usage.prompt_tokens` jauh lebih kecil dari yang dikirim | riwayat tidak dibaca | peringatan + saran `/doctor` |

## Diagnosa
- Otomatis sekali per model pada pesan pertama (`auto_probe`). Manual: `/doctor` atau `codinx doctor`. Hasil disimpan di `~/.codinx/caps.json`.
- Uji: (1) riwayat — kode rahasia di giliran pertama harus diingat di giliran ketiga (native → flat); (2) tool — panggilan `echo` native,
  lalu perjalanan-pulang `role=tool`, lalu protokol teks. Probe tidak memotong Dinar.
- Paksa: `/historymode native|flat|auto`, `/toolmode native|text|none|auto` (atau `CODINX_HISTORY_MODE`/`CODINX_TOOL_MODE`).

## Id percakapan
Setiap sesi punya id; dikirim sebagai header `X-Conversation-Id` dan field body `user`. Bila gateway butuh nama field lain,
set `conv_field` (mis. `conversation_id`). `conv_source=server` memakai id yang dikembalikan server (dibaca dari field tersebut / `id` respons).
Lihat `/status` (id respons server) dan `CODINX_DEBUG=1` → `codinx logs` untuk melihat yang sebenarnya dikirim (rahasia disamarkan).
