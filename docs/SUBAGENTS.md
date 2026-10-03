# Sub-agent

Model dapat mendelegasikan pekerjaan lewat tool `task` (parameter `agent` opsional). Tanpa `agent` → penelusur read-only (`read, list, glob, grep, webfetch, websearch`).

Sub-agent khusus = file Markdown di `agents/` (bawaan), `~/.codinx/agents/`, atau `<proyek>/.codinx/agents/`:

```markdown
---
name: reviewer-strict
description: Reviewer ketat untuk kode keamanan-kritis
tools: read, grep, glob, list, bash
---
(isi = system prompt sub-agent)
```
- `tools` membatasi tool yang ditawarkan; semuanya tetap melewati izin. Sub-agent tidak bisa memanggil `task` lagi.
- Bawaan: `explore`, `reviewer`, `tester`, `doc-writer`, `security-auditor`, `planner`. Lihat dengan `/agents`.
