# Hooks

Perintah shell yang dijalankan pada event siklus hidup. Konfigurasi di `~/.codinx/hooks.json` (global). Hooks proyek
(`<proyek>/.codinx/hooks.json`) hanya dimuat bila `"trust_project": true` di konfigurasi global.

```json
{"hooks": {
  "PreToolUse":  [{"matcher": "bash", "command": "python3 ~/.codinx/guard.py"}],
  "PostToolUse": [{"matcher": "edit|write|multiedit", "command": "ruff check --quiet ."}],
  "UserPromptSubmit": [{"command": "date +'Sekarang: %F %T'"}],
  "Stop": [{"command": "notify-send 'CodinX selesai'"}]
}}
```
- `matcher`: regex nama tool (`*` = semua) — hanya untuk PreToolUse/PostToolUse.
- Stdin: JSON `{event, cwd, tool, args, result?, prompt?, final?}`. Env: `CODINX_HOOK_EVENT`, `CODINX_PROJECT_DIR`. `timeout` (detik, bawaan 30).
- **Exit 0** = lanjut (stdout ditambahkan sebagai konteks untuk UserPromptSubmit / ke hasil tool untuk PostToolUse).
- **Exit 2** = BLOKIR: PreToolUse membatalkan tool (stderr dikirim ke model), UserPromptSubmit membatalkan pesan.
- Exit lain = peringatan non-blokir. Lihat yang aktif dengan `/hooks`. Contoh: `examples/hooks.json`.
