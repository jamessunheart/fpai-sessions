"""
Full Potential Projects Dashboard - Central Brain Hub
Manages all projects, cross-project memory, and unified AI intelligence.

This is the meta-layer that sees and coordinates all projects.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import sqlite3
import json
import os
import httpx
import asyncio

# =============================================================================
# Configuration
# =============================================================================

DATABASE_PATH = "projects.db"
PORT = 8660

import os as _os

# AI Configuration — keys from env
ANTHROPIC_API_KEY = _os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = _os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Telegram notifications
TELEGRAM_BOT_TOKEN = _os.environ.get("TELEGRAM_BOT_TOKEN", "")
JAMES_CHAT_ID = _os.environ.get("JAMES_CHAT_ID", "1759822075")

# Known projects and their API endpoints
PROJECTS = {
    "cocoon": {
        "name": "COCOON",
        "description": "One-person recovery cocoon for 12-minute nervous system resets",
        "url": "/projects/cocoon/",
        "api": "http://localhost:8651/api",
        "icon": "🥚",
        "color": "#e8a857"
    }
}

# =============================================================================
# App Setup
# =============================================================================

app = FastAPI(title="Full Potential Projects Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Database Setup
# =============================================================================

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Projects table - registry of all projects
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '📁',
            color TEXT DEFAULT '#888',
            status TEXT DEFAULT 'active',
            api_port INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Memory/Learnings table - cross-project knowledge
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            category TEXT NOT NULL,
            learning TEXT NOT NULL,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    
    # Project snapshots - periodic state captures for history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            metrics TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    
    # Global activity - cross-project activity feed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            project_name TEXT,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert COCOON project if not exists
    cursor.execute("""
        INSERT OR IGNORE INTO projects (id, name, description, icon, color, api_port)
        VALUES ('cocoon', 'COCOON', 'One-person recovery cocoon for 12-minute nervous system resets', '🥚', '#e8a857', 8651)
    """)
    
    conn.commit()
    conn.close()

# Initialize on startup
init_db()

# =============================================================================
# Models
# =============================================================================

class ProjectCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = "📁"
    color: Optional[str] = "#888"

class LearningCreate(BaseModel):
    project_id: Optional[str] = None
    category: str
    learning: str
    context: Optional[str] = None

class ChatMessage(BaseModel):
    message: str

# =============================================================================
# AI Brain Functions
# =============================================================================

async def ask_meta_brain(prompt: str, context: Dict = None) -> str:
    """Ask the meta-brain that knows about all projects"""
    system_prompt = """You are the meta-brain for Full Potential's project management system.

You have visibility across ALL projects and can:
1. See the status of every project
2. Identify patterns and learnings
3. Suggest resource allocation
4. Help prioritize across projects
5. Share knowledge between projects

Be concise and actionable. Focus on what moves things forward.
"""
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": AI_MODEL,
                    "max_tokens": 500,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            data = response.json()
            return data.get("content", [{}])[0].get("text", "Unable to process request.")
    except Exception as e:
        print(f"Meta-brain error: {e}")
        return f"Brain temporarily unavailable: {e}"

async def fetch_project_status(project_id: str) -> Dict:
    """Fetch current status from a project's API"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    conn.close()
    
    if not project:
        return {"error": "Project not found"}
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"http://localhost:{project['api_port']}/api/status")
            return response.json()
    except Exception as e:
        return {"error": str(e), "status": "offline"}

# =============================================================================
# API Routes - Projects
# =============================================================================

@app.get("/")
async def root():
    """Redirect to dashboard"""
    return HTMLResponse(content=open("static/index.html").read())

@app.get("/api/projects")
async def list_projects():
    """List all projects with their current status"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
    projects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Fetch live status for each project
    for project in projects:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"http://localhost:{project['api_port']}/api/status")
                status_data = response.json()
                project['live_status'] = status_data
                project['online'] = True
        except:
            project['online'] = False
            project['live_status'] = None
    
    return projects

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get detailed project info including live status"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    conn.close()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_dict = dict(project)
    project_dict['live_status'] = await fetch_project_status(project_id)
    
    return project_dict

@app.post("/api/projects")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO projects (id, name, description, icon, color)
        VALUES (?, ?, ?, ?, ?)
    """, (project.id, project.name, project.description, project.icon, project.color))
    
    conn.commit()
    conn.close()
    
    return {"message": "Project created", "project_id": project.id}

# =============================================================================
# API Routes - Memory/Learnings
# =============================================================================

@app.get("/api/memory")
async def get_memory(project_id: Optional[str] = None, category: Optional[str] = None):
    """Get learnings/memory, optionally filtered by project or category"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM learnings WHERE 1=1"
    params = []
    
    if project_id:
        query += " AND (project_id = ? OR project_id IS NULL)"
        params.append(project_id)
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    query += " ORDER BY created_at DESC LIMIT 50"
    
    cursor.execute(query, params)
    learnings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return learnings

@app.post("/api/memory")
async def add_learning(learning: LearningCreate):
    """Add a new learning/memory"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO learnings (project_id, category, learning, context)
        VALUES (?, ?, ?, ?)
    """, (learning.project_id, learning.category, learning.learning, learning.context))
    
    conn.commit()
    learning_id = cursor.lastrowid
    conn.close()
    
    return {"message": "Learning saved", "id": learning_id}

@app.get("/api/memory/categories")
async def get_memory_categories():
    """Get all learning categories"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM learnings")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

# =============================================================================
# API Routes - Global Activity
# =============================================================================

@app.get("/api/activity")
async def get_global_activity(limit: int = 50):
    """Get activity across all projects"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM global_activity 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    activities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return activities

# =============================================================================
# API Routes - Dashboard Summary
# =============================================================================

@app.get("/api/summary")
async def get_dashboard_summary():
    """Get complete dashboard summary - all projects, metrics, activity"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all projects
    cursor.execute("SELECT * FROM projects")
    projects = [dict(row) for row in cursor.fetchall()]
    
    # Get recent learnings
    cursor.execute("SELECT * FROM learnings ORDER BY created_at DESC LIMIT 10")
    recent_learnings = [dict(row) for row in cursor.fetchall()]
    
    # Get recent activity
    cursor.execute("SELECT * FROM global_activity ORDER BY created_at DESC LIMIT 10")
    recent_activity = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Fetch live status for active projects
    project_statuses = []
    for project in projects:
        status = {"project": project, "online": False}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"http://localhost:{project['api_port']}/api/status")
                status['live'] = response.json()
                status['online'] = True
        except:
            status['live'] = None
        project_statuses.append(status)
    
    return {
        "projects": project_statuses,
        "total_projects": len(projects),
        "active_projects": sum(1 for p in project_statuses if p['online']),
        "recent_learnings": recent_learnings,
        "recent_activity": recent_activity
    }

# =============================================================================
# API Routes - Meta Brain Chat
# =============================================================================

@app.post("/api/brain/chat")
async def chat_with_meta_brain(chat: ChatMessage):
    """Chat with the meta-brain that sees all projects"""
    
    # Get current state of all projects
    summary = await get_dashboard_summary()
    
    # Build context
    projects_context = "\n".join([
        f"- {p['project']['name']} ({p['project']['icon']}): {'Online' if p['online'] else 'Offline'}" +
        (f" - {p['live'].get('summary', {}).get('phase', 'Unknown phase')}" if p.get('live') else "")
        for p in summary['projects']
    ])
    
    learnings_context = "\n".join([
        f"- [{l['category']}] {l['learning']}"
        for l in summary['recent_learnings'][:5]
    ]) if summary['recent_learnings'] else "No learnings recorded yet."
    
    prompt = f"""Current state of all projects:
{projects_context}

Recent learnings:
{learnings_context}

Total projects: {summary['total_projects']}
Active projects: {summary['active_projects']}

User question: {chat.message}

Provide a helpful, actionable response."""

    response = await ask_meta_brain(prompt)
    
    return {
        "response": response,
        "context": {
            "total_projects": summary['total_projects'],
            "active_projects": summary['active_projects']
        }
    }

# =============================================================================
# Static Files
# =============================================================================

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

