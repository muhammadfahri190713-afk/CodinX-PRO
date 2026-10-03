---
name: commit-message
description: Menulis pesan commit yang jelas (Conventional Commits) dari diff nyata.
---
# Pesan commit
1. `git status --short` dan `git diff --staged` (atau `git diff`): pahami perubahan sebenarnya.
2. Format: `<tipe>(<ruang-lingkup>): <ringkasan imperatif <=72 char>` — tipe: feat, fix, docs, refactor, test, chore, perf, build, ci.
3. Badan (opsional): MENGAPA perubahan dibuat, bukan apa yang terlihat dari diff. Footer: `BREAKING CHANGE:` / `Refs #123`.
4. Satu commit = satu maksud. Tambahkan file spesifik, bukan `git add -A` buta. Jangan commit rahasia (skill `secret-scan`).
