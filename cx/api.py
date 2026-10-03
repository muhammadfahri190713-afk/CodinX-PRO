"""Klien chat OpenAI-compatible (stdlib): streaming SSE, tool call, dan toleran terhadap proxy yang 'aneh'."""
import json
import re
import ssl
import time
import urllib.error
import urllib.request

from . import log, wire

CONV_KEYS = ("conversation_id", "chat_id", "session_id", "thread_id")
_THINK = re.compile(r"<think>.*?</think>\s*", re.S)


class ApiError(Exception):
    def __init__(self, msg, status=None, body=""):
        super().__init__(msg)
        self.status = status
        self.body = body


def _ctx(cfg):
    if cfg.get("insecure_tls"):
        c = ssl.create_default_context()
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
        return c
    return None


def _open(cfg, key, path, payload=None, conv_id=None, timeout=600):
    url = cfg["base_url"].rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "CodinX/1.1")
    if conv_id:
        req.add_header("X-Conversation-Id", conv_id)
    if payload and payload.get("stream"):
        req.add_header("Accept", "text/event-stream")
    return urllib.request.urlopen(req, timeout=timeout, context=_ctx(cfg))


def _is_video_model(model):
    text = " ".join(str(model.get(k, "")) for k in ("id", "name", "type", "category", "endpoint")).lower()
    # Endpoint /models dapat mengembalikan katalog chat + video sekaligus.
    return any(token in text for token in (
        "video", "seedance", "veo-", "wan-", "nova-reel", "p-video", "happyhorse", "minimax-h3"
    ))


def list_model_specs(cfg, key):
    """Ambil model live: id dipakai backend, name hanya untuk tampilan."""
    try:
        with _open(cfg, key, "/models", timeout=20) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        raise ApiError(f"HTTP {e.code}: {body}", e.code, body)
    except Exception as e:
        raise ApiError(str(getattr(e, "reason", e)))
    items = d.get("data", d) if isinstance(d, dict) else d
    specs = []
    for item in items if isinstance(items, list) else []:
        m = item if isinstance(item, dict) else {"id": str(item)}
        model_id = str(m.get("id") or m.get("model") or "").strip()
        if not model_id or _is_video_model(m):
            continue
        display = str(m.get("name") or m.get("display_name") or model_id.replace("-", " ").title()).strip()
        role = str(m.get("role") or m.get("tier") or "FREE").upper()
        if role not in ("FREE", "PRO", "MAX"):
            role = "FREE"
        specs.append({"id": model_id, "name": display, "role": role, "trial": int(m.get("trial") or 0), "price": str(m.get("price") or "")})
    return sorted(specs, key=lambda m: m["id"])


def list_models(cfg, key):
    return [m["id"] for m in list_model_specs(cfg, key)]


def chat(cfg, key, messages, tools=None, on_text=None, on_reasoning=None, conv_id=None, timeout=600):
    """-> (assistant_message, usage, meta).  meta = {'id': id respons pertama, 'conv': id percakapan dari server}."""
    field = cfg.get("conv_field") or ""
    payload = {"model": cfg["model"], "messages": messages, "stream": True, "stream_options": {"include_usage": True}}
    if conv_id:
        payload["user"] = conv_id
        if field:
            payload[field] = conv_id
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if cfg.get("temperature") is not None:
        payload["temperature"] = cfg["temperature"]

    log.debug("http_request", url=cfg["base_url"], model=cfg["model"], messages=len(messages), tools=bool(tools),
              conv=bool(conv_id), conv_field=field or None)
    resp, last, stripped = None, "", False
    for attempt in range(4):
        try:
            resp = _open(cfg, key, "/chat/completions", payload, conv_id, timeout)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:800]
            last = f"HTTP {e.code}: {body}"
            if e.code in (400, 422) and not stripped and any(k and k in payload for k in ("stream_options", "user", field)):
                stripped = True                      # buang field opsional yang mungkin ditolak, coba sekali lagi
                for k in ("stream_options", "user", field):
                    if k:
                        payload.pop(k, None)
                continue
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            log.debug("http_error", status=e.code, body=body[:300])
            raise ApiError(last, e.code, body)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = str(getattr(e, "reason", e))
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise ApiError("Tidak bisa terhubung ke " + cfg["base_url"] + ": " + last)
    if resp is None:
        raise ApiError(last or "request gagal")

    content, calls, usage = [], {}, None
    meta = {"id": None, "conv": None}

    def note_meta(obj):
        if isinstance(obj, dict):
            if not meta["id"] and obj.get("id"):
                meta["id"] = str(obj["id"])
            for k in ((field,) if field else ()) + CONV_KEYS:
                if k and obj.get(k) and not meta["conv"]:
                    meta["conv"] = str(obj[k])

    def take(d):
        t = d.get("content")
        if isinstance(t, list):                        # content berupa array bagian
            t = "".join(p.get("text", "") for p in t if isinstance(p, dict))
        if t is None:
            t = d.get("text")
        if t:
            content.append(t)
            if on_text:
                on_text(t)
        r = d.get("reasoning_content") or d.get("reasoning")
        if r and on_reasoning:
            on_reasoning(r)
        for tc in d.get("tool_calls") or []:
            idx = tc.get("index")
            if idx is None:
                idx = (max(calls) + (1 if tc.get("id") else 0)) if calls else 0
            cur = calls.setdefault(idx, {"name": "", "args": ""})
            fn = tc.get("function") or {}
            nm = fn.get("name")
            if nm and nm != cur["name"]:
                cur["name"] = nm if not cur["name"] else cur["name"] + nm
            a = fn.get("arguments")
            if a not in (None, ""):
                cur["args"] += json.dumps(a, ensure_ascii=False) if isinstance(a, (dict, list)) else a

    with resp:
        if "event-stream" not in resp.headers.get("Content-Type", ""):      # proxy tanpa streaming
            obj = json.loads(resp.read().decode())
            if isinstance(obj, dict) and obj.get("error") and not obj.get("choices"):
                raise ApiError(str(obj["error"])[:400])
            note_meta(obj)
            ch = (obj.get("choices") or [{}])[0]
            take(ch.get("message") or {"text": ch.get("text")})
            usage = obj.get("usage")
        else:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                d = line[5:].strip()
                if d == "[DONE]":
                    break
                try:
                    ev = json.loads(d)
                except ValueError:
                    continue
                if ev.get("error") and not ev.get("choices"):
                    raise ApiError(str(ev["error"])[:400])
                note_meta(ev)
                if ev.get("usage"):
                    usage = ev["usage"]
                for ch in ev.get("choices") or []:
                    delta = ch.get("delta")
                    if delta is None and ch.get("message") and not content and not calls:
                        delta = ch["message"]               # beberapa proxy memakai 'message' di chunk akhir
                    if delta is None and ch.get("text"):
                        delta = {"text": ch["text"]}
                    take(delta or {})

    text = _THINK.sub("", "".join(content))
    msg = {"role": "assistant", "content": text}
    if calls:
        msg["tool_calls"] = [{"id": wire.new_call_id(), "type": "function",
                              "function": {"name": c["name"], "arguments": wire.fix_args(c["args"])}}
                             for _, c in sorted(calls.items()) if c["name"]]
        if not msg["tool_calls"]:
            del msg["tool_calls"]
    if not usage:
        est = sum(len(json.dumps(m, ensure_ascii=False)) for m in messages) // 4
        usage = {"prompt_tokens": est, "completion_tokens": len(text) // 4, "total_tokens": est + len(text) // 4, "estimated": True}
    return msg, usage, meta
