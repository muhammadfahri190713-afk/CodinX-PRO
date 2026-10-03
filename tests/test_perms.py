import unittest

from cx import perms


class Decide(unittest.TestCase):
    def setUp(self):
        self.cfg = {"tool_policy": {}, "permission": {}}
        self.p = perms.Perms(self.cfg)
        # jangan menulis config.json milik siapa pun
        self.p.allow_always = lambda tool: self.cfg["tool_policy"].__setitem__(tool, "allow")

    def test_safe_bash_allowed_unsafe_asks(self):
        self.assertEqual(self.p.decide("bash", "ls -la"), "allow")
        self.assertEqual(self.p.decide("bash", "git status"), "allow")
        self.assertEqual(self.p.decide("bash", "npm install"), "ask")

    def test_metacharacters_downgrade_allow_to_ask(self):
        for cmd in ("ls; rm x", "cat a > b", "echo $(whoami)", "ls | wc", "cat a && rm b"):
            self.assertEqual(self.p.decide("bash", cmd), "ask", cmd)

    def test_hard_deny(self):
        for cmd in ("rm -rf /", "rm -rf /*", "rm -rf ~", "rm -fr /root", "rm -r -f /", "mkfs.ext4 /dev/sda1",
                    "dd if=x of=/dev/sda", "reboot", "shutdown -h now", ":(){ :|: & };:"):
            self.assertEqual(self.p.decide("bash", cmd), "deny", cmd)
        self.assertEqual(self.p.decide("bash", "rm -rf build"), "ask")

    def test_hard_deny_survives_auto_and_allow_policy(self):
        self.p.auto = True
        self.cfg["tool_policy"]["bash"] = "allow"
        self.assertEqual(self.p.decide("bash", "rm -rf /"), "deny")
        self.assertEqual(self.p.decide("bash", "npm install"), "allow")

    def test_auto_turns_ask_into_allow(self):
        self.p.auto = True
        self.assertEqual(self.p.decide("bash", "npm install"), "allow")

    def test_read_rules(self):
        self.assertEqual(self.p.decide("read", "/etc/hosts"), "allow")
        self.assertEqual(self.p.decide("read", "/app/.env"), "ask")
        self.assertEqual(self.p.decide("read", "/root/.ssh/id_rsa"), "ask")

    def test_policy_overrides(self):
        for pol, want in (("deny", "deny"), ("off", "deny"), ("allow", "allow"), ("ask", "ask")):
            self.cfg["tool_policy"]["edit"] = pol
            self.assertEqual(self.p.decide("edit", "/x"), want, pol)

    def test_camera_is_off_by_default(self):
        self.assertFalse(self.p.enabled("camera"))
        self.assertEqual(self.p.decide("camera", "/dev/video0"), "deny")

    def test_mcp_policy_per_tool_then_parent(self):
        self.assertEqual(self.p.decide("mcp__s__t", "{}"), "ask")
        self.cfg["tool_policy"]["mcp"] = "allow"
        self.assertEqual(self.p.decide("mcp__s__t", "{}"), "allow")
        self.cfg["tool_policy"]["mcp__s__t"] = "deny"
        self.assertEqual(self.p.decide("mcp__s__t", "{}"), "deny")
        self.cfg["tool_policy"] = {"mcp": "off"}
        self.assertEqual(self.p.decide("mcp__s__t", "{}"), "deny")

    def test_wildcards(self):
        self.assertTrue(perms.wild("git *", "git status"))
        self.assertTrue(perms.wild("*.env", "/a/b.env"))
        self.assertFalse(perms.wild("git *", "gitx"))


if __name__ == "__main__":
    unittest.main()
