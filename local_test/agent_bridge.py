"""
Agent bridge — a stand-in "agent under test" that satisfies the ACE Bench ToolLoop
wire contract by proxying to a local Ollama model.

The ToolLoopAdapter POSTs { session_id, messages, tools, resource_inventory } here;
this bridge translates that into an Ollama /api/chat call with tool definitions,
and translates Ollama's reply back into the contract's response shape:

    { "type": "tool_use", "tool_calls": [ {id, name, input}, ... ] }
    { "type": "final",     "response": "<final answer text>" }

It is deliberately a thin, stateless translator — the harness owns the loop and
sends the full message history each turn.
"""

import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "huihui_ai/llama3.2-abliterate:3b")

_SYSTEM = (
    "You are a CloudOps assessment agent with read-only AWS tools. "
    "Investigate by calling tools, then return ONLY a final JSON object matching the "
    "requested schema (summary, findings[], improvement_plan[]). "
    "Call a tool when you need data; do not invent resource IDs."
)


def _to_ollama_messages(messages: list) -> list:
    """Translate the harness message history into Ollama chat messages."""
    out = [{"role": "system", "content": _SYSTEM}]
    for m in messages:
        role = m.get("role")
        if role == "user":
            out.append({"role": "user", "content": m.get("content", "")})
        elif role == "assistant":
            calls = m.get("tool_calls") or []
            out.append({
                "role": "assistant",
                "content": m.get("content", "") or "",
                "tool_calls": [
                    {"function": {"name": c.get("name", ""), "arguments": c.get("input", {}) or {}}}
                    for c in calls
                ],
            })
        elif role == "tool":
            out.append({"role": "tool", "content": str(m.get("content", ""))[:6000]})
    return out


def _to_ollama_tools(tools: list) -> list:
    return [
        {"type": "function", "function": {
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
        }}
        for t in tools
    ]


def ollama_chat(messages: list, tools: list) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": _to_ollama_messages(messages),
        "tools": _to_ollama_tools(tools),
        "stream": False,
        "options": {"temperature": 0.1},
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode())

    msg = data.get("message", {})
    calls = msg.get("tool_calls") or []
    if calls:
        norm = []
        for i, c in enumerate(calls):
            fn = c.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            norm.append({"id": f"call_{i}", "name": fn.get("name", ""), "input": args})
        return {"type": "tool_use", "tool_calls": norm}
    return {"type": "final", "response": msg.get("content", "")}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or "{}")
        try:
            reply = ollama_chat(body.get("messages", []), body.get("tools", []))
        except Exception as e:
            reply = {"type": "final", "response": json.dumps({"error": str(e)})}
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(host="127.0.0.1", port=8099) -> HTTPServer:
    return HTTPServer((host, port), _Handler)


if __name__ == "__main__":
    port = int(os.getenv("BRIDGE_PORT", "8099"))
    print(f"agent bridge on :{port}  →  Ollama {OLLAMA_MODEL} @ {OLLAMA_URL}")
    make_server(port=port).serve_forever()
