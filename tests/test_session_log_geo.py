import json
import os
import re
import stat
import tempfile
import unittest
import urllib.error
from unittest import mock

from cx import config, geo, log
from cx.session import Session
from .helpers import read


class SessionStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        p = mock.patch.object(config, "SESSIONS", self.dir)
        p.start()
        self.addCleanup(p.stop)

    def test_roundtrip_title_and_permissions(self):
        s = Session("/proj")
        s.messages = [{"role": "user", "content": "Halo dunia\nbaris kedua"}, {"role": "assistant", "content": "hai"}]
        s.todos, s.remote_id, s.remote_conv, s.tokens_total = [{"content": "x", "status": "pending"}], "chatcmpl-1", "conv-9", 42
        s.save()
        self.assertEqual(stat.S_IMODE(os.stat(s.path).st_mode), 0o600)
        t = Session.load(s.id)
        self.assertEqual((t.title, t.messages, t.todos, t.remote_id, t.remote_conv, t.tokens_total, t.cwd),
                         ("Halo dunia", s.messages, s.todos, "chatcmpl-1", "conv-9", 42, "/proj"))

    def test_empty_session_is_not_saved(self):
        s = Session("/p")
        s.save()
        self.assertEqual(os.listdir(self.dir), [])

    def test_list_and_latest_for_cwd(self):
        made = {}
        for cwd, created in (("/a", 100), ("/b", 200), ("/a", 300)):
            s = Session(cwd)
            s.created = created
            s.id = f"id-{cwd[1:]}-{created}"
            s.messages = [{"role": "user", "content": f"pesan {created}"}]
            s.save()
            made[created] = s.id
        self.assertEqual([i["created"] for i in Session.list_all()], [300, 200, 100])
        self.assertEqual(Session.latest_for("/a").id, made[300])
        self.assertEqual(Session.latest_for("/b").id, made[200])
        self.assertIsNone(Session.latest_for("/zzz"))

    def test_undo_redo_restores_files_and_messages(self):
        d = tempfile.mkdtemp()
        old, new = os.path.join(d, "ada.txt"), os.path.join(d, "baru.txt")
        with open(old, "w") as f:
            f.write("asli")
        s = Session(d)
        s.messages = [{"role": "user", "content": "sebelum"}, {"role": "assistant", "content": "ok"}]
        turn = s.begin_turn("ubah file")
        s.messages.append({"role": "user", "content": "ubah file"})
        turn["backups"][old] = b"asli"
        turn["backups"][new] = None
        with open(old, "w") as f:
            f.write("DIUBAH")
        with open(new, "w") as f:
            f.write("file baru")
        s.messages.append({"role": "assistant", "content": "selesai"})

        t = s.undo()
        self.assertEqual(t["user"], "ubah file")
        self.assertEqual(read(old), "asli")
        self.assertFalse(os.path.exists(new))
        self.assertEqual(len(s.messages), 2)
        self.assertIsNone(s.undo())                      # tidak ada giliran lagi

        self.assertIsNotNone(s.redo())
        self.assertEqual(read(old), "DIUBAH")
        self.assertEqual(read(new), "file baru")
        self.assertEqual([m["content"] for m in s.messages][-2:], ["ubah file", "selesai"])
        self.assertIsNone(s.redo())

    def test_drop_turn_and_export(self):
        s = Session("/p")
        s.messages = [{"role": "user", "content": "a"}]
        s.begin_turn("b")
        s.messages.append({"role": "user", "content": "b"})
        s.drop_turn()
        self.assertEqual(len(s.messages), 1)
        s.messages += [{"role": "assistant", "content": "jawaban", "tool_calls": [{"id": "1", "function": {"name": "bash", "arguments": "{}"}}]},
                       {"role": "tool", "tool_call_id": "1", "content": "keluaran"}]
        md = s.export_md()
        for needle in ("User", "jawaban", "`bash`", "keluaran"):
            self.assertIn(needle, md)


class Logging(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        p = mock.patch.object(log, "LOG_DIR", self.dir)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(log.set_enabled, False)

    def test_disabled_by_default_writes_nothing(self):
        log.set_enabled(False)
        log.debug("x", a=1)
        self.assertEqual(os.listdir(self.dir), [])

    def test_enabled_writes_json_lines_and_redacts(self):
        log.set_enabled(True)
        secret = "sk-" + "a1b2c3d4" * 5
        log.debug("http_request", auth="Bearer " + "z9y8x7w6v5u4t3s2", key=secret, note="api_key=" + "q" * 20, event="bentrok-kw-aman")
        lines = log.tail(5)
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertEqual((rec["ev"], rec["event"]), ("http_request", "bentrok-kw-aman"))
        self.assertNotIn(secret, lines[0])
        self.assertNotIn("z9y8x7w6v5u4t3s2", lines[0])
        self.assertIn("[REDACTED]", lines[0])
        fn = os.path.join(self.dir, os.listdir(self.dir)[0])
        self.assertEqual(stat.S_IMODE(os.stat(fn).st_mode), 0o600)

    def test_tail_limits_lines(self):
        log.set_enabled(True)
        for i in range(10):
            log.debug("e", i=i)
        self.assertEqual(len(log.tail(3)), 3)
        self.assertEqual(json.loads(log.tail(1)[0])["i"], 9)


class Geo(unittest.TestCase):
    cfg = {"timezone": "Asia/Jakarta"}

    def test_next_reset_is_next_local_midnight(self):
        now, nxt = geo.now(self.cfg), geo.next_reset(self.cfg)
        self.assertEqual((nxt.hour, nxt.minute, nxt.second), (0, 0, 0))
        self.assertGreater(nxt, now)
        self.assertLessEqual((nxt - now).total_seconds(), 86400)
        self.assertEqual(geo.tz_name(self.cfg), "Asia/Jakarta")

    def test_day_key_and_remaining_format(self):
        self.assertRegex(geo.day_key(self.cfg), r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(geo.remaining_str(self.cfg), r"^\d+j \d+m$")

    def test_different_timezones_give_different_reset_instants(self):
        a = geo.next_reset({"timezone": "Asia/Jakarta"})
        b = geo.next_reset({"timezone": "Asia/Jayapura"})
        self.assertNotEqual(a.utcoffset(), b.utcoffset())            # WIB vs WIT

    def test_invalid_timezone_does_not_crash(self):
        self.assertIsNotNone(geo.now({"timezone": "Mars/Olympus"}))

    def test_lookup_falls_back_to_system_when_offline_and_caches(self):
        d = tempfile.mkdtemp()
        with mock.patch.object(geo, "GEO_FILE", os.path.join(d, "geo.json")), \
                mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            info = geo.lookup(force=True)
            self.assertEqual(info["source"], "system")
            self.assertTrue(info["tz"])
            self.assertTrue(os.path.exists(os.path.join(d, "geo.json")))
            self.assertEqual(geo.lookup()["tz"], info["tz"])         # dari cache, tanpa jaringan

    def test_lookup_parses_ip_service(self):
        d = tempfile.mkdtemp()
        body = json.dumps({"success": True, "region": "Jawa Barat", "city": "Bandung", "country": "Indonesia",
                           "timezone": {"id": "Asia/Jakarta"}}).encode()
        resp = mock.MagicMock()
        resp.__enter__.return_value.read.return_value = body
        with mock.patch.object(geo, "GEO_FILE", os.path.join(d, "geo.json")), mock.patch("urllib.request.urlopen", return_value=resp):
            info = geo.lookup(force=True)
        self.assertEqual((info["province"], info["tz"], info["source"]), ("Jawa Barat", "Asia/Jakarta", "ip"))


if __name__ == "__main__":
    unittest.main()
