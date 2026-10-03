import importlib
import os
import sys
import unittest

from cx import highlight
from . import ROOT

VENDOR = os.path.join(ROOT, "cx", "vendor")


class VendoredPygments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        highlight.available()

    def test_license_and_metadata_ship_with_vendor(self):
        for f in ("PYGMENTS_LICENSE", "PYGMENTS_AUTHORS", "PYGMENTS_VERSION"):
            self.assertTrue(os.path.getsize(os.path.join(VENDOR, f)) > 0, f)
        with open(os.path.join(VENDOR, "PYGMENTS_LICENSE")) as f:
            self.assertIn("Redistribution and use in source and binary forms", f.read())

    def test_popular_languages_are_available(self):
        from pygments.lexers import get_lexer_by_name
        for lang in ("python", "bash", "json", "yaml", "javascript", "typescript", "sql", "dockerfile", "diff", "markdown",
                     "html", "css", "go", "rust", "java", "c", "cpp", "php", "ruby", "toml", "ini", "nginx", "powershell"):
            self.assertIsNotNone(get_lexer_by_name(lang), lang)

    def test_every_registered_lexer_module_imports(self):
        from pygments.lexers._mapping import LEXERS
        self.assertGreater(len(LEXERS), 200)
        bad = []
        for name, entry in LEXERS.items():
            try:
                importlib.import_module(entry[0])
            except Exception as e:                      # noqa: BLE001
                bad.append((name, type(e).__name__))
        self.assertEqual(bad, [])

    def test_vendored_copy_is_the_one_in_use(self):
        import pygments
        self.assertTrue(os.path.realpath(pygments.__file__).startswith(os.path.realpath(VENDOR)))


if __name__ == "__main__":
    unittest.main()
