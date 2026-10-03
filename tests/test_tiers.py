import os
import tempfile
import unittest
from unittest import mock

from cx import tiers


class Tiers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = mock.patch.object(tiers, "USAGE_FILE", os.path.join(self.tmp, "usage.json"))
        self.p.start()
        self.cfg = {"tier": "free", "timezone": "Asia/Jakarta", "dinar_token_unit": 8000, "trial_mode": False}

    def tearDown(self):
        self.p.stop()

    def test_catalog_matches_spec(self):
        cat = tiers.catalog()
        self.assertEqual(len(cat), 170)
        self.assertEqual({m["role"] for m in cat}, {"FREE", "PRO", "MAX"})
        self.assertEqual(len({m["id"] for m in cat}), 170)

    def test_gating(self):
        self.assertTrue(tiers.can_use_model(self.cfg, "gpt-5-mini")[0])
        ok, _, msg = tiers.can_use_model(self.cfg, "gpt-6-sol")
        self.assertFalse(ok)
        self.assertIn("MAX", msg)
        self.cfg["tier"] = "pro"
        self.assertFalse(tiers.can_use_model(self.cfg, "gpt-6-sol")[0])
        self.cfg["tier"] = "max"
        self.assertTrue(tiers.can_use_model(self.cfg, "gpt-6-sol")[0])

    def test_trial_models_for_free(self):
        for _ in range(3):
            ok, via, _ = tiers.precheck(self.cfg, "claude-haiku-4.5")
            self.assertTrue(ok and via)
            tiers.record(self.cfg, "claude-haiku-4.5", 100, via)
        self.assertFalse(tiers.can_use_model(self.cfg, "claude-haiku-4.5")[0])
        ok, via, _ = tiers.precheck(self.cfg, "deepseek-v4-flash-0731")
        self.assertTrue(ok and via)
        tiers.record(self.cfg, "deepseek-v4-flash-0731", 100, via)
        self.assertFalse(tiers.can_use_model(self.cfg, "deepseek-v4-flash-0731")[0])

    def test_dinar_cost_and_daily_limit(self):
        self.assertEqual(tiers.record(self.cfg, "gpt-5-mini", 100, False), 65)
        self.assertEqual(tiers.record(self.cfg, "gpt-5-mini", 20000, False), 65 * 3)     # 20000/8000 -> 3 unit
        self.assertEqual(tiers.status(self.cfg)["dinar"], 65 + 195)
        for _ in range(20):
            tiers.record(self.cfg, "gpt-5-mini", 10, False)
        ok, _, msg = tiers.precheck(self.cfg, "gpt-5-mini")
        self.assertFalse(ok)
        self.assertIn("Limit harian habis", msg)

    def test_paid_tiers_are_not_charged(self):
        self.cfg["tier"] = "pro"
        tiers.record(self.cfg, "gpt-5-mini", 100000, False)
        self.assertEqual(tiers.status(self.cfg)["dinar"], 0)
        self.assertTrue(tiers.precheck(self.cfg, "gpt-5-mini")[0])



class TrialMode(unittest.TestCase):
    """Masa uji coba: semua model gratis."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = mock.patch.object(tiers, "USAGE_FILE", os.path.join(self.tmp, "usage.json"))
        self.p.start()
        self.cfg = {"tier": "free", "timezone": "Asia/Jakarta", "dinar_token_unit": 8000, "trial_mode": True}

    def tearDown(self):
        self.p.stop()

    def test_every_model_is_usable_on_the_free_tier(self):
        for m in tiers.catalog():
            ok, via_trial, msg = tiers.can_use_model(self.cfg, m["id"])
            self.assertTrue(ok and not via_trial and msg == "", m["id"])
        self.assertTrue(tiers.can_use_model(self.cfg, "model-yang-tidak-ada-di-katalog")[0])

    def test_nothing_is_charged_and_there_is_no_daily_limit(self):
        for _ in range(100):
            ok, via, _ = tiers.precheck(self.cfg, "gpt-6-sol")                  # model MAX
            self.assertTrue(ok and not via)
            self.assertEqual(tiers.record(self.cfg, "gpt-6-sol", 50000, via), 0)
        st = tiers.status(self.cfg)
        self.assertEqual((st["dinar"], st["requests"], st["trial"]), (0, 100, True))
        self.assertEqual(st["trials"], {})

    def test_labels_and_switching_back_to_paid_rules(self):
        self.assertIn("gratis", tiers.plan_label(self.cfg))
        self.assertTrue(tiers.trial_mode({}))                                  # bawaan: aktif
        self.cfg["trial_mode"] = False
        self.assertEqual(tiers.plan_label(self.cfg), "FREE")
        self.assertFalse(tiers.can_use_model(self.cfg, "gpt-6-sol")[0])
        self.assertEqual(tiers.record(self.cfg, "gpt-5-mini", 100, False), 65)


if __name__ == "__main__":
    unittest.main()
