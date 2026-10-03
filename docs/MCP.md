# MCP (Model Context Protocol)

CodinX menjadi klien MCP via **stdio** (stdlib saja). Konfigurasi `~/.codinx/mcp.json` (global; proyek bila `trust_project`):

```json
{"mcpServers": {
  "contoh": {"command": "python3", "args": ["/opt/codinx/examples/mcp-echo-server.py"], "env": {"NAMA": "nilai"}}
}}
```
- Server dimulai malas (saat tool dibutuhkan pertama kali) dengan handshake `initialize` → `notifications/initialized` → `tools/list`.
- Tool tampil ke model sebagai `mcp__<server>__<tool>`, selalu lewat sistem izin (tanya per tool; `Selalu izinkan` menyimpan per tool; kebijakan `mcp` = induk).
- `/mcp` melihat status, `/mcp reload` memuat ulang. MCP tidak tersedia di mode `/plan` dan untuk sub-agent.
- Protokol didukung: tools (`tools/list`, `tools/call`) dengan konten teks. Resources/prompts/sampling belum.
