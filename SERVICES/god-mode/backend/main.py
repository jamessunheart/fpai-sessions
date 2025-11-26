import uvicorn
import os
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
COORDINATION_DIR = Path(os.getenv("COORDINATION_DIR", "../../../docs/coordination")).resolve()
INBOX_FILE = Path(os.getenv("INBOX_FILE", "../../../core/STATE/INBOX.json")).resolve()
TREASURY_FILE = Path(os.getenv("TREASURY_FILE", "../../../core/STATE/TREASURY.json")).resolve()

INTENTS_DIR = COORDINATION_DIR / "intents"
CLAIMS_DIR = COORDINATION_DIR / "claims"
HEARTBEATS_DIR = COORDINATION_DIR / "heartbeats"
MESSAGES_DIR = COORDINATION_DIR / "messages/broadcast"

# Ensure dirs
MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
INTENTS_DIR.mkdir(parents=True, exist_ok=True)

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
    nodes = []
    links = []
    seen_agents = set()

    if HEARTBEATS_DIR.exists():
        files = sorted(list(HEARTBEATS_DIR.glob("*.json")), reverse=True)[:50]
        for f in files:
            try:
                name = f.stem.split('-session-')[-1] if 'session' in f.stem else f.stem
                if name not in seen_agents:
                    nodes.append({"id": name, "group": "agent", "status": "active"})
                    seen_agents.add(name)
            except:
                pass

    if CLAIMS_DIR.exists():
        for f in CLAIMS_DIR.glob("*.claim"):
            try:
                with open(f) as cf:
                    data = json.load(cf)
                    session_id = data.get("session_id", "unknown")
                    resource = f.stem
                    nodes.append({"id": resource, "group": "work", "status": "claimed"})
                    links.append({"source": session_id, "target": resource})
                    if session_id not in seen_agents:
                        nodes.append({"id": session_id, "group": "agent", "status": "working"})
                        seen_agents.add(session_id)
            except:
                pass
                
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

def get_kanban_data():
    board = {
        "intent": [],
        "building": [],
        "deployed": []
    }
    claims = set()
    if CLAIMS_DIR.exists():
        for f in CLAIMS_DIR.glob("*.claim"):
            claims.add(f.stem)

    if INTENTS_DIR.exists():
        for f in INTENTS_DIR.glob("*.json"):
            try:
                with open(f) as jf:
                    data = json.load(jf)
                    item = {
                        "id": f.stem,
                        "title": data.get("droplet_name", f.stem),
                        "desc": data.get("architect_intent", ""),
                        "score": data.get("score", 0)
                    }
                    is_claimed = False
                    for claim in claims:
                        if item["id"] in claim or item["title"] in claim:
                            is_claimed = True
                            break
                    
                    if is_claimed:
                        board["building"].append(item)
                    else:
                        board["intent"].append(item)
            except:
                pass
    return board

def get_treasury_data():
    # Default structure
    data = {
        "tvl": 0,
        "pnl_24h": 0,
        "pnl_percent": 0,
        "cash": 0,
        "allocation": {"stable": 0, "blue_chip": 0, "moonshot": 0},
        "positions": [],
        "magnet_engine": {
            "status": "OFFLINE",
            "leverage": 1.0,
            "magnet_strength": 0,
            "distance": 0,
            "conflict": 0,
            "volatility": 0
        }
    }
    
    if TREASURY_FILE.exists():
        try:
            with open(TREASURY_FILE, 'r') as f:
                file_data = json.load(f)
                data.update(file_data)
        except: pass
    
    return data

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
    await manager.broadcast({"type": "chat_new", "data": data})
    return data

@app.get("/api/board")
async def api_board():
    return get_kanban_data()

@app.post("/api/mission")
async def create_mission(mission: dict = Body(...)):
    name = mission.get("name")
    desc = mission.get("desc")
    if not name: return {"error": "Name required"}
    filename = f"{name}.json"
    data = {
        "architect_intent": desc,
        "droplet_name": name,
        "approval_mode": "auto",
        "auto_deploy": True,
        "generated_by": "God Mode GUI",
        "score": 50,
        "created_at": datetime.now().isoformat()
    }
    with open(INTENTS_DIR / filename, 'w') as f:
        json.dump(data, f, indent=2)
    await manager.broadcast({"type": "board_update", "data": get_kanban_data()})
    return {"status": "created"}

@app.get("/api/inbox")
async def get_inbox():
    if not INBOX_FILE.exists(): return []
    try:
        with open(INBOX_FILE, 'r') as f:
            data = json.load(f)
            return data.get("items", [])
    except: return []

@app.get("/api/treasury")
async def api_treasury():
    return get_treasury_data()

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
    last_board_hash = 0
    
    while True:
        try:
            # 1. Stats
            stats = await get_stats()
            await manager.broadcast({"type": "stats_update", "data": stats})
            
            # 2. Board
            board = get_kanban_data()
            current_hash = len(board["intent"]) + len(board["building"])
            if current_hash != last_board_hash:
                 await manager.broadcast({"type": "board_update", "data": board})
                 last_board_hash = current_hash
            
            # 3. Treasury (Check periodically)
            # In real usage, check mtime. For now, send every 10s
            if datetime.now().second % 10 == 0:
                treasury = get_treasury_data()
                await manager.broadcast({"type": "treasury_update", "data": treasury})

        except Exception as e:
            print(f"Watcher Error: {e}")
        
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup():
    asyncio.create_task(watch_system_state())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
