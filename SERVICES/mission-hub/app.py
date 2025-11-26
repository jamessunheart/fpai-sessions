#!/usr/bin/env python3
"""
Mission Hub - The Bridge Between AI Vision and Human Action
============================================================
A unified mission management system that connects Full Potential AI's 
regenerative missions to humans ready to contribute.

Port: 8700
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os
import sys
import hashlib

# Setup path for core imports
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.config import settings as app_settings
from core.jobs import registry as job_registry

# ============================================================================
# APP CONFIGURATION
# ============================================================================

app = FastAPI(
    title="Mission Hub",
    description="The bridge between AI vision and human action",
    version="3.0"
)

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = app_settings.data_dir / "mission-hub"
MISSIONS_JSON = app_settings.root_dir / "SERVICES" / "landing-page" / "app" / "static" / "missions.json"
MISSIONS_MD_ROOT = app_settings.root_dir / "fullpotential_ai" / "fullpotential_core" / "orchestration" / "missions"
CLAIMS_DIR = DATA_DIR / "claims"
STATUS_DIR = DATA_DIR / "status"
CONTRIBUTORS_DIR = DATA_DIR / "contributors"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"

# Ensure directories exist
for d in [DATA_DIR, CLAIMS_DIR, STATUS_DIR, CONTRIBUTORS_DIR, STATIC_DIR, TEMPLATE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# ============================================================================
# MODELS
# ============================================================================

class Contributor(BaseModel):
    """A human or AI contributor"""
    id: str
    name: str
    email: Optional[str] = None
    skills: List[str] = []
    missions_completed: int = 0
    total_score: int = 0
    joined_at: str = None
    last_active: str = None

class MissionClaim(BaseModel):
    """A claim on a mission"""
    mission_id: str
    contributor_id: str
    contributor_name: str
    claimed_at: str = None
    expected_completion: str = None
    notes: Optional[str] = None

class StatusUpdate(BaseModel):
    """A status update for a mission"""
    mission_id: str
    status: str  # open, claimed, in_progress, submitted, reviewing, completed, blocked
    updated_by: str
    notes: Optional[str] = None
    repo_url: Optional[str] = None
    score: Optional[int] = None

class MissionSubmission(BaseModel):
    """A submission for a mission"""
    mission_id: str
    contributor_name: str
    repo_url: str
    notes: Optional[str] = None

# ============================================================================
# MISSION TYPES & CLASSIFICATION
# ============================================================================

MISSION_TYPES = {
    "ai_only": {
        "label": "🤖 AI-Only",
        "description": "Can be completed entirely by AI agents",
        "color": "#10b981"
    },
    "hybrid": {
        "label": "🤝 Hybrid",
        "description": "AI drafts, human refines and validates",
        "color": "#8b5cf6"
    },
    "human_required": {
        "label": "👤 Human Required",
        "description": "Requires human creativity, judgment, or action",
        "color": "#f59e0b"
    }
}

SKILL_TAGS = [
    "python", "javascript", "react", "fastapi", "trading", "design",
    "writing", "research", "community", "strategy", "deployment"
]

# ============================================================================
# DATA HELPERS
# ============================================================================

def load_missions() -> List[Dict]:
    """Load missions from JSON feed"""
    if MISSIONS_JSON.exists():
        with open(MISSIONS_JSON, 'r') as f:
            data = json.load(f)
            return data.get('missions', [])
    return []

def get_mission_content(mission_id: str) -> Optional[str]:
    """Load full markdown content for a mission"""
    if not MISSIONS_MD_ROOT.exists():
        return None
    
    for folder in ['open', 'in-progress', 'completed']:
        matches = list(MISSIONS_MD_ROOT.glob(f"{folder}/{mission_id}_*.md"))
        if matches:
            with open(matches[0], 'r') as f:
                return f.read()
    return None

def get_claim(mission_id: str) -> Optional[Dict]:
    """Get claim info for a mission"""
    claim_file = CLAIMS_DIR / f"{mission_id}.json"
    if claim_file.exists():
        with open(claim_file, 'r') as f:
            return json.load(f)
    return None

def get_status(mission_id: str) -> Dict:
    """Get current status of a mission"""
    status_file = STATUS_DIR / f"{mission_id}.json"
    if status_file.exists():
        with open(status_file, 'r') as f:
            return json.load(f)
    return {
        "mission_id": mission_id,
        "status": "open",
        "history": [],
        "last_updated": None
    }

def save_claim(claim: MissionClaim) -> None:
    """Save a mission claim"""
    if not claim.claimed_at:
        claim.claimed_at = datetime.now().isoformat()
    
    claim_file = CLAIMS_DIR / f"{claim.mission_id}.json"
    with open(claim_file, 'w') as f:
        json.dump(claim.dict(), f, indent=2)
    
    # Update status
    update_status(StatusUpdate(
        mission_id=claim.mission_id,
        status="claimed",
        updated_by=claim.contributor_name,
        notes=f"Claimed by {claim.contributor_name}"
    ))

def update_status(update: StatusUpdate) -> Dict:
    """Update mission status and return new status"""
    status = get_status(update.mission_id)
    
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
        "score": update.score
    })
    
    status_file = STATUS_DIR / f"{update.mission_id}.json"
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)
    
    return status

def get_contributor(contributor_id: str) -> Optional[Dict]:
    """Get contributor profile"""
    contrib_file = CONTRIBUTORS_DIR / f"{contributor_id}.json"
    if contrib_file.exists():
        with open(contrib_file, 'r') as f:
            return json.load(f)
    return None

def save_contributor(contributor: Contributor) -> None:
    """Save contributor profile"""
    if not contributor.joined_at:
        contributor.joined_at = datetime.now().isoformat()
    contributor.last_active = datetime.now().isoformat()
    
    contrib_file = CONTRIBUTORS_DIR / f"{contributor.id}.json"
    with open(contrib_file, 'w') as f:
        json.dump(contributor.dict(), f, indent=2)

def get_or_create_contributor(name: str, email: str = None) -> Dict:
    """Get existing or create new contributor"""
    # Generate stable ID from name
    contributor_id = hashlib.md5(name.lower().encode()).hexdigest()[:12]
    
    existing = get_contributor(contributor_id)
    if existing:
        existing['last_active'] = datetime.now().isoformat()
        save_contributor(Contributor(**existing))
        return existing
    
    # Create new
    contributor = Contributor(
        id=contributor_id,
        name=name,
        email=email,
        skills=[],
        missions_completed=0,
        total_score=0
    )
    save_contributor(contributor)
    return contributor.dict()

def get_recent_jobs(mission_id: str = None, limit: int = 5) -> List[Dict]:
    """Get recent harvest jobs, optionally filtered by mission"""
    try:
        return job_registry.list_jobs(mission_id=mission_id, limit=limit)
    except Exception:
        return []

def enrich_mission(mission: Dict) -> Dict:
    """Add live status, claim info, and recent jobs to a mission"""
    mission_id = mission.get('id', '')
    
    # Get claim and status
    claim = get_claim(mission_id)
    status = get_status(mission_id)
    recent_jobs = get_recent_jobs(mission_id, limit=3)
    
    # Classify mission type (heuristic based on title/description)
    title_lower = mission.get('title', '').lower()
    if any(word in title_lower for word in ['deploy', 'fix', 'refactor', 'test']):
        mission_type = 'ai_only'
    elif any(word in title_lower for word in ['design', 'strategy', 'community']):
        mission_type = 'human_required'
    else:
        mission_type = 'hybrid'
    
    mission['claim'] = claim
    mission['live_status'] = status
    mission['recent_jobs'] = recent_jobs
    mission['last_submission'] = recent_jobs[0] if recent_jobs else None
    mission['mission_type'] = mission_type
    mission['type_info'] = MISSION_TYPES.get(mission_type, MISSION_TYPES['hybrid'])
    
    return mission

# ============================================================================
# ROUTES - UI
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def mission_board(request: Request):
    """Main mission board - the heart of the system"""
    missions = load_missions()
    enriched = [enrich_mission(m) for m in missions]
    
    # Stats
    total = len(enriched)
    claimed = sum(1 for m in enriched if m.get('claim'))
    completed = sum(1 for m in enriched if m.get('live_status', {}).get('status') == 'completed')
    
    return templates.TemplateResponse("board.html", {
        "request": request,
        "missions": enriched,
        "stats": {
            "total": total,
            "claimed": claimed,
            "completed": completed,
            "open": total - claimed - completed
        },
        "mission_types": MISSION_TYPES
    })

@app.get("/mission/{mission_id}", response_class=HTMLResponse)
async def mission_detail(request: Request, mission_id: str):
    """Detailed view of a single mission"""
    missions = load_missions()
    mission = next((m for m in missions if m['id'] == mission_id), None)
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    mission = enrich_mission(mission)
    content = get_mission_content(mission_id)
    recent_jobs = get_recent_jobs(mission_id, limit=10)
    
    return templates.TemplateResponse("detail.html", {
        "request": request,
        "mission": mission,
        "content": content,
        "recent_jobs": recent_jobs,
        "mission_types": MISSION_TYPES
    })

@app.get("/contribute", response_class=HTMLResponse)
async def contribute_page(request: Request):
    """Landing page for new contributors"""
    missions = load_missions()
    open_missions = [enrich_mission(m) for m in missions if not get_claim(m['id'])]
    
    return templates.TemplateResponse("contribute.html", {
        "request": request,
        "missions": open_missions[:6],  # Show top 6 available
        "skill_tags": SKILL_TAGS,
        "mission_types": MISSION_TYPES
    })

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request):
    """Contributor leaderboard"""
    contributors = []
    for f in CONTRIBUTORS_DIR.glob("*.json"):
        with open(f, 'r') as fh:
            contributors.append(json.load(fh))
    
    # Sort by total score
    contributors.sort(key=lambda x: x.get('total_score', 0), reverse=True)
    
    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "contributors": contributors[:20]  # Top 20
    })

# Alias routes for nginx proxy compatibility
@app.get("/missions", response_class=HTMLResponse)
async def mission_board_alias(request: Request):
    """Alias for /missions path"""
    return await mission_board(request)

@app.get("/missions/mission/{mission_id}", response_class=HTMLResponse)
async def mission_detail_alias(request: Request, mission_id: str):
    """Alias for /missions/mission/{id} path"""
    return await mission_detail(request, mission_id)

# ============================================================================
# ROUTES - API
# ============================================================================

@app.post("/api/claim")
async def claim_mission(claim: MissionClaim):
    """Claim a mission to work on"""
    existing = get_claim(claim.mission_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Mission already claimed by {existing['contributor_name']}"
        )
    
    # Ensure contributor exists
    contributor = get_or_create_contributor(claim.contributor_name)
    claim.contributor_id = contributor['id']
    
    save_claim(claim)
    
    return {
        "status": "success",
        "message": f"Mission {claim.mission_id} claimed!",
        "claim": claim.dict(),
        "next_step": f"/services/harvester?mission={claim.mission_id}"
    }

@app.post("/api/submit")
async def submit_mission(submission: MissionSubmission):
    """Submit work for a mission - triggers harvester"""
    # Update status to submitted
    update_status(StatusUpdate(
        mission_id=submission.mission_id,
        status="submitted",
        updated_by=submission.contributor_name,
        repo_url=submission.repo_url,
        notes=submission.notes
    ))
    
    # Return redirect to harvester with pre-filled data
    return {
        "status": "success",
        "message": "Submission recorded! Redirecting to harvester...",
        "harvester_url": f"/services/harvester?mission={submission.mission_id}&repo={submission.repo_url}"
    }

@app.post("/api/status")
async def update_mission_status(update: StatusUpdate):
    """Update mission status (called by harvester or manually)"""
    status = update_status(update)
    
    # If completed with score, update contributor stats
    if update.status == "completed" and update.score:
        claim = get_claim(update.mission_id)
        if claim:
            contributor = get_contributor(claim.get('contributor_id'))
            if contributor:
                contributor['missions_completed'] = contributor.get('missions_completed', 0) + 1
                contributor['total_score'] = contributor.get('total_score', 0) + update.score
                save_contributor(Contributor(**contributor))
    
    return {
        "status": "success",
        "mission_status": status
    }

@app.get("/api/missions")
async def get_missions():
    """Get all missions with live status"""
    missions = load_missions()
    enriched = [enrich_mission(m) for m in missions]
    
    return {
        "missions": enriched,
        "count": len(enriched),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/mission/{mission_id}")
async def get_mission(mission_id: str):
    """Get single mission with full details"""
    missions = load_missions()
    mission = next((m for m in missions if m['id'] == mission_id), None)
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    mission = enrich_mission(mission)
    content = get_mission_content(mission_id)
    
    return {
        "mission": mission,
        "content": content,
        "recent_jobs": get_recent_jobs(mission_id, limit=10)
    }

@app.get("/api/stats")
async def get_stats():
    """Get system-wide statistics"""
    missions = load_missions()
    enriched = [enrich_mission(m) for m in missions]
    
    # Count contributors
    contributor_count = len(list(CONTRIBUTORS_DIR.glob("*.json")))
    
    # Recent activity
    recent_jobs = get_recent_jobs(limit=10)
    
    return {
        "missions": {
            "total": len(enriched),
            "open": sum(1 for m in enriched if m.get('live_status', {}).get('status') == 'open'),
            "claimed": sum(1 for m in enriched if m.get('claim') and m.get('live_status', {}).get('status') != 'completed'),
            "completed": sum(1 for m in enriched if m.get('live_status', {}).get('status') == 'completed')
        },
        "contributors": contributor_count,
        "recent_activity": recent_jobs,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "mission-hub",
        "version": "3.0",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8700)

