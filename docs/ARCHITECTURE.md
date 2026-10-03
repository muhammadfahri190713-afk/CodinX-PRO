# Arsitektur

```
 pengguna ─► cli.py ─► app.py (REPL, slash command, skills, memori)
                          │
                          ▼
                      agent.py ── loop: prompt → model → tool → hasil → …
                       │   │
       ┌───────────────┘   └──────────────┐
       ▼                                  ▼
   wire.py (adaptor)                  tools.py ── perms.py (izin) ── hooks.py
   native / text / flat                  │            ▲
       │                                 ├─ mcp.py (server MCP)
       ▼                                 └─ sub-agent (agents.py)
    api.py ──HTTP/SSE──► proxy OpenAI-compatible
```

| Modul | Tugas |
|---|---|
| `cli.py` | argparse: interaktif, `run`, `doctor`, `models`, `sessions`, `logs`, `connect` |
| `app.py` | REPL, slash command, `$skill`/`@file`/`!shell`, probe otomatis, pusat izin |
| `agent.py` | loop agent, system prompt (memori, skills, sub-agent, AGENTS.md), kompaksi, sub-agent |
| `wire.py` | mengubah riwayat kanonik → format yang diterima proxy (native/text/flat), parser tool-call teks |
| `api.py` | klien HTTP+SSE (stdlib), retry, parsing proxy yang tidak standar |
| `doctor.py`, `caps.py` | uji kemampuan proxy/model, simpan hasil per model |
| `tools.py` | 17 tool + dispatcher (hooks, izin, MCP) |
| `perms.py` | kebijakan izin, pola, hard-deny |
| `ui.py`, `themes.py`, `highlight.py` | terminal: banner, Markdown, tabel, prompt izin, syntax highlight |
| `session.py` | sesi persisten, undo/redo file |
| `memory.py`, `skills.py`, `agents.py` | memori, skills, sub-agent |
| `hooks.py`, `mcp.py` | ekstensi: hooks shell & server MCP (stdio) |
| `tiers.py`, `geo.py` | paket FREE/PRO/MAX, Dinar, reset tengah malam lokal |
| `config.py`, `vault.py`, `guard.py`, `log.py` | konfigurasi/.env, brankas kunci, kompatibilitas legacy, log debug |

**Prinsip:** riwayat disimpan dalam satu format kanonik (gaya OpenAI); `wire.to_wire()` menerjemahkannya saat kirim, sehingga
berganti model/proxy di tengah sesi tidak merusak riwayat.
