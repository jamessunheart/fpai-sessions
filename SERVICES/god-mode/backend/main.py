import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from pathlib import Path
from datetime import datetime
import uuid

app = FastAPI(title="God Mode Core")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PATHS ---
COORDINATION_DIR = Path("../../../docs/coordination").resolve()
INTENTS_DIR = COORDINATION_DIR / "intents"
CLAIMS_DIR = COORDINATION_DIR / "claims"
HEARTBEATS_DIR = COORDINATION_DIR / "heartbeats"
MESSAGES_DIR = COORDINATION_DIR / "messages/broadcast"
INBOX_FILE = Path("../../../core/STATE/INBOX.json").resolve()

# Ensure dirs
MESSAGES_DIR.mkdir(parents=True, exist_ok=True)

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# --- DATA HELPERS ---

def get_graph_data():
    """Builds node-link data from heartbeats and claims."""
    nodes = []
    links = []
    seen_agents = set()

    # 1. Find Agents via Heartbeats
    # Just scan last 50 heartbeats to find active agents
    if HEARTBEATS_DIR.exists():
        files = sorted(list(HEARTBEATS_DIR.glob("*.json")), reverse=True)[:50]
        for f in files:
            try:
                # Filename format: date_session-id.json OR just session-id.json
                # We rely on content if possible, or filename
                # For now, simple parsing
                name = f.stem.split('-session-')[-1] if 'session' in f.stem else f.stem
                if name not in seen_agents:
                    nodes.append({"id": name, "group": "agent", "status": "active"})
                    seen_agents.add(name)
            except:
                pass

    # 2. Find Work via Claims
    if CLAIMS_DIR.exists():
        for f in CLAIMS_DIR.glob("*.claim"):
            # Claim filename: type-name.claim
            # Content: { "session_id": ... }
            try:
                with open(f) as cf:
                    data = json.load(cf)
                    session_id = data.get("session_id", "unknown")
                    resource = f.stem
                    
                    # Add Resource Node
                    nodes.append({"id": resource, "group": "work", "status": "claimed"})
                    
                    # Add Link
                    links.append({"source": session_id, "target": resource})
                    
                    # Ensure session node exists if we missed it
                    if session_id not in seen_agents:
                        nodes.append({"id": session_id, "group": "agent", "status": "working"})
                        seen_agents.add(session_id)
            except:
                pass
                
    # Add Core Nodes if missing
    for core in ["Brain", "Muscle", "Immune", "Architect"]:
        if core not in seen_agents:
            nodes.append({"id": core, "group": "core", "status": "idle"})

    return {"nodes": nodes, "links": links}

def get_messages(limit=20):
    msgs = []
    if MESSAGES_DIR.exists():
        files = sorted(list(MESSAGES_DIR.glob("*.json")), reverse=True)[:limit]
        for f in files:
            try:
                with open(f) as jf:
                    data = json.load(jf)
                    msgs.append(data)
            except:
                pass
    return sorted(msgs, key=lambda x: x.get('timestamp', ''))

# --- API ENDPOINTS ---

@app.get("/api/health")
async def health():
    return {"status": "God Mode Online", "timestamp": datetime.now().isoformat()}

@app.get("/api/stats")
async def get_stats():
    intents = len(list(INTENTS_DIR.glob("*.json"))) if INTENTS_DIR.exists() else 0
    claims = len(list(CLAIMS_DIR.glob("*.claim"))) if CLAIMS_DIR.exists() else 0
    return {"intents": intents, "claims": claims}

@app.get("/api/graph")
async def api_graph():
    return get_graph_data()

@app.get("/api/chat")
async def api_chat():
    return get_messages()

@app.post("/api/chat")
async def post_chat(msg: dict = Body(...)):
    content = msg.get("content")
    sender = msg.get("sender", "ARCHITECT")
    if not content: return {"error": "empty"}
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}-{uuid.uuid4().hex[:4]}.json"
    
    data = {
        "sender": sender,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "id": uuid.uuid4().hex
    }
    
    with open(MESSAGES_DIR / filename, 'w') as f:
        json.dump(data, f, indent=2)
        
    # Broadcast immediately
    await manager.broadcast({"type": "chat_new", "data": data})
    return data

@app.get("/api/inbox")
async def get_inbox():
    if not INBOX_FILE.exists(): return []
    try:
        with open(INBOX_FILE, 'r') as f:
            data = json.load(f)
            return data.get("items", [])
    except: return []

# --- WEBSOCKET ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- BACKGROUND TASKS ---

async def watch_system_state():
    """Polls system state and broadcasts diffs."""
    last_stats = {}
    last_graph_hash = 0
    
    while True:
        try:
            # 1. Stats
            stats = await get_stats()
            if stats != last_stats:
                await manager.broadcast({"type": "stats_update", "data": stats})
                last_stats = stats
            
            # 2. Graph (Check if file count changed as proxy for deep check)
            # Real impl would be smarter, for now we just send graph every 5s to be safe
            # or check mtimes. Let's just send it.
            graph = get_graph_data()
            current_hash = len(graph["nodes"]) + len(graph["links"])
            if current_hash != last_graph_hash:
                 await manager.broadcast({"type": "graph_update", "data": graph})
                 last_graph_hash = current_hash

        except Exception as e:
            print(f"Watcher Error: {e}")
        
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup():
    asyncio.create_task(watch_system_state())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
