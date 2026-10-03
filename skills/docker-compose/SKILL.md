---
name: docker-compose
description: Menulis dan men-debug docker-compose: service, volume, jaringan, healthcheck, env.
---
# Docker Compose
Kerangka `compose.yaml`:
```yaml
services:
  app:
    build: .
    ports: ["3000:3000"]
    env_file: .env
    depends_on:
      db: {condition: service_healthy}
    restart: unless-stopped
  db:
    image: postgres:16
    environment: {POSTGRES_PASSWORD: ${DB_PASSWORD}}
    volumes: [dbdata:/var/lib/postgresql/data]
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U postgres"], interval: 5s, retries: 10}
volumes: {dbdata: {}}
```
Perintah: `docker compose config` (validasi) -> `docker compose up -d --build` -> `docker compose ps` -> `docker compose logs -f --tail=100 app`.
Debug: `docker compose exec app sh`, `docker inspect`, cek port bentrok (`ss -ltnp`). Jangan commit `.env`; jangan `down -v` tanpa izin (menghapus data).
