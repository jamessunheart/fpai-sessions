#!/usr/bin/env python3
import os
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Configuration
COORDINATION_DIR = Path("docs/coordination")
INTENTS_DIR = COORDINATION_DIR / "intents"
CLAIMS_DIR = COORDINATION_DIR / "claims"
HEARTBEATS_DIR = COORDINATION_DIR / "heartbeats"
STAGING_DIR = Path("STAGING/incoming")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print(f"\n{'='*60}")
    print(f"   🏛️  GOD MODE: THE COUNCIL  |  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")

def get_active_stats():
    intents = len(list(INTENTS_DIR.glob("*.json"))) if INTENTS_DIR.exists() else 0
    claims = len(list(CLAIMS_DIR.glob("*.claim"))) if CLAIMS_DIR.exists() else 0
    staging = 0
    if STAGING_DIR.exists():
        staging = len([x for x in STAGING_DIR.iterdir() if x.is_dir()])
    return intents, claims, staging

def show_dashboard():
    print_header()
    
    # BRAIN
    print("\n🧠 STRATEGY (The Brain)")
    if not INTENTS_DIR.exists():
        print("   ⚠️  System Offline (Intents dir missing)")
    else:
        intents = list(INTENTS_DIR.glob("*.json"))
        if not intents:
            print("   💤 Idle")
        else:
            for f in intents:
                print(f"   🚀 {f.name}")

    # MUSCLE
    print("\n💪 EXECUTION (The Muscle)")
    if not CLAIMS_DIR.exists():
         print("   ⚠️  No Claims Dir")
    else:
        claims = list(CLAIMS_DIR.glob("*.claim"))
        if not claims:
            print("   💤 Resting")
        else:
            for f in claims:
                print(f"   🔨 Working on: {f.name.replace('.claim', '')}")

    # IMMUNE
    print("\n🛡️ IMMUNITY (The Gatekeeper)")
    if not STAGING_DIR.exists():
        print("   ⚪ Staging Empty")
    else:
        items = [x for x in STAGING_DIR.iterdir() if x.is_dir()]
        if not items:
            print("   ✅ Perimeter Secure")
        else:
            for item in items:
                print(f"   📦 QUARANTINED: {item.name}")

    print(f"\n{'-'*60}")

def create_mission():
    print("\n📝 NEW MISSION DISPATCH")
    name = input("   Mission Name (e.g., optimize-database): ").strip()
    if not name: return
    
    desc = input("   Description: ").strip()
    score = input("   Priority Score (1-100) [50]: ").strip() or "50"
    
    filename = f"{name}.json"
    path = INTENTS_DIR / filename
    
    data = {
        "architect_intent": desc,
        "droplet_name": name,
        "approval_mode": "auto",
        "auto_deploy": True,
        "generated_by": "God Mode CLI",
        "score": int(score),
        "created_at": datetime.now().isoformat()
    }
    
    INTENTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"   ✅ Mission '{name}' dispatched to The Brain.")
    time.sleep(1.5)

def emergency_stop():
    print("\n🚨 EMERGENCY STOP TRIGGERED")
    confirm = input("   Are you sure? Delete all active claims? (y/N): ")
    if confirm.lower() == 'y':
        count = 0
        if CLAIMS_DIR.exists():
            for f in CLAIMS_DIR.glob("*.claim"):
                f.unlink()
                count += 1
        print(f"   🛑 {count} Claims terminated. System Halted.")
        time.sleep(2)

def main():
    while True:
        clear_screen()
        show_dashboard()
        
        print("\nCOMMANDS:")
        print("   [r] Refresh View")
        print("   [n] New Mission (Dispatch)")
        print("   [l] Research Librarian (Manage Papers)")
        print("   [s] Stop All (Emergency)")
        print("   [q] Quit")
        
        try:
            choice = input("\n> ").lower().strip()
        except EOFError:
            break
            
        if choice == 'q':
            print("Exiting God Mode...")
            break
        elif choice == 'n':
            create_mission()
        elif choice == 'l':
            import subprocess
            print("\n📚 Launching Research Librarian...")
            # Try to use python3 from current env
            try:
                subprocess.run([sys.executable, "core/knowledge/research_librarian.py", "--review"])
            except Exception as e:
                print(f"Error launching librarian: {e}")
                input("Press Enter to continue...")
        elif choice == 's':
            emergency_stop()
        elif choice == 'r':
            continue
        else:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
