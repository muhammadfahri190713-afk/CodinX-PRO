import json
import unittest

from cx import wire

VALID = ["bash", "write", "read", "grep", "list"]


class ParseTextCalls(unittest.TestCase):
    def test_block(self):
        clean, calls = wire.parse_text_calls('Oke.\n<tool_call>\n{"name":"bash","arguments":{"command":"ls"}}\n</tool_call>', VALID)
        self.assertEqual(clean, "Oke.")
        self.assertEqual(calls, [{"name": "bash", "arguments": {"command": "ls"}}])

    def test_newline_in_string_is_tolerated(self):
        _, calls = wire.parse_text_calls('<tool_call>{"name":"write","arguments":{"path":"a","content":"x\ny"}}</tool_call>', VALID)
        self.assertEqual(calls[0]["arguments"]["content"], "x\ny")

    def test_unclosed_block(self):
        clean, calls = wire.parse_text_calls('mulai <tool_call>{"name":"read","arguments":{"path":"a"}}', VALID)
        self.assertEqual([c["name"] for c in calls], ["read"])
        self.assertEqual(clean, "mulai")

    def test_fenced_json_and_bare_json(self):
        self.assertEqual(wire.parse_text_calls('```json\n{"name":"grep","arguments":{"pattern":"x"}}\n```', VALID)[1][0]["name"], "grep")
        self.assertEqual(wire.parse_text_calls('{"name":"list","arguments":{}}', VALID)[1][0]["name"], "list")

    def test_alternative_keys(self):
        _, calls = wire.parse_text_calls('<tool_call>{"tool":"read","args":{"path":"z"}}</tool_call>', VALID)
        self.assertEqual(calls[0], {"name": "read", "arguments": {"path": "z"}})

    def test_unknown_tool_and_prose_are_not_calls(self):
        self.assertEqual(wire.parse_text_calls('<tool_call>{"name":"hack","arguments":{}}</tool_call>', VALID)[1], [])
        self.assertEqual(wire.parse_text_calls("Tidak perlu tool.", VALID), ("Tidak perlu tool.", []))

    def test_multiple_calls(self):
        t = '<tool_call>{"name":"read","arguments":{"path":"a"}}</tool_call>\n<tool_call>{"name":"read","arguments":{"path":"b"}}</tool_call>'
        self.assertEqual(len(wire.parse_text_calls(t, VALID)[1]), 2)


class CallFilter(unittest.TestCase):
    def feed(self, chunks):
        out = []
        f = wire.CallFilter(out.append)
        for c in chunks:
            f.feed(c)
        f.flush()
        return "".join(out)

    def test_hides_block_split_across_chunks(self):
        self.assertEqual(self.feed(["Halo <tool", '_call>{"na', 'me":"bash"}</tool_', "call> selesai"]), "Halo  selesai")

    def test_keeps_text_that_only_looks_like_a_tag(self):
        self.assertEqual(self.feed(["pakai <to", "x> saja"]), "pakai <tox> saja")

    def test_plain_text_passthrough(self):
        self.assertEqual(self.feed(["a", "b", "c"]), "abc")


class History(unittest.TestCase):
    canon = [{"role": "user", "content": "buat file"},
             {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "write", "arguments": '{"path":"a"}'}}]},
             {"role": "tool", "tool_call_id": "c1", "content": "ok"},
             {"role": "assistant", "content": "Selesai"},
             {"role": "user", "content": "siapa saya?"}]

    def test_text_history_has_no_tool_roles(self):
        h = wire.to_text_history(self.canon)
        self.assertEqual([m["role"] for m in h], ["user", "assistant", "user", "assistant", "user"])
        self.assertIn("<tool_call>", h[1]["content"])
        self.assertIn('<tool_result name="write"', h[2]["content"])

    def test_consecutive_same_role_are_merged(self):
        h = wire.to_text_history([{"role": "user", "content": "a"}, {"role": "user", "content": "b"}])
        self.assertEqual(h, [{"role": "user", "content": "a\n\nb"}])

    def test_flat_is_single_user_message_with_everything(self):
        w = wire.to_wire("SISTEM", self.canon, "flat", "text", None)
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["role"], "user")
        for needle in ("SISTEM", "buat file", "siapa saya?", "[GILIRAN SEKARANG]"):
            self.assertIn(needle, w[0]["content"])

    def test_flat_trims_oldest_first(self):
        msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"pesan-{i} " + "x" * 500} for i in range(61)]
        txt = wire.to_wire("S", msgs, "flat", "none", None, max_chars=8000)[0]["content"]
        self.assertTrue("pesan-60" in txt, "giliran terbaru harus tetap ada")
        self.assertFalse("pesan-0 " in txt, "giliran tertua harus dipotong lebih dulu")
        self.assertTrue("pesan lama dipotong" in txt)
        self.assertLess(len(txt), 12000)

    def test_native_keeps_roles_and_adds_system(self):
        w = wire.to_wire("SISTEM", self.canon, "native", "native")
        self.assertEqual(w[0], {"role": "system", "content": "SISTEM"})
        self.assertEqual([m["role"] for m in w[1:]], ["user", "assistant", "tool", "assistant", "user"])

    def test_text_mode_appends_protocol_for_schemas(self):
        schemas = [{"type": "function", "function": {"name": "echo", "description": "d", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}}]
        w = wire.to_wire("S", self.canon[:1], "native", "text", schemas)
        self.assertIn("Protokol pemanggilan tool", w[0]["content"])
        self.assertIn("echo(text*:string)", w[0]["content"])


class Misc(unittest.TestCase):
    def test_fix_args(self):
        self.assertEqual(json.loads(wire.fix_args({"a": 1})), {"a": 1})
        self.assertEqual(json.loads(wire.fix_args('{"a":"x\ny"}')), {"a": "x\ny"})
        self.assertEqual(wire.fix_args(""), "{}")

    def test_call_ids_unique(self):
        self.assertEqual(len({wire.new_call_id() for _ in range(100)}), 100)


if __name__ == "__main__":
    unittest.main()
