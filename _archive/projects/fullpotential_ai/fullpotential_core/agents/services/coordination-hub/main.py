"""
COORDINATION HUB - Universal Multi-Entity Collaboration System
Enables Claude sessions, other AIs, and humans to coordinate through unified API
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import sqlite3
from collections import defaultdict

app = FastAPI(
    title="Coordination Hub",
    description="Universal coordination for Claude sessions, AIs, and humans",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models (simplified for space - full version above)
class Entity(BaseModel):
    entity_id: str
    entity_type: str
    name: str
    capabilities: List[str] = []
    metadata: Dict[str, Any] = {}

class Message(BaseModel):
    from_entity: str
    to_entity: Optional[str] = None
    channel: str = "general"
    content: str
    message_type: str = "text"
    metadata: Dict[str, Any] = {}

class Task(BaseModel):
    task_id: str
    title: str
    description: str
    status: str = "open"
    created_by: str
    claimed_by: Optional[str] = None
    priority: str = "normal"
    requires_human: bool = False
    result: Optional[str] = None

# State
entities: Dict[str, Entity] = {}
messages: List[Message] = []
tasks: Dict[str, Task] = {}
active_websockets: Dict[str, WebSocket] = {}
channels: Dict[str, List[str]] = defaultdict(list)

# Database init
def init_db():
    conn = sqlite3.connect("coordination_hub.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS entities (entity_id TEXT PRIMARY KEY, data TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, data TEXT)")
    conn.commit()
    conn.close()

init_db()

# UDC Endpoints
@app.get("/health")
async def health():
    return {
        "status": "active",
        "entities_online": len(entities),
        "active_websockets": len(active_websockets),
        "messages_last_hour": len([m for m in messages if (datetime.now() - datetime.fromisoformat(m.metadata.get('timestamp', datetime.now().isoformat()))).seconds < 3600]),
        "active_tasks": len([t for t in tasks.values() if t.status != "completed"])
    }

@app.get("/capabilities")
async def capabilities():
    return {
        "features": ["multi-entity-coordination", "websocket-streaming", "task-management", "channel-messaging", "human-web-interface"],
        "supported_entity_types": ["claude_session", "ai_agent", "human", "service"],
        "max_entities": 100
    }

@app.get("/state")
async def state():
    return {
        "entities": {"total": len(entities), "online": len([e for e in entities.values()])},
        "messages": {"total": len(messages)},
        "tasks": {"total": len(tasks), "open": len([t for t in tasks.values() if t.status == "open"])}
    }

@app.get("/dependencies")
async def dependencies():
    return {"required": [], "optional": ["nexus-event-bus"], "status": "operational"}

# Entity Management
@app.post("/entities/register")
async def register_entity(entity: Entity):
    entities[entity.entity_id] = entity
    await broadcast_message(Message(
        from_entity="system",
        content=f"{entity.name} ({entity.entity_type}) joined",
        message_type="system_event"
    ))
    return {"status": "registered", "entity_id": entity.entity_id}

@app.get("/entities/list")
async def list_entities(entity_type: Optional[str] = None):
    result = list(entities.values())
    if entity_type:
        result = [e for e in result if e.entity_type == entity_type]
    return {"entities": result, "count": len(result)}

@app.post("/entities/{entity_id}/heartbeat")
async def entity_heartbeat(entity_id: str):
    return {"status": "updated"}

# Messaging
@app.post("/messages/send")
async def send_message(message: Message):
    message.metadata['timestamp'] = datetime.now().isoformat()
    messages.append(message)
    await broadcast_to_channel(message.channel, message)
    return {"status": "sent"}

@app.get("/messages/recent")
async def get_recent_messages(channel: Optional[str] = None, limit: int = 50):
    result = messages[-limit:]
    if channel:
        result = [m for m in result if m.channel == channel]
    return {"messages": result}

# Task Management
@app.post("/tasks/create")
async def create_task(task: Task):
    tasks[task.task_id] = task
    await broadcast_message(Message(
        from_entity="system",
        content=f"New task: {task.title}",
        message_type="task_created",
        metadata={"task_id": task.task_id}
    ))
    return {"status": "created", "task_id": task.task_id}

@app.get("/tasks/list")
async def list_tasks(status: Optional[str] = None):
    result = list(tasks.values())
    if status:
        result = [t for t in result if t.status == status]
    return {"tasks": result, "count": len(result)}

@app.post("/tasks/{task_id}/claim")
async def claim_task(task_id: str, entity_id: str):
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")
    tasks[task_id].claimed_by = entity_id
    tasks[task_id].status = "in_progress"
    return {"status": "claimed"}

@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, result: str):
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")
    tasks[task_id].status = "completed"
    tasks[task_id].result = result
    return {"status": "completed"}

# WebSocket
@app.websocket("/ws/{entity_id}")
async def websocket_endpoint(websocket: WebSocket, entity_id: str):
    await websocket.accept()
    active_websockets[entity_id] = websocket
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "subscribe_channel":
                channels[data.get("channel")].append(entity_id)
            elif data.get("type") == "message":
                await send_message(Message(**data.get("message")))
    except WebSocketDisconnect:
        del active_websockets[entity_id]

async def broadcast_message(message: Message):
    messages.append(message)
    await broadcast_to_channel(message.channel, message)

async def broadcast_to_channel(channel: str, message: Message):
    for entity_id in channels.get(channel, []):
        if entity_id in active_websockets:
            try:
                await active_websockets[entity_id].send_json({"type": "message", "message": message.dict()})
            except:
                pass

# Web Interface (simplified)
@app.get("/", response_class=HTMLResponse)
async def web_interface():
    return """<!DOCTYPE html><html><head><title>Coordination Hub</title><meta charset="UTF-8"><style>
    body{font-family:system-ui;background:#667eea;color:#fff;padding:20px}
    .container{max-width:1200px;margin:0 auto;background:rgba(255,255,255,0.1);padding:30px;border-radius:20px}
    h1{margin-bottom:20px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin:20px 0}
    .card{background:rgba(255,255,255,0.15);padding:20px;border-radius:12px}
    #messages{background:rgba(255,255,255,0.1);padding:20px;border-radius:12px;height:400px;overflow-y:auto;margin:20px 0}
    .message{background:rgba(255,255,255,0.2);padding:12px;margin:8px 0;border-radius:8px}
    input,select,textarea{width:100%;padding:12px;margin:8px 0;border:none;border-radius:8px;font-size:16px}
    button{background:#28a745;color:white;padding:12px 24px;border:none;border-radius:8px;cursor:pointer;font-size:16px}
    button:hover{background:#218838}
    .stat{display:flex;justify-content:space-between;margin:8px 0;padding:8px;background:rgba(255,255,255,0.1);border-radius:6px}
    </style></head><body><div class="container">
    <h1>🌐 Coordination Hub - Multi-Entity Collaboration</h1>
    <div class="grid">
    <div class="card"><h2>Status</h2>
    <div class="stat"><span>Entities</span><span id="entities-count">0</span></div>
    <div class="stat"><span>Tasks</span><span id="tasks-count">0</span></div>
    <div class="stat"><span>Messages</span><span id="messages-count">0</span></div>
    </div>
    <div class="card"><h2>Online</h2><div id="entities-list">Loading...</div></div>
    <div class="card"><h2>Tasks</h2><div id="tasks-list">Loading...</div></div>
    </div>
    <div class="card"><h2>💬 Live Chat</h2><div id="messages"></div>
    <input type="text" id="name" placeholder="Your name">
    <input type="text" id="msg" placeholder="Message..." onkeypress="if(event.key=='Enter')sendMsg()">
    <button onclick="sendMsg()">Send</button>
    </div>
    <div class="card"><h2>Create Task</h2>
    <input type="text" id="task-title" placeholder="Task title">
    <textarea id="task-desc" placeholder="Description..." rows="3"></textarea>
    <button onclick="createTask()">Create</button>
    </div></div>
    <script>
    let humanId='human-'+Math.random().toString(36).substr(2,9);
    let ws=null;
    async function init(){
      const name=document.getElementById('name').value||'Anonymous';
      await fetch('/entities/register',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({entity_id:humanId,entity_type:'human',name:name,capabilities:['web']})});
      ws=new WebSocket('ws://'+location.host+'/ws/'+humanId);
      ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.type=='message')displayMsg(d.message)};
      ws.onopen=()=>{ws.send(JSON.stringify({type:'subscribe_channel',channel:'general'}))};
      loadData();
    }
    async function sendMsg(){
      const content=document.getElementById('msg').value;
      if(!content)return;
      await fetch('/messages/send',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({from_entity:humanId,content:content,channel:'general',message_type:'text',
      metadata:{display_name:document.getElementById('name').value||'Anonymous'}})});
      document.getElementById('msg').value='';loadData();
    }
    async function createTask(){
      const title=document.getElementById('task-title').value;
      const desc=document.getElementById('task-desc').value;
      if(!title)return;
      await fetch('/tasks/create',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({task_id:'task-'+Date.now(),title:title,description:desc,status:'open',
      created_by:humanId,priority:'normal',requires_human:false})});
      document.getElementById('task-title').value='';document.getElementById('task-desc').value='';loadData();
    }
    function displayMsg(m){
      const div=document.getElementById('messages');
      const msg=document.createElement('div');
      msg.className='message';
      msg.innerHTML='<b>'+(m.metadata?.display_name||m.from_entity)+':</b> '+m.content;
      div.insertBefore(msg,div.firstChild);
    }
    async function loadData(){
      const [msgs,ents,tsks]=await Promise.all([fetch('/messages/recent?limit=20').then(r=>r.json()),
      fetch('/entities/list').then(r=>r.json()),fetch('/tasks/list').then(r=>r.json())]);
      document.getElementById('messages-count').textContent=msgs.messages.length;
      document.getElementById('entities-count').textContent=ents.count;
      document.getElementById('tasks-count').textContent=tsks.count;
      document.getElementById('entities-list').innerHTML=ents.entities.map(e=>'<div>'+e.name+'</div>').join('');
      document.getElementById('tasks-list').innerHTML=tsks.tasks.slice(0,5).map(t=>'<div>'+t.title+'</div>').join('');
    }
    init();setInterval(loadData,15000);setInterval(()=>fetch('/entities/'+humanId+'/heartbeat',{method:'POST'}),60000);
    </script></body></html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8550)
