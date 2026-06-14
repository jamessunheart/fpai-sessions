#!/usr/bin/env python3
"""Lead Capture API — receives leads from web forms, Facebook Lead Ads, and webhooks.

Endpoints:
  POST /api/leads/capture     — Web form submission (name, email, message)
  POST /api/leads/fb-webhook  — Facebook Lead Ads webhook
  GET  /api/leads/fb-webhook  — Facebook webhook verification
  GET  /api/leads/stats       — Quick stats
  GET  /api/leads/health      — Health check
"""

import json
import os
import sqlite3
import hashlib
import hmac
import time
import requests
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

DB_PATH = "/opt/fpai/leads/leads.db"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8442685490:AAHcoDv6MWjUjqb1FH2DJch9tQiSPYfzYnY")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8514069423")
FB_VERIFY_TOKEN = os.environ.get("FB_VERIFY_TOKEN", "fpai_leads_2026")
PORT = 8190


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT, company TEXT, title TEXT, domain TEXT,
        source TEXT, industry TEXT, location TEXT, linkedin_url TEXT,
        phone TEXT, score INTEGER DEFAULT 0, status TEXT DEFAULT 'new',
        notes TEXT, raw_data TEXT, created_at TEXT, updated_at TEXT,
        UNIQUE(email)
    )""")
    db.commit()
    return db


def notify_telegram(lead_info):
    """Send new lead notification to Sunheart."""
    msg = (
        f"NEW LEAD\n\n"
        f"Name: {lead_info.get('name', 'Unknown')}\n"
        f"Email: {lead_info.get('email', 'N/A')}\n"
        f"Phone: {lead_info.get('phone', 'N/A')}\n"
        f"Source: {lead_info.get('source', 'web')}\n"
    )
    if lead_info.get("message"):
        msg += f"Message: {lead_info['message'][:200]}\n"
    if lead_info.get("company"):
        msg += f"Company: {lead_info['company']}\n"

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10,
        )
    except Exception:
        pass


def save_lead(data):
    """Save a lead to the database and notify."""
    db = get_db()
    email = (data.get("email") or "").lower().strip()
    if not email:
        return None

    now = datetime.now(timezone.utc).isoformat()
    try:
        db.execute(
            """INSERT OR REPLACE INTO leads
               (name, email, company, phone, source, notes, raw_data, status, score, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 30, ?, ?)""",
            (
                data.get("name", ""),
                email,
                data.get("company", ""),
                data.get("phone", ""),
                data.get("source", "web_form"),
                data.get("message", ""),
                json.dumps(data),
                now, now,
            ),
        )
        db.commit()
        notify_telegram(data)
        return email
    except Exception as e:
        return None


class LeadHandler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        if isinstance(body, str):
            body = body.encode()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, "")

    def do_GET(self):
        path = urlparse(self.path)

        if path.path == "/api/leads/health":
            self._send(200, json.dumps({"status": "ok", "service": "lead-capture"}))

        elif path.path == "/api/leads/stats":
            db = get_db()
            total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            today_count = db.execute(
                "SELECT COUNT(*) FROM leads WHERE created_at LIKE ?", (f"{today}%",)
            ).fetchone()[0]
            self._send(200, json.dumps({"total": total, "today": today_count}))

        elif path.path == "/api/leads/fb-webhook":
            # Facebook webhook verification
            qs = parse_qs(path.query)
            mode = qs.get("hub.mode", [None])[0]
            token = qs.get("hub.verify_token", [None])[0]
            challenge = qs.get("hub.challenge", [None])[0]
            if mode == "subscribe" and token == FB_VERIFY_TOKEN:
                self._send(200, challenge or "ok", "text/plain")
            else:
                self._send(403, json.dumps({"error": "verification failed"}))

        elif path.path == "/api/leads/form":
            # Serve a simple lead capture form
            html = """<!DOCTYPE html>
<html><head><title>Full Potential AI - Get Started</title>
<style>
body{font-family:system-ui;max-width:500px;margin:60px auto;padding:20px;background:#0a0a0a;color:#e0e0e0}
h1{color:#fff;font-size:24px}
p{color:#999;line-height:1.6}
input,textarea{width:100%;padding:12px;margin:8px 0 16px;border:1px solid #333;background:#111;color:#fff;border-radius:6px;font-size:15px;box-sizing:border-box}
input:focus,textarea:focus{border-color:#4a9eff;outline:none}
button{background:#4a9eff;color:#fff;border:none;padding:14px 28px;border-radius:6px;font-size:16px;cursor:pointer;width:100%}
button:hover{background:#3a8eef}
.ok{color:#4a9eff;display:none;text-align:center;padding:20px}
</style></head><body>
<h1>Full Potential AI</h1>
<p>Unlock your full potential with AI-powered consulting. Tell us about yourself.</p>
<form id="f" onsubmit="return sub()">
<input name="name" placeholder="Your name" required>
<input name="email" type="email" placeholder="Email" required>
<input name="company" placeholder="Company (optional)">
<input name="phone" placeholder="Phone (optional)">
<textarea name="message" rows="3" placeholder="What are you looking for?"></textarea>
<button type="submit">Get Started</button>
</form>
<div class="ok" id="ok">Thanks! We'll be in touch soon.</div>
<script>
function sub(){
var f=document.getElementById('f'),d=new FormData(f),o={};
d.forEach((v,k)=>o[k]=v);
fetch('/api/leads/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)})
.then(r=>{f.style.display='none';document.getElementById('ok').style.display='block'});
return false}
</script></body></html>"""
            self._send(200, html, "text/html")

        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        if path == "/api/leads/capture":
            try:
                data = json.loads(body)
                data["source"] = data.get("source", "web_form")
                result = save_lead(data)
                if result:
                    self._send(200, json.dumps({"status": "ok", "email": result}))
                else:
                    self._send(400, json.dumps({"error": "email required"}))
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)}))

        elif path == "/api/leads/fb-webhook":
            # Facebook Lead Ads webhook
            try:
                payload = json.loads(body)
                for entry in payload.get("entry", []):
                    for change in entry.get("changes", []):
                        if change.get("field") == "leadgen":
                            lead_data = change.get("value", {})
                            save_lead({
                                "name": lead_data.get("full_name", ""),
                                "email": lead_data.get("email", ""),
                                "phone": lead_data.get("phone_number", ""),
                                "source": "facebook_lead_ad",
                                "raw_data": lead_data,
                            })
                self._send(200, json.dumps({"status": "ok"}))
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)}))

        else:
            self._send(404, json.dumps({"error": "not found"}))

    def log_message(self, format, *args):
        pass  # Suppress default logging


if __name__ == "__main__":
    print(f"Lead Capture API starting on port {PORT}")
    server = HTTPServer(("127.0.0.1", PORT), LeadHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down")
        server.server_close()
