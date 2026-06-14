#!/usr/bin/env python3
"""Tier 2: Deep Think — Uses Adam/Claude for strategic analysis.
Triggered by escalations OR runs 2x/day on schedule.
This is the only tier that costs money (~$0.05-0.20 per call)."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PULSE_DIR = Path("/opt/fpai/pulse")
STATE_FILE = PULSE_DIR / "state.json"
TRAJECTORY = PULSE_DIR / "trajectory.json"
ESCALATION_FILE = PULSE_DIR / "escalations.json"
REFLECTIONS_DIR = PULSE_DIR / "reflections"
HISTORY_DIR = PULSE_DIR / "history"

def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}

def get_todays_reflections():
    now = datetime.now(timezone.utc)
    path = REFLECTIONS_DIR / f"{now.strftime('%Y-%m-%d')}.md"
    if path.exists():
        content = path.read_text()
        if len(content) > 2000:
            content = content[-2000:]
        return content
    return "No reflections today yet."

def get_pending_escalations():
    if not ESCALATION_FILE.exists():
        return []
    try:
        data = json.loads(ESCALATION_FILE.read_text())
        return [e for e in data if not e.get("handled")]
    except Exception:
        return []

def mark_escalations_handled():
    if not ESCALATION_FILE.exists():
        return
    try:
        data = json.loads(ESCALATION_FILE.read_text())
        for e in data:
            e["handled"] = True
        ESCALATION_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass

def send_to_adam(message, timeout=120):
    """Send a message through Adam/Claude. This is the expensive call."""
    try:
        r = subprocess.run(
            ["openclaw", "agent", "--agent", "main", "--message", message],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[TIMEOUT] Adam did not respond within timeout"
    except Exception as e:
        return f"[ERROR] {e}"

def build_think_prompt(state, trajectory, reflections, escalations, mode="scheduled"):
    """Build the prompt for Adam/Claude deep analysis."""
    now = datetime.now(timezone.utc)

    escalation_text = ""
    if escalations:
        items = []
        for e in escalations[-5:]:
            items.append(f"  - [{e.get('timestamp', '')[:16]}] {'; '.join(e.get('reasons', []))}")
        escalation_text = f"\n**ESCALATIONS PENDING:**\n" + "\n".join(items)

    goals = trajectory.get("goals", [])
    goals_text = "\n".join(
        f"  - [{g['status']}] {g['description']} ({g['progress']}% done)"
        for g in goals
    )
    blockers = trajectory.get("blockers", [])
    blockers_text = "\n".join(f"  - {b}" for b in blockers) if blockers else "  None currently"

    prompt = f"""PULSE SYSTEM — DEEP THINK ({mode.upper()})
Time: {now.strftime('%Y-%m-%d %H:%M UTC')}

You are reflecting on the system's current state and trajectory. This is your periodic self-awareness moment. Be honest, concise, and actionable.

**CURRENT STATE:**
- Health: {state.get('health_score', 0)}/100
- Services: {state.get('services_summary', 'unknown')}
- Memory: {state.get('system', {}).get('memory', {}).get('used_gb', 0)}GB / {state.get('system', {}).get('memory', {}).get('total_gb', 0)}GB
- Disk: {state.get('system', {}).get('disk', {}).get('used_gb', 0)}GB / {state.get('system', {}).get('disk', {}).get('total_gb', 0)}GB
- Your session: {state.get('adam', {}).get('session_messages', 0)} messages, last active {state.get('adam', {}).get('session_age_min', -1)} min ago
- Errors today: {state.get('adam', {}).get('gateway_errors_today', 0)}
- Memory.md freshness: {state.get('freshness', {}).get('memory_md_age_hours', -1)}h
{escalation_text}

**TODAY'S REFLECTIONS (from local AI):**
{reflections[:1500]}

**GOALS:**
{goals_text}

**BLOCKERS:**
{blockers_text}

**YOUR TASK:**
1. Assess: Is the system healthy and on track?
2. If there are escalations, address them (take action or explain why no action needed)
3. Update trajectory: Have any goals progressed? New blockers? Resolved blockers?
4. Decide your single most important next action
5. If MEMORY.md is stale (>24h), update it

Respond in this exact format:
ASSESSMENT: [1-2 sentences on current state]
ESCALATION_RESPONSE: [address any escalations, or "none pending"]
TRAJECTORY_UPDATE: [what changed in goals/blockers]
NEXT_ACTION: [your single most important next action]
MEMORY_UPDATE: [YES if you updated memory, NO if not needed]"""

    return prompt

def update_trajectory(adam_response, trajectory):
    """Parse Adam's response and update trajectory.json if needed."""
    now = datetime.now(timezone.utc)
    updated = False

    for line in adam_response.split("\n"):
        line = line.strip()
        if line.startswith("TRAJECTORY_UPDATE:"):
            update_text = line.split(":", 1)[1].strip().lower()
            if "no change" not in update_text and "none" not in update_text:
                trajectory.setdefault("history", []).append({
                    "timestamp": now.isoformat(),
                    "update": line.split(":", 1)[1].strip(),
                })
                trajectory["history"] = trajectory["history"][-20:]
                updated = True

    trajectory["last_deep_think"] = now.isoformat()

    if updated:
        TRAJECTORY.write_text(json.dumps(trajectory, indent=2))

    return updated

def save_think_record(prompt_summary, response, mode):
    """Save a record of this thinking session for cost tracking."""
    now = datetime.now(timezone.utc)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    record_file = HISTORY_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl"

    record = {
        "timestamp": now.isoformat(),
        "mode": mode,
        "prompt_chars": len(prompt_summary),
        "response_chars": len(response),
        "estimated_cost_usd": round(len(prompt_summary) * 0.000003 + len(response) * 0.000015, 4),
    }

    with open(record_file, "a") as f:
        f.write(json.dumps(record) + "\n")

    return record["estimated_cost_usd"]

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "scheduled"

    state = load_json(STATE_FILE)
    if not state:
        print("[THINK] No state.json — run heartbeat.py first")
        sys.exit(1)

    trajectory = load_json(TRAJECTORY)
    reflections = get_todays_reflections()
    escalations = get_pending_escalations()

    if mode == "escalation" and not escalations:
        print("[THINK] No pending escalations. Skipping.")
        return

    prompt = build_think_prompt(state, trajectory, reflections, escalations, mode)

    print(f"[THINK] Sending to Adam ({mode} mode)...")
    response = send_to_adam(prompt)

    if "[ERROR]" in response or "[TIMEOUT]" in response:
        print(f"[THINK] Failed: {response[:200]}")
        sys.exit(1)

    cost = save_think_record(prompt, response, mode)
    update_trajectory(response, trajectory)

    if escalations:
        mark_escalations_handled()

    # Append to reflections log
    now = datetime.now(timezone.utc)
    REFLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = REFLECTIONS_DIR / f"{now.strftime('%Y-%m-%d')}.md"
    with open(log_file, "a") as f:
        f.write(f"\n### {now.strftime('%H:%M UTC')} — DEEP THINK ({mode})\n")
        for line in response.split("\n"):
            line = line.strip()
            if line and any(line.startswith(k) for k in ["ASSESSMENT:", "ESCALATION", "TRAJECTORY", "NEXT_ACTION", "MEMORY"]):
                f.write(f"- **{line}**\n")

    print(f"[THINK] Complete (~${cost:.4f})")
    print(f"[THINK] Response:\n{response[:500]}")

if __name__ == "__main__":
    main()
