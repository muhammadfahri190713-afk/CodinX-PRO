---
name: docker-image
description: Menulis Dockerfile yang kecil, cepat di-build, dan aman (multi-stage, non-root, cache layer).
---
# Dockerfile
- Basis kecil & dipin: `python:3.12-slim` / `node:20-alpine`. Multi-stage untuk memisahkan build & runtime.
- Urutan layer demi cache: salin file dependensi dulu -> install -> baru salin kode.
- `USER` non-root, `HEALTHCHECK`, `.dockerignore` (`.git`, `.env`, `node_modules`, `__pycache__`). Jangan `COPY .env` ke image.
- Build & uji: `docker build -t app:dev .` -> `docker run --rm -p 3000:3000 --env-file .env app:dev` -> cek `webfetch http://localhost:3000`.
- Pindai ukuran: `docker image ls app:dev`; riwayat layer: `docker history app:dev`.
