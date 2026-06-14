#!/usr/bin/env python3
"""Mission monitor that surfaces newly created missions to local alerts."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

MISSION_DIR = Path("/opt/fpai/orchestration/missions/open")
STATE_PATH = Path("/var/log/fpai/mission_state.json")
ALERT_LOG_PATH = Path("/var/log/fpai/mission_alerts.log")
ALERT_MD_PATH = Path("/opt/fpai/docs/status/ALERTS.md")
CONSTITUTION_PATH = Path("/opt/fpai/core/knowledge/CONSTITUTION.md")
FEED_SCRIPT = Path("/opt/fpai/orchestration/tools/generate_mission_feed.py")
SLACK_WEBHOOK = os.environ.get("FPAI_SLACK_WEBHOOK")  # Placeholder for future use


def load_state() -> Dict[str, List[str]]:
    if not STATE_PATH.exists():
        return {"missions": []}
    try:
        return json.loads(STATE_PATH.read_text())
    except json.JSONDecodeError:
        return {"missions": []}


def save_state(missions: List[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"missions": missions}, indent=2))


def prepend_alert(message: str) -> None:
    ALERT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = ALERT_MD_PATH.read_text() if ALERT_MD_PATH.exists() else ""
    content = f"{message}\n\n"
    if existing:
        content += existing
    ALERT_MD_PATH.write_text(content)


def log_alert(message: str) -> None:
    ALERT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG_PATH.open("a") as fh:
        fh.write(f"{message}\n")


def notify_slack_placeholder(message: str) -> None:
    # Placeholder hook for future Slack integration once webhook is available.
    if not SLACK_WEBHOOK:
        return
    # Example implementation (disabled):
    # import requests
    # requests.post(SLACK_WEBHOOK, json={"text": message}, timeout=5)


def load_constitution_principles() -> List[str]:
    if not CONSTITUTION_PATH.exists():
        return []
    principles: List[str] = []
    for line in CONSTITUTION_PATH.read_text().splitlines():
        stripped = line.strip()
        if not stripped or not stripped[0].isdigit():
            continue
        if "**" not in stripped:
            continue
        first = stripped.find("**")
        second = stripped.find("**", first + 2)
        if second == -1:
            continue
        principles.append(stripped[first + 2 : second])
    return principles


def constitution_notes(principles: List[str]) -> List[str]:
    if not principles:
        return ["    ↳ Constitutional Check: Constitution document missing — please verify `/opt/fpai/core/knowledge/CONSTITUTION.md`. "]
    return [f"    ↳ Constitutional Check: Checking alignment with: {principle}" for principle in principles]


def main() -> None:
    if not MISSION_DIR.exists():
        return

    known = set(load_state().get("missions", []))
    current = sorted(p.name for p in MISSION_DIR.glob("*.md"))
    new_missions = [name for name in current if name not in known]

    if not new_missions:
        save_state(current)
        return

    principles = load_constitution_principles()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    for mission in new_missions:
        entry = f"🚨 [{timestamp}] NEW MISSION: {mission}"
        notes = constitution_notes(principles)
        block = "\n".join([entry, *notes])
        log_alert(block)
        prepend_alert(block)
        notify_slack_placeholder(block)

    save_state(current)
    refresh_mission_feed()


def refresh_mission_feed() -> None:
    if FEED_SCRIPT.exists():
        subprocess.run(["python3", str(FEED_SCRIPT)], check=False)


if __name__ == "__main__":
    main()
