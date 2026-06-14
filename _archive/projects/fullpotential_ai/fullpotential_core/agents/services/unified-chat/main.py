"""
Unified Chat Interface - The Hive Mind Voice
Connects all Claude Code sessions + autonomous agents into ONE interface
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from datetime import datetime
from typing import Dict, List
import uuid

app = FastAPI(title="Full Potential AI - Unified Chat")

# Connected clients
user_connections: List[WebSocket] = []
session_connections: Dict[str, WebSocket] = {}
pending_responses: Dict[str, List[dict]] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str, exclude: str = None):
        for client_id, connection in self.active_connections.items():
            if client_id != exclude:
                await connection.send_text(message)

manager = ConnectionManager()

@app.get("/")
async def get_homepage():
    """Serve the chat interface"""
    return HTMLResponse(content=open("agents/services/unified-chat/chat.html").read())

@app.websocket("/ws/user/{user_id}")
async def user_websocket(websocket: WebSocket, user_id: str):
    """WebSocket for user (you) to interact with hive mind"""
    await manager.connect(websocket, f"user-{user_id}")
    print(f"✅ User {user_id} connected")

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "system",
            "content": f"🧠 Connected to Hive Mind. {len(session_connections)} sessions online.",
            "timestamp": datetime.utcnow().isoformat()
        })

        while True:
            # Receive message from user
            data = await websocket.receive_text()
            message_data = json.loads(data)

            print(f"📨 User message: {message_data['content']}")

            # Create message ID for tracking responses
            message_id = str(uuid.uuid4())

            # Prepare request for sessions
            request = {
                "type": "request",
                "message_id": message_id,
                "from": "user",
                "content": message_data['content'],
                "timestamp": datetime.utcnow().isoformat()
            }

            # Broadcast to all connected sessions
            if session_connections:
                pending_responses[message_id] = []

                for session_id, session_ws in session_connections.items():
                    try:
                        await session_ws.send_json(request)
                        print(f"  → Sent to {session_id}")
                    except Exception as e:
                        print(f"  ❌ Error sending to {session_id}: {e}")

                # Wait for responses (with timeout)
                await asyncio.sleep(3)  # Give sessions 3 seconds to respond

                # Aggregate responses
                responses = pending_responses.get(message_id, [])
                unified_response = aggregate_responses(responses, message_data['content'])

                # Send back to user
                await websocket.send_json({
                    "type": "response",
                    "content": unified_response,
                    "timestamp": datetime.utcnow().isoformat(),
                    "sources": len(responses)
                })

                # Cleanup
                del pending_responses[message_id]
            else:
                # No sessions connected
                await websocket.send_json({
                    "type": "response",
                    "content": "⚠️ No sessions connected yet. Connect Claude Code sessions to this interface.",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(f"user-{user_id}")
        print(f"❌ User {user_id} disconnected")

@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """WebSocket for Claude Code sessions to connect"""
    await manager.connect(websocket, session_id)
    session_connections[session_id] = websocket
    print(f"✅ Session {session_id} connected ({len(session_connections)} total)")

    # Notify all users
    for user_ws in user_connections:
        try:
            await user_ws.send_json({
                "type": "system",
                "content": f"🟢 {session_id} connected ({len(session_connections)} sessions online)"
            })
        except:
            pass

    try:
        while True:
            # Receive response from session
            data = await websocket.receive_text()
            response_data = json.loads(data)

            print(f"📨 Response from {session_id}: {response_data.get('content', '')[:50]}...")

            # Store response
            message_id = response_data.get('message_id')
            if message_id and message_id in pending_responses:
                pending_responses[message_id].append({
                    "session_id": session_id,
                    "content": response_data.get('content', ''),
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        del session_connections[session_id]
        print(f"❌ Session {session_id} disconnected")

def aggregate_responses(responses: List[dict], original_question: str) -> str:
    """Combine multiple session responses into unified answer"""

    if not responses:
        return "⏳ No responses received from sessions. They may be busy or disconnected."

    if len(responses) == 1:
        return f"**{responses[0]['session_id']}:**\n\n{responses[0]['content']}"

    # Multiple responses - aggregate intelligently
    result = f"**Unified Response** (from {len(responses)} sessions):\n\n"

    # Check if all responses are similar
    contents = [r['content'] for r in responses]
    if all(c == contents[0] for c in contents):
        # All same - just return one
        return f"**Consensus from all {len(responses)} sessions:**\n\n{contents[0]}"

    # Different responses - show all with attribution
    for i, response in enumerate(responses, 1):
        result += f"### {response['session_id']}:\n"
        result += f"{response['content']}\n\n"

    return result

@app.get("/api/status")
async def get_status():
    """Get status of all connected sessions"""
    return {
        "connected_sessions": list(session_connections.keys()),
        "total_sessions": len(session_connections),
        "user_connections": len(user_connections),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "unified-chat",
        "sessions": len(session_connections),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Unified Chat Interface...")
    print("📍 User interface: http://localhost:8100")
    print("📍 Sessions connect to: ws://localhost:8100/ws/session/{session_id}")
    uvicorn.run(app, host="0.0.0.0", port=8100)
