# Izin

Tool sensitif meminta izin dengan prompt kuning **"Apakah anda ingin izinkan ini?"** — pilihan **Iya / Tidak / Selalu izinkan**
(←/→ + Enter, atau tombol `i`/`t`/`s`). *Tidak* → agent mencoba cara lain. *Selalu izinkan* → tool itu bebas dipakai (tersimpan di `tool_policy`).

## Kebijakan per tool (`/permissions`)
`bawaan → tanya → izinkan → tolak → mati`. *Mati* = tool tidak ditawarkan ke model sama sekali. Kamera mati secara bawaan.
Tool: `bash`, `edit` (write/edit/multiedit), `read`, `webfetch` (+`websearch`), `localhost`, `camera`, `task`, `memory`, `skill`, `mcp`, `external_directory`.

## Aturan bawaan
- `bash`: perintah baca-saja yang aman (`ls`, `cat`, `git status/diff/log`, …) otomatis; selain itu tanya. Perintah dengan metakarakter shell (`; & | > $( )`) selalu tanya.
- `read`: bebas, kecuali `*.env`, kunci SSH, `*.pem` (tanya). `edit` di luar folder proyek → tanya (`external_directory`).
- Tool MCP: tanya per tool; kebijakan induk `mcp` bisa mematikan/mengizinkan semuanya.

## Hard-deny (selalu diblokir, bahkan dengan `/auto`)
`rm -rf /`, `rm -rf ~`, `mkfs*`, `dd … of=/dev/<disk>`, fork bomb, tulis ke `/dev/<disk>`, `chmod -R` / `chown -R` pada `/`, `shutdown/reboot/halt/poweroff`, `wipefs`.

## Mode
- `/plan`: read-only (write/edit/multiedit/camera/MCP disembunyikan & diblokir). `/build`: normal. `/auto`: semua "tanya" jadi "izinkan" (hard-deny tetap).
