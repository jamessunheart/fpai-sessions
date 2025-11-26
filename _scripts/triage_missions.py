#!/usr/bin/env python3
"""
Mission Triage System
Scans the `missions/` directory for new/available missions.
Routes them to [AUTO-CANDIDATE] or [HUMAN-REQUIRED] based on the AFP.
"""
import os
import re
from pathlib import Path

# --- Configuration ---
ROOT_DIR = Path(__file__).parent.parent.absolute()
MISSIONS_DIR = ROOT_DIR / "missions"

def parse_mission(content):
    """Extracts metadata from mission markdown."""
    meta = {}
    security_match = re.search(r"Security Level:\*\* (.*)", content)
    complexity_match = re.search(r"Complexity:\*\* (.*)", content)
    status_match = re.search(r"Status:\*\* (.*)", content)
    
    if security_match: meta['security'] = security_match.group(1).strip()
    if complexity_match: meta['complexity'] = complexity_match.group(1).strip()
    if status_match: meta['status'] = status_match.group(1).strip()
    
    return meta

def evaluate_suitability(meta):
    """Determines if a mission is safe for auto-execution."""
    sec = meta.get('security', '').lower()
    comp = meta.get('complexity', '').lower()
    
    # AFP Rules
    # Security: Must be LOW or MEDIUM (if trusted). For v1, only LOW.
    if "low" not in sec:
        return False, "Security Level too high"
        
    # Complexity: Must be SIMPLE or MODERATE.
    if "complex" in comp:
        return False, "Complexity too high"
        
    return True, "Safe for Auto-Build"

def triage_mission(filepath):
    content = filepath.read_text(encoding='utf-8')
    meta = parse_mission(content)
    
    current_status = meta.get('status', '')
    
    # Skip if already claimed, completed, or triaged
    if "Available" not in current_status:
        return
    
    is_safe, reason = evaluate_suitability(meta)
    
    new_status = ""
    if is_safe:
        print(f"🤖 Auto-Queueing: {filepath.name}")
        new_status = "> **Status:** [AUTO-CANDIDATE] (Ready for Builder)"
    else:
        print(f"👤 Human-Queueing: {filepath.name} ({reason})")
        new_status = "> **Status:** [HUMAN-REQUIRED] (Complexity/Security)"
        
    # Atomic Update
    new_content = re.sub(r"> \*\*Status:\*\* Available", new_status, content)
    filepath.write_text(new_content, encoding='utf-8')

def main():
    print("🚦 Triaging Missions...")
    if not MISSIONS_DIR.exists():
        print("No missions directory found.")
        return

    count = 0
    for file in MISSIONS_DIR.glob("*.md"):
        triage_mission(file)
        count += 1
        
    print(f"✅ Triaged {count} missions.")

if __name__ == "__main__":
    main()






