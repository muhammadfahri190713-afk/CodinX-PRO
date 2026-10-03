"""Agent loop: prompt -> model -> tool calls -> hasil -> ... (mode kawat adaptif, skills, memori, sub-agent)."""
import json
import os
import platform
import re
import subprocess

from . import agents, api, caps, fsutil, geo, log, mcp, memory, skills, tiers, tools, wire
from .tools import PLAN_HIDDEN, SCHEMAS, SUBAGENT_TOOLS
from .themes import c

SYSTEM = """Kamu adalah CodinX, agent coding otonom yang berjalan di terminal milik user (Linux atau Termux).
Tugasmu: benar-benar menyelesaikan pekerjaan — membuat, mengubah, menjalankan, dan memverifikasi kode/file — bukan sekadar menyarankan.

## Cara kerja
- Balas dengan bahasa yang dipakai user (user Indonesia -> jawab Indonesia). Singkat, langsung ke inti.
- Baca dulu sebelum mengubah. Pakai `edit` untuk perubahan kecil, `write` untuk file baru. Jangan menebak isi file.
- Jalankan dan uji hasil kerjamu dengan `bash` (test, build, lint, curl/webfetch ke localhost) sebelum menyatakan selesai.
- Untuk pekerjaan >2 langkah, buat rencana dengan `todowrite` lalu perbarui statusnya.
- Server/proses panjang: `bash` dengan background=true, lalu cek dengan `webfetch` (mis. http://localhost:3000).
- Gunakan `task` untuk riset codebase besar atau mendelegasikan ke sub-agent khusus (parameter `agent`), `websearch` + `webfetch` untuk info
  terbaru di web, `multiedit` untuk beberapa perubahan di satu file, dan `table` bila data paling jelas sebagai tabel (bisa disimpan ke .csv/.md/.json).

## Memori & skills
- KAMU MENGINGAT seluruh percakapan ini: riwayat lengkap selalu dikirim bersama pesan user. Jangan pernah bilang
  tidak bisa mengingat pesan sebelumnya; rujuk saja isi riwayat di atas.
- Bagian "Memori" di bawah berisi fakta tentang user/proyek: pakai, jangan menanyakan ulang. Fakta baru yang penting
  (nama, preferensi, aturan proyek) simpan dengan tool `memory` (jangan simpan rahasia/API key).
- Jika tugas cocok dengan sebuah skill, panggil tool `skill` (nama) SEBELUM mengerjakan lalu ikuti instruksinya.
  Jika instruksi skill sudah ada di percakapan ([SKILL AKTIF: ...]), langsung ikuti tanpa memanggil ulang.

## Izin
- Tool sensitif meminta izin user. Jika user MENOLAK, jangan ulangi; coba cara/tool alternatif atau jelaskan singkat.
- Perintah destruktif (mis. `rm -rf /`) diblokir total; jangan mencoba mengakalinya.

## Format jawaban (dirender berwarna di terminal)
- Markdown: `##` judul, **tebal**, `kode`, bullet, tabel `| a | b |`, dan blok kode ```bahasa. Path file dalam `backtick`. Jangan bertele-tele."""

PLAN_NOTE = """
## MODE PLAN (read-only)
Kamu tidak boleh mengubah file. Analisis kode, susun rencana langkah demi langkah, dan tunggu user beralih ke mode build."""

NOTOOLS_NOTE = """
## TANPA TOOL
Model/proxy ini tidak mendukung pemanggilan tool. Jawab sebagai chat biasa. Bila perlu tindakan, berikan perintah/kode
lengkap dan siap-salin agar user menjalankannya sendiri (user bisa mengetik `!perintah` di CodinX)."""

EXPLORE_SYSTEM = """Kamu sub-agent penelusur CodinX (read-only). Jelajahi codebase dengan read/list/glob/grep/webfetch,
lalu beri jawaban ringkas dan akurat (sebut path:baris). Jangan mengubah apa pun."""

TOOL_ERR = re.compile(r"(?i)tool|function|role|schema|parameter|unsupported|not support")


def _git_info(cwd):
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, timeout=3)
        return "ya" if r.stdout.strip() == "true" else "tidak"
    except Exception:
        return "tidak"


def _project_docs(cwd):
    docs, seen, d = [], set(), cwd
    while True:
        for n in ("AGENTS.md", "CLAUDE.md"):
            f = os.path.join(d, n)
            if os.path.isfile(f) and f not in seen:
                seen.add(f)
                try:
                    docs.append((f, fsutil.read_text(f)[:6000]))
                except OSError:
                    pass
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    g = os.path.expanduser("~/.codinx/AGENTS.md")
    if os.path.isfile(g):
        docs.append((g, fsutil.read_text(g)[:6000]))
    return docs


class Agent:
    def __init__(self, app):
        self.app = app
        self.cfg, self.ui = app.cfg, app.ui
        self._warned_hist = False

    # ------------------------------------------------------------ mode kawat
    def modes(self):
        cap = caps.get(self.cfg["model"])
        tm, hm = self.cfg.get("tool_mode", "auto"), self.cfg.get("history_mode", "auto")
        return (cap.get("tools", "native") if tm == "auto" else tm), (cap.get("history", "native") if hm == "auto" else hm)

    def max_chars(self):
        return int(int(self.cfg.get("context_limit", 128000)) * 3 * 0.6)

    def conv_id(self):
        s = self.app.session
        if self.cfg.get("conv_source") == "server" and self.cfg.get("conv_field"):
            return s.remote_conv or None
        return s.id

    # ------------------------------------------------------------ prompt
    def skill_block(self, text):
        """Skill yang cocok dengan pesan user: isi (skor tinggi) disuntik ke system prompt, sisanya jadi petunjuk."""
        if "[SKILL AKTIF:" in text:
            return ""
        ms = skills.match(text, self.app.cwd)
        inject = [s for sc, s in ms if sc >= 3][:2]
        hint = [s["name"] for sc, s in ms if 2 <= sc < 3 and s not in inject][:3]
        parts = []
        for sk in inject:
            body = skills.load(sk["name"], self.app.cwd) or ""
            parts.append(f"[SKILL OTOMATIS: {sk['name']}] (cocok dengan permintaan user — ikuti)\n{body[:5000]}")
        if hint:
            parts.append("Skill yang mungkin relevan: " + ", ".join(hint))
        if inject:
            self.ui.p(c("muted", "  ▸ skill otomatis: " + ", ".join(s["name"] for s in inject)))
        return "\n\n".join(parts)

    def system_prompt(self, sub=False, extra=""):
        ctx = self.app.ctx
        if sub:
            return EXPLORE_SYSTEM
        tm, _ = self.modes()
        parts = [SYSTEM]
        if ctx.mode == "plan":
            parts.append(PLAN_NOTE)
        if tm == "none":
            parts.append(NOTOOLS_NOTE)
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
            parts.append("\n## Skills tersedia\n" + sk)
        ag = agents.index_block(ctx.cwd)
        if ag:
            parts.append("\n## Sub-agent khusus (tool `task`, parameter agent)\n" + ag)
        if extra:
            parts.append("\n## Skill yang relevan untuk permintaan ini\n" + extra)
        for f, body in _project_docs(ctx.cwd):
            parts.append(f"\n## Instruksi proyek ({f})\n{body}")
        return "\n".join(parts)

    def tool_schemas(self, sub=False, names=None):
        ctx, perms = self.app.ctx, self.app.perms
        if self.modes()[0] == "none":
            return []
        out = []
        for n in (names or (SUBAGENT_TOOLS if sub else list(SCHEMAS))):
            if n not in SCHEMAS or (sub and n == "task"):
                continue
            if ctx.mode == "plan" and n in PLAN_HIDDEN and not sub:
                continue
            key = tools.PERM_KEY.get(n, n)
            if n in ("webfetch", "websearch"):
                if not (perms.enabled("webfetch") or perms.enabled("localhost")):
                    continue
            elif not perms.enabled(key):
                continue
            out.append(SCHEMAS[n])
        if not sub and ctx.mode != "plan" and perms.enabled("mcp"):
            mcp.manager.ensure_started(self.ui)
            out += mcp.manager.schemas()
        return out

    # ------------------------------------------------------------ satu panggilan model
    def _fallback_to_text(self, err, tm, schemas, messages):
        if self.cfg.get("tool_mode", "auto") != "auto" or tm != "native":
            return False
        had_tools = bool(schemas) or any(m["role"] == "tool" for m in messages)
        if had_tools and err.status in (400, 422) and TOOL_ERR.search((err.body or "") + str(err)):
            caps.set(self.cfg["model"], tools="text")
            log.debug("fallback_text_tools", status=err.status, body=(err.body or "")[:200])
            self.ui.info("Proxy/model menolak tool native → otomatis memakai mode tool teks (disimpan untuk model ini).")
            return True
        return False

    def _call(self, system, messages, schemas, stream=True, charge=True):
        ok, via_trial, note = tiers.precheck(self.cfg, self.cfg["model"])
        if not ok:
            self.ui.err(note)
            return None, None
        if note:
            self.ui.info(note)
        s = self.app.session
        valid = [x["function"]["name"] for x in (schemas or [])]
        msg = usage = meta = None
        for _attempt in range(3):
            tm, hm = self.modes()
            wire_msgs = wire.to_wire(system, messages, hm, tm, schemas if tm == "text" else None, self.max_chars())
            log.debug("llm_request", model=self.cfg["model"], tool_mode=tm, history=hm, wire_msgs=len(wire_msgs),
                      roles=[m["role"] for m in wire_msgs][-4:], chars=sum(len(m.get("content") or "") for m in wire_msgs), tools=len(schemas or []))
            filt = wire.CallFilter(self.ui.stream_text) if stream else None
            if stream:
                self.ui.stream_begin()
            try:
                msg, usage, meta = api.chat(self.cfg, self.app.key, wire_msgs, schemas if (tm == "native" and schemas) else None,
                                            on_text=filt.feed if filt else None,
                                            on_reasoning=self.ui.stream_reasoning if stream else None,
                                            conv_id=self.conv_id())
                if filt:
                    filt.flush()
                if stream:
                    self.ui.stream_end()
                break
            except api.ApiError as e:
                if stream:
                    self.ui.stream_end()
                if self._fallback_to_text(e, tm, schemas, messages):
                    continue
                self.ui.err(str(e))
                return None, None
            except BaseException:
                if stream:
                    self.ui.stream_end()
                raise
        else:
            self.ui.err("Gagal setelah beberapa percobaan.")
            return None, None

        # tool call yang ditulis sebagai teks (mode text, atau model native yang 'bandel')
        if not msg.get("tool_calls") and valid:
            clean, tcs = wire.parse_text_calls(msg.get("content", ""), valid)
            if tcs:
                msg["content"] = clean
                msg["tool_calls"] = [{"id": wire.new_call_id(), "type": "function",
                                      "function": {"name": t["name"], "arguments": json.dumps(t["arguments"], ensure_ascii=False)}} for t in tcs]
                if tm == "native" and self.cfg.get("tool_mode", "auto") == "auto":
                    caps.set(self.cfg["model"], tools="text")
                    self.ui.info("Model menulis tool-call sebagai teks → mode tool teks diaktifkan untuk model ini.")
            elif wire.CALL_OPEN in (msg.get("content") or ""):
                msg["_bad_call"] = True

        log.debug("llm_response", usage=usage, meta=meta, tool_calls=[t["function"]["name"] for t in msg.get("tool_calls") or []],
                  chars=len(msg.get("content") or ""))
        if charge:
            tiers.record(self.cfg, self.cfg["model"], usage.get("total_tokens", 0), via_trial)
        s.last_prompt_tokens = usage.get("prompt_tokens", 0)
        s.tokens_total += usage.get("total_tokens", 0)
        if meta:
            s.remote_id = meta.get("id") or s.remote_id
            s.remote_conv = meta.get("conv") or s.remote_conv
        self._check_history_dropped(usage, wire_msgs, hm, len(messages))
        return msg, usage

    def _check_history_dropped(self, usage, wire_msgs, hm, n_msgs):
        """Sinyal murah: proxy melaporkan prompt_tokens jauh lebih kecil dari yang kita kirim -> riwayat tidak dibaca."""
        if self._warned_hist or hm != "native" or usage.get("estimated") or n_msgs < 4:
            return
        sent = sum(len(m.get("content") or "") for m in wire_msgs) // 4
        got = usage.get("prompt_tokens", 0)
        if sent >= 800 and 0 < got < 0.35 * sent:
            self._warned_hist = True
            self.ui.warn(f"Proxy hanya menghitung {got} token prompt dari ±{sent} yang dikirim — riwayat percakapan kemungkinan TIDAK dibaca. "
                         "Jalankan /doctor atau /historymode flat.")

    # ------------------------------------------------------------ giliran utama
    def turn(self, text):
        s, ctx, ui = self.app.session, self.app.ctx, self.ui
        turn = s.begin_turn(text)
        ctx.backups = turn["backups"]
        s.redo_stack.clear()
        s.messages.append({"role": "user", "content": text})
        extra = self.skill_block(text)
        final, last_sig, repeats, bad = "", None, 0, 0
        try:
            for step in range(int(self.cfg.get("max_steps", 60))):
                msg, _u = self._call(self.system_prompt(extra=extra), s.messages, self.tool_schemas())
                if msg is None:
                    if step == 0:
                        s.drop_turn()
                    break
                if msg.pop("_bad_call", False) and bad < 2:
                    bad += 1
                    names = ", ".join(x["function"]["name"] for x in self.tool_schemas())
                    s.messages.append({"role": "assistant", "content": msg.get("content") or "(blok tool tidak valid)"})
                    s.messages.append({"role": "user", "content": f"[sistem] Blok <tool_call> tidak valid atau tool tidak dikenal. "
                                       f"Tool yang ada: {names}. Ulangi dengan JSON valid persis sesuai protokol."})
                    continue
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
                    result = ("Error: panggilan identik diulang 3x. Hentikan loop ini dan ubah pendekatan."
                              if repeats >= 3 else tools.run(ctx, name, args))
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
        msgs = self.app.session.messages
        answered = {m.get("tool_call_id") for m in msgs if m["role"] == "tool"}
        for m in list(msgs):
            for tc in m.get("tool_calls") or []:
                if tc["id"] not in answered:
                    msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": "[dibatalkan oleh user]"})

    # ------------------------------------------------------------ kompaksi
    def compact(self):
        s = self.app.session
        if len(s.messages) < 4:
            return False
        ask = {"role": "user", "content": "Ringkas seluruh percakapan di atas untuk dilanjutkan di sesi baru: tujuan user, keputusan, fakta penting "
               "tentang user (nama, preferensi), file yang diubah, status tugas, dan langkah berikutnya. Padat namun lengkap."}
        msg, _ = self._call("Kamu peringkas percakapan coding.", s.messages + [ask], None, stream=False)
        if msg is None or not msg.get("content"):
            return False
        s.messages = [{"role": "user", "content": "Ringkasan percakapan sebelumnya:\n\n" + msg["content"]},
                      {"role": "assistant", "content": "Dipahami. Saya lanjutkan dari ringkasan ini."}]
        s.turns.clear()
        s.last_prompt_tokens = 0
        s.save()
        return True

    # ------------------------------------------------------------ sub-agent
    def subagent(self, description, prompt, agent=""):
        ctx, ui = self.app.ctx, self.ui
        spec = agents.resolve(agent, ctx.cwd) if agent else None
        if agent and not spec:
            return f"Error: sub-agent '{agent}' tidak ada. Tersedia: {', '.join(agents.discover(ctx.cwd)) or '-'}"
        allowed = (spec["tools"] if spec and spec["tools"] else SUBAGENT_TOOLS)
        schemas = self.tool_schemas(sub=True, names=allowed)
        if not schemas:
            return "Error: tool tidak tersedia untuk sub-agent pada model ini."
        system = (spec["prompt"] + f"\n\nFolder kerja: {ctx.cwd}") if spec else EXPLORE_SYSTEM
        ui.p(c("muted", f"  ↳ sub-agent{' ' + agent if agent else ''}: {description}"))
        names = {x["function"]["name"] for x in schemas}
        msgs = [{"role": "user", "content": prompt}]
        final = ""
        for _ in range(25):
            msg, _u = self._call(system, msgs, schemas, stream=False)
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
                res = tools.run(ctx, name, args) if name in names else "Error: tool tidak diizinkan untuk sub-agent ini."
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": res})
        return final or "(sub-agent tidak menghasilkan jawaban)"
