#!/usr/bin/env python3
"""Server MCP minimal (stdio, JSON-RPC per baris): tool `echo`, `add`, dan `boom` (selalu galat). Untuk contoh & test."""
import json
import sys

TOOLS = [
    {"name": "echo", "description": "Mengembalikan teks yang diberikan.",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "add", "description": "Menjumlahkan dua angka.",
     "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}},
    {"name": "boom", "description": "Selalu mengembalikan galat (uji penanganan error).",
     "inputSchema": {"type": "object", "properties": {}}},
]


def reply(mid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": mid}
    msg["error" if error else "result"] = error or result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    try:
        msg = json.loads(line)
    except ValueError:
        continue
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if method == "initialize":
        reply(mid, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "echo", "version": "1.0"}})
    elif method == "tools/list":
        reply(mid, {"tools": TOOLS})
    elif method == "tools/call":
        name, a = params.get("name"), params.get("arguments") or {}
        if name == "echo":
            reply(mid, {"content": [{"type": "text", "text": str(a.get("text", ""))}]})
        elif name == "add":
            reply(mid, {"content": [{"type": "text", "text": str(a.get("a", 0) + a.get("b", 0))}]})
        elif name == "boom":
            reply(mid, {"content": [{"type": "text", "text": "meledak"}], "isError": True})
        else:
            reply(mid, error={"code": -32602, "message": f"tool tidak dikenal: {name}"})
    elif mid is not None:
        reply(mid, error={"code": -32601, "message": f"method tidak didukung: {method}"})
