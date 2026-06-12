#!/usr/bin/env python3
"""Patch intake agent to also pull leads from the primary server's score page API."""

f = "/opt/fpai/leads/intake-agent.py"
with open(f) as fh:
    code = fh.read()

if "sync_from_primary" in code:
    print("Already patched")
    exit(0)

sync_func = '''
def sync_from_primary():
    """Pull new leads captured on the primary server (score page) into local DB."""
    try:
        r = requests.get("https://fullpotential.ai/api/leads/pending", timeout=10)
        if r.status_code != 200:
            return
        data = r.json()
        leads = data.get("leads", [])
        if not leads:
            return
        db = get_db()
        synced_ids = []
        for lead in leads:
            email = (lead.get("email") or "").lower().strip()
            if not email:
                continue
            existing = db.execute("SELECT id FROM leads WHERE email = ?", (email,)).fetchone()
            if existing:
                synced_ids.append(lead["id"])
                continue
            now = lead.get("created_at", "")
            try:
                qa = lead.get("qualifying_answers")
                if isinstance(qa, str):
                    pass
                elif qa:
                    qa = json.dumps(qa)
                db.execute(
                    """INSERT OR IGNORE INTO leads
                       (name, email, source, message, qualifying_answers, raw_data, status, score, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, 'new', 30, ?, ?)""",
                    (
                        lead.get("name", ""),
                        email,
                        lead.get("source", "fullpotential.ai/score"),
                        lead.get("message", ""),
                        qa,
                        lead.get("raw_data", "{}"),
                        now, now,
                    )
                )
                db.commit()
                synced_ids.append(lead["id"])
                log.info(f"Synced lead from primary: {email}")
            except Exception as e:
                log.error(f"Failed to sync {email}: {e}")
        if synced_ids:
            try:
                requests.post(
                    "https://fullpotential.ai/api/leads/synced",
                    json={"ids": synced_ids},
                    timeout=10,
                )
            except Exception:
                pass
        db.close()
    except Exception as e:
        log.error(f"Primary sync error: {e}")

'''

# Insert sync function before get_new_leads
code = code.replace("def get_new_leads():", sync_func + "\ndef get_new_leads():")

# Add sync call in the main loop, before get_new_leads
code = code.replace(
    "            leads = get_new_leads()",
    "            sync_from_primary()\n            leads = get_new_leads()"
)

with open(f, "w") as fh:
    fh.write(code)

print("Intake agent patched with primary server sync")
