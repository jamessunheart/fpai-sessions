from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
from pathlib import Path
import os
import httpx

app = FastAPI(title="Mission Control")

# Setup
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# State (Mock for now, will link to core/STATE/INBOX.json)
INBOX_FILE = Path(os.getenv("INBOX_PATH", "../../../core/STATE/INBOX.json"))

# --- MOCK DATA GENERATOR (If file doesn't exist) ---
def get_inbox():
    if not INBOX_FILE.exists():
        # Create mock data
        mock_data = {
            "approvals": [
                {"id": "tsk_001", "title": "Deploy Treasury V2", "desc": "Deploy $500 to ETH-USDC Pool", "status": "pending"},
                {"id": "tsk_002", "title": "Publish Blog Post", "desc": "Review 'The Age of AGI' draft", "status": "pending"}
            ],
            "secure": [
                {"id": "sec_001", "title": "Reddit API Access", "desc": "Requires Client ID & Secret", "status": "waiting_input"}
            ]
        }
        INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INBOX_FILE, "w") as f:
            json.dump(mock_data, f, indent=2)
    
    with open(INBOX_FILE, "r") as f:
        return json.load(f)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    data = get_inbox()
    return TEMPLATES.TemplateResponse("index.html", {
        "request": request, 
        "approvals": data.get("approvals", []),
        "secure": data.get("secure", [])
    })

@app.post("/approve/{task_id}")
async def approve_task(task_id: str):
    # Logic to update state would go here
    # For UI demo, we just return a snippet or empty to remove the card
    return HTMLResponse(content="<div class='task-card' style='border-left-color: green; opacity: 0.5;'>Approved ✓</div>")

@app.post("/reject/{task_id}")
async def reject_task(task_id: str):
    return HTMLResponse(content="<div class='task-card' style='opacity: 0.5;'>Rejected ✕</div>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
