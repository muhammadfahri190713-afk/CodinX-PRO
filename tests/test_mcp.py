import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from cx import mcp, perms, tools, ui
from cx.session import Session
from . import ROOT

FAKE = os.path.join(ROOT, "tests", "fake_mcp_server.py")


class Manager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = mcp.Manager()
        cls.m.specs = {"echo": {"command": sys.executable, "args": [FAKE]},
                       "rusak": {"command": "/tidak/ada/binernya"},
                       "mati": {"command": sys.executable, "args": ["-c", "import sys; sys.exit(0)"]}}
        cls.m.ensure_started()

    @classmethod
    def tearDownClass(cls):
        cls.m.stop_all()

    def test_good_server_started_and_bad_ones_report_errors(self):
        self.assertTrue(self.m.servers["echo"].started)
        self.assertEqual({t["name"] for t in self.m.servers["echo"].tools}, {"echo", "add", "boom"})
        self.assertFalse(self.m.servers["rusak"].started)
        self.assertTrue(self.m.servers["rusak"].error)
        self.assertFalse(self.m.servers["mati"].started)
        self.assertTrue(self.m.servers["mati"].error)

    def test_schemas_are_openai_function_format(self):
        schemas = {s["function"]["name"]: s["function"] for s in self.m.schemas()}
        self.assertEqual(set(schemas), {"mcp__echo__echo", "mcp__echo__add", "mcp__echo__boom"})
        fn = schemas["mcp__echo__add"]
        self.assertTrue(fn["description"].startswith("[MCP:echo]"))
        self.assertEqual(fn["parameters"]["type"], "object")
        self.assertEqual(fn["parameters"]["required"], ["a", "b"])

    def test_calls(self):
        self.assertEqual(self.m.call("mcp__echo__echo", {"text": "halo"}), "halo")
        self.assertEqual(self.m.call("mcp__echo__add", {"a": 2, "b": 3.5}), "5.5")
        self.assertEqual(self.m.call("mcp__echo__boom", {}), "Error: meledak")
        self.assertTrue(self.m.has("mcp__echo__echo"))
        self.assertFalse(self.m.has("mcp__echo__nope"))

    def test_unknown_tool_on_server_raises_mcp_error(self):
        srv = self.m.servers["echo"]
        with self.assertRaises(mcp.MCPError):
            srv.call("tidak-ada", {})

    def test_status_rows(self):
        rows = {r[0]: r for r in self.m.status()}
        self.assertTrue(rows["echo"][1].startswith("✓"))
        self.assertTrue(rows["rusak"][1].startswith("✗"))

    def test_name_sanitising(self):
        self.assertEqual(mcp._safe("mcp__my-server__do.thing"), "mcp__my_server__do_thing")
        self.assertLessEqual(len(mcp._safe("x" * 200)), 64)
        self.assertEqual(mcp._params(None), {"type": "object", "properties": {}})
        self.assertEqual(mcp._params({"type": "object", "$schema": "x"}), {"type": "object", "properties": {}})


class ThroughTools(unittest.TestCase):
    def setUp(self):
        self.m = mcp.Manager()
        self.m.specs = {"echo": {"command": sys.executable, "args": [FAKE]}}
        self.m.ensure_started()
        p = mock.patch.object(mcp, "manager", self.m)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.m.stop_all)
        self.cwd = tempfile.mkdtemp()
        self.cfg = {"tool_policy": {}, "permission": {}}
        self.perms = perms.Perms(self.cfg)
        u = ui.UI()
        u.quiet = True
        self.ctx = tools.Ctx(self.cwd, self.perms, u, Session(self.cwd), self.cfg)

    def call(self, name, **a):
        return tools.run(self.ctx, name, a)

    def test_default_policy_asks_and_non_interactive_denies(self):
        self.assertIn("MENOLAK", self.call("mcp__echo__echo", text="x"))

    def test_parent_policy_allows_all_mcp_tools(self):
        self.cfg["tool_policy"]["mcp"] = "allow"
        self.assertEqual(self.call("mcp__echo__echo", text="halo"), "halo")
        self.assertEqual(self.call("mcp__echo__add", a=1, b=2), "3")

    def test_per_tool_deny_beats_parent_allow(self):
        self.cfg["tool_policy"].update({"mcp": "allow", "mcp__echo__echo": "deny"})
        self.assertIn("kebijakan", self.call("mcp__echo__echo", text="x"))
        self.assertEqual(self.call("mcp__echo__add", a=1, b=1), "2")

    def test_unknown_mcp_tool_and_plan_mode(self):
        self.cfg["tool_policy"]["mcp"] = "allow"
        self.assertIn("tidak dikenal", self.call("mcp__echo__ghaib"))
        self.ctx.mode = "plan"
        self.assertIn("PLAN", self.call("mcp__echo__echo", text="x"))

    def test_server_death_surfaces_as_error_not_crash(self):
        self.cfg["tool_policy"]["mcp"] = "allow"
        self.m.servers["echo"].stop()
        out = self.call("mcp__echo__echo", text="x")
        self.assertTrue(out.startswith("Error: MCP"))


class Config(unittest.TestCase):
    def test_load_from_json_global_and_trusted_project(self):
        home, cwd = tempfile.mkdtemp(), tempfile.mkdtemp()
        os.makedirs(os.path.join(cwd, ".codinx"))
        with open(os.path.join(home, "mcp.json"), "w") as f:
            json.dump({"mcpServers": {"g": {"command": "a"}, "off": {"command": "b", "disabled": True}, "rusak": {"args": []}}}, f)
        with open(os.path.join(cwd, ".codinx", "mcp.json"), "w") as f:
            json.dump({"mcpServers": {"p": {"command": "c"}}}, f)
        with mock.patch.object(mcp.config, "HOME", home):
            m = mcp.Manager()
            m.load(cwd, {})
            self.assertEqual(set(m.specs), {"g"})                                  # proyek butuh trust; disabled/rusak diabaikan
            m.load(cwd, {"trust_project": True})
            self.assertEqual(set(m.specs), {"g", "p"})


if __name__ == "__main__":
    unittest.main()
