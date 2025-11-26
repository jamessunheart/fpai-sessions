import os
import json
import logging
import secrets
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

# Configuration
class Settings:
    # Use absolute path for reliability
    PROJECT_ROOT = Path("/Users/jamessunheart/FPAI_Cockpit")
    
    # Service URLs
    BRAIN_URL = "http://localhost:8500"
    MUSCLE_URL = "http://localhost:8400"
    
    # Auth
    USERNAME = "admin"
    PASSWORD = "fpai-admin"

settings = Settings()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MissionControl")

app = FastAPI(title="Mission Control")

# Allow CORS for God Mode integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, settings.USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Setup Templates
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# State File Logic
# We use the absolute PROJECT_ROOT to avoid relative path issues
INBOX_FILE = settings.PROJECT_ROOT / "core" / "STATE" / "INBOX.json"

def get_inbox():
    # Ensure directory exists
    try:
        INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create state dir: {e}")

    # Create default if missing
    if not INBOX_FILE.exists():
        try:
            mock_data = {
                "approvals": [
                    {"id": "tsk_001", "title": "Deploy Treasury V2", "desc": "Deploy $500 to ETH-USDC Pool", "status": "pending"},
                    {"id": "tsk_002", "title": "Publish Blog Post", "desc": "Review 'The Age of AGI' draft", "status": "pending"}
                ],
                "secure": [
                    {"id": "sec_001", "title": "Reddit API Access", "desc": "Requires Client ID & Secret", "status": "waiting_input"}
                ]
            }
            with open(INBOX_FILE, "w") as f:
                json.dump(mock_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write initial inbox: {e}")
            return {"approvals": [], "secure": []}
            
    try:
        with open(INBOX_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read inbox: {e}")
        return {"approvals": [], "secure": []}

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Removed auth for iframe embedding simplicity (add X-Frame-Options allow if needed)
    data = get_inbox()
    return TEMPLATES.TemplateResponse("index.html", {
        "request": request, 
        "approvals": data.get("approvals", []),
        "secure": data.get("secure", [])
    })

@app.get("/telemetry")
async def telemetry(limit: int = 10):
    """Provide live telemetry to God Mode."""
    # Mock telemetry for now, connect to real logs later
    return [
        {"timestamp": "2025-11-23T22:00:00", "event_type": "task_start", "source": "muscle", "payload": {"task": "Deploy V2"}},
        {"timestamp": "2025-11-23T22:05:00", "event_type": "alert", "source": "immune", "payload": {"msg": "High CPU Load"}}
    ][:limit]

@app.post("/approve/{task_id}")
async def approve_task(task_id: str):
    return HTMLResponse(content="<div class='task-card' style='border-left-color: green; opacity: 0.5;'>Approved ✓</div>")

@app.post("/reject/{task_id}")
async def reject_task(task_id: str):
    return HTMLResponse(content="<div class='task-card' style='opacity: 0.5;'>Rejected ✕</div>")

if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 to allow external access (e.g. from ngrok/serveo)
    print(f"🌍 Starting Mission Control on port 8080...")
    uvicorn.run(app, host="0.0.0.0", port=8080)
