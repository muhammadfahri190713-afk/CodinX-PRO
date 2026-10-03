#!/usr/bin/env python3
"""Buat subset Pygments (BSD-2-Clause) di cx/vendor/pygments untuk syntax highlighting.

Semua modul inti, formatter, style, dan filter disalin. Lexer dipilih berdasarkan prioritas bahasa populer
(+ dependensi antar-lexer) sampai anggaran ukuran terpenuhi, lalu `_mapping.py` dibuat ulang agar konsisten.

  python3 scripts/vendor_pygments.py --budget-kb 900
"""
import argparse
import ast
import importlib
import os
import shutil
import sys
import zlib

PRIORITY = [
    "special", "text", "python", "javascript", "shell", "html", "css", "data", "markup", "sql", "c_cpp", "c_like", "jvm", "go",
    "rust", "php", "ruby", "dotnet", "diff", "configs", "make", "scripting", "perl", "objective", "haskell", "ml", "erlang",
    "functional", "julia", "r", "templates", "webmisc", "graphql", "dsls", "zig", "d", "crystal", "nimrod", "elm", "gdscript",
    "solidity", "typst", "tcl", "asm", "hdl", "pascal", "fortran", "basic", "console", "lisp", "matlab", "vyper", "wgsl",
    "webassembly", "yang", "dns", "email", "textfmts", "installers", "testing", "robotframework", "prolog", "smalltalk",
]


def csize(path):
    with open(path, "rb") as f:
        return len(zlib.compress(f.read(), 9))


def deps(src_lexers, stem):
    out = set()
    path = os.path.join(src_lexers, stem + ".py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    def add(d):
        if d != stem and os.path.exists(os.path.join(src_lexers, d + ".py")):
            out.add(d)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("pygments.lexers."):
                add(node.module.split(".")[2])
            elif node.module == "pygments.lexers":            # from pygments.lexers import _xxx_builtins
                for alias in node.names:
                    add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("pygments.lexers."):
                    add(alias.name.split(".")[2])
    return out


def closure(src_lexers, stem, seen=None):
    seen = seen if seen is not None else set()
    if stem in seen:
        return seen
    seen.add(stem)
    for d in deps(src_lexers, stem):
        closure(src_lexers, d, seen)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-kb", type=int, default=900)
    ap.add_argument("--src", default="")
    ap.add_argument("--dest", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cx", "vendor"))
    a = ap.parse_args()

    if a.src:
        sys.path.insert(0, a.src)
    import pygments
    src = os.path.dirname(pygments.__file__)
    src_lex = os.path.join(src, "lexers")
    dest = os.path.join(a.dest, "pygments")
    shutil.rmtree(a.dest, ignore_errors=True)
    os.makedirs(os.path.join(dest, "lexers"))

    total = 0
    for f in os.listdir(src):                                   # inti
        p = os.path.join(src, f)
        if f.endswith(".py"):
            shutil.copy2(p, dest)
            total += csize(p)
    for sub in ("formatters", "styles", "filters"):             # formatter/style/filter lengkap
        shutil.copytree(os.path.join(src, sub), os.path.join(dest, sub), ignore=shutil.ignore_patterns("__pycache__"))
        total += sum(csize(os.path.join(r, f)) for r, _, fs in os.walk(os.path.join(src, sub)) for f in fs
                     if f.endswith(".py") and "__pycache__" not in r)
    shutil.copy2(os.path.join(src_lex, "__init__.py"), os.path.join(dest, "lexers"))
    total += csize(os.path.join(src_lex, "__init__.py"))

    all_mods = sorted(f[:-3] for f in os.listdir(src_lex) if f.endswith(".py") and f not in ("__init__.py", "_mapping.py"))
    budget = a.budget_kb * 1000
    kept = set()

    def try_add(stem):
        nonlocal total
        need = {m for m in closure(src_lex, stem) if m not in kept}
        cost = sum(csize(os.path.join(src_lex, m + ".py")) for m in need)
        if total + cost + 16000 > budget:                       # 16 KB cadangan untuk _mapping.py
            return False
        for m in need:
            shutil.copy2(os.path.join(src_lex, m + ".py"), os.path.join(dest, "lexers"))
        kept.update(need)
        total += cost
        return True

    for stem in PRIORITY:
        if stem in all_mods:
            try_add(stem)
    rest = sorted((m for m in all_mods if m not in kept and not m.startswith("_")),
                  key=lambda m: csize(os.path.join(src_lex, m + ".py")))
    for stem in rest:                                           # isi sisa anggaran dengan lexer kecil
        try_add(stem)

    # _mapping.py yang konsisten dengan modul yang ada
    mapping = importlib.import_module("pygments.lexers._mapping").LEXERS
    keep_mods = {"pygments.lexers." + m for m in kept}
    lines = ["# Subset otomatis (scripts/vendor_pygments.py): hanya lexer yang disertakan.", "LEXERS = {"]
    n = 0
    for k, v in sorted(mapping.items()):
        if v[0] in keep_mods:
            lines.append(f"    {k!r}: {v!r},")
            n += 1
    lines.append("}")
    with open(os.path.join(dest, "lexers", "_mapping.py"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    total += 14000

    for name in ("LICENSE", "AUTHORS"):                        # lisensi BSD-2 wajib ikut
        for root in (os.path.dirname(src), os.path.join(os.path.dirname(src), "pygments-%s.dist-info" % pygments.__version__)):
            for r, _, fs in os.walk(root):
                if name in fs and os.path.basename(r) != "pygments" or (name in fs and r == root):
                    shutil.copy2(os.path.join(r, name), os.path.join(a.dest, "PYGMENTS_" + name))
                    break
    with open(os.path.join(a.dest, "PYGMENTS_VERSION"), "w") as f:
        f.write(pygments.__version__ + "\n")
    print(f"pygments {pygments.__version__}: {len(kept)} modul lexer, {n} lexer terdaftar, ±{total // 1000} KB terkompresi")
    verify(a.dest)


def verify(vendor):
    """Pastikan SEMUA lexer terdaftar bisa diimpor dari salinan vendor (bukan dari pygments sistem)."""
    import subprocess
    code = ("import sys, importlib; sys.path.insert(0, %r); import pygments; "
            "assert pygments.__file__.startswith(%r), pygments.__file__; "
            "from pygments.lexers._mapping import LEXERS; bad=[]\n"
            "for k, v in LEXERS.items():\n"
            "    try: importlib.import_module(v[0])\n"
            "    except Exception as e: bad.append((k, type(e).__name__))\n"
            "print('verifikasi: %%d lexer, %%d gagal' %% (len(LEXERS), len(bad)), bad[:5]); sys.exit(1 if bad else 0)") % (vendor, vendor)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    if r.returncode:
        sys.exit(1)


if __name__ == "__main__":
    main()
