"""
Companion Claude - Main Service
Your proactive AI director that finds you and orchestrates everything
"""

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
from datetime import datetime
import asyncio

from context_engine import ContextEngine
from prompt_encoder import PromptEncoder
from proactive_notifier import ProactiveNotifier
from agent_orchestrator import AgentOrchestrator

app = FastAPI(title="Companion Claude", version="1.0.0")

# Initialize components
context_engine = ContextEngine()
prompt_encoder = PromptEncoder()
notifier = ProactiveNotifier(context_engine)
orchestrator = AgentOrchestrator()

templates = Jinja2Templates(directory="templates")

# ==================== Models ====================

class MessageRequest(BaseModel):
    message: str
    priority: str = "normal"

class DelegateRequest(BaseModel):
    task: str
    target: str = "auto"

class EncodeRequest(BaseModel):
    intent: str
    target: str = "auto"

class NotificationRequest(BaseModel):
    title: str
    message: str
    type: str = "info"

# ==================== Health & Status ====================

@app.get("/health")
def health():
    """UDC: Health check"""
    return {
        "status": "healthy",
        "service": "companion-claude",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/capabilities")
def capabilities():
    """UDC: Service capabilities"""
    return {
        "service": "companion-claude",
        "capabilities": [
            "context_awareness",
            "proactive_notifications",
            "prompt_encoding",
            "agent_orchestration",
            "priority_management",
            "intelligent_delegation"
        ],
        "features": {
            "monitors_activity": True,
            "sends_notifications": True,
            "orchestrates_agents": True,
            "encodes_prompts": True,
            "learns_patterns": True
        }
    }

@app.get("/state")
def state():
    """UDC: Current service state"""
    return {
        "status": "operational",
        "uptime": "running",
        "active_notifications": notifier.get_active_count(),
        "context_updates": context_engine.get_state("total_updates") or "0",
        "last_activity_detected": context_engine.get_state("last_activity"),
        "james_status": context_engine._get_james_status()
    }

@app.get("/dependencies")
def dependencies():
    """UDC: Service dependencies"""
    return {
        "required": [
            "SSOT.json (coordination state)",
            "SQLite (context database)",
            "File system access"
        ],
        "optional": [
            "Session coordination scripts",
            "Service APIs",
            "Notification system"
        ],
        "status": {
            "ssot_available": context_engine.ssot_path.exists(),
            "database_initialized": True,
            "file_monitor_active": True
        }
    }

@app.get("/message")
def message():
    """UDC: Service message/status"""
    context = context_engine.get_current_context()
    james = context.get("james_status", {})

    activity = james.get("activity", "unknown")
    last_active = james.get("last_active", "unknown")

    return {
        "message": f"Companion Claude monitoring James - {activity}",
        "james_activity": activity,
        "last_active": last_active,
        "proactive_mode": "enabled",
        "suggestions_available": len(context.get("suggestions", []))
    }

# ==================== Context API ====================

@app.get("/context")
def get_context():
    """Get current James context"""
    return context_engine.get_current_context()

@app.get("/context/james")
def get_james_status():
    """Get just James's status"""
    return context_engine._get_james_status()

@app.get("/priorities")
def get_priorities():
    """Get current priority stack"""
    return context_engine._get_priorities()

@app.get("/blockers")
def get_blockers():
    """Get current blockers"""
    return context_engine._get_blockers()

@app.get("/suggestions")
def get_suggestions():
    """Get proactive suggestions"""
    context = context_engine.get_current_context()
    return context.get("suggestions", [])

# ==================== Messaging ====================

@app.post("/message")
def send_message(request: MessageRequest):
    """Send a message to James"""
    result = notifier.send_notification(
        title="Companion Claude",
        message=request.message,
        notification_type="message",
        priority=request.priority
    )

    return {
        "sent": True,
        "method": result.get("method"),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/notification")
def send_notification(request: NotificationRequest):
    """Send a notification to James"""
    result = notifier.send_notification(
        title=request.title,
        message=request.message,
        notification_type=request.type
    )

    return {
        "sent": True,
        "method": result.get("method"),
        "timestamp": datetime.now().isoformat()
    }

# ==================== Agent Orchestration ====================

@app.get("/sessions")
def get_sessions():
    """Get all session status"""
    return orchestrator.get_all_sessions()

@app.post("/sessions/{session_id}/start")
def start_session(session_id: str):
    """Start a session"""
    result = orchestrator.start_session(session_id)
    return result

@app.post("/sessions/{session_id}/stop")
def stop_session(session_id: str):
    """Stop a session"""
    result = orchestrator.stop_session(session_id)
    return result

@app.get("/services")
def get_services():
    """Get all service status"""
    return orchestrator.get_all_services()

@app.post("/delegate")
def delegate_task(request: DelegateRequest):
    """Delegate a task to appropriate agent(s)"""

    # Encode the intent
    encoding = prompt_encoder.encode_intent(request.task, request.target)

    # Delegate to agents
    delegation_results = orchestrator.delegate(
        task=request.task,
        routing=encoding["routing"],
        prompts=encoding["prompts"]
    )

    return {
        "task": request.task,
        "encoding": encoding,
        "delegations": delegation_results,
        "timestamp": datetime.now().isoformat()
    }

# ==================== Prompt Encoding ====================

@app.post("/encode-prompt")
def encode_prompt(request: EncodeRequest):
    """Encode an intent into AI prompts"""
    result = prompt_encoder.encode_intent(request.intent, request.target)
    return result

@app.post("/encode-batch")
def encode_batch(intents: List[str]):
    """Encode multiple intents"""
    results = prompt_encoder.encode_batch(intents)
    return {"encodings": results}

# ==================== Director Dashboard ====================

@app.get("/director", response_class=HTMLResponse)
async def director_dashboard(request: Request):
    """Director dashboard UI"""
    context = context_engine.get_current_context()

    return templates.TemplateResponse("director_dashboard.html", {
        "request": request,
        "context": context,
        "timestamp": datetime.now().isoformat()
    })

@app.websocket("/ws/director")
async def websocket_director(websocket: WebSocket):
    """WebSocket for real-time director updates"""
    await websocket.accept()

    try:
        while True:
            # Send context updates every 2 seconds
            context = context_engine.get_current_context()
            await websocket.send_json(context)
            await asyncio.sleep(2)
    except:
        pass

# ==================== CLI Interface ====================

@app.post("/cli")
def cli_command(command: str, args: Optional[List[str]] = None):
    """Execute a CLI command"""

    commands = {
        "status": lambda: context_engine.get_current_context(),
        "briefing": lambda: generate_briefing(),
        "priorities": lambda: context_engine._get_priorities(),
        "help": lambda: get_help(),
    }

    if command in commands:
        return commands[command]()
    else:
        raise HTTPException(status_code=404, detail=f"Unknown command: {command}")

def generate_briefing() -> Dict:
    """Generate morning briefing"""
    context = context_engine.get_current_context()

    return {
        "type": "briefing",
        "timestamp": datetime.now().isoformat(),
        "james_status": context.get("james_status"),
        "priorities": context.get("priorities"),
        "system_state": context.get("system_state"),
        "wins_yesterday": context.get("wins_today"),  # Would track across days
        "suggestions": context.get("suggestions")
    }

def get_help() -> Dict:
    """Get help information"""
    return {
        "service": "Companion Claude",
        "description": "Your proactive AI director",
        "commands": {
            "companion status": "Get current status",
            "companion briefing": "Get daily briefing",
            "companion priorities": "Show priority stack",
            "companion help": "Show this help",
            "companion delegate <task>": "Delegate a task",
            "companion encode <intent>": "Encode an intent"
        },
        "dashboard": "http://localhost:8900/director"
    }

# ==================== Background Tasks ====================

@app.on_event("startup")
async def startup_event():
    """Initialize background monitoring"""
    # Start proactive monitoring
    asyncio.create_task(proactive_monitoring_loop())

async def proactive_monitoring_loop():
    """Background loop for proactive monitoring"""
    while True:
        try:
            # Check if we should send proactive notifications
            suggestions = context_engine._generate_suggestions()

            for suggestion in suggestions:
                if suggestion.get("priority") == "high":
                    notifier.send_notification(
                        title="Companion Claude",
                        message=suggestion.get("message"),
                        notification_type="suggestion",
                        priority="high"
                    )

            # Update context
            context_engine.update_state("last_check", datetime.now().isoformat())

        except Exception as e:
            print(f"Error in monitoring loop: {e}")

        # Check every 60 seconds
        await asyncio.sleep(60)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8900)
