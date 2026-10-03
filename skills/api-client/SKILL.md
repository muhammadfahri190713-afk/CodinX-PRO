---
name: api-client
description: Membangun klien API HTTP (curl/Python): auth, retry, timeout, paginasi, pengujian.
---
# Klien API
- Eksplorasi dengan `webfetch` (method/headers/body) atau `curl -sS -D- -H 'Authorization: Bearer $TOKEN' URL`.
- Python: `urllib.request` (tanpa dependensi) atau `requests`; SELALU set timeout, tangani 429/5xx dengan backoff eksponensial.
- Token dari environment/.env — jangan hardcode, jangan cetak ke log. Paginasi: ikuti `next`/cursor sampai habis.
- Pisahkan: fungsi `request()` tunggal, lapisan parsing, lapisan bisnis. Uji dengan server tiruan lokal (`http.server`) — bukan API sungguhan.
- Dokumentasikan contoh request/response nyata di README.
