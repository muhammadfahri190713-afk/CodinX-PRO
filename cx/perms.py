"""Permission engine: policy per tool (default/ask/allow/deny/off), pattern rules, hard-deny."""
import re

from . import config

HARD_DENY = [
    r"\brm\b[^;&|]*\s-[a-zA-Z]*[rR][a-zA-Z]*[^;&|]*\s(/|/\*|~|~/|\$HOME|/root)(\s|$)",
    r"\bmkfs(\.\w+)?\b",
    r"\bdd\b[^;&|]*\bof=/dev/(sd|nvme|vd|hd|xvd|mmcblk)",
    r":\s*\(\s*\)\s*\{[^}]*:\s*\|\s*:",
    r">\s*/dev/(sd|nvme|vd|hd)",
    r"\bchmod\s+-R\s+[0-7]{3,4}\s+/(\s|$)",
    r"\bchown\s+-R\s+\S+\s+/(\s|$)",
    r"\b(shutdown|reboot|halt|poweroff|init\s+0)\b",
    r"\bwipefs\b|\bshred\b[^;&|]*\s/dev/",
]
META = re.compile(r"[;&|`$<>\n]|\$\(")

SAFE_BASH = {
    "*": "ask", "ls*": "allow", "pwd": "allow", "cat *": "allow", "head *": "allow", "tail *": "allow",
    "echo *": "allow", "wc *": "allow", "which *": "allow", "git status*": "allow", "git diff*": "allow",
    "git log*": "allow", "git branch*": "allow", "python3 --version": "allow", "node --version": "allow",
    "npm --version": "allow", "whoami": "allow", "date": "allow", "uname*": "allow",
}
DEFAULT_RULES = {
    "*": "ask",
    "read": {"*": "allow", "*.env": "ask", "*.env.*": "ask", "*id_rsa*": "ask", "*id_ed25519*": "ask", "*.pem": "ask"},
    "edit": "allow",
    "bash": SAFE_BASH,
    "webfetch": "allow",
    "localhost": "allow",
    "camera": "ask",
    "external_directory": "ask",
}
ALWAYS_OK = {"list", "glob", "grep", "todowrite", "todoread", "task", "skill", "memory", "table"}
DEFAULT_POLICY = {"camera": "off"}      # kamera mati sampai diaktifkan di /permissions
POLICY_CYCLE = ["default", "ask", "allow", "deny", "off"]


def wild(pattern, subject):
    rx = "^" + re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".") + "$"
    return re.match(rx, subject, re.S) is not None


def hard_denied(cmd):
    return any(re.search(p, cmd) for p in HARD_DENY)


class Perms:
    def __init__(self, cfg):
        self.cfg = cfg
        self.auto = False              # --auto / /auto : semua "ask" jadi "allow" (hard-deny tetap berlaku)
        self.session_allow = []

    def policy(self, tool):
        pol = self.cfg.get("tool_policy", {})
        return pol.get(tool, DEFAULT_POLICY.get(tool, "default"))

    def enabled(self, tool):
        return self.policy(tool) != "off"

    def decide(self, tool, subject=""):
        if tool == "bash" and hard_denied(subject):
            return "deny"
        if tool.startswith("mcp__"):               # tool MCP: kebijakan per-tool, lalu kebijakan induk "mcp"
            pols = self.cfg.get("tool_policy", {})
            pol = pols.get(tool) or pols.get("mcp") or "default"
        else:
            pol = self.policy(tool)
        if pol in ("off", "deny"):
            return "deny"
        if pol == "allow":
            return "allow"
        if pol == "ask":
            return "allow" if self.auto else "ask"
        if tool in ALWAYS_OK:
            return "allow"
        act, matched = self._eval(tool, subject)
        if tool == "bash" and act == "allow" and matched != "*" and META.search(subject):
            act = "ask"
        if act == "ask" and self.auto:
            act = "allow"
        return act

    def _eval(self, tool, subject):
        rule = self.cfg.get("permission", {}).get(tool, DEFAULT_RULES.get(tool, DEFAULT_RULES["*"]))
        if isinstance(rule, str):
            return rule, "*"
        act, matched = None, None
        for pat, a in rule.items():
            if wild(pat, subject):
                act, matched = a, pat
        return act or "ask", matched

    def allow_always(self, tool):
        self.cfg.setdefault("tool_policy", {})[tool] = "allow"
        config.save(self.cfg)

    def set_policy(self, tool, value):
        pol = self.cfg.setdefault("tool_policy", {})
        if value == "default":
            pol.pop(tool, None)
        else:
            pol[tool] = value
        config.save(self.cfg)
