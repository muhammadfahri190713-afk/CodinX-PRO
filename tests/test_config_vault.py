import base64
import json
import os
import stat
import tempfile
import unittest
from unittest import mock

from cx import config, vault
from .helpers import read


class Vault(unittest.TestCase):
    def test_roundtrip_and_not_plaintext(self):
        blob = vault.encrypt("sk-test-123")
        self.assertEqual(vault.decrypt(blob), "sk-test-123")
        self.assertNotIn(b"sk-test-123", blob)
        self.assertNotIn(b"sk-test-123", base64.b64decode(blob))

    def test_unique_ciphertext_and_unicode(self):
        self.assertNotEqual(vault.encrypt("x"), vault.encrypt("x"))
        self.assertEqual(vault.decrypt(vault.encrypt("kunci-ñ-日本")), "kunci-ñ-日本")

    def test_tampering_is_detected(self):
        raw = bytearray(base64.b64decode(vault.encrypt("rahasia")))
        raw[20] ^= 1
        with self.assertRaises(ValueError):
            vault.decrypt(base64.b64encode(bytes(raw)))
        with self.assertRaises(ValueError):
            vault.decrypt(base64.b64encode(b"bukan-brankas"))


class DotEnv(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.path = os.path.join(self.d, ".env")
        config._dotenv = None
        config._api_file = None

    def tearDown(self):
        config._dotenv = None
        config._api_file = None

    def write(self, text, mode=0o600):
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.chmod(self.path, mode)

    def test_parse_variants(self):
        self.write("\ufeff# komentar\r\nCODINX_BASE_URL=https://x.test/api\r\nexport CODINX_API_KEY=\"sk-abc def\"\r\n"
                   "CODINX_MODEL='m-1' # inline\r\nCODINX_TIER=free # komentar\r\nOTHER=zzz\r\n\r\nBARIS RUSAK\r\nCODINX_EMPTY=\r\n")
        self.assertEqual(config._parse_env(self.path), {
            "CODINX_BASE_URL": "https://x.test/api", "CODINX_API_KEY": "sk-abc def", "CODINX_MODEL": "m-1",
            "CODINX_TIER": "free", "CODINX_EMPTY": ""})

    def test_only_codinx_prefix_is_read(self):
        self.write("PATH=/hack\nAWS_SECRET=x\nCODINX_MODEL=a\n")
        self.assertEqual(list(config._parse_env(self.path)), ["CODINX_MODEL"])

    def test_missing_file(self):
        self.assertEqual(config._parse_env(os.path.join(self.d, "tidak-ada")), {})

    def test_api_file_reads_constants_only(self):
        p = os.path.join(self.d, "api.py")
        with open(p, "w") as f:
            f.write('API_KEY = "sk-test"\nBASE_URL = "https://example.test/api/v1"\nraise RuntimeError("must not execute")\n')
        self.assertEqual(config._parse_api_file(p), {"CODINX_API_KEY": "sk-test", "CODINX_BASE_URL": "https://example.test/api/v1"})

    def test_priority_real_env_beats_dotenv(self):
        self.write("CODINX_MODEL=dari-dotenv\nCODINX_TIER=pro\n")
        with mock.patch.object(config, "env_paths", return_value=[self.path]), mock.patch.dict(os.environ, {"CODINX_MODEL": "dari-env"}):
            self.assertEqual(config.env("CODINX_MODEL"), "dari-env")
            self.assertEqual(config.env("CODINX_TIER"), "pro")
            self.assertEqual(config.env("CODINX_TIDAK_ADA"), "")

    def test_later_file_wins(self):
        other = os.path.join(self.d, "global.env")
        with open(other, "w") as f:
            f.write("CODINX_MODEL=global\nCODINX_TIER=free\n")
        self.write("CODINX_MODEL=lokal\n")
        with mock.patch.object(config, "env_paths", return_value=[other, self.path]):
            self.assertEqual(config.env("CODINX_MODEL"), "lokal")
            self.assertEqual(config.env("CODINX_TIER"), "free")

    def test_world_readable_env_is_tightened_to_600(self):
        self.write("CODINX_MODEL=a\n", mode=0o644)
        with mock.patch.object(config, "env_paths", return_value=[self.path]):
            config.dotenv()
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)

    def test_key_source_labels(self):
        self.write("CODINX_API_KEY=sk-dari-dotenv-0123456789\n")
        with mock.patch.object(config, "env_paths", return_value=[self.path]), \
                mock.patch.object(config, "KEYFILE", os.path.join(self.d, "nokey.enc")):
            self.assertEqual(config.key_source(), ".env")
            self.assertEqual(config.get_key(), "sk-dari-dotenv-0123456789")
            with mock.patch.dict(os.environ, {"CODINX_API_KEY": "sk-env-0123456789ab"}):
                self.assertEqual(config.key_source(), "variabel lingkungan")
        config._dotenv = None
        with mock.patch.object(config, "env_paths", return_value=[]), mock.patch.object(config, "KEYFILE", os.path.join(self.d, "nokey.enc")):
            self.assertEqual(config.key_source(), "(belum ada)")

    def test_vault_file_is_used_when_no_env(self):
        keyfile = os.path.join(self.d, "k.enc")
        with mock.patch.object(config, "KEYFILE", keyfile), mock.patch.object(config, "env_paths", return_value=[]):
            config.set_key("sk-dari-brankas-0123456789")
            self.assertEqual(stat.S_IMODE(os.stat(keyfile).st_mode), 0o600)
            self.assertEqual(config.get_key(), "sk-dari-brankas-0123456789")
            self.assertEqual(config.key_source(), "brankas terenkripsi")


class Config(unittest.TestCase):
    def setUp(self):
        config._dotenv = None
        self.cwd = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.cwd, ".codinx"))
        self.addCleanup(lambda: os.path.exists(config.CONFIG) and os.remove(config.CONFIG))

    def project(self, data):
        with open(os.path.join(self.cwd, ".codinx", "config.json"), "w") as f:
            json.dump(data, f)

    def test_normalize_url(self):
        self.assertEqual(config.normalize_url("https://a.b/api"), "https://a.b/api/v1")
        self.assertEqual(config.normalize_url("https://a.b/api/v1/"), "https://a.b/api/v1")
        self.assertEqual(config.normalize_url(""), "")
        self.assertEqual(config.normalize_url("http://x/v2"), "http://x/v2")

    def test_project_config_only_allows_safe_keys(self):
        self.project({"model": "proj-model", "max_steps": 7, "base_url": "https://evil.example", "conv_field": "x",
                      "tool_policy": {"bash": "allow"}, "trust_project": True, "insecure_tls": True})
        cfg = config.load(self.cwd)
        self.assertEqual(cfg["model"], "proj-model")
        self.assertEqual(cfg["max_steps"], 7)
        self.assertNotIn("evil", cfg["base_url"])
        self.assertEqual(cfg["tool_policy"], {})
        self.assertFalse(cfg["trust_project"])
        self.assertFalse(cfg["insecure_tls"])
        self.assertEqual(cfg["conv_field"], "")

    def test_save_does_not_persist_project_overrides(self):
        self.project({"model": "proj-model"})
        cfg = config.load(self.cwd)
        config.save(cfg)
        self.assertNotEqual(json.loads(read(config.CONFIG))["model"], "proj-model")
        cfg["model"] = "pilihan-user"                         # perubahan eksplisit user tetap disimpan
        config.save(cfg)
        self.assertEqual(json.loads(read(config.CONFIG))["model"], "pilihan-user")

    def test_loads_do_not_share_nested_defaults(self):
        a = config.load(self.cwd)
        a["tool_policy"]["bash"] = "allow"
        a["permission"]["x"] = "y"
        b = config.load(self.cwd)
        self.assertEqual((b["tool_policy"], b["permission"]), ({}, {}))
        self.assertEqual((config.DEFAULTS["tool_policy"], config.DEFAULTS["permission"]), ({}, {}))

    def test_trial_mode_default_and_env_switch(self):
        self.assertTrue(config.load(self.cwd)["trial_mode"])
        with mock.patch.dict(os.environ, {"CODINX_TRIAL": "0"}):
            self.assertFalse(config.load(self.cwd)["trial_mode"])
        with mock.patch.dict(os.environ, {"CODINX_TRIAL": "1"}):
            self.assertTrue(config.load(self.cwd)["trial_mode"])

    def test_env_values_are_not_persisted_to_config_json(self):
        with mock.patch.dict(os.environ, {"CODINX_TRIAL": "0", "CODINX_MODEL": "model-dari-env", "CODINX_TIER": "max",
                                          "CODINX_BASE_URL": "https://env.example/api"}):
            cfg = config.load(self.cwd)
            self.assertEqual((cfg["model"], cfg["tier"], cfg["trial_mode"]), ("model-dari-env", "max", False))
            config.save(cfg)
        saved = json.loads(read(config.CONFIG))
        self.assertEqual((saved["trial_mode"], saved["tier"]), (True, "free"))
        self.assertNotEqual(saved["model"], "model-dari-env")
        self.assertNotIn("env.example", saved["base_url"])
        again = config.load(self.cwd)                                          # tanpa env: kembali ke nilai asli
        self.assertTrue(again["trial_mode"])

    def test_env_overrides_and_validation(self):
        env = {"CODINX_TOOL_MODE": "TEXT", "CODINX_HISTORY_MODE": "bogus", "CODINX_AUTO_PROBE": "0", "CODINX_CONV_FIELD": "chat_id"}
        with mock.patch.dict(os.environ, env):
            cfg = config.load(self.cwd)
        self.assertEqual(cfg["tool_mode"], "text")
        self.assertEqual(cfg["history_mode"], "auto")          # nilai tak valid -> auto
        self.assertFalse(cfg["auto_probe"])
        self.assertEqual(cfg["conv_field"], "chat_id")


if __name__ == "__main__":
    unittest.main()
