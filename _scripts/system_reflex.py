#!/usr/bin/env python3
"""
System Reflex
Reads the Nervous System (PULSE.json + ASSEMBLY.json) and triggers automated responses (Missions).
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
ASSEMBLY_FILE = STATE_DIR / "ASSEMBLY.json"
MISSIONS_DIR = ROOT_DIR / "missions"
GENERATOR_SCRIPT = ROOT_DIR / "_scripts/generate_mission_spec.py"

def load_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return {}

def mission_exists(title_fragment):
    """Checks if a mission with this title already exists (active or completed)."""
    if not MISSIONS_DIR.exists():
        return False
    for file in MISSIONS_DIR.glob("*.md"):
        if title_fragment.lower().replace(" ", "-") in file.name.lower():
            return True
    return False

def trigger_mission(title, goal, security, complexity, context, deliverables, steps):
    """Calls the generator script to create a new mission."""
    if mission_exists(title):
        print(f"⏭️  Mission '{title}' already exists. Skipping.")
        return

    print(f"⚡ TRIGGERING REFLEX: {title}")
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
        print(f"✅ Mission Created: {title}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to trigger mission: {e}")

def check_assembly_health(assembly):
    """Checks for blockages in the assembly line."""
    
    # 1. TRAFFIC BLINDNESS
    if assembly.get("traffic", {}).get("status") == "⚪ Unknown":
        trigger_mission(
            title="Install Traffic Probe",
            goal="Enable visibility into inbound traffic sources.",
            security="low",
            complexity="simple",
            context="The assembly line is blind to traffic. We need to install a tracker (PostHog/Google Analytics/Log Analyzer).",
            deliverables=["Analytics Script Installed", "Dashboard Link"],
            steps=["Select analytics provider", "Add script to layout.tsx", "Verify data flow"]
        )

    # 2. STOREFRONT DOWN
    storefront_status = assembly.get("storefront", {}).get("status", "")
    if "🔴" in storefront_status or "Error" in storefront_status:
         trigger_mission(
            title="Emergency Storefront Repair",
            goal="Restore public access to fullpotential.com immediately.",
            security="high",
            complexity="moderate",
            context=f"Storefront reported status: {storefront_status}. Traffic is hitting a wall.",
            deliverables=["Root Cause Analysis", "Fix Deployed", "200 OK Verification"],
            steps=["Check Nginx logs", "Check Next.js service status", "Restart services", "Verify with curl"]
        )

    # 3. FULFILLMENT BLOCKED
    fulfillment = assembly.get("fulfillment", {})
    if "Blocked" in fulfillment.get("status", ""):
        trigger_mission(
            title="Unblock Fulfillment SMTP",
            goal="Restore email delivery capabilities.",
            security="medium",
            complexity="moderate",
            context=f"Blocker detected: {fulfillment.get('blocker')}. Customers are paying but not receiving products.",
            deliverables=["SMTP Credentials Injected", "Test Email Sent"],
            steps=["Obtain SMTP Connection String", "Update /etc/fpai/env file", "Restart Service", "Run Test Order"]
        )

def check_business_reflexes(pulse):
    """Evaluates business state (Revenue/Missions)."""
    revenue = pulse.get("revenue", {})
    missions = pulse.get("missions", {})
    
    # 1. SURVIVAL REFLEX: No Revenue > 24h
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

def main():
    print("🧠 System Reflex Active...")
    
    # Load States
    pulse = load_json(PULSE_FILE)
    assembly = load_json(ASSEMBLY_FILE)
    
    # Check Reflexes
    if assembly:
        check_assembly_health(assembly)
    
    if pulse:
        check_business_reflexes(pulse)

if __name__ == "__main__":
    main()
