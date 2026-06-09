#!/usr/bin/env python3
"""Daily analytics aggregator — pushes score page stats to the bus for CORA.
Runs as a daily cron/timer. Reads from the analytics.db on primary,
writes summary to bus.db on local machine.
"""

import json
import sqlite3
import os
import requests
from datetime import datetime, timezone

ANALYTICS_DB = "/opt/fpai/leads/analytics.db"
LEADS_DB = "/opt/fpai/leads/leads.db"
BUS_DB = "/opt/fpai/memory-bus/bus.db"

def get_daily_analytics():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stats = {"date": today, "events": {}}

    if os.path.exists(ANALYTICS_DB):
        db = sqlite3.connect(ANALYTICS_DB)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT event, COUNT(*) as cnt FROM page_analytics WHERE created_at LIKE ? GROUP BY event",
            (today + "%",)
        ).fetchall()
        for r in rows:
            stats["events"][r["event"]] = r["cnt"]

    if os.path.exists(LEADS_DB):
        db = sqlite3.connect(LEADS_DB)
        today_leads = db.execute(
            "SELECT COUNT(*) FROM leads WHERE created_at LIKE ?",
            (today + "%",)
        ).fetchone()[0]
        stats["new_leads_today"] = today_leads

    return stats


def write_to_bus(stats):
    if not os.path.exists(BUS_DB):
        print("Bus DB not found at", BUS_DB)
        return False

    db = sqlite3.connect(BUS_DB)
    now = datetime.now(timezone.utc).isoformat()

    db.execute(
        """INSERT INTO messages (sender, recipient, thread, content, priority, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "analytics",
            "cora",
            "score_page_analytics",
            json.dumps(stats),
            "normal",
            now,
        )
    )
    db.commit()
    print("Written to bus:", json.dumps(stats, indent=2))
    return True


if __name__ == "__main__":
    stats = get_daily_analytics()
    print("Daily analytics:", json.dumps(stats, indent=2))
    write_to_bus(stats)
