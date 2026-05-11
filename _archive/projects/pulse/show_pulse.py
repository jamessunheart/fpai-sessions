#!/usr/bin/env python3
"""Show pulse state in a human-readable format. Zero cost."""

import json
import os
from pathlib import Path

STATE_FILE = Path("/opt/fpai/pulse/state.json")
TRAJ_FILE = Path("/opt/fpai/pulse/trajectory.json")
ESC_FILE = Path("/opt/fpai/pulse/escalations.json")

def main():
    state = json.loads(STATE_FILE.read_text())
    traj = json.loads(TRAJ_FILE.read_text())

    ts = state["timestamp"][:19].replace("T", " ")
    hs = state["health_score"]
    svc = state["services_summary"]
    mem = state["system"]["memory"]
    disk = state["system"]["disk"]
    adam = state["adam"]
    fresh = state["freshness"]
    changes = state.get("changes", [])

    mem_used = mem["used_gb"]
    mem_total = mem["total_gb"]
    disk_used = disk["used_gb"]
    disk_total = disk["total_gb"]
    sess_msgs = adam["session_messages"]
    sess_age = adam["session_age_min"]
    errs = adam["gateway_errors_today"]
    mem_age = fresh["memory_md_age_hours"]
    scout = fresh["scout_ran_today"]

    print(f"Health: {hs}/100  |  Services: {svc}  |  Updated: {ts} UTC")
    print(f"Memory: {mem_used}GB / {mem_total}GB  |  Disk: {disk_used}GB / {disk_total}GB")
    print(f"Adam: {sess_msgs} msgs, last active {sess_age}m ago  |  Errors today: {errs}")
    print(f"Freshness: MEMORY.md {mem_age}h old  |  Scout today: {scout}")

    if changes:
        print(f"Changes: {' | '.join(changes)}")

    print()
    print("Goals:")
    for g in traj.get("goals", []):
        progress = g["progress"]
        desc = g["description"]
        status = g["status"]
        bar = "\u2588" * (progress // 10) + "\u2591" * (10 - progress // 10)
        print(f"  [{bar}] {progress:3d}% {desc} ({status})")

    blockers = traj.get("blockers", [])
    if blockers:
        print()
        print("Blockers:")
        for b in blockers:
            print(f"  - {b}")

    if ESC_FILE.exists():
        esc = json.loads(ESC_FILE.read_text())
        pending = [e for e in esc if not e.get("handled")]
        if pending:
            print()
            print(f"WARNING: {len(pending)} pending escalation(s)")

if __name__ == "__main__":
    main()
