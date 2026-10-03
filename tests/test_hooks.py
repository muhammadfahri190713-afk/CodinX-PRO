import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from cx import config, hooks, perms, tools, ui
from cx.session import Session

PY = sys.executable


class HookCase(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.cwd = os.path.realpath(tempfile.mkdtemp())
        p = mock.patch.object(config, "HOME", self.home)
        p.start()
        self.addCleanup(p.stop)

    def write(self, hook_map, where=None):
        path = where or os.path.join(self.home, "hooks.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"hooks": hook_map}, f)

    def run_hook(self, event, payload=None, tool=None, cfg=None):
        return hooks.run(event, self.cwd, cfg or {}, payload or {}, tool=tool)


class HookRun(HookCase):
    def test_exit2_blocks_with_stderr_message(self):
        self.write({"PreToolUse": [{"matcher": "bash", "command": "echo 'dilarang keras' >&2; exit 2"}]})
        r = self.run_hook("PreToolUse", {"tool": "bash"}, tool="bash")
        self.assertTrue(r["blocked"])
        self.assertIn("dilarang keras", r["message"])

    def test_matcher_is_regex_and_case_insensitive(self):
        self.write({"PreToolUse": [{"matcher": "edit|write", "command": "exit 2"}]})
        self.assertFalse(self.run_hook("PreToolUse", tool="bash")["blocked"])
        self.assertTrue(self.run_hook("PreToolUse", tool="write")["blocked"])
        self.assertTrue(self.run_hook("PreToolUse", tool="EDIT")["blocked"])
        self.write({"PreToolUse": [{"matcher": "*", "command": "exit 2"}]})
        self.assertTrue(self.run_hook("PreToolUse", tool="anything")["blocked"])
        self.write({"PreToolUse": [{"command": "exit 2"}]})                      # tanpa matcher = semua
        self.assertTrue(self.run_hook("PreToolUse", tool="read")["blocked"])

    def test_stdin_payload_and_stdout_output(self):
        cmd = f"{PY} -c \"import sys,json; d=json.load(sys.stdin); print(d['event'], d['tool'], d['args']['path'], d['cwd'] == '{self.cwd}')\""
        self.write({"PostToolUse": [{"matcher": "write", "command": cmd}]})
        r = self.run_hook("PostToolUse", {"tool": "write", "args": {"path": "/x"}}, tool="write")
        self.assertFalse(r["blocked"])
        self.assertEqual(r["output"], "PostToolUse write /x True")

    def test_other_nonzero_exit_is_warning_not_block(self):
        self.write({"PreToolUse": [{"command": "echo oops >&2; exit 1"}]})
        r = self.run_hook("PreToolUse", tool="bash")
        self.assertFalse(r["blocked"])
        self.assertIn("rc=1", r["message"])

    def test_timeout_is_not_fatal(self):
        self.write({"UserPromptSubmit": [{"command": "sleep 5", "timeout": 1}]})
        r = self.run_hook("UserPromptSubmit", {"prompt": "x"})
        self.assertFalse(r["blocked"])
        self.assertIn("timeout", r["message"])

    def test_env_vars_for_hooks(self):
        self.write({"Stop": [{"command": "echo $CODINX_HOOK_EVENT $CODINX_PROJECT_DIR"}]})
        self.assertEqual(self.run_hook("Stop")["output"], f"Stop {self.cwd}")

    def test_missing_or_broken_config_is_ignored(self):
        self.assertFalse(self.run_hook("PreToolUse", tool="bash")["blocked"])
        with open(os.path.join(self.home, "hooks.json"), "w") as f:
            f.write("{bukan json")
        self.assertFalse(self.run_hook("PreToolUse", tool="bash")["blocked"])

    def test_project_hooks_require_trust(self):
        self.write({"PreToolUse": [{"command": "exit 2"}]}, where=os.path.join(self.cwd, ".codinx", "hooks.json"))
        self.assertFalse(self.run_hook("PreToolUse", tool="bash", cfg={})["blocked"])
        self.assertTrue(self.run_hook("PreToolUse", tool="bash", cfg={"trust_project": True})["blocked"])

    def test_global_and_trusted_project_hooks_are_merged(self):
        self.write({"UserPromptSubmit": [{"command": "echo global"}]})
        self.write({"UserPromptSubmit": [{"command": "echo proyek"}]}, where=os.path.join(self.cwd, ".codinx", "hooks.json"))
        out = self.run_hook("UserPromptSubmit", cfg={"trust_project": True})["output"].splitlines()
        self.assertEqual(out, ["global", "proyek"])


class HookIntegration(HookCase):
    def setUp(self):
        super().setUp()
        self.cfg = {"tool_policy": {}, "permission": {}}
        self.perms = perms.Perms(self.cfg)
        self.perms.auto = True
        u = ui.UI()
        u.quiet = True
        self.ctx = tools.Ctx(self.cwd, self.perms, u, Session(self.cwd), self.cfg)

    def test_pre_hook_blocks_tool_execution(self):
        self.write({"PreToolUse": [{"matcher": "bash", "command": "echo 'DROP terlarang' >&2; exit 2"}]})
        out = tools.run(self.ctx, "bash", {"command": "touch dibuat.txt"})
        self.assertTrue(out.startswith("Error: diblokir oleh hook"))
        self.assertIn("DROP terlarang", out)
        self.assertFalse(os.path.exists(os.path.join(self.cwd, "dibuat.txt")))

    def test_post_hook_output_is_fed_back_to_model(self):
        self.write({"PostToolUse": [{"matcher": "bash", "command": "echo lint: ada 2 peringatan"}]})
        out = tools.run(self.ctx, "bash", {"command": "echo halo"})
        self.assertIn("halo", out)
        self.assertIn("[hook]", out)
        self.assertIn("lint: ada 2 peringatan", out)

    def test_hook_does_not_affect_other_tools(self):
        self.write({"PreToolUse": [{"matcher": "bash", "command": "exit 2"}]})
        with open(os.path.join(self.cwd, "a.txt"), "w") as f:
            f.write("isi")
        self.assertIn("isi", tools.run(self.ctx, "read", {"path": "a.txt"}))


if __name__ == "__main__":
    unittest.main()
