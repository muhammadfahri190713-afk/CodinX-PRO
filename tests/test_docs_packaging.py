import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

import cx
from . import ROOT
from .helpers import read, run_cli


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GeneratedDocs(unittest.TestCase):
    def test_generated_docs_are_in_sync_with_code(self):
        gen = load_script("gen_docs")
        captured = {}
        gen.write = lambda name, text: captured.__setitem__(name, text.rstrip() + "\n")
        gen.cmds()
        gen.conf()
        gen.skl()
        self.assertEqual(set(captured), {"COMMANDS.md", "CONFIG.md", "SKILLS.md"})
        for name, text in captured.items():
            self.assertEqual(read(os.path.join(ROOT, "docs", name)), text, f"docs/{name} usang — jalankan `make docs`")

    def test_all_docs_exist_and_have_titles(self):
        files = sorted(f for f in os.listdir(os.path.join(ROOT, "docs")) if f.endswith(".md"))
        self.assertGreaterEqual(len(files), 11)
        for f in files:
            self.assertTrue(read(os.path.join(ROOT, "docs", f)).lstrip().startswith("# "), f)

    def test_readme_links_every_doc_and_all_links_resolve(self):
        readme = read(os.path.join(ROOT, "README.md"))
        for f in os.listdir(os.path.join(ROOT, "docs")):
            self.assertIn(f"docs/{f}", readme, f"README tidak menautkan docs/{f}")
        for target in set(re.findall(r"\]\(((?!https?://|#)[^)\s]+)\)", readme)):
            self.assertTrue(os.path.exists(os.path.join(ROOT, target.split("#")[0])), target)

    def test_changelog_matches_version(self):
        first = re.search(r"^## \[([\d.]+)\]", read(os.path.join(ROOT, "CHANGELOG.md")), re.M).group(1)
        self.assertEqual(first, cx.__version__)

    def test_command_and_skill_files_have_frontmatter(self):
        for d, key in (("commands", "description"), ("agents", "description"), ("skills", "description")):
            base = os.path.join(ROOT, d)
            for entry in os.listdir(base):
                path = os.path.join(base, entry, "SKILL.md") if d == "skills" else os.path.join(base, entry)
                text = read(path)
                self.assertTrue(text.startswith("---\n"), path)
                self.assertIn(f"\n{key}:", text.split("\n---", 1)[0], path)


class RepoHygiene(unittest.TestCase):
    def test_no_secrets_anywhere_in_the_repo(self):
        ss = load_script("secret_scan")
        hits = []
        for p in ss.walk([ROOT]):
            if os.path.basename(p) in ss.SECRET_FILES:        # file lokal milik developer; di-ignore git
                continue
            hits += ss.scan_file(p)
        self.assertEqual(hits, [], "rahasia terdeteksi di repo")

    def test_gitignore_protects_secrets_but_not_source(self):
        if not shutil.which("git"):
            self.skipTest("git tidak tersedia")
        d = tempfile.mkdtemp()
        subprocess.run(["git", "-C", d, "init", "-q"])
        shutil.copy(os.path.join(ROOT, ".gitignore"), d)
        ignored = lambda p: subprocess.run(["git", "-C", d, "check-ignore", "-q", p]).returncode == 0
        for p in (".env", ".env.local", ".seed", ".key.enc", "x.enc", "cx/__pycache__/a.pyc", "app.log", ".codinx/config.json"):
            self.assertTrue(ignored(p), f"{p} harus di-ignore")
        for p in (".env.example", "cx/vendor/pygments/lexers/python.py", "skills/web-check/SKILL.md", "examples/hooks.json",
                  "tests/test_wire.py", ".github/workflows/ci.yml", "scripts/secret_scan.py"):
            self.assertFalse(ignored(p), f"{p} TIDAK boleh di-ignore")

    def test_env_example_is_a_safe_template(self):
        text = read(os.path.join(ROOT, ".env.example"))
        self.assertIn("CODINX_API_KEY=isi_api_key_kamu_di_sini", text)
        self.assertIn("CODINX_BASE_URL=", text)
        self.assertFalse(os.path.exists(os.path.join(ROOT, ".seed")), ".seed (kunci plaintext) tidak boleh ada di repo")

    def test_dockerignore_excludes_secrets(self):
        text = read(os.path.join(ROOT, ".dockerignore"))
        for needle in (".env", ".seed", "*.enc"):
            self.assertIn(needle, text)

    def test_required_project_files_exist(self):
        for f in ("README.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md", "Makefile",
                  "Dockerfile", ".editorconfig", ".github/workflows/ci.yml", ".github/PULL_REQUEST_TEMPLATE.md",
                  "completions/codinx.bash", "completions/_codinx", "install.sh", "uninstall.sh", "package.json", "bin/codinx",
                  "scripts/build_zip.py", "scripts/vendor_pygments.py", "scripts/gen_docs.py", "scripts/secret_scan.py",
                  "scripts/install-git-hooks.sh", "data/models.json", "api.example.py", "examples/mcp-echo-server.py"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, f)), f)

    def test_executables_have_exec_bit_and_shebang(self):
        for f in ("bin/codinx", "install.sh", "uninstall.sh", "scripts/install-git-hooks.sh", "scripts/pre-commit",
                  "scripts/build_zip.py", "scripts/secret_scan.py", "scripts/vendor_pygments.py", "scripts/gen_docs.py",
                  "examples/mcp-echo-server.py"):
            p = os.path.join(ROOT, f)
            self.assertTrue(os.stat(p).st_mode & stat.S_IXUSR, f"{f} tidak executable")
            self.assertTrue(read(p).startswith("#!"), f)

    def test_shell_scripts_parse(self):
        for f in ("install.sh", "uninstall.sh", "scripts/install-git-hooks.sh", "scripts/pre-commit"):
            r = subprocess.run(["bash", "-n", os.path.join(ROOT, f)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f + r.stderr)

    def test_package_json_exposes_documented_script(self):
        pkg = json.loads(read(os.path.join(ROOT, "package.json")))
        self.assertEqual(pkg["scripts"]["codinx-agents"], "python3 bin/codinx")

    def test_models_catalog_matches_spec(self):
        cat = json.loads(read(os.path.join(ROOT, "data", "models.json")))
        self.assertEqual(len(cat), 170)
        self.assertTrue(all(set(m) >= {"name", "id", "role", "trial"} for m in cat))


class Entrypoints(unittest.TestCase):
    def test_version_and_help_via_launcher_logic(self):
        home = tempfile.mkdtemp()
        self.assertIn(f"CodinX {cx.__version__}", run_cli(home, home, ["--version"]))
        out = run_cli(home, home, ["--help"])
        for sub in ("run", "doctor", "models", "sessions", "logs", "connect"):
            self.assertIn(sub, out)

    def test_models_listing(self):
        home = tempfile.mkdtemp()
        env = {"CODINX_BASE_URL": "http://127.0.0.1:1/v1", "CODINX_API_KEY": "k"}
        self.assertTrue("170 model" in run_cli(home, home, ["models"], env), "daftar penuh harus 170 model")
        out = run_cli(home, home, ["models", "claude-haiku"], env)
        self.assertTrue("claude-haiku-4.5" in out and "PRO" in out, "filter nama model")

    def test_real_entrypoint_runs_without_root(self):
        home = tempfile.mkdtemp()
        env = {"CODINX_HOME": os.path.join(home, ".codinx")}
        r = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "codinx"), "--version"],
                           capture_output=True, text=True, env={**os.environ, **env})
        self.assertEqual(r.returncode, 0)
        self.assertIn("CodinX", r.stdout)


if __name__ == "__main__":
    unittest.main()
