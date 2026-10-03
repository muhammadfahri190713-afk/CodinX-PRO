"""Adaptor 'kawat': riwayat kanonik (gaya OpenAI) -> format yang bisa diterima proxy mana pun.

  native  : pesan role system/user/assistant/tool + tools=[...]  (OpenAI penuh)
  text    : tool dipanggil lewat blok <tool_call>{json}</tool_call> di teks biasa
  flat    : seluruh riwayat dijadikan SATU pesan user (untuk gateway yang hanya membaca pesan terakhir)
"""
import json
import re
import uuid

CALL_OPEN, CALL_CLOSE = "<tool_call>", "</tool_call>"
_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
_OPEN_TAIL = re.compile(r"<tool_call>\s*(\{.*)$", re.S)
_FENCE = re.compile(r"```(?:json|tool_call|tool)?\s*(\{.*?\})\s*```", re.S)


def new_call_id():
    return "call_" + uuid.uuid4().hex[:24]


def loads(s):
    """JSON longgar: toleran newline mentah di string dan sampah setelah objek."""
    s = (s or "").strip()
    try:
        return json.loads(s, strict=False)
    except ValueError:
        pass
    i = s.find("{")
    if i >= 0:
        try:
            return json.JSONDecoder(strict=False).raw_decode(s[i:])[0]
        except ValueError:
            return None
    return None


def fix_args(s):
    """Pastikan argumen tool berupa string JSON valid (kalau bisa diperbaiki)."""
    if isinstance(s, (dict, list)):
        return json.dumps(s, ensure_ascii=False)
    obj = loads(s)
    return json.dumps(obj, ensure_ascii=False) if isinstance(obj, dict) else (s or "{}")


# ------------------------------------------------------------------ protokol teks
def _type(v):
    t = v.get("type", "any")
    return t if isinstance(t, str) else "any"


def protocol_prompt(schemas):
    cat = []
    for s in schemas:
        f = s["function"]
        params = f["parameters"].get("properties", {})
        req = set(f["parameters"].get("required", []))
        sig = ", ".join(f"{k}{'*' if k in req else ''}:{_type(v)}" for k, v in params.items())
        cat.append(f"- {f['name']}({sig}) — {f['description']}")
    return (
        "## Protokol pemanggilan tool (mode teks)\n"
        "Kamu BISA memakai tool. Untuk memanggil tool, tulis blok PERSIS seperti ini (JSON valid):\n"
        "<tool_call>\n"
        '{"name": "NAMA_TOOL", "arguments": {"param": "nilai"}}\n'
        "</tool_call>\n"
        "Aturan:\n"
        "- Boleh beberapa blok <tool_call> dalam satu balasan. Setelah blok terakhir, BERHENTI dan tunggu hasilnya.\n"
        '- Hasil datang di pesan berikutnya: <tool_result name="..." id="...">...</tool_result>. Jangan menulis hasil sendiri.\n'
        "- Jangan membungkus blok dengan ``` dan jangan menjelaskan format ini ke user.\n"
        "- Jika tidak perlu tool, jawab biasa tanpa blok.\n"
        "Tool tersedia (parameter bertanda * wajib):\n" + "\n".join(cat)
    )


def _norm(obj, valid):
    if not isinstance(obj, dict):
        return None
    fn = obj.get("function") if isinstance(obj.get("function"), dict) else None
    src = fn or obj
    name = src.get("name") or obj.get("tool") or obj.get("tool_name")
    args = src.get("arguments", obj.get("args", obj.get("parameters", obj.get("input", {}))))
    if isinstance(args, str):
        args = loads(args) or {}
    if name in valid and isinstance(args, dict):
        return {"name": name, "arguments": args}
    return None


def parse_text_calls(content, valid):
    """-> (teks_bersih, [ {name, arguments} ])"""
    valid, text, calls = set(valid), content or "", []
    for m in _BLOCK.finditer(text):
        c = _norm(loads(m.group(1)), valid)
        if c:
            calls.append(c)
    clean = _BLOCK.sub("", text)
    if not calls:                                   # blok terbuka tanpa penutup (output terpotong)
        m = _OPEN_TAIL.search(text)
        if m:
            c = _norm(loads(m.group(1)), valid)
            if c:
                calls.append(c)
                clean = text[:m.start()]
    if not calls:                                   # blok ```json {..} ```
        for m in _FENCE.finditer(text):
            c = _norm(loads(m.group(1)), valid)
            if c:
                calls.append(c)
        if calls:
            clean = _FENCE.sub("", text)
    if not calls and text.strip().startswith("{"):  # balasan = satu objek JSON
        c = _norm(loads(text), valid)
        if c:
            calls.append(c)
            clean = ""
    return clean.strip(), calls


class CallFilter:
    """Sembunyikan blok <tool_call>…</tool_call> dari tampilan stream (tangani tag yang terpotong)."""

    def __init__(self, emit):
        self.emit, self.buf, self.hidden = emit, "", False

    def feed(self, s):
        self.buf += s
        out = []
        while True:
            if self.hidden:
                i = self.buf.find(CALL_CLOSE)
                if i < 0:
                    self.buf = self.buf[-len(CALL_CLOSE):]
                    break
                self.buf, self.hidden = self.buf[i + len(CALL_CLOSE):], False
                continue
            i = self.buf.find(CALL_OPEN)
            if i >= 0:
                out.append(self.buf[:i])
                self.buf, self.hidden = self.buf[i + len(CALL_OPEN):], True
                continue
            keep = 0
            for k in range(min(len(CALL_OPEN) - 1, len(self.buf)), 0, -1):
                if CALL_OPEN.startswith(self.buf[-k:]):
                    keep = k
                    break
            out.append(self.buf[:len(self.buf) - keep])
            self.buf = self.buf[len(self.buf) - keep:]
            break
        t = "".join(out)
        if t:
            self.emit(t)

    def flush(self):
        if not self.hidden and self.buf:
            self.emit(self.buf)
        self.buf = ""


# ------------------------------------------------------------------ konversi riwayat
def calls_to_text(tool_calls):
    out = []
    for tc in tool_calls or []:
        fn = tc["function"]
        args = loads(fn.get("arguments") or "{}")
        args = args if isinstance(args, dict) else {}
        out.append(CALL_OPEN + "\n" + json.dumps({"name": fn["name"], "arguments": args}, ensure_ascii=False) + "\n" + CALL_CLOSE)
    return "\n".join(out)


def _merge_same_role(msgs):
    out = []
    for m in msgs:
        if out and out[-1]["role"] == m["role"] and m["role"] in ("user", "assistant"):
            out[-1] = {"role": m["role"], "content": out[-1]["content"] + "\n\n" + m["content"]}
        else:
            out.append(m)
    return out


def to_text_history(messages):
    """Ubah assistant.tool_calls + role=tool menjadi teks biasa (user/assistant saja)."""
    out, names, pending = [], {}, []

    def flush():
        if pending:
            out.append({"role": "user", "content": "\n".join(pending)})
            pending.clear()
    for m in messages:
        r = m["role"]
        if r == "tool":
            nm = names.get(m.get("tool_call_id"), "tool")
            pending.append(f'<tool_result name="{nm}" id="{m.get("tool_call_id", "")}">\n{m.get("content", "")}\n</tool_result>')
            continue
        flush()
        if r == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                names[tc["id"]] = tc["function"]["name"]
            body = (m.get("content") or "").strip()
            out.append({"role": "assistant", "content": (body + "\n" if body else "") + calls_to_text(m["tool_calls"])})
        else:
            out.append({"role": r, "content": str(m.get("content") or "")})
    flush()
    return _merge_same_role(out)


def _clean_native(messages):
    out = []
    for m in messages:
        n = {"role": m["role"], "content": str(m.get("content") or "")}
        if m.get("tool_calls"):
            n["tool_calls"] = m["tool_calls"]
        if m.get("tool_call_id"):
            n["tool_call_id"] = m["tool_call_id"]
        out.append(n)
    return out


def _shrink(txt, limit):
    if len(txt) <= limit:
        return txt
    h = limit // 2
    return txt[:h] + f"\n… [{len(txt) - limit} karakter dipotong] …\n" + txt[-h:]


def flatten(system, messages, max_chars=60000):
    entries = []
    n = len(messages)
    for i, m in enumerate(messages):
        who = "USER" if m["role"] == "user" else "ASSISTANT"
        entries.append(f"{who}: " + _shrink(str(m["content"]), 6000 if i >= n - 2 else 1500))
    head = "[INSTRUKSI SISTEM — patuhi sepenuhnya]\n" + system + "\n\n[RIWAYAT PERCAKAPAN]\n"
    tail = ("\n\n[GILIRAN SEKARANG]\nBalas sebagai ASSISTANT untuk pesan USER terakhir di atas. "
            "Jangan menulis awalan 'ASSISTANT:' dan jangan mengulang riwayat.")
    budget, kept, used = max(max_chars - len(head) - len(tail), 2000), [], 0
    for e in reversed(entries):
        if used + len(e) + 2 > budget and kept:
            break
        kept.append(e)
        used += len(e) + 2
    kept.reverse()
    omitted = len(entries) - len(kept)
    body = (f"(… {omitted} pesan lama dipotong …)\n\n" if omitted else "") + "\n\n".join(kept)
    return head + body + tail


def to_wire(system, messages, history="native", tool_mode="native", schemas=None, max_chars=60000):
    sys_txt = system + ("\n\n" + protocol_prompt(schemas) if tool_mode == "text" and schemas else "")
    textual = tool_mode in ("text", "none") or history == "flat"
    msgs = to_text_history(messages) if textual else _clean_native(messages)
    if history == "flat":
        return [{"role": "user", "content": flatten(sys_txt, msgs, max_chars)}]
    return ([{"role": "system", "content": sys_txt}] if sys_txt else []) + msgs
