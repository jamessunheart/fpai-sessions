#!/usr/bin/env python3
"""Show pulse cost tracking."""

import json
import os
import glob
from datetime import datetime, timezone

HISTORY_DIR = "/opt/fpai/pulse/history"

def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = 0
    today_total = 0

    files = sorted(glob.glob(os.path.join(HISTORY_DIR, "*.jsonl")))
    if not files:
        print("No cost records yet.")
        return

    for f in files:
        day = os.path.basename(f).replace(".jsonl", "")
        day_cost = 0
        count = 0
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    day_cost += r.get("estimated_cost_usd", 0)
                    count += 1
                except Exception:
                    pass
        total += day_cost
        if day == today:
            today_total = day_cost
        print(f"  {day}: ${day_cost:.4f} ({count} thinks)")

    print()
    print(f"Today: ${today_total:.4f}")
    print(f"All time: ${total:.4f}")

if __name__ == "__main__":
    main()
