"""Diagnosa proxy/model: (1) apakah riwayat percakapan diteruskan, (2) apakah tool bisa dipanggil (native / teks).
Hasilnya disimpan per model (caps.json) dan dipakai otomatis oleh agent. Probe tidak memotong Dinar."""
from . import api, caps, wire

SYS = "Kamu asisten yang patuh. Jawab sangat singkat."
ECHO = {"type": "function", "function": {
    "name": "echo", "description": "Mengembalikan teks yang diberikan.",
    "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}}
T = 60  # detik per probe


def _chat(cfg, key, msgs, tools=None):
    return api.chat(cfg, key, msgs, tools, timeout=T)[0]


def _hard(e):
    """Galat jaringan/otentikasi (bukan penolakan format) -> hentikan diagnosa."""
    return e.status is None or e.status in (401, 403, 404, 429)


def test_history(cfg, key, notes):
    h = [{"role": "user", "content": "Kode rahasia saya adalah 4821. Balas hanya dengan kata: OK"},
         {"role": "assistant", "content": "OK"},
         {"role": "user", "content": "Sebutkan kode rahasia saya tadi. Jawab hanya dengan angkanya."}]
    for mode in ("native", "flat"):
        try:
            r = _chat(cfg, key, wire.to_wire(SYS, h, mode, "none" if mode == "flat" else "native"))
            if "4821" in (r.get("content") or ""):
                return mode
            notes.append(f"riwayat {mode}: model tidak mengingat kode")
        except api.ApiError as e:
            if _hard(e):
                raise
            notes.append(f"riwayat {mode}: HTTP {e.status}")
    return None


def test_tools(cfg, key, history, notes):
    u = {"role": "user", "content": "Panggil tool echo dengan text='halo'. Jangan menjawab dengan teks biasa."}
    tc = None
    try:                                             # 1) native
        for _ in range(2):
            r = _chat(cfg, key, wire.to_wire(SYS, [u], "native", "native"), [ECHO])
            if r.get("tool_calls") and r["tool_calls"][0]["function"]["name"] == "echo":
                tc = r["tool_calls"][0]
                break
        if tc is None:
            notes.append("tool native: model tidak memanggil tool")
        elif history != "flat":                      # round-trip: server harus menerima role=tool
            msgs = [u, {"role": "assistant", "content": "", "tool_calls": [tc]},
                    {"role": "tool", "tool_call_id": tc["id"], "content": "halo"}]
            r2 = _chat(cfg, key, wire.to_wire(SYS, msgs, history, "native"), [ECHO])
            if not (r2.get("content") or r2.get("tool_calls")):
                tc = None
                notes.append("tool native: balasan kosong setelah hasil tool")
    except api.ApiError as e:
        if _hard(e):
            raise
        tc = None
        notes.append(f"tool native: HTTP {e.status} {(e.body or '')[:80]}")
    if tc is not None:
        return "native"
    try:                                             # 2) protokol teks
        r = _chat(cfg, key, wire.to_wire(SYS, [u], history, "text", [ECHO]))
        _, calls = wire.parse_text_calls(r.get("content") or "", ["echo"])
        if calls:
            return "text"
        notes.append("tool teks: model tidak menulis <tool_call>")
    except api.ApiError as e:
        if _hard(e):
            raise
        notes.append(f"tool teks: HTTP {e.status}")
    return "none"


def run(app):
    """-> {'model','history','tools','notes'}. Menyimpan hasil ke caps.json."""
    cfg, key, model = app.cfg, app.key, app.cfg["model"]
    notes = []
    hist = test_history(cfg, key, notes)
    tools = test_tools(cfg, key, hist or "native", notes)
    caps.set(model, history=hist or "native", history_ok=bool(hist), tools=tools)
    return {"model": model, "history": hist, "tools": tools, "notes": notes}


def summary(res):
    h = {"native": "native ✓", "flat": "flat ⚠ (proxy tidak meneruskan riwayat)", None: "tidak pasti"}[res["history"]]
    t = {"native": "native ✓", "text": "teks ⚠ (tanpa function-calling)", "none": "tidak ada ✗"}[res["tools"]]
    return f"riwayat: {h} · tool: {t}"
