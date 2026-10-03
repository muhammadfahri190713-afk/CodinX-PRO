#!/usr/bin/env python3
"""Regenerasi docs/COMMANDS.md, docs/CONFIG.md, dan docs/SKILLS.md dari kode & folder (agar tidak menyimpang)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("HOME", "/tmp/codinx-gen-docs")

from cx import agents, config, skills  # noqa: E402
from cx.app import COMMANDS  # noqa: E402

DESC = {
    "base_url": "Endpoint OpenAI-compatible (otomatis ditambah /v1 bila belum ada).",
    "model": "Model aktif (id seperti di /models).",
    "trial_mode": "Masa uji coba: SEMUA model gratis (tanpa kunci paket, Dinar tidak dipotong). false = aturan paket FREE/PRO/MAX + Dinar.",
    "tier": "Paket: free | pro | max (menentukan model yang boleh dipakai & batas Dinar).",
    "timezone": "Zona waktu IANA untuk reset harian Dinar (kosong = deteksi dari IP).",
    "dinar_token_unit": "Tiap kelipatan token ini dalam 1 request dihitung +1 request (65 Dinar).",
    "tool_policy": "Kebijakan per tool: ask | allow | deny | off (diatur lewat /permissions).",
    "trust_project": "Izinkan hooks.json & mcp.json dari folder proyek (hanya dari konfigurasi global).",
    "tool_mode": "auto | native | text | none — cara memanggil tool (auto = hasil /doctor per model).",
    "history_mode": "auto | native | flat — cara mengirim riwayat (flat = digabung jadi 1 pesan).",
    "auto_probe": "Diagnosa otomatis sekali per model.",
    "conv_field": "Nama field body untuk id percakapan, mis. conversation_id / chat_id (kosong = tidak dikirim).",
    "conv_source": "client = id sesi CodinX | server = pakai id yang diberikan server.",
    "theme": "Tema warna (lihat /theme).",
    "agent": "build | plan.",
    "context_limit": "Batas konteks (token) untuk kompaksi otomatis pada 80%.",
    "temperature": "Suhu sampling (null = default model).",
    "max_steps": "Maksimum langkah model per pesan user.",
    "show_thinking": "Tampilkan proses berpikir model.",
    "show_details": "Tampilkan output tool.",
    "insecure_tls": "Lewati verifikasi sertifikat TLS (hanya untuk proxy lokal bersertifikat sendiri).",
    "permission": "Aturan pola lanjutan per tool (lihat docs/PERMISSIONS.md).",
}
ENV = [("CODINX_BASE_URL", "base_url"), ("CODINX_API_KEY", "(rahasia; tidak pernah disimpan ke config.json)"), ("CODINX_MODEL", "model"),
       ("CODINX_TRIAL", "trial_mode (1 = uji coba, semua model gratis | 0 = aturan paket)"), ("CODINX_TIER", "tier"), ("CODINX_TOOL_MODE", "tool_mode"), ("CODINX_HISTORY_MODE", "history_mode"),
       ("CODINX_AUTO_PROBE", "auto_probe (0/1)"), ("CODINX_CONV_FIELD", "conv_field"), ("CODINX_CONV_SOURCE", "conv_source"),
       ("CODINX_DEBUG", "log debug (1 = aktif)")]


def write(name, text):
    with open(os.path.join(ROOT, "docs", name), "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def cmds():
    custom = []
    d = os.path.join(ROOT, "commands")
    for f in sorted(os.listdir(d)):
        if f.endswith(".md"):
            meta, _ = skills.parse(open(os.path.join(d, f), encoding="utf-8").read())
            custom.append((f"/{f[:-3]}", meta.get("description", "")))
    t = "# Perintah\n\n> Dihasilkan otomatis dari kode oleh `scripts/gen_docs.py` — jangan edit manual.\n\n## Slash command (di dalam CodinX)\n\n| Perintah | Fungsi |\n|---|---|\n"
    t += "".join(f"| `{c}` | {d} |\n" for c, d in COMMANDS)
    t += "\n## Perintah custom bawaan (`commands/*.md`)\n\n| Perintah | Fungsi |\n|---|---|\n" + "".join(f"| `{c}` | {d} |\n" for c, d in custom)
    t += "\nBuat sendiri: `~/.codinx/commands/<nama>.md` atau `<proyek>/.codinx/commands/<nama>.md` (placeholder `$ARGUMENTS`, `$1`…`$9`, `` !`cmd` ``, `@file`).\n"
    t += "\n## Input khusus\n\n- `@path` melampirkan file/folder · `!perintah` menjalankan shell · akhiri baris dengan `\\` untuk multi-baris · `$nama` memuat skill.\n"
    t += "\n## Subcommand CLI\n\n| Perintah | Fungsi |\n|---|---|\n| `codinx` | mode interaktif |\n| `codinx run \"pesan\"` | satu prompt non-interaktif (`-c`, `--auto`, `--plan`, `--format json`, `--no-probe`, `-m model`; pesan `-` = stdin; boleh `/skill …`) |\n| `codinx connect` | atur endpoint + API key |\n| `codinx doctor` | diagnosa proxy |\n| `codinx models [filter]` | daftar model & paket |\n| `codinx sessions` | daftar sesi |\n| `codinx logs [-n N]` | log debug terbaru |\n"
    write("COMMANDS.md", t)


def conf():
    t = "# Konfigurasi\n\n> Dihasilkan otomatis dari kode oleh `scripts/gen_docs.py`.\n\nPrioritas: **variabel lingkungan nyata > `.env` > brankas/`config.json`** (untuk koneksi); "
    t += "`<proyek>/.codinx/config.json` hanya boleh mengubah: " + ", ".join(f"`{k}`" for k in sorted(config.PROJECT_KEYS)) + ".\n\n"
    t += "## `~/.codinx/config.json`\n\n| Kunci | Bawaan | Arti |\n|---|---|---|\n"
    t += "".join(f"| `{k}` | `{v!r}` | {DESC.get(k, '')} |\n" for k, v in config.DEFAULTS.items())
    t += "\n## Variabel lingkungan / `.env` (hanya awalan `CODINX_`)\n\n| Variabel | Menentukan |\n|---|---|\n" + "".join(f"| `{a}` | {b} |\n" for a, b in ENV)
    t += "\n## File data di `~/.codinx/`\n\n`config.json` · `.key.enc` (kunci terenkripsi) · `.env` · `sessions/` · `memory.json` · `usage.json` · `geo.json` · `caps.json` (hasil diagnosa) · `history` · `skills/` · `commands/` · `agents/` · `hooks.json` · `mcp.json` · `logs/` · `shares/` · `bg/`\n"
    write("CONFIG.md", t)


def skl():
    t = "# Skills\n\nSkill = folder berisi `SKILL.md` (frontmatter `name` + `description`, lalu instruksi). Hanya nama+deskripsi masuk prompt (progressive disclosure); isi dimuat saat dipakai.\n\n"
    t += "## Cara menjalankan\n\n| Cara | Contoh |\n|---|---|\n| Menu interaktif | `/skills` lalu pilih nomor |\n| Perintah langsung | `/skill web-check cek port 3000` atau `/web-check cek port 3000` |\n| Di dalam kalimat | `tolong $secret-scan sebelum push` |\n| Otomatis | permintaan yang cocok → isi skill disuntik ke prompt |\n| Oleh model | tool `skill` (jika proxy mendukung tool) |\n| Mode `run` | `codinx run \"/skill debug-fix error x\"` |\n\n"
    t += "## Membuat skill\n\n`~/.codinx/skills/<nama>/SKILL.md` (global) atau `<proyek>/.codinx/skills/<nama>/SKILL.md`. Skrip pendukung di `scripts/`; rujuk dengan `{SKILLDIR}/scripts/x.py` (otomatis diganti path absolut).\n\n"
    sk = skills.discover(ROOT)
    t += f"## Skill bawaan ({len(sk)})\n\n| Skill | Deskripsi | Skrip |\n|---|---|---|\n"
    for n, s in sk.items():
        sd = os.path.join(s["dir"], "scripts")
        scr = ", ".join(sorted(os.listdir(sd))) if os.path.isdir(sd) else ""
        t += f"| `{n}` | {s['description']} | {scr} |\n"
    ag = agents.discover(ROOT)
    t += f"\n## Sub-agent bawaan ({len(ag)}) — lihat `docs/SUBAGENTS.md`\n\n" + "".join(f"- `{n}`: {a['description']}\n" for n, a in ag.items())
    write("SKILLS.md", t)


if __name__ == "__main__":
    cmds(); conf(); skl()
    print("docs/COMMANDS.md, docs/CONFIG.md, docs/SKILLS.md dibuat")
