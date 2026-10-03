---
name: node-api
description: Membuat API Node.js (Express/Fastify): rute, validasi, env, error handling, test.
---
# API Node
1. `npm init -y && npm i express dotenv` (atau `fastify`), `npm i -D nodemon`. Tambah scripts `start`, `dev`, `test` di package.json.
2. Struktur: `src/server.js` (listen), `src/app.js` (rute, middleware — agar mudah dites), `src/routes/*.js`, `.env.example`.
3. Wajib: `express.json()`, handler 404, middleware error 4-argumen, validasi input, `process.env.PORT || 3000`, CORS seperlunya.
4. Uji: jalankan di background (`bash` background=true) lalu `webfetch` ke `http://localhost:3000/health` dan rute lain.
5. Test: `node --test` (bawaan Node 20+) atau supertest. Jangan commit `.env`; sediakan `.env.example`.
