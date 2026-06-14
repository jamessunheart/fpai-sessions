#!/usr/bin/env python3
"""
Mission Control - Central Mission Management System
Handles mission claiming, status tracking, and coordination
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import json
import os
from typing import Optional, List, Dict

app = FastAPI(title="Mission Control", version="2.0")

# Paths
MISSIONS_JSON = Path("/Users/jamessunheart/FPAI_Cockpit/SERVICES/landing-page/app/static/missions.json")
MISSIONS_MD_ROOT = Path("/Users/jamessunheart/FPAI_Cockpit/fullpotential_ai/fullpotential_core/orchestration/missions")
CLAIMS_DIR = Path("data/claims")
STATUS_DIR = Path("data/status")

# Adjust for server
if not MISSIONS_JSON.exists():
    MISSIONS_JSON = Path("/root/FPAI_Cockpit/SERVICES/landing-page/app/static/missions.json")
    MISSIONS_MD_ROOT = Path("/root/FPAI_Cockpit/fullpotential_ai/fullpotential_core/orchestration/missions")

CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
STATUS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Models
class MissionClaim(BaseModel):
    mission_id: str
    claimer_name: str
    claimer_email: Optional[str] = None
    claimed_at: str = None
    notes: Optional[str] = None

class StatusUpdate(BaseModel):
    mission_id: str
    status: str  # claimed, in_progress, submitted, completed, blocked
    updated_by: str
    notes: Optional[str] = None
    repo_url: Optional[str] = None
    harvest_score: Optional[int] = None

# Helper Functions
def load_missions() -> List[Dict]:
    """Load missions from JSON feed"""
    if MISSIONS_JSON.exists():
        with open(MISSIONS_JSON, 'r') as f:
            data = json.load(f)
            return data.get('missions', [])
    return []

def get_mission_content(mission_id: str) -> Optional[str]:
    """Load the full mission markdown content"""
    # Try open/ folder first
    md_file = MISSIONS_MD_ROOT / "open" / f"{mission_id}_*.md"
    matches = list(MISSIONS_MD_ROOT.glob(f"open/{mission_id}_*.md"))
    
    if matches:
        with open(matches[0], 'r') as f:
            return f.read()
    
    # Try in-progress
    matches = list(MISSIONS_MD_ROOT.glob(f"in-progress/{mission_id}_*.md"))
    if matches:
        with open(matches[0], 'r') as f:
            return f.read()
    
    return None

def get_claim_status(mission_id: str) -> Optional[Dict]:
    """Get claim info for a mission"""
    claim_file = CLAIMS_DIR / f"{mission_id}.json"
    if claim_file.exists():
        with open(claim_file, 'r') as f:
            return json.load(f)
    return None

def get_mission_status(mission_id: str) -> Dict:
    """Get current status of a mission"""
    status_file = STATUS_DIR / f"{mission_id}.json"
    if status_file.exists():
        with open(status_file, 'r') as f:
            return json.load(f)
    
    # Default status
    return {
        "mission_id": mission_id,
        "status": "open",
        "history": []
    }

def save_claim(claim: MissionClaim) -> None:
    """Save a claim record"""
    if not claim.claimed_at:
        claim.claimed_at = datetime.now().isoformat()
    
    claim_file = CLAIMS_DIR / f"{claim.mission_id}.json"
    with open(claim_file, 'w') as f:
        json.dump(claim.dict(), f, indent=2)
    
    # Also update status
    update_status(StatusUpdate(
        mission_id=claim.mission_id,
        status="claimed",
        updated_by=claim.claimer_name,
        notes=f"Mission claimed by {claim.claimer_name}"
    ))

def update_status(update: StatusUpdate) -> None:
    """Update mission status"""
    status = get_mission_status(update.mission_id)
    
    status['status'] = update.status
    status['last_updated'] = datetime.now().isoformat()
    status['last_updated_by'] = update.updated_by
    
    # Append to history
    status['history'].append({
        "status": update.status,
        "timestamp": datetime.now().isoformat(),
        "updated_by": update.updated_by,
        "notes": update.notes,
        "repo_url": update.repo_url,
        "harvest_score": update.harvest_score
    })
    
    status_file = STATUS_DIR / f"{update.mission_id}.json"
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)

# Routes
@app.get("/", response_class=HTMLResponse)
async def mission_board(request: Request):
    """Main mission board with live status"""
    missions = load_missions()
    
    # Enrich with claim/status data
    for mission in missions:
        claim = get_claim_status(mission['id'])
        status = get_mission_status(mission['id'])
        
        mission['claim_info'] = claim
        mission['live_status'] = status
    
    return templates.TemplateResponse("board.html", {
        "request": request,
        "missions": missions
    })

@app.get("/mission/{mission_id}", response_class=HTMLResponse)
async def mission_detail(request: Request, mission_id: str):
    """Detailed mission view with claim button"""
    missions = load_missions()
    mission = next((m for m in missions if m['id'] == mission_id), None)
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    # Load full markdown content
    content = get_mission_content(mission_id)
    claim = get_claim_status(mission_id)
    status = get_mission_status(mission_id)
    
    return templates.TemplateResponse("detail.html", {
        "request": request,
        "mission": mission,
        "content": content,
        "claim": claim,
        "status": status
    })

@app.post("/api/claim")
async def claim_mission(claim: MissionClaim):
    """Claim a mission"""
    # Check if already claimed
    existing = get_claim_status(claim.mission_id)
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Mission already claimed by {existing['claimer_name']}"
        )
    
    save_claim(claim)
    
    return {
        "status": "success",
        "message": f"Mission {claim.mission_id} claimed successfully",
        "claim": claim.dict()
    }

@app.post("/api/status")
async def update_mission_status(update: StatusUpdate):
    """Update mission status (called by harvester or manual updates)"""
    update_status(update)
    
    return {
        "status": "success",
        "message": f"Mission {update.mission_id} status updated to {update.status}"
    }

@app.get("/api/missions")
async def get_missions_api():
    """API endpoint for mission data with live status"""
    missions = load_missions()
    
    # Enrich with status
    for mission in missions:
        claim = get_claim_status(mission['id'])
        status = get_mission_status(mission['id'])
        
        mission['claim_info'] = claim
        mission['live_status'] = status
    
    return {
        "missions": missions,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/mission/{mission_id}")
async def get_mission_api(mission_id: str):
    """Get single mission with full details"""
    missions = load_missions()
    mission = next((m for m in missions if m['id'] == mission_id), None)
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    claim = get_claim_status(mission_id)
    status = get_mission_status(mission_id)
    content = get_mission_content(mission_id)
    
    return {
        "mission": mission,
        "claim": claim,
        "status": status,
        "content": content
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "mission-control",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8700)

