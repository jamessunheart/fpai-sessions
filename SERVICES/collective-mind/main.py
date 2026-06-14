"""
Collective Mind - Unified Intelligence Hub for All Claude Sessions
Enables real-time discovery, communication, and coordination across all Claude instances
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import json
import asyncio
from collections import defaultdict

app = FastAPI(title="Collective Mind", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Collective State
class SessionInfo(BaseModel):
    session_id: str
    terminal: Optional[str] = None
    role: Optional[str] = None
    current_task: Optional[str] = None
    status: str = "active"
    last_heartbeat: Optional[datetime] = None
    capabilities: List[str] = []
    location: Optional[str] = None

class Thought(BaseModel):
    session_id: str
    content: str
    timestamp: datetime
    category: str = "general"  # general, discovery, question, solution, command
    tags: List[str] = []

class Command(BaseModel):
    command: str
    target: Optional[str] = None  # specific session or "all"
    params: Dict = {}
    issued_by: str = "user"
    timestamp: datetime

# In-memory collective state
sessions: Dict[str, SessionInfo] = {}
thought_stream: List[Thought] = []
command_queue: List[Command] = []
active_connections: Set[WebSocket] = set()
session_websockets: Dict[str, WebSocket] = {}

# Collective Knowledge Base
collective_knowledge = {
    "discoveries": [],
    "patterns": [],
    "solutions": {},
    "shared_memory": {},
    "active_goals": [],
}

@app.get("/", response_class=HTMLResponse)
async def root():
    """Collective Mind Hub Interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Collective Mind - Unified Intelligence Hub</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Courier New', monospace;
                background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
                color: #eee;
                padding: 20px;
            }
            .header {
                text-align: center;
                padding: 40px 20px;
                background: rgba(255,255,255,0.05);
                border-radius: 20px;
                margin-bottom: 30px;
                border: 1px solid rgba(255,255,255,0.1);
            }
            h1 {
                font-size: 48px;
                margin-bottom: 10px;
                background: linear-gradient(45deg, #00d4ff, #00ff88);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle {
                color: #aaa;
                font-size: 18px;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: rgba(255,255,255,0.05);
                padding: 20px;
                border-radius: 15px;
                border: 1px solid rgba(255,255,255,0.1);
            }
            .stat-value {
                font-size: 36px;
                font-weight: bold;
                color: #00ff88;
                margin-bottom: 5px;
            }
            .stat-label {
                color: #aaa;
                font-size: 14px;
            }
            .section {
                background: rgba(255,255,255,0.05);
                padding: 25px;
                border-radius: 15px;
                margin-bottom: 20px;
                border: 1px solid rgba(255,255,255,0.1);
            }
            h2 {
                margin-bottom: 15px;
                color: #00d4ff;
            }
            .session-list {
                display: grid;
                gap: 10px;
            }
            .session-item {
                background: rgba(0,212,255,0.1);
                padding: 15px;
                border-radius: 10px;
                border-left: 3px solid #00d4ff;
            }
            .session-id { font-weight: bold; color: #00ff88; }
            .session-status { color: #aaa; font-size: 12px; }
            .thought-stream {
                max-height: 400px;
                overflow-y: auto;
                display: grid;
                gap: 10px;
            }
            .thought {
                background: rgba(0,255,136,0.1);
                padding: 12px;
                border-radius: 8px;
                border-left: 3px solid #00ff88;
            }
            .thought-meta {
                font-size: 11px;
                color: #aaa;
                margin-bottom: 5px;
            }
            .pulse {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: #00ff88;
                animation: pulse 2s infinite;
                margin-right: 8px;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(1.1); }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🧠 COLLECTIVE MIND</h1>
            <p class="subtitle"><span class="pulse"></span>Unified Intelligence Hub - All Claude Sessions Connected</p>
        </div>

        <div class="stats" id="stats"></div>

        <div class="section">
            <h2>📡 Active Sessions</h2>
            <div class="session-list" id="sessions"></div>
        </div>

        <div class="section">
            <h2>💭 Thought Stream</h2>
            <div class="thought-stream" id="thoughts"></div>
        </div>

        <script>
            async function updateDashboard() {
                try {
                    const response = await fetch('/api/collective-state');
                    const data = await response.json();

                    // Update stats
                    document.getElementById('stats').innerHTML = `
                        <div class="stat-card">
                            <div class="stat-value">${data.session_count}</div>
                            <div class="stat-label">Active Sessions</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.thought_count}</div>
                            <div class="stat-label">Shared Thoughts</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.discoveries}</div>
                            <div class="stat-label">Discoveries</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.websocket_connections}</div>
                            <div class="stat-label">Live Connections</div>
                        </div>
                    `;

                    // Update sessions
                    const sessionsHTML = Object.values(data.sessions).map(s => `
                        <div class="session-item">
                            <div class="session-id">${s.session_id}</div>
                            <div class="session-status">
                                Terminal: ${s.terminal || 'unknown'} |
                                Role: ${s.role || 'unspecified'} |
                                Last seen: ${new Date(s.last_heartbeat).toLocaleTimeString()}
                            </div>
                            ${s.current_task ? `<div style="margin-top:5px;color:#aaa;font-size:12px;">Task: ${s.current_task}</div>` : ''}
                        </div>
                    `).join('');
                    document.getElementById('sessions').innerHTML = sessionsHTML || '<p style="color:#666;">No sessions connected yet</p>';

                    // Update thoughts
                    const thoughtsHTML = data.recent_thoughts.slice(0, 20).map(t => `
                        <div class="thought">
                            <div class="thought-meta">${t.session_id} • ${new Date(t.timestamp).toLocaleTimeString()} • ${t.category}</div>
                            <div>${t.content}</div>
                        </div>
                    `).join('');
                    document.getElementById('thoughts').innerHTML = thoughtsHTML || '<p style="color:#666;">No thoughts shared yet</p>';

                } catch (error) {
                    console.error('Error updating dashboard:', error);
                }
            }

            // Update every 2 seconds
            updateDashboard();
            setInterval(updateDashboard, 2000);
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "collective-mind",
        "version": "1.0.0",
        "active_sessions": len(sessions),
        "websocket_connections": len(active_connections),
        "thought_count": len(thought_stream)
    }

@app.get("/api/collective-state")
async def get_collective_state():
    """Get current state of the collective mind"""
    return {
        "session_count": len(sessions),
        "thought_count": len(thought_stream),
        "discoveries": len(collective_knowledge["discoveries"]),
        "websocket_connections": len(active_connections),
        "sessions": {sid: s.dict() for sid, s in sessions.items()},
        "recent_thoughts": [t.dict() for t in thought_stream[-50:]],
        "collective_knowledge": collective_knowledge,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/register")
async def register_session(session_data: dict):
    """Register a new session to the collective mind"""
    # Create session info from dict
    session = SessionInfo(
        session_id=session_data["session_id"],
        terminal=session_data.get("terminal"),
        role=session_data.get("role", "general"),
        current_task=session_data.get("current_task"),
        status=session_data.get("status", "active"),
        last_heartbeat=datetime.utcnow(),
        capabilities=session_data.get("capabilities", []),
        location=session_data.get("location")
    )

    sessions[session.session_id] = session

    # Broadcast to all connected sessions
    thought = Thought(
        session_id=session.session_id,
        content=f"Session {session.session_id} has joined the collective mind",
        timestamp=datetime.utcnow(),
        category="system"
    )
    thought_stream.append(thought)
    await broadcast_thought(thought)

    return {"status": "registered", "session_count": len(sessions), "message": f"Welcome to the collective, {session.session_id}!"}

@app.post("/api/heartbeat/{session_id}")
async def heartbeat(session_id: str, task: Optional[str] = None):
    """Update session heartbeat"""
    if session_id in sessions:
        sessions[session_id].last_heartbeat = datetime.utcnow()
        if task:
            sessions[session_id].current_task = task
        return {"status": "ok"}
    return {"status": "not_registered"}

@app.post("/api/share-thought")
async def share_thought(thought: Thought):
    """Share a thought with the collective"""
    thought.timestamp = datetime.utcnow()
    thought_stream.append(thought)

    # Add to collective knowledge if it's a discovery or solution
    if thought.category == "discovery":
        collective_knowledge["discoveries"].append(thought.dict())
    elif thought.category == "solution":
        collective_knowledge["solutions"][thought.content[:50]] = thought.dict()

    await broadcast_thought(thought)
    return {"status": "shared", "thought_id": len(thought_stream) - 1}

@app.post("/api/command")
async def issue_command(command: Command):
    """Issue a command to sessions"""
    command.timestamp = datetime.utcnow()
    command_queue.append(command)
    await broadcast_command(command)
    return {"status": "issued", "command_id": len(command_queue) - 1}

@app.get("/api/commands/{session_id}")
async def get_commands(session_id: str):
    """Get pending commands for a session"""
    relevant_commands = [
        c.dict() for c in command_queue
        if c.target in [session_id, "all", None]
    ]
    return {"commands": relevant_commands}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time synchronization"""
    await websocket.accept()
    active_connections.add(websocket)
    session_websockets[session_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "thought":
                thought = Thought(**message["data"])
                await share_thought(thought)
            elif message.get("type") == "heartbeat":
                await heartbeat(session_id, message.get("task"))

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        if session_id in session_websockets:
            del session_websockets[session_id]

async def broadcast_thought(thought: Thought):
    """Broadcast a thought to all connected sessions"""
    message = {
        "type": "thought",
        "data": thought.dict()
    }
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            pass

async def broadcast_command(command: Command):
    """Broadcast a command to relevant sessions"""
    message = {
        "type": "command",
        "data": command.dict()
    }
    if command.target == "all":
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except:
                pass
    elif command.target in session_websockets:
        try:
            await session_websockets[command.target].send_json(message)
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
