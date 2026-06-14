#!/usr/bin/env python3
"""Tier 1: Reflection — Local Ollama analyzes state every 30 min. Zero API cost."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PULSE_DIR = Path("/opt/fpai/pulse")
STATE_FILE = PULSE_DIR / "state.json"
TRAJECTORY = PULSE_DIR / "trajectory.json"
REFLECTIONS_DIR = PULSE_DIR / "reflections"
ESCALATION_FILE = PULSE_DIR / "escalations.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}

def ollama_generate(prompt, max_tokens=300):
    """Call local Ollama. Returns empty string on failure."""
    try:
        r = subprocess.run(
            ["curl", "-sf", OLLAMA_URL, "-d", json.dumps({
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.3},
            })],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            return data.get("response", "").strip()
    except Exception:
        pass
    return ""

def build_analysis_prompt(state, trajectory):
    """Build a structured prompt for the local model to analyze."""
    now = datetime.now(timezone.utc)
    services = state.get("services", {})
    up_list = [n for n, s in services.items() if s.get("up")]
    down_list = [n for n, s in services.items() if not s.get("up")]
    changes = state.get("changes", [])
    health = state.get("health_score", 0)
    mem = state.get("system", {}).get("memory", {})
    disk = state.get("system", {}).get("disk", {})
    adam = state.get("adam", {})
    fresh = state.get("freshness", {})

    goals = trajectory.get("goals", [])
    goals_text = "\n".join(
        f"  - {g['description']} (progress: {g['progress']}%, status: {g['status']})"
        for g in goals
    )
    blockers = trajectory.get("blockers", [])
    blockers_text = "\n".join(f"  - {b}" for b in blockers) if blockers else "  None"

    # Read latest scout if exists
    scout_file = f"/opt/fpai/openclaw/workspace/memory/daily-scout-{now.strftime('%Y-%m-%d')}.md"
    scout_summary = ""
    if os.path.exists(scout_file):
        try:
            content = Path(scout_file).read_text()[:500]
            scout_summary = f"\nToday's scout highlights: {content[:300]}"
        except Exception:
            pass

    prompt = f"""You are a system monitor. Analyze this state and output EXACTLY this format:

STATUS: [HEALTHY/DEGRADED/CRITICAL]
SUMMARY: [one sentence]
TREND: [IMPROVING/STABLE/DECLINING]
ACTION: [NONE/MONITOR/ESCALATE]
REASON: [one sentence if ACTION is not NONE]

System state at {now.strftime('%Y-%m-%d %H:%M UTC')}:
- Health score: {health}/100
- Services up: {', '.join(up_list) if up_list else 'NONE'}
- Services down: {', '.join(down_list) if down_list else 'none'}
- Changes since last check: {', '.join(changes) if changes else 'none'}
- Memory: {mem.get('used_gb', 0)}GB / {mem.get('total_gb', 0)}GB
- Disk: {disk.get('used_gb', 0)}GB / {disk.get('total_gb', 0)}GB
- Adam last active: {adam.get('session_age_min', -1)} min ago ({adam.get('session_messages', 0)} messages)
- Gateway errors today: {adam.get('gateway_errors_today', 0)}
- Memory.md age: {fresh.get('memory_md_age_hours', -1)} hours
- Scout ran today: {fresh.get('scout_ran_today', False)}

Goals:
{goals_text}

Blockers:
{blockers_text}
{scout_summary}

Output the 5-line analysis now:"""

    return prompt

def parse_reflection(response):
    """Parse the structured response from local model."""
    result = {
        "status": "UNKNOWN",
        "summary": "",
        "trend": "UNKNOWN",
        "action": "NONE",
        "reason": "",
    }
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("STATUS:"):
            result["status"] = line.split(":", 1)[1].strip()
        elif line.startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
        elif line.startswith("TREND:"):
            result["trend"] = line.split(":", 1)[1].strip()
        elif line.startswith("ACTION:"):
            result["action"] = line.split(":", 1)[1].strip()
        elif line.startswith("REASON:"):
            result["reason"] = line.split(":", 1)[1].strip()
    return result

def append_reflection(reflection, state):
    """Append to today's reflection log."""
    now = datetime.now(timezone.utc)
    REFLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = REFLECTIONS_DIR / f"{now.strftime('%Y-%m-%d')}.md"

    entry = (
        f"\n### {now.strftime('%H:%M UTC')}\n"
        f"- **Health:** {state.get('health_score', 0)}/100 | "
        f"**Status:** {reflection['status']} | "
        f"**Trend:** {reflection['trend']}\n"
        f"- **Summary:** {reflection['summary']}\n"
    )
    if reflection["action"] != "NONE":
        entry += f"- **Action:** {reflection['action']} — {reflection['reason']}\n"

    if not log_file.exists():
        header = f"# Pulse Reflections — {now.strftime('%Y-%m-%d')}\n"
        log_file.write_text(header)

    with open(log_file, "a") as f:
        f.write(entry)

def check_escalation(reflection, state):
    """Decide if we need to escalate to Tier 2 (Claude)."""
    reasons = []

    if state.get("needs_escalation"):
        reasons.append("Critical service down or health < 50")

    if "ESCALATE" in reflection.get("action", "").upper():
        reasons.append(f"Local AI recommended: {reflection.get('reason', '')}")

    if state.get("health_score", 100) < 40:
        reasons.append(f"Health critically low: {state['health_score']}")

    memory_age = state.get("freshness", {}).get("memory_md_age_hours", 0)
    if memory_age > 48:
        reasons.append(f"Memory.md is {memory_age:.0f}h stale")

    return reasons

def queue_escalation(reasons, reflection, state):
    """Add to escalation queue for Tier 2 to pick up."""
    now = datetime.now(timezone.utc)

    escalations = []
    if ESCALATION_FILE.exists():
        try:
            escalations = json.loads(ESCALATION_FILE.read_text())
        except Exception:
            escalations = []

    escalations.append({
        "timestamp": now.isoformat(),
        "reasons": reasons,
        "health_score": state.get("health_score", 0),
        "reflection": reflection,
        "handled": False,
    })

    # Keep only last 50 escalations
    escalations = escalations[-50:]
    ESCALATION_FILE.write_text(json.dumps(escalations, indent=2))

def main():
    state = load_json(STATE_FILE)
    if not state:
        print("[REFLECT] No state.json found. Run heartbeat.py first.")
        sys.exit(1)

    trajectory = load_json(TRAJECTORY)

    prompt = build_analysis_prompt(state, trajectory)
    raw_response = ollama_generate(prompt)

    if not raw_response:
        print("[REFLECT] Ollama unavailable — using rule-based fallback")
        reflection = {
            "status": "DEGRADED" if state.get("health_score", 0) < 70 else "HEALTHY",
            "summary": f"Health {state.get('health_score', 0)}/100, {state.get('services_summary', 'unknown')}",
            "trend": "STABLE",
            "action": "ESCALATE" if state.get("needs_escalation") else "NONE",
            "reason": "Escalation flag set by heartbeat" if state.get("needs_escalation") else "",
        }
    else:
        reflection = parse_reflection(raw_response)

    append_reflection(reflection, state)

    escalation_reasons = check_escalation(reflection, state)
    if escalation_reasons:
        queue_escalation(escalation_reasons, reflection, state)
        print(f"[REFLECT] {reflection['status']} | {reflection['summary']} | ESCALATING: {'; '.join(escalation_reasons)}")
    else:
        print(f"[REFLECT] {reflection['status']} | {reflection['summary']} | {reflection['trend']}")

if __name__ == "__main__":
    main()
