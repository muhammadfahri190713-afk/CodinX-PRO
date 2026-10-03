"""Tool implementations + JSON schemas (OpenAI function-calling format)."""
import difflib
import fnmatch
import html
import json
import os
import re
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config, fsutil, hooks, log, mcp, memory, skills

MAX_OUT = 30000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".cache", ".next", "dist"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
_BG = []


def _shell_command(command):
    """Pilih bash bila tersedia; fallback ke sh pada Termux minimal."""
    preferred = os.environ.get("CODINX_SHELL", "")
    if preferred:
        return [preferred, "-c", command]
    for candidate in ("bash", "sh"):
        if shutil.which(candidate):
            return [candidate, "-c", command]
    return ["/bin/sh", "-c", command]


def _s(name, desc, props, req=()):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": list(req)}}}


_str = {"type": "string"}
_int = {"type": "integer"}
_bool = {"type": "boolean"}

SCHEMAS = {
    "read": _s("read", "Baca file (bernomor baris) atau daftar isi folder. Pakai offset/limit untuk file besar.",
               {"path": _str, "offset": _int, "limit": _int}, ["path"]),
    "write": _s("write", "Tulis file baru / timpa seluruh isi file. Folder induk dibuat otomatis.",
                {"path": _str, "content": _str}, ["path", "content"]),
    "edit": _s("edit", "Ganti teks persis di file. old_str harus unik kecuali replace_all=true. Baca file dulu.",
               {"path": _str, "old_str": _str, "new_str": _str, "replace_all": _bool}, ["path", "old_str", "new_str"]),
    "list": _s("list", "Tampilkan isi folder.", {"path": _str}),
    "glob": _s("glob", "Cari file dengan pola glob (mis. **/*.py), terbaru dulu.", {"pattern": _str, "path": _str}, ["pattern"]),
    "grep": _s("grep", "Cari isi file dengan regex. include = pola nama file (mis. *.py).",
               {"pattern": _str, "path": _str, "include": _str}, ["pattern"]),
    "bash": _s("bash", "Jalankan perintah shell di folder proyek (shell baru tiap panggilan). background=true untuk server/proses "
               "panjang (mengembalikan PID + file log).",
               {"command": _str, "description": _str, "timeout": _int, "background": _bool}, ["command"]),
    "webfetch": _s("webfetch", "Ambil URL (web atau http://localhost:3000). Bisa method/headers/body seperti curl.",
                   {"url": _str, "method": _str, "headers": {"type": "object"}, "body": _str}, ["url"]),
    "todowrite": _s("todowrite", "Buat/perbarui daftar tugas untuk pekerjaan multi-langkah.",
                    {"todos": {"type": "array", "items": {"type": "object", "properties": {
                        "content": _str, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}},
                        "required": ["content", "status"]}}}, ["todos"]),
    "todoread": _s("todoread", "Baca daftar tugas saat ini.", {}),
    "task": _s("task", "Delegasikan riset/penelusuran kode ke sub-agent read-only. Hasil ringkas dikembalikan.",
               {"description": _str, "prompt": _str}, ["description", "prompt"]),
    "skill": _s("skill", "Muat instruksi lengkap sebuah skill (lihat daftar di system prompt).", {"name": _str}, ["name"]),
    "memory": _s("memory", "Kelola ingatan jangka panjang. action: add | list | remove. scope: global | project.",
                 {"action": {"type": "string", "enum": ["add", "list", "remove"]}, "text": _str,
                  "id": _int, "scope": {"type": "string", "enum": ["global", "project"]}}, ["action"]),
    "table": _s("table", "Tampilkan tabel berwarna ke user; opsional simpan ke file .csv/.md/.json lewat save_as.",
                {"columns": {"type": "array", "items": _str}, "rows": {"type": "array", "items": {"type": "array"}},
                 "title": _str, "save_as": _str}, ["columns", "rows"]),
    "camera": _s("camera", "Ambil foto dari kamera (fswebcam/ffmpeg) dan simpan sebagai gambar.",
                 {"device": _str, "output": _str}),
}
SCHEMAS["task"] = _s("task", "Delegasikan riset/pekerjaan ke sub-agent. agent = nama sub-agent khusus (lihat daftar di system prompt); "
                     "kosong = penelusur read-only. Hasil ringkas dikembalikan.",
                     {"description": _str, "prompt": _str, "agent": _str}, ["description", "prompt"])
SCHEMAS["websearch"] = _s("websearch", "Cari di web (DuckDuckGo) untuk info terbaru; lanjutkan dengan webfetch untuk membaca halaman.",
                          {"query": _str, "max_results": _int}, ["query"])
SCHEMAS["multiedit"] = _s("multiedit", "Beberapa penggantian teks dalam SATU file secara atomik (berurutan). Semua berhasil atau tidak sama sekali.",
                          {"path": _str, "edits": {"type": "array", "items": {"type": "object", "properties": {
                              "old_str": _str, "new_str": _str, "replace_all": _bool}, "required": ["old_str", "new_str"]}}},
                          ["path", "edits"])
SUBAGENT_TOOLS = ["read", "list", "glob", "grep", "webfetch", "websearch"]
PLAN_HIDDEN = {"write", "edit", "multiedit", "camera"}
PERM_KEY = {"write": "edit", "edit": "edit", "multiedit": "edit", "websearch": "webfetch"}


class Ctx:
    def __init__(self, cwd, perms, ui, session, cfg):
        self.cwd = cwd
        self.perms = perms
        self.ui = ui
        self.session = session
        self.cfg = cfg
        self.backups = {}
        self.mode = "build"
        self.subagent_fn = None

    def path(self, p):
        p = os.path.expanduser(str(p))
        return os.path.abspath(p if os.path.isabs(p) else os.path.join(self.cwd, p))

    def snap(self, p):
        if p not in self.backups:
            self.backups[p] = fsutil.read_bytes(p) if os.path.isfile(p) else None

    def authorize(self, tool, subject, preview=None):
        """None = boleh. String = pesan error untuk model."""
        act = self.perms.decide(tool, subject)
        if act == "deny":
            return f"Ditolak oleh kebijakan izin untuk '{tool}': {str(subject)[:160]}. Gunakan cara/tool lain."
        if act == "ask":
            ans = self.ui.confirm(tool, subject, preview)
            if ans == "always":
                self.perms.allow_always(tool)
            elif ans == "no":
                return (f"User MENOLAK izin untuk '{tool}'. Jangan ulangi perintah yang sama. "
                        "Coba pendekatan atau tool lain yang lebih aman, atau jelaskan ke user apa yang dibutuhkan.")
        return None

    def authorize_path(self, tool, p, preview=None):
        inside = p == self.cwd or p.startswith(self.cwd.rstrip("/") + "/")
        if not inside and tool in ("write", "edit", "multiedit"):
            err = self.authorize("external_directory", p)
            if err:
                return err
        return self.authorize(PERM_KEY.get(tool, tool), p, preview)


def _diff(old, new, p):
    n = os.path.basename(p)
    return "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "a/" + n, "b/" + n, n=2))


def _trunc(s):
    if len(s) <= MAX_OUT:
        return s
    h = MAX_OUT // 2
    return s[:h] + f"\n\n… [{len(s) - MAX_OUT} karakter dipotong] …\n\n" + s[-h:]


def t_read(ctx, path, offset=1, limit=2000, **_):
    p = ctx.path(path)
    if not os.path.exists(p):
        d = os.path.dirname(p)
        near = difflib.get_close_matches(os.path.basename(p), os.listdir(d) if os.path.isdir(d) else [], 3)
        return f"Error: file tidak ada: {p}" + (". Maksud kamu: " + ", ".join(os.path.join(d, n) for n in near) if near else "")
    err = ctx.authorize("read", p)
    if err:
        return "Error: " + err
    if os.path.isdir(p):
        return t_list(ctx, path=p)
    data = fsutil.read_bytes(p)
    if b"\0" in data[:4096]:
        return "Error: file biner, tidak bisa dibaca sebagai teks."
    lines = data.decode("utf-8", "replace").splitlines()
    offset, limit = max(1, int(offset)), max(1, int(limit))
    chunk = lines[offset - 1: offset - 1 + limit]
    body = "\n".join(f"{i:05d}| {ln[:2000]}" for i, ln in enumerate(chunk, offset))
    more = len(lines) - (offset - 1 + len(chunk))
    tail = f"\n\n(… {more} baris lagi; pakai offset={offset + len(chunk)})" if more > 0 else "\n\n(akhir file)"
    return f"<file>{p}</file>\n{body}{tail}"


def t_write(ctx, path, content, **_):
    p = ctx.path(path)
    old = fsutil.read_text(p) if os.path.isfile(p) else ""
    prev = _diff(old, content, p) if old else "+ (file baru) %d baris" % (content.count("\n") + 1)
    err = ctx.authorize_path("write", p, prev)
    if err:
        return "Error: " + err
    ctx.snap(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    ctx.ui.diff(prev if old else "")
    return f"Berhasil menulis {content.count(chr(10)) + 1} baris ke {p}"


def t_edit(ctx, path, old_str, new_str, replace_all=False, **_):
    p = ctx.path(path)
    if not os.path.isfile(p):
        return f"Error: file tidak ada: {p}"
    if old_str == new_str:
        return "Error: old_str dan new_str sama."
    text = fsutil.read_text(p)
    n = text.count(old_str)
    if n == 0:
        return "Error: old_str tidak ditemukan. Baca file lagi dan salin teks persis (termasuk spasi)."
    if n > 1 and not replace_all:
        return f"Error: old_str muncul {n} kali. Tambah konteks agar unik, atau set replace_all=true."
    new = text.replace(old_str, new_str) if replace_all else text.replace(old_str, new_str, 1)
    d = _diff(text, new, p)
    err = ctx.authorize_path("edit", p, d)
    if err:
        return "Error: " + err
    ctx.snap(p)
    with open(p, "w", encoding="utf-8") as f:
        f.write(new)
    ctx.ui.diff(d)
    return f"Berhasil mengedit {p} ({n if replace_all else 1} penggantian)"


def t_list(ctx, path=".", **_):
    p = ctx.path(path)
    if not os.path.isdir(p):
        return f"Error: bukan folder: {p}"
    names = sorted(os.listdir(p))
    out = [n + ("/" if os.path.isdir(os.path.join(p, n)) else "") for n in names if n not in SKIP_DIRS]
    return f"{p}\n" + ("\n".join(out[:500]) if out else "(kosong)")


def t_glob(ctx, pattern, path=".", **_):
    base = Path(ctx.path(path))
    hits = []
    for f in base.glob(pattern):
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        try:
            hits.append((f.stat().st_mtime, str(f)))
        except OSError:
            pass
    hits.sort(reverse=True)
    return "\n".join(h for _, h in hits[:200]) or "(tidak ada yang cocok)"


def _walk(base):
    if os.path.isfile(base):
        yield base
        return
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield os.path.join(root, f)


def t_grep(ctx, pattern, path=".", include="", **_):
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"Error: regex tidak valid: {e}"
    out = []
    for f in _walk(ctx.path(path)):
        if include and not fnmatch.fnmatch(os.path.basename(f), include):
            continue
        try:
            if os.path.getsize(f) > 2_000_000:
                continue
            with open(f, "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        if b"\0" in raw[:1024]:
            continue
        for i, ln in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
            if rx.search(ln):
                out.append(f"{f}:{i}: {ln.strip()[:200]}")
                if len(out) >= 100:
                    return "\n".join(out) + "\n(dibatasi 100 hasil)"
    return "\n".join(out) or "(tidak ada yang cocok)"


def t_bash(ctx, command, timeout=120, description="", background=False, **_):
    err = ctx.authorize("bash", command)
    if err:
        return "Error: " + err
    env = dict(os.environ, CODINX="1", PAGER="cat", GIT_PAGER="cat")
    if background:
        os.makedirs(os.path.join(config.HOME, "bg"), exist_ok=True)
        log = os.path.join(config.HOME, "bg", f"{int(time.time())}.log")
        with open(log, "wb") as lf:
            proc = subprocess.Popen(_shell_command(command), cwd=ctx.cwd, env=env, stdin=subprocess.DEVNULL,
                                    stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
        time.sleep(1.5)
        try:
            head = fsutil.read_text(log)[-1500:]
        except OSError:
            head = ""
        _BG[:] = [x for x in _BG if x.poll() is None]      # simpan referensi agar proses bisa dipanen & tanpa ResourceWarning
        _BG.append(proc)
        state = "masih berjalan" if proc.poll() is None else f"sudah selesai (exit {proc.returncode})"
        return f"Proses background PID {proc.pid} ({state}). Log: {log}\n{head}"
    timeout = min(max(int(timeout), 1), 900)
    proc = subprocess.Popen(_shell_command(command), cwd=ctx.cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out, _e = proc.communicate(timeout=timeout)
        note = "" if proc.returncode == 0 else f"\n[exit code {proc.returncode}]"
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        out, _e = proc.communicate()
        note = f"\n[dihentikan: melewati timeout {timeout}s]"
    except KeyboardInterrupt:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        raise
    text = out.decode("utf-8", "replace")
    return _trunc(text.strip() or "(tanpa output)") + note


def _html_to_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6])>", "\n", raw)
    raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", raw)).strip()


def t_webfetch(ctx, url=None, method="GET", headers=None, body=None, **_):
    if not url:
        return "Error: parameter 'url' wajib diisi. Contoh: http://localhost:3000"
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https"):
        return "Error: URL harus diawali http:// atau https://"
    local = (u.hostname or "").lower() in LOCAL_HOSTS or (u.hostname or "").endswith(".localhost")
    err = ctx.authorize("localhost" if local else "webfetch", url)
    if err:
        return "Error: " + err
    req = urllib.request.Request(url, data=body.encode() if body else None, method=method.upper())
    req.add_header("User-Agent", "CodinX/1.0")
    for k, v in (headers or {}).items():
        req.add_header(k, str(v))
    status, ctype = 0, ""
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, ctype, raw = r.status, r.headers.get("Content-Type", ""), r.read(3_000_000)
    except urllib.error.HTTPError as e:
        status, ctype, raw = e.code, e.headers.get("Content-Type", ""), e.read(500_000)
    except Exception as e:
        return f"Error: gagal mengakses {url}: {getattr(e, 'reason', e)}"
    text = raw.decode("utf-8", "replace")
    if "html" in ctype:
        text = _html_to_text(text)
    return _trunc(f"HTTP {status} {ctype}\n\n{text}")[:60000]


def t_todowrite(ctx, todos, **_):
    if not isinstance(todos, list):
        return "Error: todos harus berupa array."
    ctx.session.todos = todos
    ctx.ui.todos(todos)
    return "Daftar tugas diperbarui."


def t_todoread(ctx, **_):
    return json.dumps(ctx.session.todos, ensure_ascii=False) if ctx.session.todos else "(belum ada tugas)"


def t_task(ctx, description, prompt, agent="", **_):
    if not ctx.subagent_fn:
        return "Error: sub-agent tidak tersedia."
    return ctx.subagent_fn(description, prompt, agent)


def t_skill(ctx, name, **_):
    sk = skills.resolve(name, ctx.cwd)
    if not sk:
        return f"Error: skill '{name}' tidak ada. Tersedia: {', '.join(skills.discover(ctx.cwd)) or '-'}"
    return f"# Skill: {sk['name']}\n\n{skills.load(sk['name'], ctx.cwd)}\n\n(Ikuti instruksi skill ini sekarang untuk tugas user.)"


def t_memory(ctx, action, text="", id=None, scope="global", **_):
    if action == "add":
        if not text.strip():
            return "Error: text kosong."
        return f"Tersimpan di memori (id {memory.add(text, scope, ctx.cwd)})."
    if action == "remove":
        return f"{memory.remove(id)} ingatan dihapus." if id is not None else "Error: butuh id."
    items = memory.relevant(ctx.cwd, text)
    return "\n".join(f"[{i['id']}] ({i['scope']}) {i['text']}" for i in items) or "(memori kosong)"


def t_table(ctx, columns, rows, title="", save_as="", **_):
    ctx.ui.table(columns, rows, title or None)
    msg = "Tabel ditampilkan ke user."
    if save_as:
        p = ctx.path(save_as)
        err = ctx.authorize_path("write", p, f"+ tabel {len(rows)} baris")
        if err:
            return msg + " Penyimpanan ditolak: " + err
        ctx.snap(p)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if p.endswith(".json"):
            data = [dict(zip(columns, r)) for r in rows]
            fsutil.write_text(p, json.dumps(data, ensure_ascii=False, indent=2))
        elif p.endswith(".csv"):
            import csv
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(columns)
                w.writerows(rows)
        else:
            lines = ["| " + " | ".join(map(str, columns)) + " |", "|" + "---|" * len(columns)]
            lines += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
            fsutil.write_text(p, "\n".join(lines) + "\n")
        msg += f" Disimpan ke {p}."
    return msg


def t_camera(ctx, device="/dev/video0", output="", **_):
    err = ctx.authorize("camera", device)
    if err:
        return "Error: " + err
    out = ctx.path(output or f"camera-{int(time.time())}.jpg")
    exe = shutil.which("fswebcam") or shutil.which("ffmpeg")
    if not exe:
        return "Error: butuh fswebcam atau ffmpeg (apt install fswebcam)."
    if not os.path.exists(device):
        return f"Error: perangkat kamera {device} tidak ditemukan."
    cmd = ([exe, "-d", device, "-r", "1280x720", "--no-banner", out] if exe.endswith("fswebcam")
           else [exe, "-y", "-f", "video4linux2", "-i", device, "-frames:v", "1", out])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    except subprocess.TimeoutExpired:
        return "Error: kamera timeout."
    return f"Foto tersimpan: {out}" if r.returncode == 0 and os.path.exists(out) else "Error: " + (r.stderr or r.stdout)[-300:]


def t_multiedit(ctx, path, edits, **_):
    p = ctx.path(path)
    if not os.path.isfile(p):
        return f"Error: file tidak ada: {p}"
    if not isinstance(edits, list) or not edits:
        return "Error: edits harus array berisi minimal 1 item."
    text = fsutil.read_text(p)
    new = text
    for i, e in enumerate(edits, 1):
        if not isinstance(e, dict) or "old_str" not in e or "new_str" not in e:
            return f"Error: edit #{i} butuh old_str dan new_str. Tidak ada yang diubah."
        old, rep_, ra = e["old_str"], e["new_str"], bool(e.get("replace_all"))
        n = new.count(old)
        if not old or old == rep_:
            return f"Error: edit #{i}: old_str kosong atau sama dengan new_str. Tidak ada yang diubah."
        if n == 0:
            return f"Error: edit #{i}: old_str tidak ditemukan. Tidak ada yang diubah."
        if n > 1 and not ra:
            return f"Error: edit #{i}: old_str muncul {n} kali (tambah konteks / replace_all). Tidak ada yang diubah."
        new = new.replace(old, rep_) if ra else new.replace(old, rep_, 1)
    d = _diff(text, new, p)
    err = ctx.authorize_path("multiedit", p, d)
    if err:
        return "Error: " + err
    ctx.snap(p)
    with open(p, "w", encoding="utf-8") as f:
        f.write(new)
    ctx.ui.diff(d)
    return f"Berhasil: {len(edits)} penggantian di {p}"


_DDG_A = re.compile(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_DDG_S = re.compile(r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|div|td|span)>', re.S)


def _ddg_url(href):
    href = html.unescape(href)
    if href.startswith("//"):
        href = "https:" + href
    q = urllib.parse.urlparse(href)
    if "duckduckgo.com" in q.netloc and q.path.startswith("/l/"):
        u = urllib.parse.parse_qs(q.query).get("uddg")
        if u:
            return u[0]
    return href


def parse_ddg(page, limit=8):
    out, anchors = [], list(_DDG_A.finditer(page))
    for i, m in enumerate(anchors):
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(page)
        sn = _DDG_S.search(page, m.end(), end)
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        snippet = html.unescape(re.sub(r"<[^>]+>", "", sn.group(1))).strip() if sn else ""
        url = _ddg_url(m.group(1))
        if title and url.startswith("http"):
            out.append((title, url, snippet))
        if len(out) >= limit:
            break
    return out


def t_websearch(ctx, query, max_results=8, **_):
    err = ctx.authorize("webfetch", "cari: " + str(query))
    if err:
        return "Error: " + err
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) CodinX/1.2", "Accept-Language": "id,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            page = r.read(2_000_000).decode("utf-8", "replace")
    except Exception as e:
        return f"Error: pencarian gagal: {getattr(e, 'reason', e)}"
    res = parse_ddg(page, max(1, min(int(max_results), 15)))
    if not res:
        return "Error: tidak ada hasil (kemungkinan diblokir/captcha atau format halaman berubah). Coba webfetch ke URL spesifik."
    return "\n".join(f"{i}. {t}\n   {u}\n   {sn[:220]}" for i, (t, u, sn) in enumerate(res, 1))


TOOLS = {"websearch": t_websearch, "multiedit": t_multiedit, "read": t_read, "write": t_write, "edit": t_edit, "list": t_list, "glob": t_glob, "grep": t_grep,
         "bash": t_bash, "webfetch": t_webfetch, "todowrite": t_todowrite, "todoread": t_todoread, "task": t_task,
         "skill": t_skill, "memory": t_memory, "table": t_table, "camera": t_camera}


def _run_mcp(ctx, name, args):
    if not mcp.manager.has(name):
        return f"Error: tool MCP '{name}' tidak dikenal."
    err = ctx.authorize(name, json.dumps(args, ensure_ascii=False)[:600])
    if err:
        return "Error: " + err
    try:
        return _trunc(mcp.manager.call(name, args))
    except mcp.MCPError as e:
        return f"Error: MCP: {e}"


def run(ctx, name, args):
    is_mcp = name.startswith("mcp__")
    fn = TOOLS.get(name)
    if not fn and not is_mcp:
        return f"Error: tool '{name}' tidak ada. Tersedia: {', '.join(TOOLS)}"
    if ctx.mode == "plan" and (name in PLAN_HIDDEN or is_mcp):
        return f"Error: mode PLAN bersifat read-only; tool '{name}' tidak boleh dipakai. Susun rencana saja, user akan beralih ke /build."
    if not is_mcp and name != "webfetch" and not ctx.perms.enabled(PERM_KEY.get(name, name)):
        return f"Error: tool '{name}' dinonaktifkan user (lihat /permissions)."
    h = hooks.run("PreToolUse", ctx.cwd, ctx.cfg, {"tool": name, "args": args}, tool=name)
    if h["blocked"]:
        ctx.ui.warn(f"hook memblokir {name}: {h['message'][:120]}")
        return "Error: diblokir oleh hook — " + h["message"]
    try:
        result = _run_mcp(ctx, name, args) if is_mcp else fn(ctx, **args)
    except KeyboardInterrupt:
        raise
    except TypeError as e:
        result = f"Error: argumen salah untuk {name}: {e}"
    except Exception as e:
        result = f"Error: {type(e).__name__}: {e}"
    h2 = hooks.run("PostToolUse", ctx.cwd, ctx.cfg, {"tool": name, "args": args, "result": str(result)[:4000]}, tool=name)
    extra = "\n".join(x for x in (h2["output"], ("[hook] " + h2["message"]) if h2["message"] else "") if x)
    if extra:
        result = f"{result}\n\n[hook]\n{extra}"
    log.debug("tool", name=name, args=summarize(name, args), chars=len(str(result)), error=str(result).startswith("Error"))
    return result


def summarize(name, a):
    g = lambda k: str(a.get(k, ""))
    if name == "bash":
        return (g("command").splitlines() or [""])[0][:110] + ("  (bg)" if a.get("background") else "")
    if name in ("read", "write", "edit", "list"):
        return g("path")
    if name in ("glob", "grep"):
        return g("pattern")
    if name == "webfetch":
        return (g("method") or "GET") + " " + g("url")
    if name == "task":
        return (g("agent") + ": " if a.get("agent") else "") + g("description")
    if name == "websearch":
        return g("query")
    if name == "multiedit":
        return g("path") + f"  ({len(a.get('edits') or [])} edit)"
    if name == "todowrite":
        return f"{len(a.get('todos') or [])} item"
    if name == "skill":
        return g("name")
    if name == "memory":
        return g("action") + " " + g("text")[:60]
    if name == "table":
        return g("title") or f"{len(a.get('rows') or [])} baris"
    return ""
