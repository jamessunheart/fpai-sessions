#!/usr/bin/env python3
import sqlite3, json

db = sqlite3.connect("/opt/fpai/leads/leads.db")
db.row_factory = sqlite3.Row

print("=== Test lead status ===")
r = db.execute("SELECT name, email, source, qualifying_answers, intake_status, qualification_score FROM leads WHERE email = ?", ("pipeline-test@example.com",)).fetchone()
if r:
    print("Name:", r["name"])
    print("Email:", r["email"])
    print("Source:", r["source"])
    print("Status:", r["intake_status"])
    print("Score:", r["qualification_score"])
    qa = r["qualifying_answers"]
    if qa:
        print("Qualifying answers:", qa[:200])
else:
    print("Not found")

print()
print("=== Latest intake activity ===")
for r in db.execute("SELECT * FROM intake_log ORDER BY timestamp DESC LIMIT 5").fetchall():
    print("  {} | {:35} | {}".format(r["timestamp"], r["lead_email"], r["action"]))

print()
print("=== Latest bus messages ===")
bus = sqlite3.connect("/opt/fpai/memory-bus/bus.db")
bus.row_factory = sqlite3.Row
for r in bus.execute("SELECT from_agent, type, content, created_at FROM messages ORDER BY created_at DESC LIMIT 5").fetchall():
    c = json.loads(r["content"]) if r["content"] else {}
    name = c.get("prospect_name", c.get("prospect", ""))
    score = c.get("qualification_score", "")
    detail = ""
    if score:
        detail = "(score:{})".format(score)
    elif c.get("cycle"):
        detail = "(cycle:{})".format(c["cycle"])
    print("  {} | {:15} | {:20} | {} {}".format(r["created_at"][:19], r["from_agent"], r["type"], name, detail))

print()
print("=== Pipeline stats ===")
total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
qualified = db.execute("SELECT COUNT(*) FROM leads WHERE qualification_score >= 50").fetchone()[0]
from_call = db.execute("SELECT COUNT(*) FROM leads WHERE source = ?", ("fullpotential.ai/call",)).fetchone()[0]
print("  Total leads:", total)
print("  Qualified (50+):", qualified)
print("  From /call page:", from_call)
