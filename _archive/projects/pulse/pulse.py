#!/usr/bin/env python3
"""Pulse Orchestrator — Runs the tiered AI-to-AI communication loop.

Schedule:
  - Tier 0 (heartbeat): Every 5 minutes  — $0
  - Tier 1 (reflect):   Every 30 minutes  — $0
  - Tier 2 (think):     On escalation + 2x/day (08:00, 20:00 UTC) — ~$0.50/day
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PULSE_DIR = Path("/opt/fpai/pulse")
STATE_FILE = PULSE_DIR / "state.json"
ESCALATION_FILE = PULSE_DIR / "escalations.json"
LOCK_FILE = PULSE_DIR / "pulse.lock"
LOG_FILE = PULSE_DIR / "pulse.log"

HEARTBEAT_INTERVAL = 300     # 5 minutes
REFLECT_INTERVAL = 1800      # 30 minutes
THINK_HOURS = [8, 20]        # UTC hours for scheduled deep thinks

last_heartbeat = 0
last_reflect = 0
last_think_hour = -1

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
        # Rotate log if > 1MB
        if LOG_FILE.stat().st_size > 1_000_000:
            lines = LOG_FILE.read_text().split("\n")
            LOG_FILE.write_text("\n".join(lines[-500:]))
    except Exception:
        pass

def run_script(name, *args):
    script = PULSE_DIR / name
    try:
        r = subprocess.run(
            [sys.executable, str(script)] + list(args),
            capture_output=True, text=True, timeout=180,
            cwd=str(PULSE_DIR),
        )
        output = r.stdout.strip()
        if output:
            for line in output.split("\n"):
                log(line)
        if r.returncode != 0 and r.stderr:
            log(f"[STDERR] {r.stderr[:300]}")
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"[TIMEOUT] {name} timed out")
        return False
    except Exception as e:
        log(f"[ERROR] {name}: {e}")
        return False

def has_pending_escalations():
    if not ESCALATION_FILE.exists():
        return False
    try:
        data = json.loads(ESCALATION_FILE.read_text())
        return any(not e.get("handled") for e in data)
    except Exception:
        return False

def acquire_lock():
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            if os.path.exists(f"/proc/{pid}"):
                return False
        except Exception:
            pass
    LOCK_FILE.write_text(str(os.getpid()))
    return True

def release_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass

def main():
    global last_heartbeat, last_reflect, last_think_hour

    if not acquire_lock():
        print("Pulse already running. Exiting.")
        sys.exit(1)

    log("=== PULSE SYSTEM STARTING ===")
    log(f"Heartbeat: every {HEARTBEAT_INTERVAL}s | Reflect: every {REFLECT_INTERVAL}s | Think: {THINK_HOURS} UTC + escalations")

    try:
        while True:
            now = time.time()
            utc_now = datetime.now(timezone.utc)

            # Tier 0: Heartbeat (every 5 min)
            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                run_script("heartbeat.py")
                last_heartbeat = now

            # Tier 1: Reflect (every 30 min)
            if now - last_reflect >= REFLECT_INTERVAL:
                run_script("reflect.py")
                last_reflect = now

                # After reflection, check for escalations -> trigger Tier 2
                if has_pending_escalations():
                    log("[PULSE] Escalation detected — triggering deep think")
                    run_script("think.py", "escalation")

            # Tier 2: Scheduled deep think (2x/day)
            current_hour = utc_now.hour
            if current_hour in THINK_HOURS and current_hour != last_think_hour:
                log(f"[PULSE] Scheduled deep think ({current_hour}:00 UTC)")
                # Run fresh heartbeat + reflect first
                run_script("heartbeat.py")
                run_script("reflect.py")
                run_script("think.py", "scheduled")
                last_think_hour = current_hour

            time.sleep(30)

    except KeyboardInterrupt:
        log("=== PULSE SYSTEM STOPPED (keyboard) ===")
    finally:
        release_lock()

if __name__ == "__main__":
    main()
