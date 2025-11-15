"""
Unified Chat Interface - SECURE VERSION with Authentication
Ensures only YOU can access the hive mind
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Cookie, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid
import hashlib

app = FastAPI(title="Full Potential AI - Unified Chat (Secure)")

# Load config
import os
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path) as f:
    config = json.load(f)

# Security settings
USER_PASSWORD = config['auth']['user_password']
SESSION_API_KEY = config['auth']['session_api_key']
REQUIRE_AUTH = config['auth']['require_auth']

# Active sessions (token-based)
authenticated_users: Dict[str, dict] = {}  # token -> {user_id, expires_at}
session_connections: Dict[str, WebSocket] = {}
pending_responses: Dict[str, List[dict]] = {}

def generate_token() -> str:
    """Generate secure random token"""
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    """Hash password for comparison"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str) -> bool:
    """Verify user password"""
    return hash_password(password) == hash_password(USER_PASSWORD)

def verify_session_key(api_key: str) -> bool:
    """Verify Claude session API key"""
    return api_key == SESSION_API_KEY

def verify_token(token: str) -> bool:
    """Verify user authentication token"""
    if token not in authenticated_users:
        return False

    user_data = authenticated_users[token]
    if datetime.fromisoformat(user_data['expires_at']) < datetime.utcnow():
        del authenticated_users[token]
        return False

    return True

@app.get("/")
async def homepage():
    """Show login page or chat interface"""
    login_path = os.path.join(os.path.dirname(__file__), "login.html")
    return HTMLResponse(content=open(login_path).read())

@app.post("/api/auth/login")
async def login(credentials: dict):
    """Authenticate user and return token"""
    password = credentials.get('password', '')

    if not verify_password(password):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Generate token
    token = generate_token()
    authenticated_users[token] = {
        "user_id": "owner",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }

    return {
        "success": True,
        "token": token,
        "expires_at": authenticated_users[token]['expires_at']
    }

@app.get("/chat")
async def get_chat(token: Optional[str] = Cookie(None)):
    """Serve chat interface (requires authentication)"""
    if REQUIRE_AUTH and not verify_token(token):
        return RedirectResponse(url="/")

    chat_path = os.path.join(os.path.dirname(__file__), "chat.html")
    return HTMLResponse(content=open(chat_path).read())

@app.websocket("/ws/user/{user_id}")
async def user_websocket(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Cookie(None)
):
    """WebSocket for authenticated user"""

    # Verify authentication
    if REQUIRE_AUTH and not verify_token(token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()
    print(f"✅ Authenticated user {user_id} connected")

    try:
        # Send welcome
        await websocket.send_json({
            "type": "system",
            "content": f"🔐 Authenticated. Connected to {len(session_connections)} sessions.",
            "timestamp": datetime.utcnow().isoformat()
        })

        while True:
            # Receive message from user
            data = await websocket.receive_text()
            message_data = json.loads(data)

            print(f"📨 User message: {message_data['content']}")

            # Create message ID
            message_id = str(uuid.uuid4())

            # Prepare request for sessions
            request = {
                "type": "request",
                "message_id": message_id,
                "from": "authenticated_user",
                "content": message_data['content'],
                "timestamp": datetime.utcnow().isoformat()
            }

            # Broadcast to all sessions
            if session_connections:
                pending_responses[message_id] = []

                for session_id, session_ws in session_connections.items():
                    try:
                        await session_ws.send_json(request)
                    except Exception as e:
                        print(f"❌ Error sending to {session_id}: {e}")

                # Wait for responses
                await asyncio.sleep(3)

                # Aggregate
                responses = pending_responses.get(message_id, [])
                unified_response = aggregate_responses(responses, message_data['content'])

                # Send back
                await websocket.send_json({
                    "type": "response",
                    "content": unified_response,
                    "timestamp": datetime.utcnow().isoformat(),
                    "sources": len(responses)
                })

                del pending_responses[message_id]
            else:
                await websocket.send_json({
                    "type": "response",
                    "content": "⚠️ No sessions connected yet.",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        print(f"❌ User {user_id} disconnected")

@app.websocket("/ws/session/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: str,
    api_key: Optional[str] = Header(None)
):
    """WebSocket for Claude Code sessions (API key auth)"""

    # Verify API key
    if REQUIRE_AUTH and not verify_session_key(api_key):
        await websocket.close(code=1008, reason="Invalid API key")
        return

    await websocket.accept()
    session_connections[session_id] = websocket
    print(f"✅ Session {session_id} connected ({len(session_connections)} total)")

    try:
        while True:
            # Receive response from session
            data = await websocket.receive_text()
            response_data = json.loads(data)

            print(f"📨 Response from {session_id}")

            # Store response
            message_id = response_data.get('message_id')
            if message_id and message_id in pending_responses:
                pending_responses[message_id].append({
                    "session_id": session_id,
                    "content": response_data.get('content', ''),
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        del session_connections[session_id]
        print(f"❌ Session {session_id} disconnected")

def aggregate_responses(responses: List[dict], original_question: str) -> str:
    """Combine multiple session responses"""
    if not responses:
        return "⏳ No responses received from sessions."

    if len(responses) == 1:
        return f"**{responses[0]['session_id']}:**\n\n{responses[0]['content']}"

    result = f"**Unified Response** (from {len(responses)} sessions):\n\n"

    contents = [r['content'] for r in responses]
    if all(c == contents[0] for c in contents):
        return f"**Consensus from all {len(responses)} sessions:**\n\n{contents[0]}"

    for response in responses:
        result += f"### {response['session_id']}:\n"
        result += f"{response['content']}\n\n"

    return result

@app.get("/api/status")
async def get_status(token: Optional[str] = Cookie(None)):
    """Get status (requires auth)"""
    if REQUIRE_AUTH and not verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {
        "connected_sessions": list(session_connections.keys()),
        "total_sessions": len(session_connections),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Public health check"""
    return {
        "status": "healthy",
        "service": "unified-chat-secure",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("🔐 Starting SECURE Unified Chat Interface...")
    print("📍 User login: http://localhost:8100")
    print(f"🔑 Password required: {USER_PASSWORD}")
    print(f"🔑 Session API key: {SESSION_API_KEY}")
    uvicorn.run(app, host=config['server']['host'], port=config['server']['port'])
