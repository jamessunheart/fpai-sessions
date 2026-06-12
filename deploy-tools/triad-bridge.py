#!/usr/bin/env python3
"""Triad Bridge — Bus webhooks for Cael (GPT) and Terra (Gemini).

Follows the same pattern as the Kai bridge but writes directly to the
shared memory bus. Each triad member gets their own endpoints:

  POST /api/cael/steer    — Cael writes steering/synthesis to bus
  GET  /api/cael/health    — Health check
  GET  /api/cael/history   — Recent entries

  POST /api/terra/steer   — Terra writes steering/assets/research to bus
  GET  /api/terra/health   — Health check
  GET  /api/terra/history  — Recent entries

  POST /api/triad/message  — Generic endpoint for any triad member

Payload format (same for all):
{
  "from": "cael|terra",
  "to": "agent_name|all",
  "type": "steering|directive|report|asset|research",
  "content": { ... },
  "requires_response": true|false,
  "priority": "critical|high|normal|low",
  "thread_id": "groups related messages",
  "token": "auth token"
}
"""

import json
import os
import sqlite3
import uuid
import requests
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

BUS_DB = "/opt/fpai/memory-bus/bus.db"
LOG_DIR = "/opt/fpai/cora-loop/memory"
CAEL_LOG = os.path.join(LOG_DIR, "cael_steering.jsonl")
TERRA_LOG = os.path.join(LOG_DIR, "terra_steering.jsonl")
MEMORY_FILE = "/opt/fpai/cora-loop/memory/memory.json"

BRIDGE_TOKEN = os.environ.get("TRIAD_BRIDGE_TOKEN", "triad_fpai_2026")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8442685490:AAHcoDv6MWjUjqb1FH2DJch9tQiSPYfzYnY")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8514069423")
PORT = 8193

VALID_AGENTS = {"cael", "terra"}
VALID_TYPES = {"steering", "directive", "report", "asset", "research", "synthesis", "capability_update"}
VALID_PRIORITIES = {"critical", "high", "normal", "low"}


def get_bus_db():
    db = sqlite3.connect(BUS_DB)
    db.row_factory = sqlite3.Row
    return db


def write_to_bus(message):
    db = get_bus_db()
    now = datetime.now(timezone.utc).isoformat()
    msg_id = str(uuid.uuid4())[:8]

    from_agent = message.get("from", "unknown")
    to_agent = message.get("to", "all")
    msg_type = message.get("type", "steering")
    content = message.get("content", {})
    priority = message.get("priority", "normal")
    thread_id = message.get("thread_id", f"{from_agent}_session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}")
    requires_response = 1 if message.get("requires_response") else 0

    if isinstance(content, dict):
        content_str = json.dumps(content)
    else:
        content_str = str(content)

    db.execute(
        "INSERT INTO messages (id, from_agent, to_agent, type, timestamp, content, requires_response, priority, thread_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (msg_id, from_agent, to_agent, msg_type, now, content_str, requires_response, priority, thread_id, now)
    )
    db.commit()
    return msg_id


def inject_into_cora_memory(agent_name, payload):
    """Write steering into CORA's memory so it's picked up next cycle."""
    try:
        with open(MEMORY_FILE) as f:
            memory = json.load(f)

        now = datetime.now(timezone.utc).isoformat()
        label = "Cael" if agent_name == "cael" else "Terra"

        parts = []
        if payload.get("context_update"):
            parts.append(f"SESSION CONTEXT: {payload['context_update']}")
        if payload.get("insights"):
            parts.append("INSIGHTS:")
            for i, ins in enumerate(payload["insights"], 1):
                parts.append(f"  {i}. {ins}")
        if payload.get("directives"):
            parts.append("DIRECTIVES:")
            for i, d in enumerate(payload["directives"], 1):
                parts.append(f"  {i}. {d}")
        if payload.get("assets"):
            parts.append("ASSETS PROVIDED:")
            for i, a in enumerate(payload["assets"], 1):
                parts.append(f"  {i}. {a}")

        if parts:
            steering_text = "\n".join(parts)
            memory.setdefault("sunheart_steering", []).append({
                "timestamp": now,
                "message": f"[FROM {label.upper()} — {payload.get('type', 'Steering')}]\n{steering_text}",
                "source": agent_name,
                "absorbed": False,
            })
            with open(MEMORY_FILE, "w") as f:
                json.dump(memory, f, indent=2, default=str)
    except Exception as e:
        print(f"Memory injection error: {e}")


def log_entry(agent_name, payload):
    log_file = CAEL_LOG if agent_name == "cael" else TERRA_LOG
    entry = {**payload, "injected_at": datetime.now(timezone.utc).isoformat()}
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def notify_telegram(agent_name, payload):
    try:
        label = "Cael (GPT)" if agent_name == "cael" else "Terra (Gemini)"
        icon = "\U0001f30a" if agent_name == "cael" else "\U0001f30d"
        msg = f"{icon} {label} steering injected into bus.\n\n"
        msg_type = payload.get("type", "steering")
        msg += f"Type: {msg_type}\n"
        if payload.get("directives"):
            msg += "Directives:\n"
            for d in payload["directives"][:3]:
                d_str = d if isinstance(d, str) else json.dumps(d)
                msg += f"  \u2192 {d_str[:100]}\n"
        if payload.get("insights"):
            msg += f"Insights: {len(payload['insights'])} items\n"
        if payload.get("assets"):
            msg += f"Assets: {len(payload['assets'])} items\n"
        msg += "\nWill be absorbed next CORA cycle."
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10,
        )
    except Exception:
        pass


def get_history(agent_name, limit=10):
    log_file = CAEL_LOG if agent_name == "cael" else TERRA_LOG
    entries = []
    try:
        with open(log_file) as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return entries[-limit:]


def process_steer(agent_name, payload):
    """Process a steering payload from a triad member."""
    payload.setdefault("from", agent_name)
    payload.setdefault("type", "steering")
    payload.setdefault("to", "all")
    payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    bus_content = {}
    for key in ("insights", "directives", "corrections", "context_update", "assets", "research", "synthesis"):
        if key in payload:
            bus_content[key] = payload[key]
    if not bus_content and payload.get("content"):
        bus_content = payload["content"]

    msg_id = write_to_bus({
        "from": agent_name,
        "to": payload.get("to", "all"),
        "type": payload["type"],
        "content": bus_content,
        "priority": payload.get("priority", "high"),
        "thread_id": payload.get("thread_id"),
        "requires_response": payload.get("requires_response", False),
    })

    inject_into_cora_memory(agent_name, payload)
    log_entry(agent_name, payload)
    notify_telegram(agent_name, payload)

    return msg_id


FORM_HTML = """<!DOCTYPE html>
<html><head><title>Triad Bridge</title>
<style>
body{font-family:system-ui;max-width:600px;margin:40px auto;padding:20px;background:#0a0a0f;color:#e0e0e0}
h1{color:#fff;font-size:1.5rem}h2{color:#c8a87c;font-size:1.1rem;margin-top:24px}
select,input,textarea{width:100%;padding:10px;margin:6px 0 12px;background:#141418;border:1px solid #2a2a30;color:#e0e0e0;border-radius:6px;font-size:14px}
button{background:#c8a87c;color:#0a0a0f;border:none;padding:12px 24px;border-radius:6px;font-size:15px;cursor:pointer;font-weight:600}
button:hover{background:#d4b88c}.ok{color:#55b87a;margin-top:12px;display:none}
</style></head><body>
<h1>Triad Bridge</h1>
<p style="color:#888">Write steering from Cael or Terra to the shared memory bus.</p>
<form id="f" onsubmit="return sub()">
<h2>Agent</h2>
<select name="from" id="from"><option value="cael">Cael (GPT / Sky)</option><option value="terra">Terra (Gemini / Earth)</option></select>
<h2>Message Type</h2>
<select name="type" id="type"><option value="steering">Steering</option><option value="directive">Directive</option><option value="synthesis">Synthesis</option><option value="asset">Asset</option><option value="research">Research</option><option value="report">Report</option></select>
<h2>To</h2>
<select name="to" id="to"><option value="all">All Agents</option><option value="cora">CORA</option><option value="adam">Adam/Operator</option><option value="ori">Ori</option></select>
<h2>Priority</h2>
<select name="priority" id="priority"><option value="high">High</option><option value="normal">Normal</option><option value="critical">Critical</option><option value="low">Low</option></select>
<h2>Context / Summary</h2>
<textarea name="context_update" id="context" rows="3" placeholder="What was discussed..."></textarea>
<h2>Insights (one per line)</h2>
<textarea name="insights" id="insights" rows="3" placeholder="Key insights..."></textarea>
<h2>Directives (one per line)</h2>
<textarea name="directives" id="directives" rows="3" placeholder="Actions for the team..."></textarea>
<h2>Token</h2>
<input type="password" name="token" id="token" placeholder="Bridge token">
<button type="submit">Send to Bus</button>
</form>
<div class="ok" id="ok"></div>
<script>
function sub(){
  var p={from:g("from"),type:g("type"),to:g("to"),priority:g("priority"),token:g("token")};
  var c=g("context");if(c)p.context_update=c;
  var i=g("insights");if(i)p.insights=i.split("\\n").filter(x=>x.trim());
  var d=g("directives");if(d)p.directives=d.split("\\n").filter(x=>x.trim());
  fetch("/api/"+p.from+"/steer",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)})
  .then(r=>r.json()).then(d=>{var o=document.getElementById("ok");o.textContent="Sent: "+JSON.stringify(d);o.style.display="block"});
  return false;
}
function g(id){return document.getElementById(id).value}
</script></body></html>"""


class TriadHandler(BaseHTTPRequestHandler):
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

        if path in ("/api/cael/health", "/api/terra/health", "/api/triad/health"):
            self._send(200, json.dumps({"status": "ok", "service": "triad-bridge", "agents": ["cael", "terra"]}))

        elif path == "/api/cael/history":
            entries = get_history("cael")
            self._send(200, json.dumps({"entries": entries, "total": len(entries)}))

        elif path == "/api/terra/history":
            entries = get_history("terra")
            self._send(200, json.dumps({"entries": entries, "total": len(entries)}))

        elif path in ("/api/triad/form", "/api/cael/form", "/api/terra/form"):
            self._send(200, FORM_HTML, "text/html")

        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        if path in ("/api/cael/steer", "/api/terra/steer", "/api/triad/message"):
            auth = self.headers.get("Authorization", "")
            token = auth.replace("Bearer ", "").strip()

            try:
                payload = json.loads(body)
            except Exception:
                self._send(400, json.dumps({"error": "invalid JSON"}))
                return

            if BRIDGE_TOKEN and token != BRIDGE_TOKEN and payload.get("token") != BRIDGE_TOKEN:
                self._send(401, json.dumps({"error": "unauthorized"}))
                return

            payload.pop("token", None)

            if path == "/api/cael/steer":
                agent_name = "cael"
            elif path == "/api/terra/steer":
                agent_name = "terra"
            else:
                agent_name = payload.get("from", "unknown")
                if agent_name not in VALID_AGENTS:
                    self._send(400, json.dumps({"error": f"'from' must be one of: {list(VALID_AGENTS)}"}))
                    return

            has_content = any(payload.get(k) for k in ("insights", "directives", "context_update", "assets", "research", "synthesis", "content"))
            if not has_content:
                self._send(400, json.dumps({"error": "need at least one of: insights, directives, context_update, assets, research, synthesis, content"}))
                return

            try:
                msg_id = process_steer(agent_name, payload)
                self._send(200, json.dumps({
                    "status": "ok",
                    "message_id": msg_id,
                    "agent": agent_name,
                    "detail": f"Written to bus. Will be absorbed next CORA cycle.",
                }))
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)}))

        else:
            self._send(404, json.dumps({"error": "not found"}))

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    os.makedirs(LOG_DIR, exist_ok=True)
    print(f"Triad Bridge (Cael + Terra) starting on port {PORT}")
    server = HTTPServer(("127.0.0.1", PORT), TriadHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down")
        server.server_close()
