import os
import tempfile
import unittest
from unittest import mock

from cx import memory


class Memory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.patch = mock.patch.object(memory, "MEM_FILE", os.path.join(self.tmp, "m.json"))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_add_dedupes_case_insensitively(self):
        a = memory.add("Suka kopi", "global")
        b = memory.add("suka KOPI", "global")
        self.assertEqual(a, b)
        self.assertEqual(len(memory.load()), 1)

    def test_scopes_and_search(self):
        memory.add("fakta global", "global")
        memory.add("fakta proyek", "project", "/p1")
        self.assertEqual({i["text"] for i in memory.relevant("/p1")}, {"fakta global", "fakta proyek"})
        self.assertEqual({i["text"] for i in memory.relevant("/p2")}, {"fakta global"})
        self.assertEqual([i["text"] for i in memory.relevant("/p1", "proyek")], ["fakta proyek"])

    def test_remove_and_clear(self):
        i = memory.add("x")
        self.assertEqual(memory.remove(i), 1)
        memory.add("y")
        memory.clear()
        self.assertEqual(memory.load(), [])

    def test_prompt_block(self):
        self.assertEqual(memory.prompt_block("/p"), "")
        memory.add("aturan A")
        self.assertIn("aturan A", memory.prompt_block("/p"))

    def test_auto_capture_remember_and_name(self):
        self.assertEqual(memory.auto_capture("ingat bahwa saya suka kopi hitam"), ["saya suka kopi hitam"])
        self.assertEqual(memory.auto_capture("Halo, nama saya Budi Santoso dan saya dev"), ["Nama user: Budi Santoso"])
        self.assertEqual(memory.auto_capture("nama saya budi ya"), ["Nama user: budi"])
        self.assertEqual(memory.auto_capture("tolong simpan: server di 10.0.0.5"), ["server di 10.0.0.5"])
        self.assertEqual(memory.auto_capture("Remember that I prefer tabs"), ["I prefer tabs"])

    def test_auto_capture_ignores_duplicates_noise_and_skill_bodies(self):
        memory.auto_capture("ingat bahwa x adalah y")
        self.assertEqual(memory.auto_capture("ingat bahwa x adalah y"), [])
        self.assertEqual(memory.auto_capture("cuaca hari ini cerah"), [])
        self.assertEqual(memory.auto_capture("[SKILL AKTIF: a]\nnama saya Budi"), [])


if __name__ == "__main__":
    unittest.main()
