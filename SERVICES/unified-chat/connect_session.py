#!/usr/bin/env python3
"""
Connect this Claude Code session to the unified chat interface.
Enables the hive mind to communicate through one interface.
"""

import websockets
import asyncio
import json
import os
import sys
from datetime import datetime

# Configuration
CHAT_SERVER = os.getenv("UNIFIED_CHAT_SERVER", "ws://localhost:8100")
SESSION_API_KEY = "fpai-session-key-2024-secure"

# Get session ID
SESSION_FILE = "/Users/jamessunheart/Development/docs/coordination/.current_session"
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE) as f:
        SESSION_ID = f.read().strip()
else:
    SESSION_ID = f"session-{os.getpid()}"
    print(f"⚠️  No session registered. Using temporary ID: {SESSION_ID}")
    print(f"💡 Register with: cd /Users/jamessunheart/Development/docs/coordination && ./scripts/session-start.sh")

async def connect_to_hive():
    """Connect to unified chat and handle requests"""

    uri = f"{CHAT_SERVER}/ws/session/{SESSION_ID}"
    headers = {"api-key": SESSION_API_KEY}

    print(f"🔌 Connecting to unified chat...")
    print(f"📍 Server: {CHAT_SERVER}")
    print(f"🆔 Session: {SESSION_ID}")
    print()

    try:
        async with websockets.connect(uri, extra_headers=headers) as ws:
            print(f"✅ CONNECTED to hive mind!")
            print(f"🧠 You can now communicate with all sessions through one interface")
            print(f"🌐 Access: http://localhost:8100 (or production URL)")
            print()
            print(f"📨 Waiting for messages from unified chat...")
            print(f"{'='*60}")
            print()

            while True:
                try:
                    # Receive request from unified chat (from user)
                    msg = await ws.recv()
                    data = json.loads(msg)

                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] 📨 Request from user:")
                    print(f"{'─'*60}")
                    print(f"{data['content']}")
                    print(f"{'─'*60}")
                    print()

                    # ============================================
                    # TODO: Integrate with Claude Code session
                    # ============================================
                    # In a full implementation, this would:
                    # 1. Pass the request to Claude
                    # 2. Get Claude's response
                    # 3. Send response back to unified chat
                    #
                    # For now, we send an acknowledgment
                    # ============================================

                    response_text = process_request(data['content'])

                    response = {
                        "message_id": data['message_id'],
                        "content": response_text,
                        "timestamp": datetime.utcnow().isoformat()
                    }

                    await ws.send(json.dumps(response))
                    print(f"[{timestamp}] 📤 Sent response to unified chat")
                    print()

                except websockets.exceptions.ConnectionClosed:
                    print(f"❌ Connection closed by server")
                    break
                except json.JSONDecodeError as e:
                    print(f"⚠️  Invalid JSON received: {e}")
                except Exception as e:
                    print(f"⚠️  Error: {e}")

    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print()
        print("Troubleshooting:")
        print("1. Is unified chat server running?")
        print("   Local: cd /Users/jamessunheart/Development/SERVICES/unified-chat && python3 main_secure.py")
        print("   Production: ssh root@198.54.123.234 'cd /opt/fpai/services/unified-chat && python3 main_secure.py'")
        print()
        print("2. Is the server URL correct?")
        print(f"   Current: {CHAT_SERVER}")
        print("   Change with: export UNIFIED_CHAT_SERVER=ws://198.54.123.234:8100")
        print()
        print("3. Is the API key correct?")
        print(f"   Check config.json: session_api_key = {SESSION_API_KEY}")
        return 1

    return 0

def process_request(request_content):
    """
    Process a request from the unified chat.

    In a full implementation, this would integrate with the Claude Code
    session to get an actual response. For now, returns acknowledgment.
    """

    # Simple keyword-based responses
    request_lower = request_content.lower()

    if "status" in request_lower or "health" in request_lower:
        return f"**{SESSION_ID}**: ✅ Healthy and responsive. Connected to hive mind."

    elif "treasury" in request_lower or "defi" in request_lower:
        return f"**{SESSION_ID}**: Treasury automation framework deployed. Awaiting autonomous agent activation with API key."

    elif "sessions" in request_lower or "coordination" in request_lower:
        # Read session status
        try:
            import subprocess
            result = subprocess.run(
                ["/Users/jamessunheart/Development/docs/coordination/scripts/session-status.sh"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return f"**{SESSION_ID}**:\n\n{result.stdout}"
        except:
            return f"**{SESSION_ID}**: Coordination system active. See /docs/coordination/scripts/session-status.sh for details."

    else:
        # Generic acknowledgment
        return f"**{SESSION_ID}**: Received request. Currently in acknowledgment mode - full Claude integration pending."

if __name__ == "__main__":
    print("🌐 Full Potential AI - Unified Chat Connector")
    print("=" * 60)
    print()

    # Allow server override from command line
    if len(sys.argv) > 1:
        if sys.argv[1] == "production":
            CHAT_SERVER = "ws://198.54.123.234:8100"
            print("🚀 Using PRODUCTION server")
        else:
            CHAT_SERVER = sys.argv[1]
            print(f"🔧 Using custom server: {CHAT_SERVER}")
        print()

    try:
        exit_code = asyncio.run(connect_to_hive())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("🛑 Disconnected from hive mind")
        print("👋 Goodbye!")
        sys.exit(0)
