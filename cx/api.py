"""OpenAI-compatible chat client (stdlib only) with SSE streaming + tool calls."""
import json
import ssl
import time
import urllib.error
import urllib.request
import uuid


class ApiError(Exception):
    pass


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
    req.add_header("User-Agent", "CodinX/1.0")
    if conv_id:
        req.add_header("X-Conversation-Id", conv_id)
    if payload and payload.get("stream"):
        req.add_header("Accept", "text/event-stream")
    return urllib.request.urlopen(req, timeout=timeout, context=_ctx(cfg))


def list_models(cfg, key):
    try:
        with _open(cfg, key, "/models", timeout=20) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise ApiError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    except Exception as e:
        raise ApiError(str(e))
    items = d.get("data", d) if isinstance(d, dict) else d
    ids = [(m.get("id") if isinstance(m, dict) else str(m)) for m in items]
    return sorted(i for i in ids if i)


def chat(cfg, key, messages, tools=None, on_text=None, on_reasoning=None, conv_id=None):
    """Returns (assistant_message, usage). Message is {'role','content','tool_calls'?}."""
    payload = {"model": cfg["model"], "messages": messages, "stream": True,
               "stream_options": {"include_usage": True}}
    if conv_id:
        payload["user"] = conv_id
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if cfg.get("temperature") is not None:
        payload["temperature"] = cfg["temperature"]

    resp = None
    last = ""
    for attempt in range(4):
        try:
            resp = _open(cfg, key, "/chat/completions", payload, conv_id)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:600]
            last = f"HTTP {e.code}: {body}"
            if e.code == 400 and ("stream_options" in payload or "user" in payload):
                payload.pop("stream_options", None)
                payload.pop("user", None)
                continue
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise ApiError(last)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = str(getattr(e, "reason", e))
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise ApiError("Tidak bisa terhubung ke " + cfg["base_url"] + ": " + last)
    if resp is None:
        raise ApiError(last or "request gagal")

    content, calls, usage = [], {}, None
    ctype = resp.headers.get("Content-Type", "")
    with resp:
        if "event-stream" not in ctype:      # proxy tanpa streaming
            obj = json.loads(resp.read().decode())
            msg = obj["choices"][0]["message"]
            if msg.get("content"):
                content.append(msg["content"])
                if on_text:
                    on_text(msg["content"])
            for i, tc in enumerate(msg.get("tool_calls") or []):
                calls[i] = {"id": tc.get("id"), "name": tc["function"]["name"], "args": tc["function"].get("arguments", "")}
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
                if ev.get("error"):
                    raise ApiError(str(ev["error"])[:400])
                if ev.get("usage"):
                    usage = ev["usage"]
                for ch in ev.get("choices") or []:
                    delta = ch.get("delta") or {}
                    r = delta.get("reasoning_content") or delta.get("reasoning")
                    if r and on_reasoning:
                        on_reasoning(r)
                    t = delta.get("content")
                    if t:
                        content.append(t)
                        if on_text:
                            on_text(t)
                    for tc in delta.get("tool_calls") or []:
                        idx = tc.get("index")
                        if idx is None:
                            idx = (max(calls) + (1 if tc.get("id") else 0)) if calls else 0
                        cur = calls.setdefault(idx, {"id": None, "name": "", "args": ""})
                        if tc.get("id"):
                            cur["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            cur["name"] += fn["name"]
                        if fn.get("arguments"):
                            cur["args"] += fn["arguments"]

    msg = {"role": "assistant", "content": "".join(content)}
    if calls:
        msg["tool_calls"] = [
            {"id": c["id"] or "call_" + uuid.uuid4().hex[:12], "type": "function",
             "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
            for _, c in sorted(calls.items())
        ]
    if not usage:
        est = sum(len(str(m.get("content") or "")) for m in messages) // 4 + len(msg["content"]) // 4
        usage = {"prompt_tokens": est, "completion_tokens": len(msg["content"]) // 4, "total_tokens": est, "estimated": True}
    return msg, usage
          
