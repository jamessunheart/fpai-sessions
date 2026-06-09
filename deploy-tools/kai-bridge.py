#!/usr/bin/env python3
"""Kai → CORA Bridge — receives strategic steering from Kai sessions
and writes it into CORA's shared memory.

Endpoints:
  POST /api/kai/steer    — Accept Kai steering payload
  GET  /api/kai/health   — Health check
  GET  /api/kai/history   — Recent Kai steering entries

Payload format:
{
  "source": "kai",
  "timestamp": "ISO format (optional, auto-generated if missing)",
  "type": "strategic_steering",
  "insights": ["Array of key insights from session"],
  "directives": ["Array of directives for CORA to act on"],
  "corrections": ["Array of factual corrections to existing memory"],
  "context_update": "Free text summary of what was discussed"
}
"""

import json
import os
import hashlib
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path

MEMORY_FILE = "/opt/fpai/cora-loop/memory/memory.json"
SEED_FILE = "/opt/fpai/cora-loop/memory/seed.json"
KAI_LOG = "/opt/fpai/cora-loop/memory/kai_steering.jsonl"
BRIDGE_TOKEN = os.environ.get("KAI_BRIDGE_TOKEN", "kai_fpai_2026")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8442685490:AAHcoDv6MWjUjqb1FH2DJch9tQiSPYfzYnY")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8514069423")
PORT = 8192


def load_memory():
    with open(MEMORY_FILE) as f:
        return json.load(f)


def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2, default=str)


def inject_steering(payload):
    """Write Kai's steering into CORA's shared memory."""
    memory = load_memory()
    now = datetime.now(timezone.utc).isoformat()
    ts = payload.get("timestamp", now)

    # Build the steering message that CORA will see
    parts = []

    if payload.get("context_update"):
        parts.append(f"SESSION CONTEXT: {payload['context_update']}")

    if payload.get("insights"):
        parts.append("INSIGHTS:")
        for i, insight in enumerate(payload["insights"], 1):
            parts.append(f"  {i}. {insight}")

    if payload.get("directives"):
        parts.append("DIRECTIVES FOR CORA:")
        for i, directive in enumerate(payload["directives"], 1):
            parts.append(f"  {i}. {directive}")

    if payload.get("corrections"):
        parts.append("CORRECTIONS TO MEMORY:")
        for i, correction in enumerate(payload["corrections"], 1):
            parts.append(f"  {i}. {correction}")

    steering_text = "\n".join(parts)

    # Add to CORA's steering queue
    memory.setdefault("sunheart_steering", []).append({
        "timestamp": ts,
        "message": f"[FROM KAI — Strategic Steering]\n{steering_text}",
        "source": "kai",
        "absorbed": False,
    })

    # Apply corrections to seed if any
    if payload.get("corrections"):
        try:
            seed = json.loads(Path(SEED_FILE).read_text())
            if "kai_corrections" not in seed:
                seed["kai_corrections"] = []
            for correction in payload["corrections"]:
                seed["kai_corrections"].append({
                    "timestamp": ts,
                    "correction": correction,
                })
            Path(SEED_FILE).write_text(json.dumps(seed, indent=2))
        except Exception:
            pass

    save_memory(memory)

    # Log the full payload for audit trail
    log_entry = {**payload, "injected_at": now}
    with open(KAI_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Notify Sunheart on Telegram
    try:
        import requests
        msg = f"🧠 Kai steering injected into CORA loop.\n\n"
        if payload.get("directives"):
            msg += "Directives:\n"
            for d in payload["directives"][:3]:
                msg += f"  → {d[:100]}\n"
        msg += f"\nWill be absorbed next cycle."
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10,
        )
    except Exception:
        pass

    return len(parts)


class BridgeHandler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        if isinstance(body, str):
            body = body.encode()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, "")

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/kai/health":
            self._send(200, json.dumps({"status": "ok", "service": "kai-bridge"}))

        elif path == "/api/kai/history":
            entries = []
            try:
                with open(KAI_LOG) as f:
                    for line in f:
                        try:
                            entries.append(json.loads(line.strip()))
                        except:
                            pass
            except FileNotFoundError:
                pass
            self._send(200, json.dumps({"entries": entries[-10:], "total": len(entries)}))

        elif path == "/api/kai/form":
            html = FORM_HTML
            self._send(200, html, "text/html")

        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        if path == "/api/kai/steer":
            # Optional auth
            auth = self.headers.get("Authorization", "")
            token = auth.replace("Bearer ", "").strip()
            if BRIDGE_TOKEN and token != BRIDGE_TOKEN:
                # Also accept token in payload
                try:
                    payload = json.loads(body)
                    if payload.get("token") != BRIDGE_TOKEN:
                        self._send(401, json.dumps({"error": "unauthorized"}))
                        return
                except:
                    self._send(401, json.dumps({"error": "unauthorized"}))
                    return
            else:
                try:
                    payload = json.loads(body)
                except:
                    self._send(400, json.dumps({"error": "invalid JSON"}))
                    return

            # Validate required fields
            if not payload.get("insights") and not payload.get("directives") and not payload.get("context_update"):
                self._send(400, json.dumps({"error": "need at least one of: insights, directives, context_update"}))
                return

            payload.setdefault("source", "kai")
            payload.setdefault("type", "strategic_steering")
            payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

            try:
                count = inject_steering(payload)
                self._send(200, json.dumps({
                    "status": "ok",
                    "message": f"Steering injected ({count} sections). Will be absorbed next CORA cycle.",
                    "next_cycle": "see /api/kai/health for schedule",
                }))
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)}))

        else:
            self._send(404, json.dumps({"error": "not found"}))

    def log_message(self, format, *args):
        pass


FORM_HTML = """<!DOCTYPE html>
<html><head><title>Kai → CORA Bridge</title>
<style>
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;max-width:640px;margin:40px auto;padding:20px;background:#0a0a0a;color:#e0e0e0}
h1{color:#fff;font-size:22px;margin-bottom:4px}
.sub{color:#666;margin-bottom:24px;font-size:14px}
label{display:block;color:#999;font-size:13px;margin-top:16px;margin-bottom:4px}
textarea{width:100%;padding:10px;border:1px solid #333;background:#111;color:#fff;border-radius:6px;font-size:14px;font-family:inherit;resize:vertical}
textarea:focus{border-color:#7c5cfc;outline:none}
button{background:#7c5cfc;color:#fff;border:none;padding:12px 24px;border-radius:6px;font-size:15px;cursor:pointer;width:100%;margin-top:20px}
button:hover{background:#6a4ce0}
.ok{color:#7c5cfc;display:none;text-align:center;padding:30px;font-size:16px}
.hint{color:#555;font-size:12px;margin-top:2px}
</style></head><body>
<h1>Kai → CORA Bridge</h1>
<p class="sub">Paste Kai's session output to inject into the CORA-Operator loop.</p>
<form id="f" onsubmit="return sub()">
<input type="hidden" name="token" value="kai_fpai_2026">

<label>Session Context (what was discussed)</label>
<textarea name="context_update" rows="3" placeholder="Brief summary of the Kai-Sunheart conversation..."></textarea>

<label>Insights</label>
<textarea name="insights" rows="4" placeholder="One insight per line..."></textarea>
<div class="hint">One per line. These become observations in CORA's memory.</div>

<label>Directives for CORA</label>
<textarea name="directives" rows="4" placeholder="One directive per line..."></textarea>
<div class="hint">One per line. CORA will act on these next cycle.</div>

<label>Memory Corrections</label>
<textarea name="corrections" rows="2" placeholder="One correction per line (optional)..."></textarea>
<div class="hint">Fix factual errors in existing memory. Optional.</div>

<button type="submit">Inject into CORA Loop</button>
</form>
<div class="ok" id="ok">Steering injected. CORA will absorb it next cycle.</div>
<script>
function sub(){
var f=document.getElementById('f'),o={
  source:'kai',type:'strategic_steering',
  token:f.token.value,
  context_update:f.context_update.value,
  insights:f.insights.value.split('\\n').filter(x=>x.trim()),
  directives:f.directives.value.split('\\n').filter(x=>x.trim()),
  corrections:f.corrections.value.split('\\n').filter(x=>x.trim())
};
fetch('/api/kai/steer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)})
.then(r=>r.json()).then(d=>{
  if(d.status==='ok'){f.style.display='none';document.getElementById('ok').style.display='block'}
  else{alert('Error: '+d.error)}
}).catch(e=>alert('Error: '+e));
return false}
</script></body></html>"""


if __name__ == "__main__":
    print(f"Kai-CORA Bridge starting on port {PORT}")
    server = HTTPServer(("127.0.0.1", PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
