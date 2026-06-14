#!/usr/bin/env python3
"""Show trajectory in a human-readable format. Zero cost."""

import json
from pathlib import Path

TRAJ_FILE = Path("/opt/fpai/pulse/trajectory.json")

def main():
    traj = json.loads(TRAJ_FILE.read_text())

    print("GOALS:")
    for g in traj.get("goals", []):
        progress = g["progress"]
        desc = g["description"]
        status = g["status"].upper()
        bar = "\u2588" * (progress // 10) + "\u2591" * (10 - progress // 10)
        print(f"  [{bar}] {progress:3d}% [{status:8s}] {desc}")
        if g.get("updated"):
            updated = g["updated"]
            print(f"       Last updated: {updated}")

    blockers = traj.get("blockers", [])
    if blockers:
        print()
        print("BLOCKERS:")
        for b in blockers:
            print(f"  X {b}")
    else:
        print()
        print("BLOCKERS: None")

    decisions = traj.get("decisions_pending", [])
    if decisions:
        print()
        print("DECISIONS PENDING:")
        for d in decisions:
            print(f"  ? {d}")

    history = traj.get("history", [])
    if history:
        print()
        print("RECENT UPDATES:")
        for h in history[-5:]:
            ts = h.get("timestamp", "")[:16]
            update = h.get("update", "")
            print(f"  [{ts}] {update}")

    lt = traj.get("last_deep_think", "")
    lh = traj.get("last_human_contact", "")
    print()
    lt_display = lt[:16] if lt else "never"
    lh_display = lh[:16] if lh else "never"
    print(f"Last deep think: {lt_display}")
    print(f"Last human contact: {lh_display}")

if __name__ == "__main__":
    main()
