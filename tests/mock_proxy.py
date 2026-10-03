"""Proxy OpenAI-compatible tiruan dengan beberapa 'kepribadian' (menurut nama model) untuk menguji adaptasi CodinX.

 m-full       : OpenAI penuh
 m-notools    : HTTP 400 bila ada `tools`; patuh pada protokol <tool_call> di teks
 m-lastonly   : hanya membaca PESAN TERAKHIR (gateway stateless); tool native OK
 m-notoolrole : menerima `tools` tetapi 400 bila riwayat memuat role=tool / tool_calls
 m-dumb       : lastonly + tanpa tools, tetapi patuh protokol teks
 m-chatonly   : mengabaikan tools & protokol teks (chat murni)
"""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

MODELS = ("m-full", "m-notools", "m-lastonly", "m-notoolrole", "m-dumb", "m-chatonly")
REQUESTS = []


def content_of(m):
    c = m.get("content")
    return c if isinstance(c, str) else json.dumps(c)


def brain(model, body):
    msgs = body["messages"]
    lastonly = model in ("m-lastonly", "m-dumb")
    ctx = msgs[-1:] if lastonly else msgs
    allt = "\n".join(content_of(m) for m in ctx)
    native = bool(body.get("tools")) and model != "m-chatonly"
    proto = "Protokol pemanggilan tool" in allt and model != "m-chatonly"
    last = ctx[-1]
    if last["role"] == "tool":
        return ("text", "Selesai: " + content_of(last)[:200].replace("\n", " "))
    ut = content_of(last)
    if "[RIWAYAT PERCAKAPAN]" in ut:            # transkrip flat -> ambil giliran USER terakhir
        entries = re.split(r"\n\n(?=(?:USER|ASSISTANT): )", ut.split("[RIWAYAT PERCAKAPAN]\n", 1)[1].split("\n\n[GILIRAN SEKARANG]")[0])
        ut = entries[-1][6:] if entries[-1].startswith("USER: ") else entries[-1]
    if ut.lstrip().startswith("<tool_result"):
        return ("text", "Selesai: " + re.sub(r"</?tool_result[^>]*>", "", ut).strip()[:200].replace("\n", " "))
    low = ut.lower()

    def call(name, args):
        if native:
            return ("calls", [(name, args)])
        if proto:
            return ("text", "Baik.\n<tool_call>\n" + json.dumps({"name": name, "arguments": args}) + "\n</tool_call>")
        return ("text", "Maaf, saya tidak bisa memakai tool.")
    if "panggil tool echo" in low:
        return call("echo", {"text": "halo"})
    if "kode rahasia saya adalah" in low:
        return ("text", "OK")
    if "sebutkan kode rahasia" in low:
        m = re.search(r"kode rahasia saya adalah (\d+)", allt, re.I)
        return ("text", m.group(1) if m else "Saya tidak tahu kodenya.")
    m = re.search(r"\[SKILL AKTIF: ([\w-]+)\]", ut)
    if m:
        return ("text", f"SKILL-OK {m.group(1)} " + ("(isi skill diterima)" if "# " in ut else "(kosong)"))
    if "jalankan skill" in low:
        return call("skill", {"name": re.search(r"jalankan skill ([\w-]+)", low).group(1)})
    if "siapa nama saya" in low:
        m = re.search(r"nama saya ([A-Za-z]\w*)", allt)
        return ("text", f"Nama kamu {m.group(1)}." if m else "Maaf, saya tidak tahu nama kamu.")
    if "nama saya" in low:
        return ("text", "Halo " + re.search(r"nama saya (\w+)", low).group(1).capitalize() + "!")
    if "buat hello" in low:
        return call("write", {"path": "hello.py", "content": "print('halo dunia')\n"})
    if "[skill otomatis" in allt.lower():
        return ("text", "SKILL-AUTO-OK")
    return ("text", f"Halo! (model={model}) **CodinX** siap.")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.endswith("/models"):
            return self._json({"data": [{"id": m} for m in MODELS]})
        if self.path == "/hello":
            b = b"<html><body><h1>Halo dari localhost</h1><script>x()</script></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        self._json({"error": "nf"}, 404)

    def sse(self, o):
        self.wfile.write(("data: " + json.dumps(o) + "\n\n").encode())
        self.wfile.flush()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        model = body.get("model")
        roles = [m["role"] for m in body["messages"]]
        REQUESTS.append({"model": model, "n": len(roles), "tools": bool(body.get("tools")), "roles": roles[-3:],
                         "conv_header": self.headers.get("X-Conversation-Id"), "user": body.get("user")})
        if model in ("m-notools", "m-dumb") and body.get("tools"):
            return self._json({"error": {"message": "tools is not supported for this model"}}, 400)
        if model == "m-notoolrole" and ("tool" in roles or any("tool_calls" in m for m in body["messages"])):
            return self._json({"error": {"message": "unsupported role: tool"}}, 400)
        kind, val = brain(model, body)
        ctx_len = sum(len(content_of(m)) for m in (body["messages"][-1:] if model in ("m-lastonly", "m-dumb") else body["messages"])) // 4
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        rid = "chatcmpl-" + str(abs(hash(json.dumps(body["messages"][-1:]))) % 10 ** 8)
        if kind == "calls":
            for i, (n, a) in enumerate(val):
                s = json.dumps(a)
                h = len(s) // 2
                self.sse({"id": rid, "choices": [{"delta": {"tool_calls": [{"index": i, "id": "call_0", "function": {"name": n, "arguments": ""}}]}}]})
                self.sse({"id": rid, "choices": [{"delta": {"tool_calls": [{"index": i, "function": {"arguments": s[:h]}}]}}]})
                self.sse({"id": rid, "choices": [{"delta": {"tool_calls": [{"index": i, "function": {"arguments": s[h:]}}]}}]})
        else:
            self.sse({"id": rid, "choices": [{"delta": {"reasoning_content": "hmm"}}]})
            for i in range(0, len(val), 6):
                self.sse({"id": rid, "choices": [{"delta": {"content": val[i:i + 6]}}]})
        self.sse({"id": rid, "choices": [], "usage": {"prompt_tokens": ctx_len, "completion_tokens": 20, "total_tokens": ctx_len + 20}})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def start():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]
