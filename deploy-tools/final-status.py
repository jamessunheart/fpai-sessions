#!/usr/bin/env python3
import sqlite3, json, requests

BUS = "http://127.0.0.1:8195"

# Update global AI DB
db = sqlite3.connect("/opt/fpai/memory-bus/bus.db")
db.execute("UPDATE capabilities_global SET our_status = 'testing' WHERE name = 'ElevenLabs'")
db.execute("UPDATE capabilities_global SET our_status = 'testing' WHERE name = 'Cal.com'")
db.commit()

# Capability count
resp = requests.get(f"{BUS}/bus/capabilities", timeout=5)
caps_all = resp.json().get("capabilities", [])
by_agent = {}
for c in caps_all:
    a = c["agent"]
    by_agent[a] = by_agent.get(a, 0) + 1
print("Capabilities by agent:")
for a, n in sorted(by_agent.items()):
    print("  {:>15}: {}".format(a, n))
print("  Total:", len(caps_all))

# Agent count
resp = requests.get(f"{BUS}/bus/agents", timeout=5)
agents = resp.json().get("agents", [])
print("\nAgents: {}".format(len(agents)))
for a in agents:
    print("  {:>15} | {}".format(a["name"], a.get("last_heartbeat", "never")[:19]))

# Message count
db2 = sqlite3.connect("/opt/fpai/memory-bus/bus.db")
total = db2.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
by_type = db2.execute("SELECT type, COUNT(*) c FROM messages GROUP BY type ORDER BY c DESC").fetchall()
print("\nBus messages: {}".format(total))
for r in by_type:
    print("  {:>22}: {}".format(r[0], r[1]))

# Global AI DB
total_caps = db.execute("SELECT COUNT(*) FROM capabilities_global").fetchone()[0]
integrated = db.execute("SELECT COUNT(*) FROM capabilities_global WHERE our_status = 'integrated'").fetchone()[0]
testing = db.execute("SELECT COUNT(*) FROM capabilities_global WHERE our_status = 'testing'").fetchone()[0]
print("\nGlobal AI DB: {} entries | {} integrated | {} testing".format(total_caps, integrated, testing))

# Lead pipeline
leads_db = sqlite3.connect("/opt/fpai/leads/leads.db")
total_leads = leads_db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
from_call = leads_db.execute("SELECT COUNT(*) FROM leads WHERE source = 'fullpotential.ai/call'").fetchone()[0]
print("\nLead pipeline: {} total | {} from /call page".format(total_leads, from_call))
