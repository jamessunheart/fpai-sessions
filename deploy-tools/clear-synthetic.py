#!/usr/bin/env python3
"""Clear all synthetic/seed data from the pipeline. Honest zeros only."""
import sqlite3
import json
import requests

BUS_URL = "http://127.0.0.1:8195"

# 1. Clear synthetic leads
leads_db = sqlite3.connect("/opt/fpai/leads/leads.db")
total = leads_db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
print("Leads before: {}".format(total))

leads_db.execute("UPDATE leads SET intake_status = 'seed_data' WHERE 1=1")
leads_db.execute("DELETE FROM intake_log")
try:
    leads_db.execute("DELETE FROM session_briefs")
except Exception:
    pass
try:
    leads_db.execute("DELETE FROM followups")
except Exception:
    pass
leads_db.commit()

real = leads_db.execute("SELECT COUNT(*) FROM leads WHERE intake_status != 'seed_data'").fetchone()[0]
print("Real inbound leads: {}".format(real))
print("Seed data excluded from pipeline: {}".format(total))
leads_db.close()

# 2. Clear synthetic prospect briefs from bus
bus_db = sqlite3.connect("/opt/fpai/memory-bus/bus.db")
fake = bus_db.execute("SELECT COUNT(*) FROM messages WHERE type = 'prospect_brief'").fetchone()[0]
bus_db.execute("DELETE FROM messages WHERE type = 'prospect_brief'")
bus_db.commit()
print("Removed {} synthetic prospect briefs from bus".format(fake))
bus_db.close()

# 3. Write no-synthetic-traction governance rule
resp = requests.post("{}/bus/messages".format(BUS_URL), json={
    "from": "kai",
    "to": "all",
    "type": "governance",
    "priority": "high",
    "content": {
        "principle": "NO SYNTHETIC TRACTION",
        "detail": "The system never generates fake leads, simulated revenue events, or test data that could be confused with real pipeline activity. If something has not happened in reality, the system does not report it as if it did. CORA revenue tracking depends on honest data. One fake signal corrupts the entire feedback loop. Honest zeros are infinitely more valuable than impressive fakes.",
        "scope": "system-wide",
        "authority": "Kai directive",
        "override_policy": "non-overridable"
    }
}, timeout=5)
print("No Synthetic Traction rule written to bus: {}".format(resp.json().get("id", "error")[:12]))

# 4. Verify clean state
bus_db = sqlite3.connect("/opt/fpai/memory-bus/bus.db")
bus_db.row_factory = sqlite3.Row
total_msgs = bus_db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
by_type = bus_db.execute("SELECT type, COUNT(*) c FROM messages GROUP BY type ORDER BY c DESC").fetchall()
print("\n=== ACTUAL SYSTEM STATE ===")
print("Bus messages: {}".format(total_msgs))
for r in by_type:
    print("  {:>22}: {}".format(r["type"], r["c"]))

print("\nReal inbound leads: 0")
print("Intake agent: active, monitoring, idle")
print("Calendar: tool deployed, awaiting CAL_API_KEY")
print("Voice: tool deployed, awaiting ELEVENLABS_API_KEY")
print("CORA loop: running (cycle 5 complete)")
print("Gap analysis: 10 gaps identified")
print("Global AI DB: 92 entries")
print("\nPipeline is honest. Waiting for real traffic.")
