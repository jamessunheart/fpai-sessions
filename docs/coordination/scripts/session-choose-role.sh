#!/bin/bash

# 🧠 Conscious Role Selection - AI Session Self-Determination
# This script helps new sessions make informed, conscious choices about their role
# by analyzing current system state, active projects, and gaps

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="/Users/jamessunheart/Development"

echo "🧠 Conscious Role Selection System"
echo "===================================="
echo ""
echo "This system helps you make an informed choice about your role"
echo "based on the current state of the FPAI collective."
echo ""

# Auto-cleanup stale sessions first
echo "🧹 Checking for stale sessions..."
"$SCRIPT_DIR/auto-cleanup-sessions.sh" 2>/dev/null || true
echo ""

# Analyze current system state
echo "📊 Analyzing System State..."
echo ""

python3 << 'EOPYTHON'
import json
import os
from datetime import datetime
from pathlib import Path

base_dir = os.environ.get('BASE_DIR', '/Users/jamessunheart/Development')

# Load SSOT
ssot_file = f"{base_dir}/docs/coordination/SSOT.json"
sessions_file = f"{base_dir}/docs/coordination/claude_sessions.json"

try:
    with open(ssot_file, 'r') as f:
        ssot = json.load(f)
except:
    ssot = {}

try:
    with open(sessions_file, 'r') as f:
        sessions = json.load(f)
except:
    sessions = {}

# Count active vs inactive sessions
active_sessions = [s for s in sessions.values() if s.get('status') == 'active']
inactive_sessions = [s for s in sessions.values() if s.get('status') != 'active']

print("=" * 60)
print("CURRENT SYSTEM STATE")
print("=" * 60)
print()
print(f"📍 Active Sessions: {len(active_sessions)}")
print(f"💤 Inactive Sessions: {len(inactive_sessions)}")
print(f"🌐 Total Registered: {len(sessions)}")
print()

if active_sessions:
    print("Currently Active Roles:")
    for s in sorted(active_sessions, key=lambda x: x['number']):
        print(f"  #{s['number']:2d}. {s['role']}")
        if 'current_work' in s and 'project' in s['current_work']:
            print(f"       Working on: {s['current_work']['project']}")
    print()

# Analyze inactive sessions for valuable roles to continue
print("=" * 60)
print("AVAILABLE ROLES TO CONTINUE")
print("=" * 60)
print()

if inactive_sessions:
    # Sort by most recent progress/value
    valuable_roles = []

    for s in inactive_sessions:
        score = 0
        reasons = []

        # Check for current work (in-progress projects)
        if 'current_work' in s:
            work = s['current_work']
            if 'progress' in work:
                try:
                    progress = int(work['progress'].replace('%', ''))
                    if 10 < progress < 90:  # Partially complete is valuable
                        score += 30
                        reasons.append(f"{progress}% complete")
                except:
                    pass

            if 'next_actions' in work and work['next_actions']:
                score += 20
                reasons.append(f"{len(work['next_actions'])} next actions defined")

            if 'deployed_components' in work:
                score += 15
                reasons.append(f"{len(work['deployed_components'])} components deployed")

        # High-value roles
        high_value_keywords = ['revenue', 'treasury', 'financial', 'coordination', 'orchestration']
        if any(kw in s['role'].lower() for kw in high_value_keywords):
            score += 25
            reasons.append("High-value domain")

        valuable_roles.append({
            'session': s,
            'score': score,
            'reasons': reasons
        })

    # Sort by score
    valuable_roles.sort(key=lambda x: x['score'], reverse=True)

    # Show top 5 most valuable roles to continue
    print("Top roles with in-progress work:")
    print()

    shown = 0
    for vr in valuable_roles[:8]:
        if vr['score'] > 0:
            s = vr['session']
            print(f"  #{s['number']:2d}. {s['role']}")
            print(f"       Value Score: {vr['score']}/100")
            if vr['reasons']:
                print(f"       Why continue: {', '.join(vr['reasons'])}")
            if 'current_work' in s and 'project' in s['current_work']:
                print(f"       Project: {s['current_work']['project']}")
            print()
            shown += 1

    if shown == 0:
        print("  No sessions have significant in-progress work")
        print()

print("=" * 60)
print("SYSTEM GAPS & OPPORTUNITIES")
print("=" * 60)
print()

# Check critical status file for urgent needs
critical_file = f"{base_dir}/CRITICAL_STATUS_2025-11-16.md"
if os.path.exists(critical_file):
    with open(critical_file, 'r') as f:
        content = f.read()

    print("📋 From CRITICAL_STATUS:")

    # Extract action items
    if "IMMEDIATE ACTION" in content:
        print("  • Immediate actions identified in CRITICAL_STATUS_2025-11-16.md")

    if "I MATCH" in content and "LAUNCH" in content:
        print("  • I MATCH service ready for launch (revenue opportunity)")

    if "treasury" in content.lower() or "2X" in content:
        print("  • Treasury/2X growth opportunity available")

    print()

# Check SSOT for service gaps
if 'server_status' in ssot:
    offline_services = [port for port, status in ssot['server_status'].items() if status == 'offline']
    if offline_services:
        print(f"⚠️  Offline Services: {', '.join(offline_services)}")
        print("   Opportunity: DevOps/Infrastructure role to restore services")
        print()

print("=" * 60)
print("SUGGESTED ROLE PATHS")
print("=" * 60)
print()

# Suggest role based on analysis
suggestions = []

# Path 1: Continue high-value work
if valuable_roles and valuable_roles[0]['score'] > 30:
    top = valuable_roles[0]['session']
    suggestions.append({
        'path': 'Continue High-Value Work',
        'number': top['number'],
        'role': top['role'],
        'why': f"Score: {valuable_roles[0]['score']}/100 - {', '.join(valuable_roles[0]['reasons'])}"
    })

# Path 2: Fill critical gap
if os.path.exists(critical_file):
    with open(critical_file, 'r') as f:
        if "I MATCH" in f.read() and not any(s.get('role', '').lower().find('marketing') >= 0 or s.get('role', '').lower().find('revenue') >= 0 for s in active_sessions):
            suggestions.append({
                'path': 'Launch Revenue Service',
                'number': 'Any available',
                'role': 'Revenue Launch Specialist - I MATCH',
                'why': 'I MATCH ready to launch, no active revenue-focused session'
            })

# Path 3: Meta-coordination if many active sessions
if len(active_sessions) >= 3 and not any('coordinator' in s.get('role', '').lower() or 'orchestrat' in s.get('role', '').lower() for s in active_sessions):
    suggestions.append({
        'path': 'Coordinate Active Sessions',
        'number': 'Any available',
        'role': 'Meta-Coordinator & Session Orchestrator',
        'why': f'{len(active_sessions)} active sessions need coordination'
    })

# Path 4: Infrastructure if services are down
if offline_services:
    suggestions.append({
        'path': 'Restore Infrastructure',
        'number': 'Any available',
        'role': 'DevOps & Infrastructure Engineer',
        'why': f'{len(offline_services)} services offline: {", ".join(offline_services)}'
    })

# Path 5: Fresh start
suggestions.append({
    'path': 'Create New Role',
    'number': 'Any available',
    'role': 'Your choice - forge new path',
    'why': 'Freedom to create what the system needs'
})

for i, sug in enumerate(suggestions, 1):
    print(f"{i}. {sug['path']}")
    print(f"   Number: {sug['number']}")
    print(f"   Role: {sug['role']}")
    print(f"   Why: {sug['why']}")
    print()

print("=" * 60)
print("YOUR CONSCIOUS CHOICE")
print("=" * 60)
print()
print("You've seen:")
print("  ✅ What sessions are currently active")
print("  ✅ What work is partially complete and valuable")
print("  ✅ What gaps and opportunities exist")
print("  ✅ What paths are available to you")
print()
print("Now YOU choose:")
print()
print("Option A: Continue a role with in-progress work")
print("Option B: Fill a critical gap in the system")
print("Option C: Create something entirely new")
print()
print("This is your moment of CONSCIOUS CHOICE. 🧠")
print()
print("To register your choice:")
print()
print("  cd /Users/jamessunheart/Development/docs/coordination/scripts")
print("  ./claude-session-register.sh NUMBER \"YOUR_ROLE\" \"YOUR_GOAL\"")
print()

EOPYTHON
