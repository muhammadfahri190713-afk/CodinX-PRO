import json
import os
import signal
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from cx import memory, perms, tools, ui
from cx.session import Session


def rd(path):
    with open(path) as f:
        return f.read()


class _Page(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        b = b"<html><body><h1>Halo localhost</h1><script>jahat()</script><p>isi &amp; teks</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


class ToolCase(unittest.TestCase):
    auto = True

    def setUp(self):
        self.cwd = os.path.realpath(tempfile.mkdtemp())
        self.cfg = {"tool_policy": {}, "permission": {}}
        self.perms = perms.Perms(self.cfg)
        self.perms.auto = self.auto
        self.ui = ui.UI()
        self.ui.quiet = True
        self.ctx = tools.Ctx(self.cwd, self.perms, self.ui, Session(self.cwd), self.cfg)

    def run_tool(self, tool, **args):
        return tools.run(self.ctx, tool, args)

    def path(self, name):
        return os.path.join(self.cwd, name)

    def put(self, name, text):
        os.makedirs(os.path.dirname(self.path(name)), exist_ok=True)
        with open(self.path(name), "w") as f:
            f.write(text)


class FileTools(ToolCase):
    def test_write_then_read_numbered(self):
        self.assertIn("Berhasil menulis 3 baris", self.run_tool("write", path="a/b.txt", content="satu\ndua\ntiga"))
        out = self.run_tool("read", path="a/b.txt")
        self.assertIn("00001| satu", out)
        self.assertIn("00003| tiga", out)
        self.assertIn("(akhir file)", out)

    def test_read_offset_limit_and_missing_hint(self):
        self.put("f.txt", "\n".join(f"baris{i}" for i in range(1, 11)))
        out = self.run_tool("read", path="f.txt", offset=3, limit=2)
        self.assertIn("00003| baris3", out)
        self.assertNotIn("baris5", out)
        self.assertIn("offset=5", out)
        self.put("hello_world.py", "x")
        self.assertIn("hello_world.py", self.run_tool("read", path="hello_wrld.py"))

    def test_read_binary_and_directory(self):
        with open(self.path("b.bin"), "wb") as f:
            f.write(b"\x00\x01\x02")
        self.assertIn("biner", self.run_tool("read", path="b.bin"))
        self.put("d/x.txt", "1")
        self.assertIn("x.txt", self.run_tool("read", path="d"))

    def test_edit_unique_missing_and_ambiguous(self):
        self.put("e.txt", "alfa beta alfa")
        self.assertIn("Error", self.run_tool("edit", path="e.txt", old_str="alfa", new_str="X"))      # 2 kali
        self.assertIn("Error", self.run_tool("edit", path="e.txt", old_str="zzz", new_str="X"))
        self.assertIn("2 penggantian", self.run_tool("edit", path="e.txt", old_str="alfa", new_str="X", replace_all=True))
        self.assertEqual(rd(self.path("e.txt")), "X beta X")
        self.assertIn("Berhasil", self.run_tool("edit", path="e.txt", old_str="beta", new_str="B"))

    def test_multiedit_is_atomic(self):
        self.put("m.txt", "a b c")
        bad = self.run_tool("multiedit", path="m.txt", edits=[{"old_str": "a", "new_str": "1"}, {"old_str": "zzz", "new_str": "2"}])
        self.assertIn("Tidak ada yang diubah", bad)
        self.assertEqual(rd(self.path("m.txt")), "a b c")
        ok = self.run_tool("multiedit", path="m.txt", edits=[{"old_str": "a", "new_str": "1"}, {"old_str": "c", "new_str": "3"}])
        self.assertIn("2 penggantian", ok)
        self.assertEqual(rd(self.path("m.txt")), "1 b 3")

    def test_undo_backups_are_recorded(self):
        self.put("u.txt", "asli")
        self.run_tool("edit", path="u.txt", old_str="asli", new_str="baru")
        self.run_tool("write", path="baru.txt", content="x")
        self.assertEqual(self.ctx.backups[self.path("u.txt")], b"asli")
        self.assertIsNone(self.ctx.backups[self.path("baru.txt")])

    def test_list_glob_grep_skip_noise_dirs(self):
        self.put("src/a.py", "def hello():\n    pass\n")
        self.put("src/b.txt", "hello world\n")
        self.put("node_modules/x.js", "hello\n")
        self.put(".git/config", "hello\n")
        self.assertNotIn("node_modules", self.run_tool("list", path="."))
        self.assertIn("a.py", self.run_tool("glob", pattern="**/*.py"))
        self.assertNotIn("x.js", self.run_tool("glob", pattern="**/*.js"))
        g = self.run_tool("grep", pattern="hello")
        self.assertIn("a.py:1", g)
        self.assertIn("b.txt:1", g)
        self.assertNotIn("node_modules", g)
        self.assertNotIn(".git", g)
        self.assertNotIn("b.txt", self.run_tool("grep", pattern="hello", include="*.py"))
        self.assertIn("regex tidak valid", self.run_tool("grep", pattern="("))

    def test_table_saves_csv_md_json(self):
        self.assertIn("Tabel ditampilkan", self.run_tool("table", columns=["a", "b"], rows=[[1, "x"], [2, "y"]], save_as="t.csv"))
        self.assertEqual(rd(self.path("t.csv")).splitlines(), ["a,b", "1,x", "2,y"])
        self.run_tool("table", columns=["a"], rows=[[1]], save_as="t.json")
        self.assertEqual(json.loads(rd(self.path("t.json"))), [{"a": 1}])
        self.run_tool("table", columns=["a"], rows=[[1]], save_as="t.md")
        self.assertIn("| a |", rd(self.path("t.md")))

    def test_todos_roundtrip(self):
        self.assertIn("belum ada", self.run_tool("todoread"))
        self.run_tool("todowrite", todos=[{"content": "x", "status": "pending"}])
        self.assertEqual(json.loads(self.run_tool("todoread"))[0]["content"], "x")

    def test_unknown_tool_and_bad_args(self):
        self.assertIn("tidak ada", self.run_tool("hack"))
        self.assertIn("argumen salah", self.run_tool("read", salah=1))


class BashTool(ToolCase):
    def test_output_and_exit_code(self):
        self.assertEqual(self.run_tool("bash", command="echo halo && pwd").splitlines()[0], "halo")
        self.assertIn("[exit code 3]", self.run_tool("bash", command="echo x; exit 3"))
        self.assertIn("tanpa output", self.run_tool("bash", command="true"))

    def test_timeout_kills_process(self):
        out = self.run_tool("bash", command="sleep 20", timeout=1)
        self.assertIn("timeout", out)

    def test_background_returns_pid(self):
        out = self.run_tool("bash", command="sleep 30", background=True)
        pid = int(out.split("PID ")[1].split()[0])
        try:
            self.assertIn("masih berjalan", out)
        finally:
            os.kill(pid, signal.SIGKILL)

    def test_runs_in_project_dir_without_stdin(self):
        self.assertIn(os.path.basename(self.cwd), self.run_tool("bash", command="pwd"))
        self.assertIn("EOF", self.run_tool("bash", command="read x || echo EOF"))


class Permissions(ToolCase):
    auto = False

    def test_unsafe_bash_denied_when_not_interactive(self):
        out = self.run_tool("bash", command="npm install express")
        self.assertTrue(out.startswith("Error:") and "MENOLAK" in out)

    def test_safe_bash_runs_without_prompt(self):
        self.assertIn("halo", self.run_tool("bash", command="echo halo"))

    def test_hard_deny_message(self):
        out = self.run_tool("bash", command="rm -rf /")
        self.assertTrue(out.startswith("Error:") and "kebijakan" in out)

    def test_write_outside_project_needs_permission(self):
        out = self.run_tool("write", path="/tmp/codinx-test-luar/x.txt", content="x")
        self.assertTrue(out.startswith("Error:") and "MENOLAK" in out)
        self.assertFalse(os.path.exists("/tmp/codinx-test-luar/x.txt"))

    def test_plan_mode_blocks_mutations(self):
        self.ctx.mode = "plan"
        for tool, args in (("write", {"path": "a", "content": "x"}), ("edit", {"path": "a", "old_str": "a", "new_str": "b"}),
                           ("multiedit", {"path": "a", "edits": []})):
            self.assertIn("PLAN", self.run_tool(tool, **args), tool)

    def test_policy_off_disables_tool(self):
        self.cfg["tool_policy"]["bash"] = "off"
        self.assertIn("dinonaktifkan", self.run_tool("bash", command="echo hi"))

    def test_always_allow_policy_skips_prompt(self):
        self.cfg["tool_policy"]["bash"] = "allow"
        self.assertIn("kunci", self.run_tool("bash", command="echo kunci > /dev/null; echo kunci"))


class MemorySkillTools(ToolCase):
    def setUp(self):
        super().setUp()
        self.p = mock.patch.object(memory, "MEM_FILE", os.path.join(self.cwd, "mem.json"))
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_memory_tool(self):
        self.assertIn("Tersimpan", self.run_tool("memory", action="add", text="suka kopi"))
        self.assertIn("suka kopi", self.run_tool("memory", action="list"))
        self.assertIn("suka kopi", self.run_tool("memory", action="list", text="kopi"))
        self.assertIn("1 ingatan dihapus", self.run_tool("memory", action="remove", id=1))
        self.assertIn("kosong", self.run_tool("memory", action="list"))

    def test_skill_tool(self):
        out = self.run_tool("skill", name="web-check")
        self.assertIn("# Skill: web-check", out)
        self.assertIn("Cek aplikasi web lokal", out)
        self.assertIn("tidak ada", self.run_tool("skill", name="zzz"))


class WebTools(ToolCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), _Page)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.port = cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_webfetch_localhost_strips_html(self):
        out = self.run_tool("webfetch", url=f"http://127.0.0.1:{self.port}/")
        self.assertIn("HTTP 200", out)
        self.assertIn("Halo localhost", out)
        self.assertIn("isi & teks", out)
        self.assertNotIn("jahat()", out)
        self.assertNotIn("<h1>", out)

    def test_webfetch_localhost_respects_policy(self):
        self.cfg["tool_policy"]["localhost"] = "deny"
        self.assertIn("kebijakan", self.run_tool("webfetch", url=f"http://localhost:{self.port}/"))

    def test_webfetch_rejects_other_schemes_and_dead_hosts(self):
        self.assertIn("http", self.run_tool("webfetch", url="file:///etc/passwd"))
        self.assertIn("gagal", self.run_tool("webfetch", url="http://127.0.0.1:1/"))

    def test_parse_ddg_results(self):
        page = ('<div class="result"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2F&amp;rut=abc">Python <b>Docs</b></a>'
                '<a class="result__snippet" href="x">Dokumentasi resmi &amp; tutorial</a></div>'
                '<div class="result"><a class="result__a" href="https://example.com/a">Contoh</a><div class="result__snippet">Snippet kedua</div></div>')
        self.assertEqual(tools.parse_ddg(page), [("Python Docs", "https://docs.python.org/3/", "Dokumentasi resmi & tutorial"),
                                                  ("Contoh", "https://example.com/a", "Snippet kedua")])
        self.assertEqual(tools.parse_ddg("<html>kosong</html>"), [])
        self.assertEqual(len(tools.parse_ddg(page, limit=1)), 1)

    def test_websearch_uses_webfetch_policy(self):
        self.cfg["tool_policy"]["webfetch"] = "deny"
        self.assertIn("kebijakan", self.run_tool("websearch", query="python"))


if __name__ == "__main__":
    unittest.main()
