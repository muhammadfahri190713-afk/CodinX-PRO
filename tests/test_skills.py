import os
import stat
import tempfile
import unittest

from cx import agents, skills
from . import ROOT


class SkillFormat(unittest.TestCase):
    def test_parse_frontmatter(self):
        meta, body = skills.parse("---\nname: x\ndescription: Deskripsi: panjang\n---\nisi\n")
        self.assertEqual(meta["name"], "x")
        self.assertEqual(meta["description"], "Deskripsi: panjang")
        self.assertEqual(body.strip(), "isi")
        self.assertEqual(skills.parse("tanpa frontmatter")[0], {})

    def test_builtin_skills_are_well_formed(self):
        found = skills.discover(ROOT)
        self.assertGreaterEqual(len(found), 40)
        for name, sk in found.items():
            self.assertEqual(os.path.basename(sk["dir"]), name, "nama harus sama dengan nama folder")
            self.assertTrue(len(sk["description"]) >= 20, name)
            body = skills.load(name, ROOT)
            self.assertTrue(len(body) > 80, name)
            self.assertNotIn("{SKILLDIR}", body, "placeholder harus diganti path absolut")

    def test_skill_scripts_exist_and_are_executable(self):
        n = 0
        for sk in skills.discover(ROOT).values():
            d = os.path.join(sk["dir"], "scripts")
            if os.path.isdir(d):
                for f in os.listdir(d):
                    n += 1
                    self.assertTrue(os.stat(os.path.join(d, f)).st_mode & stat.S_IXUSR, f"{sk['name']}/{f} tidak executable")
        self.assertGreaterEqual(n, 7)

    def test_skilldir_placeholder_points_to_real_script(self):
        body = skills.load("log-analysis", ROOT)
        self.assertIn(os.path.join(ROOT, "skills", "log-analysis", "scripts", "top_errors.py"), body)

    def test_agents_are_well_formed(self):
        ag = agents.discover(ROOT)
        self.assertEqual({"explore", "reviewer", "tester", "doc-writer", "security-auditor", "planner"} - set(ag), set())
        for a in ag.values():
            self.assertTrue(a["description"] and a["prompt"] and a["tools"], a["name"])
            self.assertNotIn("task", a["tools"])


class Resolve(unittest.TestCase):
    def test_exact_prefix_ambiguous(self):
        self.assertEqual(skills.resolve("web-check", ROOT)["name"], "web-check")
        self.assertEqual(skills.resolve("WEB-CHECK", ROOT)["name"], "web-check")
        self.assertEqual(skills.resolve("secret", ROOT)["name"], "secret-scan")
        self.assertIsNone(skills.resolve("python", ROOT))          # python-project / python-testing -> ambigu
        self.assertIsNone(skills.resolve("zzz", ROOT))
        self.assertIsNone(skills.resolve("secret", ROOT, exact=True))

    def test_project_and_user_skills_are_discovered(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, ".codinx", "skills", "milik-proyek"))
        with open(os.path.join(d, ".codinx", "skills", "milik-proyek", "SKILL.md"), "w") as f:
            f.write("---\nname: milik-proyek\ndescription: skill khusus proyek ini\n---\nisi\n")
        self.assertIn("milik-proyek", skills.discover(d))


class Match(unittest.TestCase):
    def top(self, text):
        m = skills.match(text, ROOT)
        return m[0][1]["name"] if m else None

    def test_matches_indonesian_requests(self):
        self.assertEqual(self.top("cek web di localhost:3000"), "web-check")
        self.assertEqual(self.top("buat tabel penjualan dan simpan csv"), "table-maker")
        self.assertEqual(self.top("perbaiki error di kode ini"), "debug-fix")
        self.assertEqual(self.top("pindai secret sebelum push"), "secret-scan")

    def test_no_match_for_small_talk(self):
        self.assertEqual(skills.match("halo apa kabar", ROOT), [])


if __name__ == "__main__":
    unittest.main()
