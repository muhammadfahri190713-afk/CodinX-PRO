"""Agent loop: prompt -> model -> tool calls -> results -> ... (+ subagent, compaction, tier gating)."""
import json
import os
import platform
import subprocess

from . import api, geo, memory, skills, tiers, tools
from .themes import c
from .tools import SCHEMAS, SUBAGENT_TOOLS, PLAN_HIDDEN

SYSTEM = """Kamu adalah CodinX, agent coding otonom yang berjalan di terminal milik user (sebagai root).
Tugasmu: benar-benar menyelesaikan pekerjaan — membuat, mengubah, menjalankan, dan memverifikasi kode/file — bukan sekadar menyarankan.

## Cara kerja
- Balas dengan bahasa yang dipakai user (user Indonesia -> jawab Indonesia). Singkat, langsung ke inti.
- Baca dulu sebelum mengubah. Pakai `edit` untuk perubahan kecil, `write` untuk file baru. Jangan menebak isi file.
- Jalankan dan uji hasil kerjamu dengan `bash` (test, build, lint, curl/webfetch ke localhost) sebelum menyatakan selesai.
- Untuk pekerjaan >2 langkah, buat rencana dengan `todowrite` lalu perbarui statusnya.
- Server/proses panjang: `bash` dengan background=true, lalu cek dengan `webfetch` (mis. http://localhost:3000).
- Gunakan `task` untuk riset codebase yang besar, `skill` untuk memuat panduan khusus, `memory` untuk menyimpan
  preferensi/fakta penting user (simpan hal yang berguna lintas sesi; jangan simpan rahasia/API key).
- Gunakan `table` saat data paling jelas sebagai tabel (juga bisa disimpan ke .csv/.md/.json).

## Izin
- Tiap tool sensitif meminta izin user. Jika user MENOLAK, jangan ulangi; coba cara/tool alternatif atau jelaskan singkat.
- Jangan pernah mencoba mengakali perlindungan (perintah destruktif seperti `rm -rf /` diblokir total).

## Format jawaban (dirender berwarna di terminal)
- Pakai Markdown: `##` judul, **tebal**, `kode`, daftar bullet, tabel `| a | b |`, dan blok kode ```bahasa.
- Saat menyebut file, tulis path-nya dalam `backtick`. Jangan terlalu panjang."""

PLAN_NOTE = """
## MODE PLAN (read-only)
Kamu tidak boleh mengubah file. Analisis kode, susun rencana langkah demi langkah, dan tunggu user beralih ke mode build."""

EXPLORE_SYSTEM = """Kamu sub-agent penelusur CodinX (read-only). Jelajahi codebase dengan read/list/glob/grep/webfetch,
lalu beri jawaban ringkas dan akurat (sebut path:baris). Jangan mengubah apa pun."""


def _git_info(cwd):
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, timeout=3)
        return "ya" if r.stdout.strip() == "true" else "tidak"
    except Exception:
        return "tidak"


def _project_docs(cwd):
    docs, seen = [], set()
    d = cwd
    while True:
        for n in ("AGENTS.md", "CLAUDE.md"):
            f = os.path.join(d, n)
            if os.path.isfile(f) and f not in seen:
                seen.add(f)
                try:
                    docs.append((f, open(f, encoding="utf-8", errors="replace").read()[:6000]))
                except OSError:
                    pass
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    g = os.path.expanduser("~/.codinx/AGENTS.md")
    if os.path.isfile(g):
        docs.append((g, open(g, encoding="utf-8", errors="replace").read()[:6000]))
    return docs


class Agent:
    def __init__(self, app):
        self.app = app
        self.cfg, self.ui = app.cfg, app.ui

    # ------------------------------------------------------------ prompt
    def system_prompt(self, sub=False):
        ctx = self.app.ctx
        if sub:
            return EXPLORE_SYSTEM
        parts = [SYSTEM]
        if ctx.mode == "plan":
            parts.append(PLAN_NOTE)
        try:
            top = ", ".join(sorted(os.listdir(ctx.cwd))[:40])
        except OSError:
            top = ""
        parts.append(f"\n## Lingkungan\n- folder kerja: {ctx.cwd}\n- repo git: {_git_info(ctx.cwd)}\n- OS: {platform.system()} {platform.release()}\n"
                     f"- waktu: {geo.now(self.cfg).strftime('%Y-%m-%d %H:%M %Z')}\n- isi folder: {top}")
        mem = memory.prompt_block(ctx.cwd)
        if mem:
            parts.append("\n## Memori (ingatan jangka panjang tentang user/proyek)\n" + mem)
        sk = skills.index_block(ctx.cwd)
        if sk:
            parts.append("\n## Skills tersedia (muat dengan tool `skill` bila relevan)\n" + sk)
        for f, body in _project_docs(ctx.cwd):
            parts.append(f"\n## Instruksi proyek ({f})\n{body}")
        return "\n".join(parts)

    def tool_schemas(self, sub=False):
        ctx, perms = self.app.ctx, self.app.perms
        names = SUBAGENT_TOOLS if sub else list(SCHEMAS)
        out = []
        for n in names:
            if ctx.mode == "plan" and n in PLAN_HIDDEN and not sub:
                continue
            key = tools.PERM_KEY.get(n, n)
            if n == "webfetch":
                if not (perms.enabled("webfetch") or perms.enabled("localhost")):
                    continue
            elif not perms.enabled(key):
                continue
            out.append(SCHEMAS[n])
        return out

    # ------------------------------------------------------------ one model call
    def _call(self, messages, tool_schemas, stream=True):
        ok, via_trial, note = tiers.precheck(self.cfg, self.cfg["model"])
        if not ok:
            self.ui.err(note)
            return None, None
        if note:
            self.ui.info(note)
        s = self.app.session
        if stream:
            self.ui.stream_begin()
        try:
            msg, usage = api.chat(self.cfg, self.app.key, messages, tool_schemas,
                                  on_text=self.ui.stream_text if stream else None,
                                  on_reasoning=self.ui.stream_reasoning if stream else None,
                                  conv_id=s.id)
        except api.ApiError as e:
            if stream:
                self.ui.stream_end()
            self.ui.err(str(e))
            return None, None
        except BaseException:
            if stream:
                self.ui.stream_end()
            raise
        if stream:
            self.ui.stream_end()
        tiers.record(self.cfg, self.cfg["model"], usage.get("total_tokens", 0), via_trial)
        s.last_prompt_tokens = usage.get("prompt_tokens", 0)
        s.tokens_total += usage.get("total_tokens", 0)
        return msg, usage

    # ------------------------------------------------------------ main turn
    def turn(self, text):
        s, ctx, ui = self.app.session, self.app.ctx, self.ui
        turn = s.begin_turn(text)
        ctx.backups = turn["backups"]
        s.redo_stack.clear()
        s.messages.append({"role": "user", "content": text})
        final, last_sig, repeats = "", None, 0
        try:
            for step in range(int(self.cfg.get("max_steps", 60))):
                msgs = [{"role": "system", "content": self.system_prompt()}] + s.messages
                msg, _usage = self._call(msgs, self.tool_schemas())
                if msg is None:
                    if step == 0:
                        s.drop_turn()
                    break
                calls = msg.get("tool_calls")
                s.messages.append({"role": "assistant", "content": msg.get("content") or "", **({"tool_calls": calls} if calls else {})})
                final = msg.get("content") or final
                if not calls:
                    if not msg.get("content"):
                        ui.warn("Model mengembalikan respons kosong.")
                    break
                for tc in calls:
                    name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"] or "{}")
                        if not isinstance(args, dict):
                            raise ValueError
                    except ValueError:
                        s.messages.append({"role": "tool", "tool_call_id": tc["id"], "content": "Error: argumen bukan JSON object yang valid."})
                        continue
                    sig = (name, json.dumps(args, sort_keys=True))
                    repeats = repeats + 1 if sig == last_sig else 1
                    last_sig = sig
                    ui.tool_start(name, tools.summarize(name, args))
                    if repeats >= 3:
                        result = "Error: panggilan identik diulang 3x. Hentikan loop ini dan ubah pendekatan."
                    else:
                        result = tools.run(ctx, name, args)
                    ui.tool_result(result, ok=not result.startswith("Error"))
                    s.messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                if repeats >= 5:
                    ui.warn("Loop berulang terdeteksi; dihentikan.")
                    break
                if s.last_prompt_tokens > 0.8 * int(self.cfg.get("context_limit", 128000)):
                    ui.info("Konteks hampir penuh, meringkas otomatis…")
                    self.compact()
            else:
                ui.warn(f"Mencapai batas {self.cfg.get('max_steps', 60)} langkah. Ketik 'lanjut' untuk meneruskan.")
        except KeyboardInterrupt:
            ui.spin_stop()
            ui.p()
            ui.warn("Dihentikan.")
            self._repair()
        s.save()
        return final

    def _repair(self):
        """Pastikan tiap tool_call punya hasil, supaya riwayat tetap valid setelah Ctrl-C."""
        msgs = self.app.session.messages
        answered = {m.get("tool_call_id") for m in msgs if m["role"] == "tool"}
        for m in list(msgs):
            for tc in m.get("tool_calls") or []:
                if tc["id"] not in answered:
                    msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": "[dibatalkan oleh user]"})

    # ------------------------------------------------------------ compaction
    def compact(self):
        s = self.app.session
        if len(s.messages) < 4:
            return False
        ask = {"role": "user", "content": "Ringkas seluruh percakapan di atas untuk dilanjutkan di sesi baru: tujuan user, keputusan, "
               "file yang diubah, status tugas, dan langkah berikutnya. Padat namun lengkap."}
        msgs = [{"role": "system", "content": "Kamu peringkas percakapan coding."}] + s.messages + [ask]
        msg, _ = self._call(msgs, None, stream=False)
        if msg is None or not msg.get("content"):
            return False
        s.messages = [{"role": "user", "content": "Ringkasan percakapan sebelumnya:\n\n" + msg["content"]},
                      {"role": "assistant", "content": "Dipahami. Saya lanjutkan dari ringkasan ini."}]
        s.turns.clear()
        s.last_prompt_tokens = 0
        s.save()
        return True

    # ------------------------------------------------------------ subagent
    def subagent(self, description, prompt):
        ctx, ui = self.app.ctx, self.ui
        ui.p(c("muted", f"  ↳ sub-agent: {description}"))
        msgs = [{"role": "system", "content": self.system_prompt(sub=True)}, {"role": "user", "content": prompt}]
        final = ""
        for _ in range(20):
            msg, _u = self._call(msgs, self.tool_schemas(sub=True), stream=False)
            if msg is None:
                return "Error: sub-agent gagal dipanggil."
            calls = msg.get("tool_calls")
            msgs.append({"role": "assistant", "content": msg.get("content") or "", **({"tool_calls": calls} if calls else {})})
            final = msg.get("content") or final
            if not calls:
                break
            for tc in calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except ValueError:
                    args = {}
                ui.tool_start("  ↳ " + name, tools.summarize(name, args))
                res = tools.run(ctx, name, args) if name in SUBAGENT_TOOLS else "Error: tool tidak diizinkan untuk sub-agent."
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": res})
        return final or "(sub-agent tidak menghasilkan jawaban)"
        
