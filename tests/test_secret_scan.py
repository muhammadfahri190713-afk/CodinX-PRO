import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from . import ROOT

SPEC = importlib.util.spec_from_file_location("secret_scan", os.path.join(ROOT, "scripts", "secret_scan.py"))
ss = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ss)
SCRIPT = os.path.join(ROOT, "scripts", "secret_scan.py")

# kunci palsu dirakit saat runtime agar file test ini sendiri tidak memicu pemindai
FAKE = {
    "sk": "sk-" + "Ab1" * 14,
    "anthropic": "sk-ant-" + "Cd2" * 12,
    "aws": "AKIA" + "ABCD1234" * 2,
    "github": "ghp_" + "Ef3" * 14,
    "slack": "xoxb-" + "1234567890-" * 2 + "abc",
    "google": "AIza" + "Gh4" * 11 + "xy",
    "jwt": "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12,
    "privkey": "-----BEGIN " + "RSA PRIVATE KEY-----",
    "assign": "secret_token = " + "Q9" * 12,
}


class Patterns(unittest.TestCase):
    def test_each_kind_is_detected_and_masked(self):
        for kind, value in FAKE.items():
            hits = ss.scan_text(f"x = '{value}'\n" if kind != "assign" else value + "\n", "f.txt")
            self.assertEqual(len(hits), 1, kind)
            _, line, label, shown = hits[0]
            self.assertEqual(line, 1)
            self.assertNotIn(value, shown, f"{kind}: nilai harus disamarkan")
            self.assertIn("char", shown)

    def test_placeholders_and_clean_lines_pass(self):
        for line in ("CODINX_API_KEY=isi_api_key_kamu_di_sini", "api_key = your_key_here_1234567890", "token = changeme-changeme-123",
                     "password = '<password>'", "x = 1", "# komentar biasa tentang sk- prefix", "url = https://example.com/token"):
            self.assertEqual(ss.scan_text(line + "\n", "f"), [], line)

    def test_variable_names_with_underscores(self):
        for line in ("DB_PASSWORD=hunter2hunter2hunter2", 'export MY_API_KEY="abcd1234abcd1234abcd"', "secret_token: 9f8e7d6c5b4a3f2e1d0c",
                     "AWS_SECRET_ACCESS_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfi'"):
            self.assertEqual(len(ss.scan_text(line + "\n", "f")), 1, line)

    def test_code_that_merely_reads_secrets_is_not_flagged(self):
        for line in ("api_key = os.environ.get('K')", "password = getpass.getpass()", "token = request.headers['Authorization']",
                     "secret_name = 'database'", "if not password_hash_algorithm_name:"):
            self.assertEqual(ss.scan_text(line + "\n", "f"), [], line)

    def test_skill_copy_is_identical_to_script(self):
        with open(SCRIPT) as a, open(os.path.join(ROOT, "skills", "secret-scan", "scripts", "secret_scan.py")) as b:
            self.assertEqual(a.read(), b.read())

    def test_line_numbers(self):
        hits = ss.scan_text("a\nb\n" + FAKE["github"] + "\nc\n", "f")
        self.assertEqual(hits[0][1], 3)

    def test_mask_shows_only_prefix_and_length(self):
        self.assertEqual(ss.mask("sk-1234567890"), "sk-1…(13 char)")


class Files(unittest.TestCase):
    def test_walk_skips_noise_dirs_and_scan_skips_binary_and_large(self):
        d = tempfile.mkdtemp()
        for rel in ("a/ok.txt", "node_modules/x.js", ".git/c", "cx/vendor/p.py", "__pycache__/z.pyc", "tests/fixture.py"):
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            open(os.path.join(d, rel), "w").close()
        names = sorted(os.path.relpath(p, d) for p in ss.walk([d]))
        self.assertEqual(names, [os.path.join("a", "ok.txt")])
        with open(os.path.join(d, "bin.dat"), "wb") as f:
            f.write(b"\x00" + FAKE["sk"].encode())
        self.assertEqual(ss.scan_file(os.path.join(d, "bin.dat")), [])
        with open(os.path.join(d, "big.txt"), "w") as f:
            f.write(FAKE["sk"] + "\n" + "x" * 1_100_000)
        self.assertEqual(ss.scan_file(os.path.join(d, "big.txt")), [])


class Cli(unittest.TestCase):
    def run_scan(self, *args, cwd=None):
        return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, cwd=cwd)

    def test_exit_codes_and_no_secret_in_output(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "leak.py"), "w") as f:
            f.write(f"KEY = '{FAKE['sk']}'\n")
        r = self.run_scan(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("leak.py:1", r.stdout)
        self.assertNotIn(FAKE["sk"], r.stdout + r.stderr)
        os.remove(os.path.join(d, "leak.py"))
        r = self.run_scan(d)
        self.assertEqual(r.returncode, 0)
        self.assertIn("tidak ada rahasia", r.stdout)

    @unittest.skipUnless(shutil.which("git"), "git tidak tersedia")
    def test_staged_mode_blocks_env_files_and_leaks(self):
        d = tempfile.mkdtemp()
        git = lambda *a: subprocess.run(["git", "-C", d] + list(a), capture_output=True, text=True)
        git("init", "-q")
        with open(os.path.join(d, ".env"), "w") as f:
            f.write("CODINX_API_KEY=" + FAKE["sk"] + "\n")
        with open(os.path.join(d, "a.txt"), "w") as f:
            f.write("aman\n")
        git("add", "-f", ".env", "a.txt")
        r = self.run_scan("--staged", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertIn(".env", r.stdout)
        git("rm", "--cached", "-q", ".env")
        self.assertEqual(self.run_scan("--staged", cwd=d).returncode, 0)
        with open(os.path.join(d, "b.py"), "w") as f:
            f.write(f"t = '{FAKE['github']}'\n")
        git("add", "b.py")
        r = self.run_scan("--staged", cwd=d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("b.py:1", r.stdout)
        self.assertNotIn(FAKE["github"], r.stdout)

    @unittest.skipUnless(shutil.which("git"), "git tidak tersedia")
    def test_env_example_may_be_staged(self):
        d = tempfile.mkdtemp()
        subprocess.run(["git", "-C", d, "init", "-q"])
        shutil.copy(os.path.join(ROOT, ".env.example"), os.path.join(d, ".env.example"))
        subprocess.run(["git", "-C", d, "add", ".env.example"])
        self.assertEqual(self.run_scan("--staged", cwd=d).returncode, 0)


if __name__ == "__main__":
    unittest.main()
