#!/usr/bin/env python3
"""Lead Capture API — Primary Server (198.54.123.234)
Receives leads from the score page and analytics events.
Stores locally and forwards to intake agent on secondary server via bus message.
"""

import json
import os
import sqlite3
import time
import requests
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DB_PATH = "/opt/fpai/leads/leads.db"
ANALYTICS_DB_PATH = "/opt/fpai/leads/analytics.db"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8442685490:AAHcoDv6MWjUjqb1FH2DJch9tQiSPYfzYnY")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8514069423")
PORT = 8191


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT, company TEXT, title TEXT, domain TEXT,
        source TEXT, industry TEXT, location TEXT, linkedin_url TEXT,
        phone TEXT, score INTEGER DEFAULT 0, status TEXT DEFAULT 'new',
        notes TEXT, raw_data TEXT, created_at TEXT, updated_at TEXT,
        qualifying_answers TEXT, message TEXT,
        UNIQUE(email)
    )""")
    db.commit()
    return db


def get_analytics_db():
    db = sqlite3.connect(ANALYTICS_DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS page_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT NOT NULL,
        page TEXT DEFAULT 'score',
        metadata TEXT,
        ip TEXT,
        user_agent TEXT,
        created_at TEXT NOT NULL
    )""")
    db.commit()
    return db


def notify_telegram(lead_info):
    msg = (
        "🎯 NEW REAL LEAD\n\n"
        f"Name: {lead_info.get('name', 'Unknown')}\n"
        f"Email: {lead_info.get('email', 'N/A')}\n"
        f"Source: {lead_info.get('source', 'web')}\n"
    )
    if lead_info.get("message"):
        msg += f"\n{lead_info['message'][:300]}\n"

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


def save_lead(data):
    db = get_db()
    email = (data.get("email") or "").lower().strip()
    if not email:
        return None

    now = datetime.now(timezone.utc).isoformat()
    try:
        db.execute(
            """INSERT OR REPLACE INTO leads
               (name, email, company, phone, source, notes, raw_data, status, score, created_at, updated_at, qualifying_answers, message)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 30, ?, ?, ?, ?)""",
            (
                data.get("name", ""),
                email,
                data.get("company", ""),
                data.get("phone", ""),
                data.get("source", "web_form"),
                data.get("notes", data.get("message", "")),
                json.dumps(data),
                now, now,
                json.dumps(data.get("qualifying_answers")) if data.get("qualifying_answers") else None,
                data.get("message", ""),
            ),
        )
        db.commit()
        notify_telegram(data)
        return email
    except Exception as e:
        print(f"Error saving lead: {e}")
        return None


class Handler(BaseHTTPRequestHandler):
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
        path = urlparse(self.path).path

        if path == "/api/leads/health":
            self._send(200, json.dumps({"status": "ok", "service": "lead-capture-primary"}))

        elif path == "/api/leads/stats":
            db = get_db()
            total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            today_count = db.execute(
                "SELECT COUNT(*) FROM leads WHERE created_at LIKE ?", (f"{today}%",)
            ).fetchone()[0]
            self._send(200, json.dumps({"total": total, "today": today_count}))

        elif path == "/api/leads/analytics/daily":
            db = get_analytics_db()
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            rows = db.execute(
                "SELECT event, COUNT(*) as cnt FROM page_analytics WHERE created_at LIKE ? GROUP BY event",
                (today + "%",)
            ).fetchall()
            stats = {r["event"]: r["cnt"] for r in rows}
            self._send(200, json.dumps({"date": today, "events": stats}))

        elif path == "/api/leads/pending":
            db = get_db()
            rows = db.execute(
                "SELECT id, name, email, source, message, qualifying_answers, raw_data, created_at FROM leads WHERE status = 'new' ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
            leads = []
            for r in rows:
                leads.append({c: r[c] for c in r.keys()})
            self._send(200, json.dumps({"leads": leads}))

        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        if path == "/api/leads/capture":
            try:
                data = json.loads(body)
                data["source"] = data.get("source", "fullpotential.ai/score")
                result = save_lead(data)
                if result:
                    self._send(200, json.dumps({"status": "ok", "email": result}))
                else:
                    self._send(400, json.dumps({"error": "email required"}))
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)}))

        elif path == "/api/leads/synced":
            try:
                data = json.loads(body)
                ids = data.get("ids", [])
                if ids:
                    db = get_db()
                    placeholders = ",".join("?" * len(ids))
                    db.execute(f"UPDATE leads SET status = 'synced' WHERE id IN ({placeholders})", ids)
                    db.commit()
                self._send(200, json.dumps({"status": "ok", "synced": len(ids)}))
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)}))

        elif path == "/api/leads/analytics":
            try:
                data = json.loads(body)
                event = data.get("event", "unknown")
                page = data.get("page", "score")
                metadata = json.dumps(data.get("metadata", {}))
                ip = self.client_address[0]
                ua = self.headers.get("User-Agent", "")[:200]
                now = datetime.now(timezone.utc).isoformat()
                db = get_analytics_db()
                db.execute(
                    "INSERT INTO page_analytics (event, page, metadata, ip, user_agent, created_at) VALUES (?,?,?,?,?,?)",
                    (event, page, metadata, ip, ua, now)
                )
                db.commit()
                self._send(200, json.dumps({"status": "ok"}))
            except Exception:
                self._send(200, json.dumps({"status": "error"}))

        else:
            self._send(404, json.dumps({"error": "not found"}))

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    os.makedirs("/opt/fpai/leads", exist_ok=True)
    print(f"Lead Capture API (primary) starting on port {PORT}")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down")
        server.server_close()
