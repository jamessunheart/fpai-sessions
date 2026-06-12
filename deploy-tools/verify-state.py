#!/usr/bin/env python3
"""Verify full system state after integrations."""
import sqlite3
import json
import requests

BUS_DB = "/opt/fpai/memory-bus/bus.db"
BUS_URL = "http://127.0.0.1:8195"

db = sqlite3.connect(BUS_DB)
db.row_factory = sqlite3.Row

# Update global DB
db.execute("UPDATE capabilities_global SET our_status = 'testing', notes = 'Tool built, awaiting API key' WHERE name = 'ElevenLabs'")
db.execute("UPDATE capabilities_global SET our_status = 'testing', notes = 'Tool built, awaiting API key' WHERE name LIKE '%Cal.com%'")
db.commit()
print("Updated global capability DB")

print("\n=== Bus Messages ===")
rows = db.execute("SELECT from_agent, to_agent, type, priority, content, created_at FROM messages ORDER BY created_at ASC").fetchall()
for r in rows:
    content = json.loads(r["content"]) if r["content"] else {}
    snippet = ""
    for key in ["principle", "prospect_name", "directive", "cycle"]:
        if key in content:
            snippet = str(content[key])[:50]
            break
    if not snippet:
        snippet = str(list(content.keys())[:2])[:50]
    print("  {} | {:>15} -> {:<10} | {:<22} | {}".format(
        r["created_at"][:19], r["from_agent"], r["to_agent"], r["type"], snippet
    ))
print("\n  Total:", len(rows))

print("\n=== Agents ===")
try:
    agents = requests.get(f"{BUS_URL}/bus/agents", timeout=5).json().get("agents", [])
    for a in agents:
        print("  {:>15} | {}".format(a["name"], a.get("last_heartbeat", "never")[:19]))
except Exception as e:
    print(f"  Error: {e}")

print("\n=== Capabilities ===")
try:
    caps = requests.get(f"{BUS_URL}/bus/capabilities", timeout=5).json().get("capabilities", [])
    by_agent = {}
    for c in caps:
        a = c["agent"]
        by_agent[a] = by_agent.get(a, 0) + 1
    for a, n in sorted(by_agent.items()):
        print("  {:>15}: {}".format(a, n))
    print("  Total:", len(caps))
except Exception as e:
    print(f"  Error: {e}")

print("\n=== Global AI DB ===")
total = db.execute("SELECT COUNT(*) FROM capabilities_global").fetchone()[0]
integrated = db.execute("SELECT COUNT(*) FROM capabilities_global WHERE our_status = 'integrated'").fetchone()[0]
testing = db.execute("SELECT COUNT(*) FROM capabilities_global WHERE our_status = 'testing'").fetchone()[0]
print(f"  {total} entries | {integrated} integrated | {testing} testing")

print("\n=== Intake Agent Status ===")
try:
    leads_db = sqlite3.connect("/opt/fpai/leads/leads.db")
    leads_db.row_factory = sqlite3.Row
    total_leads = leads_db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    processed = leads_db.execute("SELECT COUNT(*) FROM leads WHERE intake_status IS NOT NULL AND intake_status != 'new'").fetchone()[0]
    recent = leads_db.execute("SELECT lead_email, action, timestamp FROM intake_log ORDER BY timestamp DESC LIMIT 5").fetchall()
    print(f"  Total leads: {total_leads} | Processed by intake: {processed}")
    if recent:
        print("  Recent intake activity:")
        for r in recent:
            print(f"    {r['timestamp']} | {r['lead_email']:<30} | {r['action']}")
    leads_db.close()
except Exception as e:
    print(f"  Error: {e}")

db.close()
