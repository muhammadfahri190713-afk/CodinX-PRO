"""Matriks kompatibilitas proxy: tiap 'kepribadian' proxy tiruan harus menghasilkan agent yang INGAT percakapan,
bisa menjalankan tool & skills — apa pun keterbatasan proxy-nya."""
import json
import os
import re
import unittest

from . import mock_proxy
from .helpers import ProxyCase, TempDirs, read, run_cli, run_cli_open_stdin


def caps_of(home, model):
    try:
        return json.loads(read(os.path.join(home, ".codinx", "caps.json"))).get(model, {})
    except OSError:
        return {}


class Matrix(ProxyCase):
    def scenario(self, model, want_tools, want_hist):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        h, w = t["h"], t["w"]
        o = self.cli(h, w, model, ["nama saya Budi"])
        c = caps_of(h, model)
        self.assertEqual((c.get("tools"), c.get("history")), (want_tools, want_hist), "diagnosa otomatis: " + str(c))
        self.assertIn("Halo Budi", o)
        mem = json.loads(read(os.path.join(h, ".codinx", "memory.json")))
        self.assertTrue(any("Budi" in m["text"] for m in mem), "memori jangka panjang menangkap nama")
        self.assertIn("Nama kamu Budi", self.cli(h, w, model, ["-c", "siapa nama saya?"]), "INGAT percakapan sebelumnya")
        if want_tools != "none":
            self.cli(h, w, model, ["-c", "--auto", "buat hello"])
            self.assertTrue(os.path.exists(os.path.join(w, "hello.py")), "tool write harus jalan")
            self.assertIn("Skill: table-maker", self.cli(h, w, model, ["-c", "jalankan skill table-maker"]), "skill via tool")
        for args, label in ((["$web-check cek port 3000"], "$nama"), (["/skill debug-fix error x"], "/skill"), (["/web-check"], "/<nama>")):
            self.assertIn("SKILL-OK", self.cli(h, w, model, ["-c"] + args), f"skill via {label}")
        self.assertIn("Nama kamu Budi", self.cli(h, w, model, ["-c", "siapa nama saya?"]), "masih ingat setelah banyak giliran + tool + skill")

    def test_m_full(self):
        self.scenario("m-full", "native", "native")

    def test_m_notools(self):
        self.scenario("m-notools", "text", "native")

    def test_m_lastonly(self):
        self.scenario("m-lastonly", "native", "flat")

    def test_m_notoolrole(self):
        self.scenario("m-notoolrole", "text", "native")

    def test_m_dumb_gateway(self):
        self.scenario("m-dumb", "text", "flat")

    def test_m_chatonly(self):
        self.scenario("m-chatonly", "none", "native")


class WithoutDiagnosis(ProxyCase):
    """Perilaku lama (tanpa diagnosa) membuktikan bug asli; mode otomatis memperbaikinya."""
    OLD = {"CODINX_AUTO_PROBE": "0", "CODINX_HISTORY_MODE": "native", "CODINX_TOOL_MODE": "native"}

    def dirs(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        return t["h"], t["w"]

    def test_stateless_gateway_forgets_when_history_is_native(self):
        h, w = self.dirs()
        self.cli(h, w, "m-lastonly", ["nama saya Budi"], self.OLD)
        self.assertIn("tidak tahu", self.cli(h, w, "m-lastonly", ["-c", "siapa nama saya?"], self.OLD))

    def test_no_tool_proxy_errors_when_tools_are_forced_native(self):
        h, w = self.dirs()
        out = self.cli(h, w, "m-notools", ["--auto", "buat hello"], self.OLD)
        self.assertIn("HTTP 400", out)
        self.assertFalse(os.path.exists(os.path.join(w, "hello.py")))

    def test_runtime_fallback_to_text_tools_on_400(self):
        h, w = self.dirs()
        self.cli(h, w, "m-notools", ["--auto", "buat hello"], {"CODINX_AUTO_PROBE": "0"})
        self.assertTrue(os.path.exists(os.path.join(w, "hello.py")))
        self.assertEqual(caps_of(h, "m-notools").get("tools"), "text")

    def test_early_warning_when_proxy_reports_dropped_history(self):
        h, w = self.dirs()
        ex = {"CODINX_AUTO_PROBE": "0", "CODINX_HISTORY_MODE": "native"}
        self.cli(h, w, "m-lastonly", ["nama saya Budi"], ex)
        self.cli(h, w, "m-lastonly", ["-c", "halo"], ex)
        self.assertIn("TIDAK dibaca", self.cli(h, w, "m-lastonly", ["-c", "halo lagi"], ex))

    def test_forced_flat_mode_fixes_stateless_gateway_without_probe(self):
        h, w = self.dirs()
        ex = {"CODINX_AUTO_PROBE": "0", "CODINX_HISTORY_MODE": "flat"}
        self.cli(h, w, "m-lastonly", ["nama saya Budi"], ex)
        self.assertIn("Nama kamu Budi", self.cli(h, w, "m-lastonly", ["-c", "siapa nama saya?"], ex))


class WireBehaviour(ProxyCase):
    def test_conversation_id_is_stable_within_a_session(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        mock_proxy.REQUESTS.clear()
        ex = {"CODINX_AUTO_PROBE": "0"}
        self.cli(t["h"], t["w"], "m-full", ["halo"], ex)
        self.cli(t["h"], t["w"], "m-full", ["-c", "halo lagi"], ex)
        ids = {r["conv_header"] for r in mock_proxy.REQUESTS}
        self.assertEqual(len(ids), 1)
        self.assertTrue(re.match(r"\d{8}-\d{6}-\w{4}", ids.pop()))
        self.assertTrue(all(r["conv_header"] == r["user"] for r in mock_proxy.REQUESTS))

    def test_flat_mode_sends_one_message_per_request(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        self.cli(t["h"], t["w"], "m-lastonly", ["nama saya Budi"])        # probe -> flat
        mock_proxy.REQUESTS.clear()
        self.cli(t["h"], t["w"], "m-lastonly", ["-c", "siapa nama saya?"])
        self.assertTrue(mock_proxy.REQUESTS)
        self.assertTrue(all(r["n"] == 1 and r["roles"] == ["user"] for r in mock_proxy.REQUESTS))

    def test_text_mode_never_sends_tool_roles(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        self.cli(t["h"], t["w"], "m-notoolrole", ["nama saya Budi"])
        self.cli(t["h"], t["w"], "m-notoolrole", ["-c", "--auto", "buat hello"])
        mock_proxy.REQUESTS.clear()
        self.cli(t["h"], t["w"], "m-notoolrole", ["-c", "siapa nama saya?"])
        self.assertTrue(all("tool" not in r["roles"] and not r["tools"] for r in mock_proxy.REQUESTS))

    def test_json_output_format(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        out = self.cli(t["h"], t["w"], "m-full", ["--format", "json", "halo"], {"CODINX_AUTO_PROBE": "0"})
        data = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(data["model"], "m-full")
        self.assertIn("CodinX", data["text"])
        self.assertGreater(data["tokens"], 0)

    def test_doctor_command_reports_flat(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        env = {"CODINX_BASE_URL": self.url, "CODINX_API_KEY": "k", "CODINX_MODEL": "m-lastonly"}
        out = run_cli(t["h"], t["w"], ["doctor"], env)
        self.assertIn("Diagnosa CodinX", out)
        self.assertRegex(out, r"mode\s+flat")


class Credentials(ProxyCase):
    def test_helper_really_detects_a_process_that_hangs_on_stdin(self):
        """Uji-meta: tanpa ini, test 'tidak menggantung' bisa lulus palsu."""
        out, finished = run_cli_open_stdin("/tmp", "/tmp", [], code="input()", wait=2)
        self.assertFalse(finished)
        out, finished = run_cli_open_stdin("/tmp", "/tmp", [], code="print('selesai')", wait=10)
        self.assertTrue(finished)
        self.assertIn("selesai", out)

    def test_dotenv_in_codinx_home_is_enough_to_work(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        os.makedirs(os.path.join(t["h"], ".codinx"))
        with open(os.path.join(t["h"], ".codinx", ".env"), "w") as f:
            f.write(f"CODINX_BASE_URL={self.url}\nCODINX_API_KEY=kunci-dari-dotenv\nCODINX_MODEL=m-full\nCODINX_AUTO_PROBE=0\n")
        out = run_cli(t["h"], t["w"], ["run", "--no-color", "halo"])          # tanpa variabel CODINX_* sama sekali
        self.assertIn("CodinX", out)
        self.assertNotIn("Belum terhubung", out)

    def test_missing_credentials_fail_cleanly(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        out, finished = run_cli_open_stdin(t["h"], t["w"], ["run", "--no-color", "halo"], {"CODINX_BASE_URL": self.url})
        self.assertTrue(finished, "CLI menggantung menunggu input padahal stdin bukan terminal (bug cron/CI)")
        self.assertNotIn("Traceback", out)
        self.assertIn("CODINX_API_KEY", out)                       # pesan petunjuk yang jelas

    def test_connect_requires_a_terminal(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        out, finished = run_cli_open_stdin(t["h"], t["w"], ["connect"])
        self.assertTrue(finished)
        self.assertIn("terminal interaktif", out)

    def test_debug_log_never_contains_the_api_key(self):
        t = TempDirs("h", "w")
        self.addCleanup(t.cleanup)
        key = "sk-" + "Zz9" * 14
        env = {"CODINX_BASE_URL": self.url, "CODINX_API_KEY": key, "CODINX_MODEL": "m-full", "CODINX_DEBUG": "1", "CODINX_AUTO_PROBE": "0"}
        run_cli(t["h"], t["w"], ["run", "--no-color", "halo"], env)
        logs = run_cli(t["h"], t["w"], ["logs", "-n", "50"], env)
        self.assertIn("llm_request", logs)
        self.assertIn("http_request", logs)
        self.assertNotIn(key, logs)
        cfg_text = read(os.path.join(t["h"], ".codinx", "config.json")) if os.path.exists(os.path.join(t["h"], ".codinx", "config.json")) else ""
        self.assertNotIn(key, cfg_text)


if __name__ == "__main__":
    unittest.main()
