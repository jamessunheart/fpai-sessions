#!/usr/bin/env python3
"""Tier 0: Heartbeat — Collects system state every 5 minutes. Zero LLM cost."""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

PULSE_DIR = Path("/opt/fpai/pulse")
STATE_FILE = PULSE_DIR / "state.json"
PREV_STATE = PULSE_DIR / "state.prev.json"
TRAJECTORY = PULSE_DIR / "trajectory.json"

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""

def port_up(port):
    return run(f"ss -tlnp | grep -q :{port} && echo 1") == "1"

def init_trajectory():
    if TRAJECTORY.exists():
        return
    data = {
        "goals": [
            {"id": "revenue", "description": "Generate first revenue via consulting/BaaS", "status": "active", "progress": 0, "updated": ""},
            {"id": "self_sustain", "description": "System maintains itself without daily human intervention", "status": "active", "progress": 20, "updated": ""},
            {"id": "memory_current", "description": "Keep memory and state files current within 24hrs", "status": "active", "progress": 80, "updated": ""},
        ],
        "blockers": [],
        "decisions_pending": [],
        "last_human_contact": "",
        "last_deep_think": "",
    }
    TRAJECTORY.write_text(json.dumps(data, indent=2))

def collect_state():
    now = datetime.now(timezone.utc)

    # Service health checks
    svc_checks = {
        "openclaw_gateway": {"port": 18789, "critical": True},
        "metaclaw": {"port": 30000, "critical": True},
        "shared_brain": {"port": 8770, "critical": False},
        "ai_brain": {"port": 8101, "critical": False},
        "data_service": {"port": 8125, "critical": False},
        "sparket": {"port": 8711, "critical": False},
        "code_server": {"port": 8443, "critical": False},
        "consciousness_api": {"port": 8130, "critical": False},
    }
    services = {}
    for name, cfg in svc_checks.items():
        services[name] = {
            "up": port_up(cfg["port"]),
            "port": cfg["port"],
            "critical": cfg["critical"],
        }

    # System metrics
    try:
        mem_raw = run("free -b | grep Mem | awk '{print $2, $3, $7}'").split()
        mem = {
            "total_gb": round(int(mem_raw[0]) / 1e9, 1),
            "used_gb": round(int(mem_raw[1]) / 1e9, 1),
            "avail_gb": round(int(mem_raw[2]) / 1e9, 1),
        }
    except Exception:
        mem = {"total_gb": 0, "used_gb": 0, "avail_gb": 0}

    try:
        disk_raw = run("df -B1 / | tail -1 | awk '{print $2, $3, $4}'").split()
        disk = {
            "total_gb": round(int(disk_raw[0]) / 1e9, 1),
            "used_gb": round(int(disk_raw[1]) / 1e9, 1),
            "free_gb": round(int(disk_raw[2]) / 1e9, 1),
        }
    except Exception:
        disk = {"total_gb": 0, "used_gb": 0, "free_gb": 0}

    load_raw = run("cat /proc/loadavg").split()[:3]
    load = {
        "1m": float(load_raw[0]) if load_raw else 0,
        "5m": float(load_raw[1]) if len(load_raw) > 1 else 0,
        "15m": float(load_raw[2]) if len(load_raw) > 2 else 0,
    }

    # Adam session activity
    latest_session = run("ls -t /root/.openclaw/agents/main/sessions/*.jsonl 2>/dev/null | head -1")
    session_age_min = -1
    session_messages = 0
    if latest_session:
        try:
            mtime = os.path.getmtime(latest_session)
            session_age_min = int((time.time() - mtime) / 60)
            session_messages = int(run(f"wc -l < {latest_session}") or "0")
        except Exception:
            pass

    # Gateway errors today
    log_file = f"/tmp/openclaw/openclaw-{now.strftime('%Y-%m-%d')}.log"
    error_count = int(run(f"grep -c ERROR {log_file} 2>/dev/null") or "0")

    # API usage stats
    api_error_count = 0
    api_last_used = 0
    try:
        with open("/root/.openclaw/agents/main/agent/auth-profiles.json") as f:
            ap = json.load(f)
        usage = ap.get("usageStats", {}).get("anthropic:manual", {})
        api_last_used = usage.get("lastUsed", 0)
        api_error_count = usage.get("errorCount", 0)
    except Exception:
        pass

    # Load previous state for delta detection
    prev = {}
    if PREV_STATE.exists():
        try:
            prev = json.loads(PREV_STATE.read_text())
        except Exception:
            pass

    # Health score (0-100)
    critical_up = sum(1 for s in services.values() if s["critical"] and s["up"])
    critical_total = sum(1 for s in services.values() if s["critical"])
    all_up = sum(1 for s in services.values() if s["up"])
    all_total = len(services)

    health_score = 0
    if critical_total > 0:
        health_score += (critical_up / critical_total) * 60
    if all_total > 0:
        health_score += (all_up / all_total) * 20
    if 0 <= session_age_min < 60:
        health_score += 10
    if error_count < 10:
        health_score += 10
    health_score = min(100, int(health_score))

    # Detect changes
    changes = []
    prev_services = prev.get("services", {})
    for name, svc in services.items():
        prev_up = prev_services.get(name, {}).get("up")
        if prev_up is not None and prev_up != svc["up"]:
            action = "came UP" if svc["up"] else "went DOWN"
            changes.append(f"{name} {action}")

    prev_health = prev.get("health_score", health_score)
    if abs(health_score - prev_health) >= 10:
        changes.append(f"health changed {prev_health} -> {health_score}")

    # Check if escalation needed
    critical_down = [c for c in changes if "DOWN" in c]
    needs_escalation = bool(critical_down) or health_score < 50

    # Scout status
    scout_file = f"/opt/fpai/openclaw/workspace/memory/daily-scout-{now.strftime('%Y-%m-%d')}.md"
    scout_ran_today = os.path.exists(scout_file)

    # Memory.md freshness
    memory_md = "/opt/fpai/openclaw/workspace/MEMORY.md"
    memory_age_hours = -1
    if os.path.exists(memory_md):
        memory_age_hours = round((time.time() - os.path.getmtime(memory_md)) / 3600, 1)

    state = {
        "timestamp": now.isoformat(),
        "health_score": health_score,
        "services": services,
        "services_summary": f"{all_up}/{all_total} up ({critical_up}/{critical_total} critical)",
        "system": {"memory": mem, "disk": disk, "load": load},
        "adam": {
            "session_age_min": session_age_min,
            "session_messages": session_messages,
            "gateway_errors_today": error_count,
            "api_error_count": api_error_count,
        },
        "freshness": {
            "memory_md_age_hours": memory_age_hours,
            "scout_ran_today": scout_ran_today,
        },
        "changes": changes,
        "needs_escalation": needs_escalation,
    }

    return state

def main():
    init_trajectory()

    if STATE_FILE.exists():
        PREV_STATE.write_text(STATE_FILE.read_text())

    state = collect_state()
    STATE_FILE.write_text(json.dumps(state, indent=2))

    ts = state["timestamp"][:16]
    hs = state["health_score"]
    svc = state["services_summary"]
    changes = state["changes"]
    esc = " [ESCALATION NEEDED]" if state["needs_escalation"] else ""

    if changes:
        print(f"[PULSE] {ts} health={hs} {svc} changes: {' | '.join(changes)}{esc}")
    else:
        print(f"[PULSE] {ts} health={hs} {svc} stable{esc}")

if __name__ == "__main__":
    main()
