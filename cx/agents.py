"""Sub-agent khusus (Markdown + frontmatter): agents/ bawaan, ~/.codinx/agents, <proyek>/.codinx/agents.

  ---
  name: reviewer
  description: Review kode read-only
  tools: read, grep, glob, list
  ---
  (isi = system prompt sub-agent)
"""
import os
import re

from . import config, skills

PKG_AGENTS = os.path.join(config.ROOT, "agents")


def roots(cwd):
    return [PKG_AGENTS, os.path.join(config.HOME, "agents"), os.path.join(cwd, ".codinx", "agents")]


def discover(cwd):
    found = {}
    for root in roots(cwd):
        if not os.path.isdir(root):
            continue
        for f in sorted(os.listdir(root)):
            if not f.endswith(".md"):
                continue
            try:
                with open(os.path.join(root, f), encoding="utf-8") as fh:
                    meta, body = skills.parse(fh.read())
            except OSError:
                continue
            name = meta.get("name") or f[:-3]
            tools = [t for t in re.split(r"[,\s]+", meta.get("tools", "")) if t]
            found[name] = {"name": name, "description": meta.get("description", ""), "tools": tools or None,
                           "prompt": body.strip(), "path": os.path.join(root, f)}
    return found


def resolve(name, cwd):
    found = discover(cwd)
    n = (name or "").strip().lower()
    for k, v in found.items():
        if k.lower() == n:
            return v
    return None


def index_block(cwd):
    return "\n".join(f"- {a['name']}: {a['description']}" for a in discover(cwd).values())
