#!/usr/bin/env python3
"""Patch ad-monitor.py to also pull score page analytics and write to bus."""

f = "/opt/fpai/ad-monitor/ad-monitor.py"
with open(f) as fh:
    code = fh.read()

if "score_page_analytics" in code:
    print("Already patched")
    exit(0)

# Add the analytics pull function before run_monitor
patch_func = '''
def pull_score_page_analytics():
    """Pull score page analytics from primary server and write to bus."""
    import requests as req
    try:
        r = req.get("https://fullpotential.ai/api/leads/analytics/daily", timeout=10)
        if r.status_code == 200:
            analytics = r.json()
            log(f"Score page analytics: {analytics}")

            # Also get lead stats
            r2 = req.get("https://fullpotential.ai/api/leads/stats", timeout=10)
            if r2.status_code == 200:
                lead_stats = r2.json()
                analytics["lead_stats"] = lead_stats

            # Write to bus
            db = sqlite3.connect(BUS_DB)
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                "INSERT INTO messages (sender, recipient, thread, content, priority, timestamp) VALUES (?,?,?,?,?,?)",
                ("analytics", "cora", "score_page_analytics", json.dumps(analytics), "normal", now)
            )
            db.commit()
            log("Score page analytics written to bus")
            return analytics
        else:
            log(f"Failed to pull analytics: HTTP {r.status_code}")
    except Exception as e:
        log(f"Analytics pull error: {e}")
    return None

'''

# Insert before run_monitor function
code = code.replace("def run_monitor():", patch_func + "def run_monitor():")

# Add the call inside run_monitor, after the main logic
code = code.replace(
    '    log("Ad Monitor daily check complete")',
    '    # Pull score page analytics\n    pull_score_page_analytics()\n\n    log("Ad Monitor daily check complete")'
)

with open(f, "w") as fh:
    fh.write(code)

print("Ad monitor patched with score page analytics pull")
