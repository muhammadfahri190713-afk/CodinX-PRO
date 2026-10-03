import json
import os
import tempfile
import unittest
from unittest import mock

from cx import caps, config, hooks, memory, tiers
from cx import api
from cx.app import ALIASES, COMMANDS, App


class AppCase(unittest.TestCase):
    def setUp(self):
        self.cwd = os.path.realpath(tempfile.mkdtemp())
        old = os.getcwd()
        os.chdir(self.cwd)
        self.addCleanup(os.chdir, old)
        config._dotenv = None
        self.home = tempfile.mkdtemp()
        for p in (mock.patch.object(memory, "MEM_FILE", os.path.join(self.home, "mem.json")),
                  mock.patch.object(config, "HOME", self.home)):
            p.start()
            self.addCleanup(p.stop)
        self.cfg = config.load(self.cwd)
        self.cfg["timezone"] = "Asia/Jakarta"
        self.cfg["model"] = "m-unit-test"
        self.addCleanup(caps.clear, "m-unit-test")
        self.app = App(self.cfg)
        self.app.ui.quiet = True
        self.app.save_cfg = lambda: None

    def names(self, **kw):
        return {s["function"]["name"] for s in self.app.agent.tool_schemas(**kw)}


class LiveModelCatalog(unittest.TestCase):
    def test_video_filter_and_display_name(self):
        payload = {"data": [
            {"id": "gpt-5.6-sol", "name": "GPT 5.6 Sol"},
            {"id": "seedance-2.5", "name": "Seedance 2.5", "category": "video"},
            {"id": "sana", "name": "Sana", "category": "image"},
        ]}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps(payload).encode()
        with mock.patch.object(api, "_open", return_value=Response()):
            out = api.list_model_specs({"base_url": "https://example.test/api/v1"}, "key")
        self.assertEqual([m["id"] for m in out], ["gpt-5.6-sol", "sana"])
        self.assertEqual(out[0]["name"], "GPT 5.6 Sol")


class ToolSchemas(AppCase):
    def test_default_tool_set(self):
        n = self.names()
        for t in ("read", "write", "edit", "multiedit", "bash", "webfetch", "websearch", "skill", "memory", "task",
                  "table", "todowrite", "todoread", "glob", "grep", "list"):
            self.assertIn(t, n)
        self.assertNotIn("camera", n)                                   # kamera mati secara bawaan

    def test_plan_mode_hides_mutating_tools(self):
        self.app.ctx.mode = "plan"
        n = self.names()
        for t in ("write", "edit", "multiedit", "camera"):
            self.assertNotIn(t, n)
        self.assertIn("read", n)
        self.assertIn("bash", n)

    def test_policy_off_hides_tools(self):
        self.cfg["tool_policy"].update({"bash": "off", "edit": "off", "skill": "off"})
        n = self.names()
        for t in ("bash", "write", "edit", "multiedit", "skill"):
            self.assertNotIn(t, n)
        self.cfg["tool_policy"].update({"webfetch": "off", "localhost": "off"})
        n = self.names()
        self.assertNotIn("webfetch", n)
        self.assertNotIn("websearch", n)

    def test_camera_can_be_enabled(self):
        self.cfg["tool_policy"]["camera"] = "ask"
        self.assertIn("camera", self.names())

    def test_tool_mode_none_offers_no_tools(self):
        self.cfg["tool_mode"] = "none"
        self.assertEqual(self.app.agent.tool_schemas(), [])

    def test_subagent_whitelist_excludes_task(self):
        n = self.names(sub=True, names=["read", "bash", "task", "write", "zzz"])
        self.assertEqual(n, {"read", "bash", "write"})
        self.assertEqual(self.names(sub=True), {"read", "list", "glob", "grep", "webfetch", "websearch"})


class SystemPrompt(AppCase):
    def test_sections(self):
        sp = self.app.agent.system_prompt()
        for needle in ("CodinX", "KAMU MENGINGAT", "Skills tersedia", "web-check", "Sub-agent khusus", "security-auditor", self.cwd):
            self.assertIn(needle, sp)

    def test_memory_agents_md_and_modes(self):
        memory.add("User suka jawaban singkat")
        with open("AGENTS.md", "w") as f:
            f.write("# Aturan\nGunakan tab.")
        sp = self.app.agent.system_prompt()
        self.assertIn("User suka jawaban singkat", sp)
        self.assertIn("Gunakan tab.", sp)
        self.assertNotIn("MODE PLAN", sp)
        self.app.ctx.mode = "plan"
        self.assertIn("MODE PLAN", self.app.agent.system_prompt())
        self.cfg["tool_mode"] = "none"
        self.assertIn("TANPA TOOL", self.app.agent.system_prompt())

    def test_skill_block_injects_strong_matches_and_hints_weak_ones(self):
        blk = self.app.agent.skill_block("cek web di localhost:3000")
        self.assertIn("[SKILL OTOMATIS: web-check]", blk)
        self.assertIn("Cek aplikasi web lokal", blk)
        self.assertEqual(self.app.agent.skill_block("halo apa kabar"), "")
        self.assertEqual(self.app.agent.skill_block("[SKILL AKTIF: x]\ncek web"), "")


class Skills(AppCase):
    def test_dollar_mentions(self):
        out = self.app.expand_skill_mentions("tolong $web-check dan $HOME serta $web-check lagi")
        self.assertEqual(out.count("[SKILL AKTIF: web-check]"), 1)
        self.assertIn("Cek aplikasi web lokal", out)
        self.assertNotIn("[SKILL AKTIF: HOME]", out)
        self.assertEqual(self.app.expand_skill_mentions("harga $5 dan $PATH"), "harga $5 dan $PATH")
        self.assertEqual(self.app.expand_skill_mentions("[SKILL AKTIF: a]\n$web-check"), "[SKILL AKTIF: a]\n$web-check")

    def test_run_skill_composes_prompt_with_body_and_task(self):
        with mock.patch.object(self.app, "run_turn") as rt:
            self.app.run_skill("debug-fix", "error di app.py")
        text = rt.call_args[0][0]
        self.assertTrue(text.startswith("[SKILL AKTIF: debug-fix]"))
        self.assertIn("Debugging", text)
        self.assertIn("[TUGAS USER]\nerror di app.py", text)
        self.assertFalse(rt.call_args[1]["attach"])

    def test_run_skill_default_task_and_unknown_name(self):
        with mock.patch.object(self.app, "run_turn") as rt:
            self.app.run_skill("secret", "")                               # prefix unik
            self.assertIn("Terapkan skill ini", rt.call_args[0][0])
            rt.reset_mock()
            with mock.patch.object(self.app.ui, "err") as err:
                self.app.run_skill("web-chek", "")                         # salah ketik -> saran
            rt.assert_not_called()
            self.assertIn("web-check", err.call_args[0][0])

    def test_all_ways_to_invoke_a_skill(self):
        with mock.patch.object(self.app, "run_skill") as rs:
            self.app.slash("/web-check cek port 3000")
            rs.assert_called_with("web-check", "cek port 3000")
            self.app.slash("/skill debug-fix x y")
            rs.assert_called_with("debug-fix", "x y")
            self.app.slash("/skills secret")
            rs.assert_called_with("secret", "")

    def test_builtin_command_beats_skill_and_custom_beats_skill(self):
        os.makedirs(".codinx/commands")
        with open(".codinx/commands/web-check.md", "w") as f:
            f.write("---\ndescription: tiruan\n---\nperintah kustom $ARGUMENTS\n")
        with mock.patch.object(self.app, "run_turn") as rt, mock.patch.object(self.app, "run_skill") as rs:
            self.app.slash("/web-check halo")
            rs.assert_not_called()
            self.assertIn("perintah kustom halo", rt.call_args[0][0])

    def test_unknown_command_reports_error(self):
        with mock.patch.object(self.app.ui, "err") as err:
            self.app.slash("/tidak-ada")
        self.assertIn("tidak dikenal", err.call_args[0][0])


class Submit(AppCase):
    def test_user_prompt_hook_can_block_before_any_model_call(self):
        with open(os.path.join(self.home, "hooks.json"), "w") as f:
            json.dump({"hooks": {"UserPromptSubmit": [{"command": "echo 'kata terlarang' >&2; exit 2"}]}}, f)
        with mock.patch.object(self.app.agent, "turn", side_effect=AssertionError("tidak boleh dipanggil")):
            self.assertEqual(self.app.submit("halo"), "")

    def test_hook_output_becomes_context_and_stop_hook_runs(self):
        with open(os.path.join(self.home, "hooks.json"), "w") as f:
            json.dump({"hooks": {"UserPromptSubmit": [{"command": "echo konteks-tambahan"}],
                                 "Stop": [{"command": "echo selesai > stop.flag"}]}}, f)
        with mock.patch.object(self.app.agent, "turn", return_value="jawaban") as turn:
            self.assertEqual(self.app.submit("halo"), "jawaban")
        self.assertIn("konteks-tambahan", turn.call_args[0][0])
        self.assertTrue(os.path.exists("stop.flag"))

    def test_submit_captures_memory_and_attaches_files(self):
        with open("catatan.txt", "w") as f:
            f.write("isi catatan")
        with mock.patch.object(self.app.agent, "turn", return_value="ok") as turn:
            self.app.submit("ingat bahwa kopi itu enak. lihat @catatan.txt")
        self.assertTrue(any("kopi itu enak" in m["text"] for m in memory.load()))
        sent = turn.call_args[0][0]
        self.assertIn('<file path="', sent)
        self.assertIn("isi catatan", sent)

    def test_mentions_ignore_missing_and_list_directories(self):
        os.makedirs("sub")
        open("sub/x.txt", "w").close()
        out = self.app.attach_mentions("@sub dan @tidak-ada.txt dan email@contoh.com")
        self.assertIn("<dir", out)
        self.assertIn("x.txt", out)
        self.assertNotIn("tidak-ada", out.split("</dir>")[-1])

    def test_template_expansion(self):
        out = self.app.expand_template('A=$1 B=$2 SEMUA=$ARGUMENTS', 'satu "dua tiga"')
        self.assertEqual(out, 'A=satu B=dua tiga SEMUA=satu "dua tiga"')


class Commands(AppCase):
    def test_every_listed_command_is_implemented(self):
        for cmd, desc in COMMANDS:
            self.assertTrue(desc)
            self.assertTrue(hasattr(App, "cmd_" + cmd[1:].replace("-", "_")), cmd)
        for alias, target in ALIASES.items():
            self.assertIn(target, [c for c, _ in COMMANDS], alias)

    def test_mode_commands(self):
        self.app.cmd_toolmode("TEXT")
        self.assertEqual(self.cfg["tool_mode"], "text")
        self.app.cmd_toolmode("bogus")
        self.assertEqual(self.cfg["tool_mode"], "text")
        self.app.cmd_historymode("flat")
        self.assertEqual(self.cfg["history_mode"], "flat")
        self.assertEqual(self.app.agent.modes(), ("text", "flat"))
        self.app.cmd_toolmode("auto")
        caps.set("m-unit-test", tools="none", history="native")
        self.assertEqual(self.app.agent.modes(), ("none", "flat"))

    def test_footer_reflects_modes(self):
        self.assertNotIn("riwayat:flat", self.app.footer())
        caps.set("m-unit-test", tools="text", history="flat")
        foot = self.app.footer()
        for needle in ("m-unit-test", "build", "riwayat:flat", "tool:teks", "gratis"):
            self.assertIn(needle, foot)
        self.cfg["trial_mode"] = False
        self.assertIn("Dinar", self.app.footer())

    def test_trial_mode_unlocks_everything_in_the_ui(self):
        self.assertTrue(self.cfg["trial_mode"])
        self.assertIn("gratis", tiers.plan_label(self.cfg))
        self.assertTrue(all(tiers.can_use_model(self.cfg, m["id"])[0] for m in tiers.catalog()))

    def test_memory_commands(self):
        self.app.cmd_remember("fakta satu")
        self.app.cmd_memory("add fakta dua")
        self.assertEqual({m["text"] for m in memory.load()}, {"fakta satu", "fakta dua"})
        self.app.cmd_forget("1")
        self.assertEqual([m["text"] for m in memory.load()], ["fakta dua"])
        self.app.cmd_forget("all")
        self.assertEqual(memory.load(), [])

    def test_plan_build_switch_persists_choice(self):
        self.app.cmd_plan("")
        self.assertEqual((self.app.ctx.mode, self.cfg["agent"]), ("plan", "plan"))
        self.app.cmd_agent("")
        self.assertEqual(self.app.ctx.mode, "build")

    def test_auto_toggle(self):
        self.app.cmd_auto("")
        self.assertTrue(self.app.perms.auto)
        self.app.cmd_auto("")
        self.assertFalse(self.app.perms.auto)

    def test_custom_commands_from_package_and_project(self):
        names = set(self.app.custom_commands())
        for c in ("/review", "/doc", "/security", "/publish", "/scan", "/standup", "/explain-error"):
            self.assertIn(c, names)
        self.assertGreaterEqual(len(names), 15)


if __name__ == "__main__":
    unittest.main()
