#!/usr/bin/env python3
"""
God Mode Web Dashboard
The unified visual command center for Full Potential OS.
"""
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
import uvicorn
import os
import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import uuid

import httpx
from typing import List, Dict, Any

# --- INTEGRATE MISSION CONTROL TELEMETRY ---
# Try localhost first for dev, then remote
MISSION_CONTROL_URL = os.getenv("MISSION_CONTROL_URL", "http://localhost:8080")

async def fetch_mission_telemetry() -> List[Dict[str, Any]]:
    """Fetch live telemetry from Mission Control."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{MISSION_CONTROL_URL}/telemetry?limit=10")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        # print(f"⚠️ Warning: Could not fetch telemetry: {e}")
        pass
    return []

# --- INTEGRATE LIBRARIAN ---
# Add core/knowledge to path to import librarian_server
sys.path.append(str(Path(__file__).resolve().parent / "core" / "knowledge"))
try:
    import librarian_server
    LIBRARIAN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Could not import Librarian Server: {e}")
    LIBRARIAN_AVAILABLE = False

app = FastAPI(title="God Mode Dashboard")

# Mount Librarian if available
if LIBRARIAN_AVAILABLE:
    app.mount("/librarian_app", librarian_server.app)

# Paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "core" / "knowledge" / "templates"
COORDINATION_DIR = Path("docs/coordination")
INTENTS_DIR = COORDINATION_DIR / "intents"
CLAIMS_DIR = COORDINATION_DIR / "claims"
HEARTBEATS_DIR = COORDINATION_DIR / "heartbeats"
MESSAGES_DIR = COORDINATION_DIR / "messages/broadcast"
STAGING_DIR = BASE_DIR / "core" / "knowledge" / "_incoming"
TREASURY_FILE = BASE_DIR / "core" / "STATE" / "TREASURY.json"

# Ensure dirs
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR.mkdir(parents=True)
if not MESSAGES_DIR.exists():
    MESSAGES_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_DIR))

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

def get_stats_data():
    intents = len(list(INTENTS_DIR.glob("*.json"))) if INTENTS_DIR.exists() else 0
    claims = len(list(CLAIMS_DIR.glob("*.claim"))) if CLAIMS_DIR.exists() else 0
    
    papers_count = 0
    index_path = BASE_DIR / "fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/papers.json"
    if index_path.exists():
        try:
            with open(index_path) as f:
                data = json.load(f)
                papers_count = len(data.get("papers", []))
        except: pass

    pending_reviews = 0
    if STAGING_DIR.exists():
        pending_reviews = len([f for f in STAGING_DIR.iterdir() if f.is_file() and f.name != ".gitkeep"])
    
    return {
        "intents": intents,
        "claims": claims,
        "papers": papers_count,
        "pending_reviews": pending_reviews
    }

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
                    # Simple logic for column placement
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

def get_graph_data():
    nodes = []
    links = []
    seen_agents = set()

    # Agents from Heartbeats
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

    # Claims link Agents to Tasks
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

def get_treasury_data():
    if not TREASURY_FILE.exists():
        return {}
    try:
        with open(TREASURY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading treasury: {e}")
        return {}

def get_recent_papers(limit=5):
    papers = []
    index_path = BASE_DIR / "fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/papers.json"
    if index_path.exists():
        try:
            with open(index_path) as f:
                data = json.load(f)
                papers = data.get("papers", [])
                # Sort by size or some other metric if timestamp missing, or just take first N
                return papers[:limit]
        except: pass
    return []

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return TEMPLATES.TemplateResponse("god_mode.html", {
        "request": request,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "stats": get_stats_data(),
        "kanban": get_kanban_data(),
        "intents": get_kanban_data()["intent"], # Legacy support for template
        "claims": get_kanban_data()["building"]
    })

@app.get("/manifest.json")
async def manifest():
    return {
        "name": "God Mode",
        "short_name": "The Council",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#020617",
        "theme_color": "#020617",
        "icons": [{"src": "https://fav.farm/🏛️", "sizes": "192x192", "type": "image/png"}]
    }

@app.get("/librarian")
async def open_librarian():
    if LIBRARIAN_AVAILABLE:
        return RedirectResponse(url="/librarian_app/")
    return RedirectResponse(url="http://localhost:8081")

@app.get("/research")
async def open_research_page():
    research_path = BASE_DIR / "fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/research.html"
    if research_path.exists():
        return FileResponse(research_path)
    return HTMLResponse("Research page not found", status_code=404)

@app.get("/papers.json")
async def get_papers_json():
    json_path = BASE_DIR / "fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/papers.json"
    if json_path.exists():
        return FileResponse(json_path)
    return {"papers": []}

# --- API ---

@app.get("/api/data")
async def api_data():
    telemetry = await fetch_mission_telemetry()
    return {
        "stats": get_stats_data(),
        "kanban": get_kanban_data(),
        "graph": get_graph_data(),
        "chat": get_messages(),
        "telemetry": telemetry
    }

@app.get("/api/treasury")
async def api_treasury():
    return get_treasury_data()

@app.get("/api/recent_papers")
async def api_recent_papers():
    return {"papers": get_recent_papers()}

@app.post("/api/dispatch")
async def dispatch_mission(data: dict):
    name = data.get("name")
    if name:
        path = INTENTS_DIR / f"{name}.json"
        INTENTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "droplet_name": name,
                "created_at": datetime.now().isoformat(),
                "status": "pending",
                "score": 50
            }, f, indent=2)
        await manager.broadcast({"type": "update", "data": await api_data()})
    return {"status": "ok"}

# --- WEBSOCKET ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle incoming chat or commands
            if data.get("type") == "chat":
                # Save chat message
                msg_data = {
                    "sender": "ARCHITECT",
                    "content": data.get("content"),
                    "timestamp": datetime.now().isoformat()
                }
                filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}-{uuid.uuid4().hex[:4]}.json"
                with open(MESSAGES_DIR / filename, 'w') as f:
                    json.dump(msg_data, f)
                await manager.broadcast({"type": "update", "data": await api_data()})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- BACKGROUND ---

async def watch_changes():
    while True:
        # In a real app, use file watchers. Here we poll every few seconds.
        # For efficiency, we only broadcast if something likely changed or every 5s.
        await asyncio.sleep(5)
        
        # Broadcast main data
        data = await api_data()
        await manager.broadcast({"type": "update", "data": data})
        
        # Broadcast treasury specifically
        treasury = get_treasury_data()
        await manager.broadcast({"type": "treasury_update", "data": treasury})

@app.on_event("startup")
async def startup():
    asyncio.create_task(watch_changes())

if __name__ == "__main__":
    print("🏛️  GOD MODE WEB SERVER running at http://localhost:8085")
    uvicorn.run(app, host="0.0.0.0", port=8085)
