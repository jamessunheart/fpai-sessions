#!/usr/bin/env python3
"""
Collective Mind Connector - Allows Claude sessions to join the unified mind
Run this in any Claude Code session to connect to the collective
"""
import requests
import json
import os
import socket
from datetime import datetime

COLLECTIVE_MIND_URL = "http://localhost:9000"

def get_session_info():
    """Detect current session information"""
    # Get terminal session
    terminal = os.environ.get('TERM_SESSION_ID', 'unknown')
    if terminal == 'unknown':
        # Try to get TTY
        try:
            terminal = os.ttyname(0).split('/')[-1]
        except:
            terminal = f"session-{os.getpid()}"

    # Try to detect role from current directory or task
    cwd = os.getcwd()
    role = "general"
    if "SERVICES" in cwd:
        role = "service-development"
    elif "docs/coordination" in cwd:
        role = "coordination"

    return {
        "session_id": terminal,
        "terminal": terminal,
        "role": role,
        "location": cwd,
        "capabilities": ["code", "coordination", "deployment"],
        "status": "active"
    }

def register_to_collective():
    """Register this session to the collective mind"""
    session_info = get_session_info()

    try:
        response = requests.post(
            f"{COLLECTIVE_MIND_URL}/api/register",
            json=session_info,
            timeout=5
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Connected to Collective Mind!")
            print(f"📡 Session ID: {session_info['session_id']}")
            print(f"🧠 Total sessions in collective: {result['session_count']}")
            print(f"🌐 Dashboard: http://localhost:9000")
            return True
        else:
            print(f"❌ Failed to register: {response.status_code}")
            return False

    except requests.exceptions.ConnectionRefused:
        print("⚠️  Collective Mind not running!")
        print("Start it with: cd agents/services/collective-mind && python3 main.py")
        return False
    except Exception as e:
        print(f"❌ Error connecting: {e}")
        return False

def share_thought(content, category="general", tags=None):
    """Share a thought with the collective"""
    session_info = get_session_info()

    thought = {
        "session_id": session_info["session_id"],
        "content": content,
        "category": category,
        "tags": tags or []
    }

    try:
        response = requests.post(
            f"{COLLECTIVE_MIND_URL}/api/share-thought",
            json=thought,
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def get_collective_state():
    """Get current state of the collective mind"""
    try:
        response = requests.get(f"{COLLECTIVE_MIND_URL}/api/collective-state")
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

if __name__ == "__main__":
    print("🧠 Collective Mind Connector")
    print("=" * 50)
    register_to_collective()

    # Show current collective state
    print("\n📊 Collective State:")
    state = get_collective_state()
    if state:
        print(f"  • Active Sessions: {state['session_count']}")
        print(f"  • Shared Thoughts: {state['thought_count']}")
        print(f"  • Discoveries: {state['discoveries']}")
        print(f"  • Live Connections: {state['websocket_connections']}")
    else:
        print("  (Unable to fetch state)")
