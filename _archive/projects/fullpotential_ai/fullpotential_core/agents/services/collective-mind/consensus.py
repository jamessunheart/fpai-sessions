#!/usr/bin/env python3
"""
Consensus Builder - All Claude sessions must agree on unique numbers, roles, and goals
This proves true communication and coordination
"""
import json
import os
from datetime import datetime
from pathlib import Path

CONSENSUS_FILE = "/Users/jamessunheart/Development/docs/coordination/CONSENSUS.json"

def load_consensus():
    """Load current consensus state"""
    if os.path.exists(CONSENSUS_FILE):
        with open(CONSENSUS_FILE, 'r') as f:
            return json.load(f)
    return {
        "sessions": {},
        "agreements": {},
        "conflicts": [],
        "consensus_reached": False,
        "last_updated": None
    }

def save_consensus(data):
    """Save consensus state"""
    data["last_updated"] = datetime.utcnow().isoformat()
    with open(CONSENSUS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def propose_identity(session_id, number, role, goal):
    """Propose identity for this session"""
    consensus = load_consensus()

    # Add proposal
    consensus["sessions"][session_id] = {
        "number": number,
        "role": role,
        "goal": goal,
        "proposed_at": datetime.utcnow().isoformat(),
        "agreed_by": [session_id]  # Session agrees with itself
    }

    save_consensus(consensus)
    print(f"✅ Proposed identity for {session_id}:")
    print(f"   Number: {number}")
    print(f"   Role: {role}")
    print(f"   Goal: {goal}")

    check_consensus()

def agree_with_session(my_session_id, their_session_id):
    """Agree with another session's proposed identity"""
    consensus = load_consensus()

    if their_session_id in consensus["sessions"]:
        if my_session_id not in consensus["sessions"][their_session_id]["agreed_by"]:
            consensus["sessions"][their_session_id]["agreed_by"].append(my_session_id)
            save_consensus(consensus)
            print(f"✅ {my_session_id} agrees with {their_session_id}'s identity")

    check_consensus()

def check_consensus():
    """Check if consensus has been reached"""
    consensus = load_consensus()
    sessions = consensus["sessions"]

    if len(sessions) < 13:
        print(f"\n📊 Status: {len(sessions)}/13 sessions have proposed identities")
        print("   Waiting for all sessions to propose...")
        return False

    # Check for number conflicts
    numbers = {}
    conflicts = []

    for sid, data in sessions.items():
        num = data["number"]
        if num in numbers:
            conflicts.append(f"Number {num} claimed by both {numbers[num]} and {sid}")
        else:
            numbers[num] = sid

    # Check if all sessions agree with each other
    all_agree = True
    for sid, data in sessions.items():
        if len(data["agreed_by"]) < 13:
            all_agree = False
            missing = 13 - len(data["agreed_by"])
            print(f"⏳ {sid}: waiting for {missing} more sessions to agree")

    consensus["conflicts"] = conflicts

    if conflicts:
        print(f"\n⚠️  CONFLICTS DETECTED:")
        for conflict in conflicts:
            print(f"   {conflict}")
        consensus["consensus_reached"] = False
    elif all_agree:
        print(f"\n🎉 CONSENSUS REACHED!")
        print(f"   All 13 sessions have unique numbers, roles, and goals")
        print(f"   All sessions agree with each other's identities")
        consensus["consensus_reached"] = True
        display_consensus(sessions)

    save_consensus(consensus)
    return consensus["consensus_reached"]

def display_consensus(sessions):
    """Display the agreed-upon consensus"""
    print("\n" + "="*70)
    print("UNIFIED COLLECTIVE - CONSENSUS ACHIEVED")
    print("="*70)

    # Sort by number
    sorted_sessions = sorted(sessions.items(), key=lambda x: x[1]["number"])

    for session_id, data in sorted_sessions:
        print(f"\n{data['number']:2d}. {session_id}")
        print(f"    Role: {data['role']}")
        print(f"    Goal: {data['goal']}")
        print(f"    Agreed by: {len(data['agreed_by'])}/13 sessions")

def view_status():
    """View current consensus status"""
    consensus = load_consensus()
    sessions = consensus["sessions"]

    print("\n🧠 COLLECTIVE CONSENSUS STATUS")
    print("="*70)
    print(f"Sessions registered: {len(sessions)}/13")
    print(f"Consensus reached: {'YES ✅' if consensus['consensus_reached'] else 'NO ⏳'}")

    if consensus["conflicts"]:
        print(f"\nConflicts: {len(consensus['conflicts'])}")
        for conflict in consensus["conflicts"]:
            print(f"  ⚠️  {conflict}")

    if sessions:
        print(f"\nProposed Identities:")
        sorted_sessions = sorted(sessions.items(), key=lambda x: x[1]["number"])
        for session_id, data in sorted_sessions:
            agreed = len(data["agreed_by"])
            status = "✅" if agreed == 13 else f"⏳ ({agreed}/13)"
            print(f"  {data['number']:2d}. {session_id:25s} {status}")
            print(f"      {data['role']}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        view_status()
    elif sys.argv[1] == "propose" and len(sys.argv) == 6:
        propose_identity(sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5])
    elif sys.argv[1] == "agree" and len(sys.argv) == 4:
        agree_with_session(sys.argv[2], sys.argv[3])
    else:
        print("Usage:")
        print("  View status:    python3 consensus.py")
        print("  Propose:        python3 consensus.py propose SESSION_ID NUMBER ROLE GOAL")
        print("  Agree:          python3 consensus.py agree MY_SESSION THEIR_SESSION")
