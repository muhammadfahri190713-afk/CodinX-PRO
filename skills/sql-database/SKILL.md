---
name: sql-database
description: Merancang skema SQL, migrasi, kueri, indeks, dan debugging performa (SQLite/Postgres/MySQL).
---
# SQL
- Skema: kunci primer jelas, tipe tepat, `NOT NULL`/`UNIQUE`/`FOREIGN KEY`, indeks untuk kolom `WHERE`/`JOIN`/`ORDER BY`.
- Migrasi: file bernomor (`001_init.sql`), idempoten bila bisa, uji pada salinan data; jangan ubah migrasi yang sudah dipakai.
- Kueri lambat: `EXPLAIN` (SQLite `EXPLAIN QUERY PLAN`, Postgres `EXPLAIN (ANALYZE, BUFFERS)`), hindari `SELECT *`, N+1, fungsi pada kolom terindeks.
- Parameterisasi SELALU (`?`/`$1`), jangan menyusun SQL dengan string input user.
- Eksplorasi cepat SQLite: `sqlite3 db.sqlite ".tables" ".schema <tabel>" "SELECT count(*) FROM <tabel>;"`.
- Operasi merusak (DELETE/UPDATE tanpa WHERE, DROP) — tampilkan dulu `SELECT` yang setara dan minta izin.
