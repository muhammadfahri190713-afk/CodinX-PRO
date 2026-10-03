"""Terminal UI: banner, markdown renderer, spinner, permission prompt, tool cards."""
import difflib
import os
import re
import shutil
import sys
import textwrap
import threading
import time

from . import __version__
from . import highlight
from . import themes as T
from .themes import c

ANSI_RE = re.compile(r"\033\[[0-9;]*m")

GLYPHS = {
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "D": ["██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "X": ["██╗  ██╗", "╚██╗██╔╝", " ╚███╔╝ ", " ██╔██╗ ", "██╔╝ ██╗", "╚═╝  ╚═╝"],
}


def strip_ansi(s):
    return ANSI_RE.sub("", s)


def term_width():
    return shutil.get_terminal_size((80, 24)).columns


def banner_lines():
    return ["".join(GLYPHS[ch][r] for ch in "CODINX") for r in range(6)]


# ----------------------------------------------------------------- markdown
class Markdown:
    """Line-buffered streaming markdown renderer (headings, lists, code, tables, inline)."""

    def __init__(self, write):
        self.write = write
        self.buf = ""
        self.in_code = False
        self.lang = ""
        self.code = []
        self.table = []

    def feed(self, text):
        self.buf += text
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            self._line(line)

    def flush(self):
        if self.buf:
            self._line(self.buf)
            self.buf = ""
        self._end_table()
        if self.in_code:
            self._emit_code()
            self.in_code = False

    def _emit_code(self):
        lines = highlight.render("\n".join(self.code), self.lang)
        bar = c("muted", "  │ ")
        if lines is None:
            lines = [c("info", ln) for ln in self.code]
        self.write("".join(bar + ln + T.RESET + "\n" if T.ENABLED else bar + ln + "\n" for ln in lines))
        self.code = []

    # -- inline
    def inline(self, s):
        if not T.ENABLED:
            return s
        txt = T.fg("text")
        s = re.sub(r"`([^`]+)`", lambda m: T.fg("info") + m.group(1) + txt, s)
        s = re.sub(r"\*\*(.+?)\*\*", lambda m: T.BOLD + T.fg("accent2") + m.group(1) + T.UNBOLD + txt, s)
        s = re.sub(r"(?<!\*)\*(?!\s)([^*]+?)\*(?!\*)", lambda m: T.ITALIC + m.group(1) + "\033[23m", s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                   lambda m: T.UNDERLINE + m.group(1) + "\033[24m " + T.fg("muted") + "(" + m.group(2) + ")" + txt, s)
        return txt + s + T.RESET

    # -- tables
    def _end_table(self):
        if not self.table:
            return
        rows = [[x.strip() for x in r.strip().strip("|").split("|")] for r in self.table]
        self.table = []
        header, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-{2,}:?", x) for x in r)]
        n = len(header)
        has_header = any(h.strip() for h in header)
        body = [(r + [""] * n)[:n] for r in body]
        widths = [max(len(strip_ansi(x)) for x in col) for col in zip(header, *body)]
        avail = term_width() - (3 * n + 2)
        while sum(widths) > avail and max(widths) > 8:
            widths[widths.index(max(widths))] -= 1

        def wrap(x, w):
            return textwrap.wrap(x, max(w, 1), break_long_words=True, replace_whitespace=False) or [""]

        def line(l, m, r):
            return c("muted", l + m.join("─" * (w + 2) for w in widths) + r)
        bar = c("muted", "│")

        def row_lines(r, role, bold=False):
            cells = [wrap(x, w) for x, w in zip(r, widths)]
            h = max(len(cc) for cc in cells)
            return [bar + bar.join(" " + c(role, (cc[i] if i < len(cc) else "").ljust(w), bold=bold) + " "
                                   for cc, w in zip(cells, widths)) + bar for i in range(h)]
        out = [line("┌", "┬", "┐")]
        if has_header:
            out += row_lines(header, "accent2", bold=True)
            out.append(line("├", "┼", "┤"))
        for r in body:
            out += row_lines(r, "text")
        out.append(line("└", "┴", "┘"))
        self.write("\n".join(out) + "\n")

    def _line(self, ln):
        s = ln.rstrip("\r")
        if s.strip().startswith("```"):
            self._end_table()
            if not self.in_code:
                self.in_code = True
                self.lang = s.strip()[3:].strip()
                self.code = []
                self.write(c("muted", "  ┌─ " + (self.lang or "code")) + "\n")
            else:
                self._emit_code()
                self.in_code = False
                self.write(c("muted", "  └─") + "\n")
            return
        if self.in_code:
            self.code.append(s)          # ditampung sampai blok tertutup, lalu di-highlight sekaligus
            return
        if s.lstrip().startswith("|") and s.count("|") >= 2:
            self.table.append(s)
            return
        self._end_table()
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lvl, t = len(m.group(1)), re.sub(r"[*`]", "", m.group(2))
            if lvl == 1:
                self.write("\n" + c("accent", t.upper(), bold=True) + "\n" + c("accent", "━" * min(len(t), 60)) + "\n")
            elif lvl == 2:
                self.write("\n" + c("accent2", "▌ " + t, bold=True) + "\n")
            else:
                self.write(c("info", "▸ " + t, bold=True) + "\n")
            return
        if re.match(r"^\s*([-*_])\1{2,}\s*$", s):
            self.write(c("muted", "─" * min(term_width() - 2, 60)) + "\n")
            return
        m = re.match(r"^(\s*)[-*+]\s+(.*)$", s)
        if m:
            self.write(m.group(1) + c("accent", "• ") + self.inline(m.group(2)) + "\n")
            return
        m = re.match(r"^(\s*)(\d+)[.)]\s+(.*)$", s)
        if m:
            self.write(m.group(1) + c("accent", m.group(2) + ". ") + self.inline(m.group(3)) + "\n")
            return
        if s.startswith(">"):
            self.write(c("muted", "┃ ") + c("muted", s.lstrip("> "), italic=True) + "\n")
            return
        self.write(self.inline(s) + "\n")


# ------------------------------------------------------------------- the UI
class UI:
    def __init__(self):
        self.quiet = False
        self.show_thinking = False
        self.show_details = True
        self._stop = None
        self._t = None
        self._md = None
        self._mode = None

    # basic output
    def w(self, s=""):
        if not self.quiet:
            sys.stdout.write(s)
            sys.stdout.flush()

    def p(self, s=""):
        self.w(s + "\n")

    def info(self, s):
        self.p(c("info", "ℹ ") + c("text", s))

    def ok(self, s):
        self.p(c("ok", "✓ ") + c("text", s))

    def warn(self, s):
        self.p(c("warn", "⚠ ") + c("text", s))

    def err(self, s):
        self.p(c("err", "✗ ") + c("text", s))

    # banner / home
    def banner(self, model, agent, tier, cwd, extra=""):
        rows = banner_lines()
        self.p()
        n = len(rows)
        for i, r in enumerate(rows):
            self.p("  " + T.gradient(r, i / (n * 2), 0.5 + i / (n * 2)))
        self.p("  " + c("muted", f"terminal coding agent · v{__version__} · root mode"))
        self.p()
        box = [
            ("model", model or "(belum dipilih)"),
            ("agent", agent),
            ("paket", tier.upper()),
            ("folder", cwd),
        ]
        if extra:
            box.append(("info", extra))
        wd = min(term_width() - 6, 64)
        self.p("  " + c("muted", "╭" + "─" * (wd) + "╮"))
        for k, v in box:
            body = f" {k:<7}{v}"
            body = body if len(body) <= wd else body[: wd - 1] + "…"
            self.p("  " + c("muted", "│") + c("accent2", body[:8]) + c("text", body[8:]) + " " * (wd - len(body)) + c("muted", "│"))
        self.p("  " + c("muted", "╰" + "─" * (wd) + "╯"))
        self.p()
        self.p("  " + c("muted", "/help  ·  @file  ·  !cmd  ·  /skills  ·  /models  ·  /permissions  ·  /doctor"))
        self.p()

    # spinner
    def spin_start(self, label="berpikir"):
        if self.quiet or not sys.stdout.isatty() or self._t:
            return
        self._stop = threading.Event()

        def run():
            frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            i, t0 = 0, time.time()
            while not self._stop.is_set():
                sys.stdout.write("\r" + c("accent", frames[i % 10]) + " " + c("muted", f"{label} {int(time.time() - t0)}s") + "\033[K")
                sys.stdout.flush()
                i += 1
                time.sleep(0.08)
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
        self._t = threading.Thread(target=run, daemon=True)
        self._t.start()

    def spin_stop(self):
        if self._t:
            self._stop.set()
            self._t.join()
            self._t = None

    # streaming model output
    def stream_begin(self):
        self._md = Markdown(self.w)
        self._mode = None
        self.spin_start()

    def stream_text(self, s):
        if self.quiet:
            return
        if self._mode != "text":
            self.spin_stop()
            if self._mode == "reason":
                self.w("\n")
            self._mode = "text"
        self._md.feed(s)

    def stream_reasoning(self, s):
        if self.quiet or not self.show_thinking:
            return
        if self._mode != "reason":
            self.spin_stop()
            self._mode = "reason"
            self.w(c("muted", "  ▍ berpikir: ", italic=True))
        self.w(c("muted", s.replace("\n", "\n  ▍ "), italic=True))

    def stream_end(self):
        self.spin_stop()
        if self._md:
            self._md.flush()
        self._md = None

    def markdown(self, text):
        md = Markdown(self.w)
        md.feed(text + "\n")
        md.flush()

    # tools
    def tool_start(self, name, summary):
        self.spin_stop()
        self.p(c("accent2", "  ⚙ ") + c("text", name, bold=True) + " " + c("muted", summary))

    def tool_result(self, text, ok=True):
        if not self.show_details:
            return
        lines = (text or "").splitlines() or [""]
        shown = lines[:6]
        for ln in shown:
            self.p(c("muted", "    │ ") + c("muted" if ok else "err", ln[: term_width() - 8]))
        if len(lines) > 6:
            self.p(c("muted", f"    │ … {len(lines) - 6} baris lagi"))

    def diff(self, text, limit=60, force=False):
        if (not self.show_details and not force) or not text:
            return
        for ln in text.splitlines()[:limit]:
            col = "ok" if ln.startswith("+") and not ln.startswith("+++") else "err" if ln.startswith("-") and not ln.startswith("---") else "muted"
            self.p("    " + c(col, ln[: term_width() - 6]))

    def todos(self, todos):
        self.p(c("accent", "  ☰ rencana"))
        for t in todos:
            st = t.get("status", "pending")
            mark = {"completed": c("ok", "✓"), "in_progress": c("warn", "◐"), "pending": c("muted", "○")}.get(st, "○")
            self.p(f"    {mark} " + c("muted" if st == "completed" else "text", str(t.get("content", ""))))

    def table(self, columns, rows, title=None):
        if title:
            self.p(c("accent2", "▌ " + title, bold=True))
        md = Markdown(self.w)
        md.table = ["| " + " | ".join(map(str, columns)) + " |", "|" + "---|" * len(columns)] + \
                   ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
        md._end_table()

    # permission prompt (yellow, Indonesian): Iya / Tidak / Selalu izinkan
    @staticmethod
    def _keys(data):
        i = 0
        while i < len(data):
            if data[i] == 0x1b and i + 2 < len(data) and data[i + 1:i + 2] == b"[":
                yield data[i:i + 3]
                i += 3
            else:
                yield data[i:i + 1]
                i += 1

    def choose(self, options):
        """Arrow/Tab/number/letter selection. Returns index, or None if not interactive."""
        if self.quiet or not (sys.stdin.isatty() and sys.stdout.isatty()):
            return None
        try:
            import termios
            import tty
        except ImportError:
            return None
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        idx, n = 0, len(options)
        initials = [o[0].lower() for o in options]

        def render():
            parts = []
            for i, o in enumerate(options):
                parts.append(c("accent", f"❯ {o}", bold=True) if i == idx else c("muted", f"  {o}"))
            sys.stdout.write("\r\033[K   " + "      ".join(parts))
            sys.stdout.flush()
        try:
            tty.setcbreak(fd)
            render()
            done = False
            while not done:
                data = os.read(fd, 64)
                if not data:                      # EOF -> tolak
                    idx = 1
                    break
                for k in self._keys(data):
                    if k in (b"\r", b"\n"):
                        done = True
                        break
                    if k in (b"\x1b[C", b"\x1b[B", b"\t", b"l", b"j"):
                        idx = (idx + 1) % n
                    elif k in (b"\x1b[D", b"\x1b[A", b"h", b"k", b"\x1b[Z"):
                        idx = (idx - 1) % n
                    elif k.isdigit() and 1 <= int(k) <= n:
                        idx, done = int(k) - 1, True
                        break
                    elif len(k) == 1 and k.decode("latin1").lower() in initials:
                        idx, done = initials.index(k.decode("latin1").lower()), True
                        break
                render()
        except KeyboardInterrupt:
            idx = 1
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            sys.stdout.write("\n")
        return idx

    def confirm(self, tool, subject, preview=None):
        """Returns 'once' | 'always' | 'no'."""
        self.spin_stop()
        w = term_width() - 6
        self.p()
        self.p(c("warn", "  ┃ ") + c("text", "⚙ " + tool, bold=True))
        for ln in str(subject).splitlines()[:8] or [""]:
            self.p(c("warn", "  ┃ ") + c("info", ln[:w]))
        if preview:
            for ln in preview.splitlines()[:14]:
                col = "ok" if ln.startswith("+") and not ln.startswith("+++") else "err" if ln.startswith("-") and not ln.startswith("---") else "muted"
                self.p(c("warn", "  ┃ ") + c(col, ln[:w]))
        yellow = T.YELLOW_BRIGHT if T.ENABLED else ""
        self.p(f"{yellow}  Apakah anda ingin izinkan ini?{T.RESET if T.ENABLED else ''}")
        idx = self.choose(["Iya", "Tidak", "Selalu izinkan"])
        if idx is None:
            if self.quiet or not sys.stdin.isatty():
                return "no"
            try:
                a = input("   [i]ya / [t]idak / [s]elalu izinkan › ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return "no"
            idx = 0 if a.startswith("i") else 2 if a.startswith("s") else 1
        return ("once", "no", "always")[idx]
