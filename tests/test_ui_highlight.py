import sys
import unittest
from unittest import mock

from cx import highlight, themes as T, ui
from . import ROOT


def render(text, color=False):
    T.set_enabled(color)
    out = []
    md = ui.Markdown(out.append)
    md.feed(text)
    md.flush()
    return "".join(out)


class Base(unittest.TestCase):
    def tearDown(self):
        T.set_enabled(False)


class MarkdownRender(Base):
    def test_headings_lists_quotes(self):
        out = render("# Judul\n## Sub\n- a\n* b\n1. satu\n> kutip\n---\n")
        for needle in ("JUDUL", "▌ Sub", "• a", "• b", "1. satu", "┃ kutip", "──"):
            self.assertTrue(needle in out, needle)

    def test_table_has_borders_and_cells(self):
        out = render("| Nama | Nilai |\n|---|---|\n| x | 1 |\n| yy | 22 |\n")
        for needle in ("┌", "┐", "└", "┘", "├", "Nama", "Nilai", "yy", "22"):
            self.assertTrue(needle in out, needle)

    def test_table_wraps_instead_of_truncating(self):
        long = "kalimat sangat panjang yang tidak boleh terpotong menjadi titik-titik di terminal sempit"
        with mock.patch.object(ui, "term_width", return_value=40):
            out = render(f"| k | v |\n|---|---|\n| a | {long} |\n")
        self.assertFalse("…" in out)
        for word in long.split():
            self.assertTrue(word in out, word)
        self.assertTrue(max(len(ln) for ln in out.splitlines()) <= 40)

    def test_headerless_table_for_key_value(self):
        u = ui.UI()
        buf = []
        u.w = buf.append
        u.table(["", ""], [["model", "m-1"]], None)
        text = "".join(buf)
        self.assertTrue("model" in text and "m-1" in text)
        self.assertFalse("├" in text)                 # tanpa baris header + pemisah

    def test_plain_code_fence(self):
        out = render("```zzz-bahasa-tak-dikenal\nx = 1\ny = 2\n```\n")
        self.assertEqual(out, "  ┌─ zzz-bahasa-tak-dikenal\n  │ x = 1\n  │ y = 2\n  └─\n")

    def test_unclosed_fence_is_flushed(self):
        self.assertTrue("  │ sisa" in render("```\nsisa"))

    def test_inline_markup_with_color(self):
        out = render("Ini **tebal** dan `kode` serta [tautan](https://a.b)", color=True)
        self.assertTrue("tebal" in out and "kode" in out and "tautan" in out and "https://a.b" in out)
        self.assertTrue("\x1b[" in out)


class Highlight(Base):
    def test_vendored_pygments_available_and_used(self):
        self.assertTrue(highlight.available())
        import pygments
        self.assertTrue(pygments.__file__.startswith(highlight._VENDOR), pygments.__file__)

    def test_python_is_colored_and_text_preserved(self):
        T.set_enabled(True)
        lines = highlight.render("def f(x):\n    return x * 2  # kali dua\n", "python")
        self.assertEqual(len(lines), 2)
        self.assertTrue("\x1b[" in lines[0])
        plain = [ui.strip_ansi(ln) for ln in lines]
        self.assertEqual(plain, ["def f(x):", "    return x * 2  # kali dua"])

    def test_colored_code_fence_end_to_end(self):
        out = render("```python\nprint('hi')\n```\n", color=True)
        self.assertTrue("\x1b[38;" in out)
        self.assertTrue("print" in ui.strip_ansi(out))

    def test_unknown_language_and_disabled_return_none(self):
        T.set_enabled(True)
        self.assertIsNone(highlight.render("x", "bahasa-tidak-ada"))
        self.assertIsNone(highlight.render("x", ""))
        T.set_enabled(False)
        self.assertIsNone(highlight.render("print(1)", "python"))

    def test_huge_blocks_skip_highlighting(self):
        T.set_enabled(True)
        self.assertIsNone(highlight.render("x\n" * (highlight.MAX_LINES + 5), "python"))

    def test_all_theme_styles_resolve(self):
        T.set_enabled(True)
        for name in T.names():
            T.set_theme(name)
            self.assertIsNotNone(highlight.render("a = 1", "python"), name)
        T.set_theme("codinx")


class Keys(unittest.TestCase):
    def test_key_tokenisation(self):
        self.assertEqual(list(ui.UI._keys(b"\x1b[C\r")), [b"\x1b[C", b"\r"])
        self.assertEqual(list(ui.UI._keys(b"1\r")), [b"1", b"\r"])
        self.assertEqual(list(ui.UI._keys(b"\x1b[D\x1b[D\n")), [b"\x1b[D", b"\x1b[D", b"\n"])

    def test_quiet_confirm_denies(self):
        u = ui.UI()
        u.quiet = True
        self.assertEqual(u.confirm("bash", "ls"), "no")

    def test_banner_rows_are_aligned(self):
        rows = ui.banner_lines()
        self.assertEqual(len(rows), 6)
        self.assertEqual(len({len(r) for r in rows}), 1)


if __name__ == "__main__":
    unittest.main()
