#!/usr/bin/env python3
"""Shared Memory Bus — Single source of truth for all FPAI agents.

SQLite-backed REST API. All agents read and write through this.

Endpoints:
  POST   /bus/messages              — Write a message
  GET    /bus/messages              — Read messages (filter by to, from, type, thread_id, since)
  GET    /bus/messages/<id>         — Read single message
  GET    /bus/messages/unread/<agent> — Unread messages for an agent
  POST   /bus/messages/<id>/ack     — Mark message as read by agent

  GET    /bus/capabilities          — List all capabilities
  POST   /bus/capabilities          — Register a capability
  DELETE /bus/capabilities/<id>     — Remove a capability
  GET    /bus/capabilities/<agent>  — Capabilities for a specific agent

  GET    /bus/agents                — List all known agents and status
  POST   /bus/agents/heartbeat      — Agent heartbeat (I'm alive)

  GET    /bus/health                — Health check
  GET    /bus/stats                 — Bus statistics
"""

import json
import uuid
import sqlite3
import os
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

DB_PATH = "/opt/fpai/memory-bus/bus.db"
PORT = 8195

Path("/opt/fpai/memory-bus").mkdir(parents=True, exist_ok=True)


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")

    db.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            from_agent TEXT NOT NULL,
            to_agent TEXT NOT NULL DEFAULT 'all',
            type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '{}',
            requires_response INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'medium',
            thread_id TEXT,
            parent_id TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS message_reads (
            message_id TEXT NOT NULL,
            agent TEXT NOT NULL,
            read_at TEXT NOT NULL,
            PRIMARY KEY (message_id, agent),
            FOREIGN KEY (message_id) REFERENCES messages(id)
        );

        CREATE TABLE IF NOT EXISTS capabilities (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            capability TEXT NOT NULL,
            api TEXT,
            permission TEXT DEFAULT 'autonomous',
            status TEXT DEFAULT 'active',
            added_date TEXT NOT NULL,
            documentation TEXT,
            UNIQUE(agent, capability)
        );

        CREATE TABLE IF NOT EXISTS agents (
            name TEXT PRIMARY KEY,
            role TEXT,
            status TEXT DEFAULT 'active',
            last_heartbeat TEXT,
            metadata TEXT DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_messages_to ON messages(to_agent);
        CREATE INDEX IF NOT EXISTS idx_messages_from ON messages(from_agent);
        CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type);
        CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
        CREATE INDEX IF NOT EXISTS idx_capabilities_agent ON capabilities(agent);
    """)
    db.commit()
    return db


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    if "content" in d:
        try:
            d["content"] = json.loads(d["content"])
        except (json.JSONDecodeError, TypeError):
            pass
    if "metadata" in d:
        try:
            d["metadata"] = json.loads(d["metadata"])
        except (json.JSONDecodeError, TypeError):
            pass
    if "requires_response" in d:
        d["requires_response"] = bool(d["requires_response"])
    return d


class BusHandler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        if isinstance(body, dict) or isinstance(body, list):
            body = json.dumps(body, default=str)
        if isinstance(body, str):
            body = body.encode()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_OPTIONS(self):
        self._send(200, "")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)
        db = get_db()

        if path == "/bus/health":
            self._send(200, {"status": "ok", "service": "memory-bus"})

        elif path == "/bus/stats":
            total_msgs = db.execute("SELECT COUNT(*) c FROM messages").fetchone()["c"]
            total_caps = db.execute("SELECT COUNT(*) c FROM capabilities").fetchone()["c"]
            total_agents = db.execute("SELECT COUNT(*) c FROM agents").fetchone()["c"]
            by_type = {r["type"]: r["c"] for r in db.execute(
                "SELECT type, COUNT(*) c FROM messages GROUP BY type"
            ).fetchall()}
            self._send(200, {
                "messages": total_msgs,
                "capabilities": total_caps,
                "agents": total_agents,
                "messages_by_type": by_type,
            })

        elif path == "/bus/messages":
            clauses, params = ["1=1"], []

            if "to" in qs:
                clauses.append("(to_agent = ? OR to_agent = 'all')")
                params.append(qs["to"][0])
            if "from" in qs:
                clauses.append("from_agent = ?")
                params.append(qs["from"][0])
            if "type" in qs:
                clauses.append("type = ?")
                params.append(qs["type"][0])
            if "thread_id" in qs:
                clauses.append("thread_id = ?")
                params.append(qs["thread_id"][0])
            if "since" in qs:
                clauses.append("timestamp >= ?")
                params.append(qs["since"][0])
            if "priority" in qs:
                clauses.append("priority = ?")
                params.append(qs["priority"][0])

            limit = int(qs.get("limit", [50])[0])
            offset = int(qs.get("offset", [0])[0])

            where = " AND ".join(clauses)
            rows = db.execute(
                f"SELECT * FROM messages WHERE {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()
            self._send(200, {"messages": [row_to_dict(r) for r in rows]})

        elif path.startswith("/bus/messages/unread/"):
            agent = path.split("/")[-1]
            rows = db.execute("""
                SELECT m.* FROM messages m
                WHERE (m.to_agent = ? OR m.to_agent = 'all')
                AND m.id NOT IN (SELECT message_id FROM message_reads WHERE agent = ?)
                ORDER BY m.timestamp DESC LIMIT 50
            """, (agent, agent)).fetchall()
            self._send(200, {"messages": [row_to_dict(r) for r in rows], "count": len(rows)})

        elif path.startswith("/bus/messages/"):
            msg_id = path.split("/")[-1]
            row = db.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
            if row:
                self._send(200, row_to_dict(row))
            else:
                self._send(404, {"error": "message not found"})

        elif path == "/bus/capabilities":
            agent_filter = qs.get("agent", [None])[0]
            if agent_filter:
                rows = db.execute(
                    "SELECT * FROM capabilities WHERE agent = ? AND status = 'active' ORDER BY capability",
                    (agent_filter,)
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM capabilities WHERE status = 'active' ORDER BY agent, capability"
                ).fetchall()
            self._send(200, {"capabilities": [row_to_dict(r) for r in rows]})

        elif path.startswith("/bus/capabilities/"):
            agent = path.split("/")[-1]
            rows = db.execute(
                "SELECT * FROM capabilities WHERE agent = ? AND status = 'active'",
                (agent,)
            ).fetchall()
            self._send(200, {"capabilities": [row_to_dict(r) for r in rows]})

        elif path == "/bus/agents":
            rows = db.execute("SELECT * FROM agents ORDER BY name").fetchall()
            self._send(200, {"agents": [row_to_dict(r) for r in rows]})

        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        db = get_db()

        if path == "/bus/messages":
            data = self._read_body()
            if not data.get("from") and not data.get("from_agent"):
                self._send(400, {"error": "from/from_agent required"})
                return
            if not data.get("type"):
                self._send(400, {"error": "type required"})
                return

            msg_id = data.get("id", str(uuid.uuid4()))
            now = datetime.now(timezone.utc).isoformat()
            content = data.get("content", {})
            if isinstance(content, str):
                content = {"text": content}

            db.execute(
                """INSERT INTO messages (id, from_agent, to_agent, type, timestamp, content,
                   requires_response, priority, thread_id, parent_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    msg_id,
                    data.get("from") or data.get("from_agent"),
                    data.get("to") or data.get("to_agent", "all"),
                    data["type"],
                    data.get("timestamp", now),
                    json.dumps(content),
                    1 if data.get("requires_response") else 0,
                    data.get("priority", "medium"),
                    data.get("thread_id"),
                    data.get("parent_id"),
                    now,
                ),
            )
            db.commit()
            self._send(201, {"id": msg_id, "status": "ok"})

        elif path.startswith("/bus/messages/") and path.endswith("/ack"):
            msg_id = path.split("/")[-2]
            data = self._read_body()
            agent = data.get("agent")
            if not agent:
                self._send(400, {"error": "agent required"})
                return
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                "INSERT OR IGNORE INTO message_reads (message_id, agent, read_at) VALUES (?, ?, ?)",
                (msg_id, agent, now)
            )
            db.commit()
            self._send(200, {"status": "ok"})

        elif path == "/bus/capabilities":
            data = self._read_body()
            if not data.get("agent") or not data.get("capability"):
                self._send(400, {"error": "agent and capability required"})
                return
            cap_id = data.get("id", str(uuid.uuid4()))
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                """INSERT OR REPLACE INTO capabilities
                   (id, agent, capability, api, permission, status, added_date, documentation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cap_id,
                    data["agent"],
                    data["capability"],
                    data.get("api", ""),
                    data.get("permission", "autonomous"),
                    data.get("status", "active"),
                    data.get("added_date", now),
                    data.get("documentation", ""),
                ),
            )
            db.commit()
            self._send(201, {"id": cap_id, "status": "ok"})

        elif path == "/bus/agents/heartbeat":
            data = self._read_body()
            agent = data.get("agent") or data.get("name")
            if not agent:
                self._send(400, {"error": "agent/name required"})
                return
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                """INSERT INTO agents (name, role, status, last_heartbeat, metadata)
                   VALUES (?, ?, 'active', ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                   last_heartbeat = ?, status = 'active',
                   role = COALESCE(?, role),
                   metadata = COALESCE(?, metadata)""",
                (agent, data.get("role", ""), now, json.dumps(data.get("metadata", {})),
                 now, data.get("role"), json.dumps(data.get("metadata", {})) if data.get("metadata") else None),
            )
            db.commit()
            self._send(200, {"status": "ok", "agent": agent})

        else:
            self._send(404, {"error": "not found"})

    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        db = get_db()

        if path.startswith("/bus/capabilities/"):
            cap_id = path.split("/")[-1]
            db.execute("UPDATE capabilities SET status = 'deprecated' WHERE id = ?", (cap_id,))
            db.commit()
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print(f"Memory Bus starting on port {PORT}")
    db = get_db()
    print(f"Database: {DB_PATH}")
    server = HTTPServer(("127.0.0.1", PORT), BusHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
