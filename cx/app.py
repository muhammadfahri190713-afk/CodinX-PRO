"""Interactive REPL, slash commands, connect wizard, model picker, permission centre."""
import getpass
import glob as _glob
import json
import os
import re
import shlex
import subprocess
import sys
import time

from . import __version__, api, config, geo, memory, skills, tiers, tools
from . import themes as T
from .agent import Agent
from .perms import DEFAULT_POLICY, POLICY_CYCLE, Perms
from .session import Session
from .themes import c
from .ui import UI

try:
    import readline
except ImportError:
    readline = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, ".seed")
PKG_COMMANDS = os.path.join(ROOT, "commands")

COMMANDS = [
    ("/help", "daftar perintah"), ("/new", "sesi baru"), ("/sessions", "lanjutkan sesi lama"),
    ("/models", "pilih model  (/models pro · /models claude)"), ("/connect", "atur endpoint + API key"),
    ("/permissions", "pengaturan izin tool (web, kamera, terminal…)"), ("/tier", "lihat/ubah paket FREE·PRO·MAX"),
    ("/status", "paket, Dinar, konteks"), ("/plan", "mode plan (read-only)"), ("/build", "mode build (bisa edit)"),
    ("/auto", "auto-izinkan semua (hard-deny tetap)"), ("/compact", "ringkas konteks"), ("/undo", "batalkan giliran terakhir"),
    ("/redo", "ulangi yang di-undo"), ("/init", "buat AGENTS.md"), ("/memory", "lihat/tambah/hapus memori"),
    ("/skills", "daftar skills"), ("/theme", "ganti tema warna"), ("/details", "tampil/sembunyi detail tool"),
    ("/thinking", "tampil/sembunyi proses berpikir"), ("/export", "simpan percakapan ke .md"), ("/share", "ekspor lokal untuk dibagikan"),
    ("/location", "provinsi + zona waktu (reset Dinar)"), ("/clear", "bersihkan layar"), ("/exit", "keluar"),
]
ALIASES = {"/quit": "/exit", "/q": "/exit", "/izin": "/permissions", "/perm": "/permissions", "/resume": "/sessions",
           "/continue": "/sessions", "/clear-session": "/new", "/usage": "/status", "/model": "/models", "/summarize": "/compact",
           "/themes": "/theme", "/session": "/sessions"}

PERM_ROWS = [
    ("bash", "Jalankan perintah terminal"), ("edit", "Tulis / ubah file"), ("read", "Baca file"),
    ("webfetch", "Akses web / internet"), ("localhost", "Akses localhost:3000 dkk"), ("camera", "Kamera (foto)"),
    ("task", "Sub-agent"), ("memory", "Memori jangka panjang"), ("skill", "Skills"),
    ("external_directory", "File di luar folder proyek"),
]
POLICY_LABEL = {"default": "○ bawaan", "ask": "? selalu tanya", "allow": "✓ selalu izinkan", "deny": "✗ tolak", "off": "⊘ mati"}


def _rl(s):
    return re.sub(r"(\033\[[0-9;]*m)", "\001\\1\002", s)


class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.ui = UI()
        self.ui.show_thinking = cfg.get("show_thinking", False)
        self.ui.show_details = cfg.get("show_details", True)
        T.set_theme(cfg.get("theme", "codinx"))
        self.key = config.get_key()
        self.perms = Perms(cfg)
        self.cwd = os.getcwd()
        self.session = Session(self.cwd)
        self.ctx = tools.Ctx(self.cwd, self.perms, self.ui, self.session, cfg)
        self.ctx.mode = cfg.get("agent", "build") if cfg.get("agent") in ("build", "plan") else "build"
        self.agent = Agent(self)
        self.ctx.subagent_fn = self.agent.subagent

    # ------------------------------------------------------------ connection
    def _import_seed(self):
        try:
            with open(SEED) as f:
                d = json.load(f)
            if d.get("api_key"):
                config.set_key(d["api_key"])
                self.key = d["api_key"]
            if d.get("base_url"):
                self.cfg["base_url"] = config.normalize_url(d["base_url"])
            config.save(self.cfg)
            size = os.path.getsize(SEED)
            with open(SEED, "r+b") as f:       # timpa lalu hapus: tidak ada kunci plaintext tersisa
                f.write(os.urandom(size))
            os.remove(SEED)
            self.ui.ok("Kunci API diimpor ke brankas terenkripsi (~/.codinx/.key.enc) dan file seed dihapus.")
            return True
        except (OSError, ValueError):
            return False

    def ensure_connected(self):
        if self.key and self.cfg.get("base_url"):
            return True
        if os.path.isfile(SEED) and self._import_seed():
            return True
        self.ui.warn("Belum terhubung ke endpoint.")
        return self.connect_wizard()

    def connect_wizard(self):
        cur = self.cfg.get("base_url") or config.DEFAULT_BASE_URL
        try:
            url = input(c("accent2", "  Endpoint ") + c("muted", f"[{cur}] › ")).strip() or cur
            key = getpass.getpass(c("accent2", "  API key ") + c("muted", "(tersembunyi, kosong = tetap) › ")).strip()
        except (EOFError, KeyboardInterrupt):
            self.ui.p()
            return False
        self.cfg["base_url"] = config.normalize_url(url)
        if key:
            config.set_key(key)
            self.key = key
        config.save(self.cfg)
        if not self.key:
            self.ui.err("API key kosong.")
            return False
        try:
            ids = api.list_models(self.cfg, self.key)
            self.ui.ok(f"Terhubung ke {self.cfg['base_url']} · {len(ids)} model tersedia di proxy")
        except api.ApiError as e:
            self.ui.warn(f"Tersimpan, tapi daftar model gagal diambil: {str(e)[:160]}")
        return True

    # ------------------------------------------------------------ helpers
    def set_session(self, s):
        self.session = s
        self.ctx.session = s
        self.ctx.backups = {}

    def save_cfg(self):
        config.save(self.cfg)

    def footer(self):
        st = tiers.status(self.cfg)
        lim = max(int(self.cfg.get("context_limit", 128000)), 1)
        pct = min(100, int(self.session.last_prompt_tokens * 100 / lim))
        bits = [self.ctx.mode, self.cfg["model"]]
        bits.append(f"Dinar {st['dinar']}/{st['limit']}" if st["tier"] == "FREE" else f"paket {st['tier']}")
        bits.append(f"ctx {pct}%")
        if self.perms.auto:
            bits.append("AUTO")
        return "  " + c("muted", " · ".join(bits))

    def prompt(self):
        return _rl(c("accent" if self.ctx.mode == "build" else "warn", "┃ ", bold=True))

    def custom_commands(self):
        found = {}
        for d in (PKG_COMMANDS, os.path.join(config.HOME, "commands"), os.path.join(self.cwd, ".codinx", "commands")):
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if f.endswith(".md"):
                    try:
                        meta, body = skills.parse(open(os.path.join(d, f), encoding="utf-8").read())
                    except OSError:
                        continue
                    found["/" + f[:-3]] = (meta.get("description", ""), body.strip())
        return found

    def all_command_names(self):
        return sorted({x[0] for x in COMMANDS} | set(self.custom_commands()))

    def setup_readline(self):
        if not readline:
            return
        try:
            readline.read_history_file(config.HISTORY)
        except OSError:
            pass
        readline.set_history_length(1000)
        readline.set_completer_delims(" \t\n")

        def completer(text, state):
            buf = readline.get_line_buffer()
            if buf.startswith("/") and " " not in buf:
                opts = [x for x in self.all_command_names() if x.startswith(buf)]
            elif text.startswith("@"):
                opts = ["@" + p + ("/" if os.path.isdir(p) else "") for p in _glob.glob(os.path.expanduser(text[1:]) + "*")]
            else:
                opts = []
            return opts[state] if state < len(opts) else None
        readline.set_completer(completer)
        readline.parse_and_bind("tab: complete")

    def save_history(self):
        if readline:
            try:
                readline.write_history_file(config.HISTORY)
                os.chmod(config.HISTORY, 0o600)
            except OSError:
                pass

    # ------------------------------------------------------------ input expansion
    def attach_mentions(self, text):
        extra = []
        for m in re.finditer(r"(?<!\S)@([\w./~\-]+)", text):
            p = self.ctx.path(m.group(1))
            if os.path.isfile(p):
                try:
                    body = open(p, encoding="utf-8", errors="replace").read()[:20000]
                    extra.append(f'<file path="{p}">\n{body}\n</file>')
                except OSError:
                    pass
            elif os.path.isdir(p):
                extra.append(f'<dir path="{p}">\n' + "\n".join(sorted(os.listdir(p))[:200]) + "\n</dir>")
        return text + ("\n\n" + "\n".join(extra) if extra else "")

    def expand_template(self, tpl, args):
        try:
            parts = shlex.split(args)
        except ValueError:
            parts = args.split()
        tpl = tpl.replace("$ARGUMENTS", args)
        for i in range(9, 0, -1):
            tpl = tpl.replace(f"${i}", parts[i - 1] if len(parts) >= i else "")
        tpl = re.sub(r"!`([^`]+)`", lambda m: "\n" + tools.t_bash(self.ctx, m.group(1)) + "\n", tpl)
        return self.attach_mentions(tpl)

    def shell(self, cmd):
        try:
            r = subprocess.run(["bash", "-c", cmd], cwd=self.cwd, capture_output=True, text=True, timeout=120)
            out = (r.stdout + r.stderr).strip()
        except subprocess.TimeoutExpired:
            out = "(timeout 120s)"
        self.ui.p(c("muted", out[:6000] or "(tanpa output)"))
        self.session.messages.append({"role": "user", "content": f"Saya menjalankan `{cmd}` di terminal. Outputnya:\n```\n{out[:8000]}\n```"})
        self.session.messages.append({"role": "assistant", "content": "Dicatat."})
        self.session.save()

    def run_turn(self, text):
        if not self.ensure_connected():
            return
        self.agent.turn(text)
        self.ui.p()

    # ------------------------------------------------------------ REPL
    def read_line(self):
        self.ui.p(self.footer())
        line = input(self.prompt())
        while line.endswith("\\"):
            line = line[:-1] + "\n" + input(_rl(c("muted", "… ")))
        return line

    def repl(self):
        self.setup_readline()
        ok = self.ensure_connected()
        prev = Session.latest_for(self.cwd)
        extra = ""
        if prev and ok:
            self.set_session(prev)
            extra = f"sesi dilanjutkan: {prev.title[:40] or prev.id} ({len(prev.messages)} pesan) · /new untuk baru"
        self.ui.banner(self.cfg["model"], self.ctx.mode, tiers.tier_of(self.cfg), self.cwd, extra)
        if ok:
            m = tiers.can_use_model(self.cfg, self.cfg["model"])
            if not m[0]:
                self.ui.warn(m[2])
        while True:
            try:
                line = self.read_line()
            except EOFError:
                break
            except KeyboardInterrupt:
                self.ui.p("\n" + c("muted", "  (Ctrl-C) ketik /exit atau Ctrl-D untuk keluar"))
                continue
            line = line.strip()
            if not line:
                continue
            try:
                if line.startswith("/"):
                    if self.slash(line) == "exit":
                        break
                elif line.startswith("!"):
                    self.shell(line[1:].strip())
                else:
                    self.run_turn(self.attach_mentions(line))
            except KeyboardInterrupt:
                self.ui.p("\n" + c("warn", "  dihentikan"))
        self.session.save()
        self.save_history()
        self.ui.p(c("muted", "  sampai jumpa 👋"))

    # ------------------------------------------------------------ slash commands
    def slash(self, line):
        name, _, arg = line.partition(" ")
        name = ALIASES.get(name.lower(), name.lower())
        arg = arg.strip()
        fn = getattr(self, "cmd_" + name[1:].replace("-", "_"), None)
        if fn:
            return fn(arg)
        custom = self.custom_commands().get(name)
        if custom:
            return self.run_turn(self.expand_template(custom[1], arg))
        self.ui.err(f"Perintah {name} tidak dikenal. Ketik /help")

    def cmd_help(self, arg):
        rows = [[n, d] for n, d in COMMANDS]
        self.ui.table(["perintah", "fungsi"], rows, "CodinX — perintah")
        cc = self.custom_commands()
        if cc:
            self.ui.table(["custom", "fungsi"], [[n, d] for n, (d, _) in cc.items()], "Perintah custom")
        self.ui.p(c("muted", "  @file lampirkan file · !perintah jalankan shell · akhiri baris dengan \\ untuk multi-baris · Ctrl-C hentikan"))

    def cmd_exit(self, arg):
        return "exit"

    def cmd_clear(self, arg):
        sys.stdout.write("\033[2J\033[H")
        self.ui.banner(self.cfg["model"], self.ctx.mode, tiers.tier_of(self.cfg), self.cwd)

    def cmd_new(self, arg):
        self.session.save()
        self.set_session(Session(self.cwd))
        self.ui.ok("Sesi baru dimulai.")

    def cmd_connect(self, arg):
        self.connect_wizard()

    def cmd_status(self, arg):
        st = tiers.status(self.cfg)
        g = geo.lookup()
        rows = [["model", self.cfg["model"]], ["paket", st["tier"]], ["mode", self.ctx.mode],
                ["endpoint", self.cfg["base_url"]], ["folder", self.cwd], ["sesi", f"{self.session.id} ({len(self.session.messages)} pesan)"],
                ["token konteks", f"{self.session.last_prompt_tokens}/{self.cfg.get('context_limit')}"],
                ["request hari ini", st["requests"]]]
        if st["tier"] == "FREE":
            rows.append(["Dinar", f"{st['dinar']}/{st['limit']}  (reset 00:00 dalam {st['reset_in']})"])
        rows.append(["zona waktu", f"{geo.tz_name(self.cfg)}" + (f" · {g.get('province')}" if g.get("province") else "")])
        if st["trials"]:
            rows.append(["trial terpakai", ", ".join(f"{k}:{v}" for k, v in st["trials"].items())])
        self.ui.table(["", ""], rows, "Status")

    def cmd_location(self, arg):
        g = geo.lookup(force=(arg == "refresh"))
        rows = [["provinsi", g.get("province") or "-"], ["kota", g.get("city") or "-"], ["negara", g.get("country") or "-"],
                ["zona waktu", geo.tz_name(self.cfg)], ["sumber", g.get("source")],
                ["reset berikutnya", geo.next_reset(self.cfg).strftime("%Y-%m-%d %H:%M %Z")], ["sisa", geo.remaining_str(self.cfg)]]
        self.ui.table(["", ""], rows, "Lokasi (untuk reset Dinar jam 00:00)")
        self.ui.p(c("muted", "  Lokasi dari IP publik via ipwho.is (di-cache 24 jam). Paksa zona waktu: edit \"timezone\" di config.json. /location refresh = ambil ulang."))

    def cmd_tier(self, arg):
        if not arg:
            st = tiers.status(self.cfg)
            self.ui.info(f"Paket saat ini: {st['tier']}. Ganti: /tier free | pro | max")
            return
        if arg.lower() not in ("free", "pro", "max"):
            self.ui.err("Pilih: free | pro | max")
            return
        self.cfg["tier"] = arg.lower()
        self.save_cfg()
        self.ui.ok(f"Paket diubah ke {arg.upper()}.")
        ok, _, msg = tiers.can_use_model(self.cfg, self.cfg["model"])
        if not ok:
            self.ui.warn(msg + " Pilih model lain dengan /models.")

    def cmd_plan(self, arg):
        self.ctx.mode = "plan"
        self.cfg["agent"] = "plan"
        self.save_cfg()
        self.ui.ok("Mode PLAN: read-only, tidak bisa mengubah file.")

    def cmd_build(self, arg):
        self.ctx.mode = "build"
        self.cfg["agent"] = "build"
        self.save_cfg()
        self.ui.ok("Mode BUILD: bisa membuat, mengedit, dan menjalankan.")

    def cmd_agent(self, arg):
        (self.cmd_plan if (arg == "plan" or (not arg and self.ctx.mode == "build")) else self.cmd_build)(arg)

    def cmd_auto(self, arg):
        self.perms.auto = not self.perms.auto
        (self.ui.warn if self.perms.auto else self.ui.ok)("AUTO " + ("AKTIF: semua izin 'tanya' dilewati (perintah destruktif tetap diblokir)." if self.perms.auto else "mati."))

    def cmd_details(self, arg):
        self.ui.show_details = not self.ui.show_details
        self.cfg["show_details"] = self.ui.show_details
        self.save_cfg()
        self.ui.ok("Detail tool: " + ("tampil" if self.ui.show_details else "disembunyikan"))

    def cmd_thinking(self, arg):
        self.ui.show_thinking = not self.ui.show_thinking
        self.cfg["show_thinking"] = self.ui.show_thinking
        self.save_cfg()
        self.ui.ok("Proses berpikir: " + ("tampil" if self.ui.show_thinking else "disembunyikan"))

    def cmd_theme(self, arg):
        if arg and T.set_theme(arg):
            self.cfg["theme"] = arg
            self.save_cfg()
            self.ui.ok(f"Tema: {arg}")
            return
        self.ui.p("  " + "  ".join(c("accent" if n == T.current() else "muted", n) for n in T.names()))
        self.ui.p(c("muted", "  pakai: /theme <nama>"))

    def cmd_compact(self, arg):
        if not self.ensure_connected():
            return
        self.ui.spin_start("meringkas")
        ok = self.agent.compact()
        self.ui.spin_stop()
        self.ui.ok("Konteks diringkas.") if ok else self.ui.warn("Tidak ada yang diringkas (terlalu pendek atau gagal).")

    def cmd_undo(self, arg):
        t = self.session.undo()
        if not t:
            return self.ui.warn("Tidak ada yang bisa di-undo.")
        self.ui.ok(f"Undo: {len(t['backups'])} file dikembalikan, pesan dihapus: \"{t['user'][:50]}\"")

    def cmd_redo(self, arg):
        t = self.session.redo()
        self.ui.ok("Redo berhasil.") if t else self.ui.warn("Tidak ada yang bisa di-redo.")

    def cmd_init(self, arg):
        self.run_turn("Analisis proyek ini (struktur, bahasa, cara build/test/run, konvensi) lalu buat atau perbarui file AGENTS.md "
                      "di root folder berisi panduan ringkas untuk agent coding. Jangan menulis rahasia.")

    def cmd_export(self, arg):
        name = arg or f"codinx-{self.session.id}.md"
        p = self.ctx.path(name)
        open(p, "w", encoding="utf-8").write(self.session.export_md())
        self.ui.ok("Diekspor: " + p)

    def cmd_share(self, arg):
        d = os.path.join(config.HOME, "shares")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, self.session.id + ".md")
        open(p, "w", encoding="utf-8").write(self.session.export_md())
        self.ui.ok("Ekspor lokal (tanpa upload): " + p)

    def cmd_skills(self, arg):
        sk = skills.discover(self.cwd)
        if not sk:
            return self.ui.info("Belum ada skill. Letakkan di ~/.codinx/skills/<nama>/SKILL.md")
        self.ui.table(["skill", "deskripsi"], [[n, s["description"][:70]] for n, s in sk.items()], "Skills")

    def cmd_memory(self, arg):
        sub, _, rest = arg.partition(" ")
        if sub == "add" and rest:
            self.ui.ok(f"Tersimpan (id {memory.add(rest, 'global')}).")
        elif sub in ("rm", "del", "hapus") and rest.strip().isdigit():
            self.ui.ok(f"{memory.remove(rest.strip())} dihapus.")
        elif sub == "clear":
            memory.clear()
            self.ui.ok("Memori dikosongkan.")
        else:
            items = memory.relevant(self.cwd)
            if not items:
                return self.ui.info("Memori kosong. /memory add <teks> — atau biarkan agent menyimpannya sendiri.")
            self.ui.table(["id", "lingkup", "isi"], [[i["id"], i["scope"], i["text"][:80]] for i in items], "Memori")

    def cmd_sessions(self, arg):
        items = Session.list_all()[:15]
        if not items:
            return self.ui.info("Belum ada sesi tersimpan.")
        self.ui.table(["#", "judul", "folder", "pesan"], [[i + 1, it["title"][:34] or it["id"], it["cwd"][-24:], it["n"]] for i, it in enumerate(items)], "Sesi")
        try:
            a = input(c("muted", "  nomor untuk dilanjutkan (enter batal) › ")).strip()
        except (EOFError, KeyboardInterrupt):
            return
        if a.isdigit() and 1 <= int(a) <= len(items):
            self.session.save()
            self.set_session(Session.load(items[int(a) - 1]["id"]))
            self.ui.ok(f"Sesi dilanjutkan: {self.session.title[:50]}")

    # ------------------------------------------------------------ models
    def cmd_models(self, arg):
        q = arg.strip().lower()
        cat = list(tiers.catalog())
        known = {m["id"] for m in cat}
        if self.key:
            try:
                cat += [{"name": i, "id": i, "role": "FREE", "trial": 0, "price": ""} for i in api.list_models(self.cfg, self.key) if i not in known]
            except api.ApiError:
                pass
        items = [m for m in cat if not q or q in m["id"].lower() or q in m["name"].lower() or q == m["role"].lower()]
        if not items:
            return self.ui.warn("Tidak ada model cocok.")
        cnt = {r: sum(1 for m in cat if m["role"] == r) for r in ("FREE", "PRO", "MAX")}
        self.ui.p(c("muted", f"  {len(cat)} model · FREE {cnt['FREE']} · PRO {cnt['PRO']} · MAX {cnt['MAX']} · paket kamu: ") + c("accent2", tiers.tier_of(self.cfg), bold=True))
        shown = items[:40]
        for i, m in enumerate(shown, 1):
            ok, via, _ = tiers.can_use_model(self.cfg, m["id"])
            mark = c("ok", "✓") if ok and not via else c("warn", "◐") if ok else c("muted", "🔒")
            cur = c("accent", " ◀ aktif", bold=True) if m["id"] == self.cfg["model"] else ""
            tag = f"[{m['role']}" + (f" · trial {m['trial']}x" if m.get("trial") else "") + "]"
            self.ui.p(f"  {i:>3} {mark} " + c("text" if ok else "muted", m["id"]) + " " + c("muted", tag) + cur)
        if len(items) > len(shown):
            self.ui.p(c("muted", f"  … {len(items) - len(shown)} lagi — persempit: /models claude · /models free · /models pro"))
        try:
            a = input(c("muted", "  pilih nomor / id (enter batal) › ")).strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not a:
            return
        pick = shown[int(a) - 1] if a.isdigit() and 1 <= int(a) <= len(shown) else next((m for m in cat if m["id"] == a), None)
        if not pick:
            return self.ui.err("Model tidak ditemukan.")
        ok, _, msg = tiers.can_use_model(self.cfg, pick["id"])
        if not ok:
            return self.ui.warn(msg)
        self.cfg["model"] = pick["id"]
        self.save_cfg()
        self.ui.ok(f"Model: {pick['id']}" + (f"  ({msg})" if msg else ""))

    # ------------------------------------------------------------ permission centre
    def cmd_permissions(self, arg):
        while True:
            rows = [[i + 1, t, POLICY_LABEL[self.perms.policy(t)] + (" (bawaan)" if t not in self.cfg.get("tool_policy", {}) and t in DEFAULT_POLICY else ""), d]
                    for i, (t, d) in enumerate(PERM_ROWS)]
            self.ui.table(["#", "izin", "status", "keterangan"], rows, "Pengaturan izin CodinX")
            self.ui.p(c("muted", "  ketik nomor = ganti status (bawaan → tanya → izinkan → tolak → mati) · r = reset semua · enter = selesai"))
            try:
                a = input(c("accent", "  izin › ")).strip().lower()
            except (EOFError, KeyboardInterrupt):
                self.ui.p()
                return
            if not a:
                return
            if a == "r":
                self.cfg["tool_policy"] = {}
                self.save_cfg()
                continue
            if a.isdigit() and 1 <= int(a) <= len(PERM_ROWS):
                t = PERM_ROWS[int(a) - 1][0]
                order = [x for x in POLICY_CYCLE if not (x == "default" and t in DEFAULT_POLICY)]
                cur = self.perms.policy(t)
                nxt = order[(order.index(cur) + 1) % len(order)] if cur in order else order[0]
                self.perms.set_policy(t, nxt)
