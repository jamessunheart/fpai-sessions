#!/usr/bin/env python3
"""Add analytics endpoint to lead-capture-api.py"""

f = "/opt/fpai/leads/lead-capture-api.py"
with open(f) as fh:
    code = fh.read()

changed = False

# 1. Add analytics table to get_db()
if "page_analytics" not in code:
    old = "    db.commit()\n    return db"
    new = '''    db.execute("""CREATE TABLE IF NOT EXISTS page_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT NOT NULL,
        page TEXT DEFAULT 'score',
        metadata TEXT,
        ip TEXT,
        user_agent TEXT,
        created_at TEXT NOT NULL
    )""")
    db.commit()
    return db'''
    code = code.replace(old, new, 1)
    changed = True
    print("Added page_analytics table")

# 2. Add POST /api/leads/analytics endpoint
if '"/api/leads/analytics"' not in code:
    old_marker = '''        else:
            self._send(404, json.dumps({"error": "not found"}))

    def log_message'''
    new_marker = '''        elif path == "/api/leads/analytics":
            try:
                data = json.loads(body)
                event = data.get("event", "unknown")
                page = data.get("page", "score")
                metadata = json.dumps(data.get("metadata", {}))
                ip = self.client_address[0]
                ua = self.headers.get("User-Agent", "")[:200]
                now = datetime.now(timezone.utc).isoformat()
                db = get_db()
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

    def log_message'''
    code = code.replace(old_marker, new_marker, 1)
    changed = True
    print("Added POST /api/leads/analytics endpoint")

# 3. Add GET /api/leads/analytics/daily endpoint
if '"/api/leads/analytics/daily"' not in code:
    old_marker2 = '        elif path.path in ("/call"'
    new_marker2 = '''        elif path.path == "/api/leads/analytics/daily":
            db = get_db()
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            rows = db.execute(
                "SELECT event, COUNT(*) as cnt FROM page_analytics WHERE created_at LIKE ?",
                (today + "%",)
            ).fetchall()
            stats = {}
            for r in rows:
                stats[r["event"]] = r["cnt"]
            self._send(200, json.dumps({"date": today, "events": stats}))

        elif path.path in ("/call"'''
    code = code.replace(old_marker2, new_marker2, 1)
    changed = True
    print("Added GET /api/leads/analytics/daily endpoint")

if changed:
    with open(f, "w") as fh:
        fh.write(code)
    print("Lead capture API updated")
else:
    print("No changes needed")
