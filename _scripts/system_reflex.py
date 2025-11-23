#!/usr/bin/env python3
"""
System Reflex
Reads the Nervous System (PULSE.json) and triggers automated responses (Missions).
Acts as the autonomic nervous system, maintaining homeostasis and seizing opportunity.
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# --- Configuration ---
ROOT_DIR = Path(__file__).parent.parent.absolute()
STATE_DIR = ROOT_DIR / "core/STATE"
PULSE_FILE = STATE_DIR / "PULSE.json"
MISSIONS_DIR = ROOT_DIR / "missions"
GENERATOR_SCRIPT = ROOT_DIR / "_scripts/generate_mission_spec.py"

def load_pulse():
    if not PULSE_FILE.exists():
        print("⚠️ No Pulse found. Skipping reflex.")
        return None
    try:
        with open(PULSE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error reading Pulse: {e}")
        return None

def mission_exists(title_fragment):
    """Checks if a mission with a similar title already exists to avoid spam."""
    if not MISSIONS_DIR.exists():
        return False
    for f in MISSIONS_DIR.glob("*.md"):
        if title_fragment.lower() in f.name.lower().replace("-", " "):
            return True
    return False

def trigger_mission(title, goal, security, complexity, context, deliverables, steps):
    """Calls the spec generator to spawn a new mission."""
    if mission_exists(title):
        print(f"⏸ Mission '{title}' already active. Skipping.")
        return

    print(f"⚡ TRIGGERING MISSION: {title}")
    
    cmd = [
        str(GENERATOR_SCRIPT),
        "--title", title,
        "--goal", goal,
        "--security", security,
        "--complexity", complexity,
        "--context", context,
        "--deliverables", *deliverables,
        "--steps", *steps
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to trigger mission: {e}")

def check_reflexes(pulse):
    """Evaluates state and fires reflexes."""
    
    revenue = pulse.get("revenue", {})
    missions = pulse.get("missions", {})
    timestamp = pulse.get("timestamp")
    
    # 1. SURVIVAL REFLEX: No Revenue > 24h (Simulated check, logic can be refined)
    # For v1, we just check if revenue is exactly 0 and we haven't panicked yet
    if revenue.get("total_revenue", 0) == 0:
        trigger_mission(
            title="First Sale Traffic",
            goal="Drive initial traffic to storefront to break zero revenue.",
            security="low",
            complexity="moderate",
            context="Storefront is live but revenue is $0. We need to verify the funnel works with real users.",
            deliverables=["100 Unique Visitors", "Funnel Analytics Report"],
            steps=["Post to social channels", "Share with beta testers", "Check Nginx access logs for hits"]
        )

    # 2. GROWTH REFLEX: Momentum Detected
    # If we have sales but low open missions, scale up
    if revenue.get("total_revenue", 0) > 0 and missions.get("open", 0) < 3:
        trigger_mission(
            title="Scale Ad Spend",
            goal="Amplify what is working. Increase visibility.",
            security="medium",
            complexity="complex",
            context="Revenue signal detected. System is ready for load.",
            deliverables=["Ad Campaign Plan", "Budget Allocation"],
            steps=["Analyze top traffic source", "Create creative assets", "Launch test campaign"]
        )

    # 3. MAINTENANCE REFLEX: High Workload
    if missions.get("open", 0) > 10:
        print("⚠️ High workload detected. Suppressing new growth missions.")

def main():
    print("🧠 System Reflex Active...")
    pulse = load_pulse()
    if pulse:
        check_reflexes(pulse)

if __name__ == "__main__":
    main()
