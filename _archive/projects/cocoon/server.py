"""
COCOON Command Center - Backend Server
Business 2.0 with AI

A collaborative command center where multiple assistants can execute the COCOON project.
AI (Cursor) can read progress and help James dynamically update tasks.
Features an intelligent "Brain" that responds to inputs and guides progress.
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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

APP_PASSWORD = "cocoon2026"  # Simple auth - change in production
DATABASE_PATH = "cocoon.db"
PORT = 8650

import os as _os

# Telegram notifications to James
TELEGRAM_BOT_TOKEN = _os.environ.get("TELEGRAM_BOT_TOKEN", "")
JAMES_CHAT_ID = _os.environ.get("JAMES_CHAT_ID", "1759822075")

# AI Brain Configuration - Uses centralized key from /opt/fpai/api_keys.json
ANTHROPIC_API_KEY = _os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = _os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Project Configuration
PROJECT_CONFIG = {
    "name": "COCOON",
    "goal": "Get the first cocoon prototype built and into use as fast as possible",
    "phases": [
        {"id": "research", "name": "Research & Sourcing", "focus": "Find fabricators and add them to tracker"},
        {"id": "outreach", "name": "Outreach", "focus": "Contact all fabricators with outreach messages"},
        {"id": "evaluation", "name": "Evaluation", "focus": "Evaluate responses, schedule calls, get quotes"},
        {"id": "selection", "name": "Selection", "focus": "Compare options and select the best fabricator"}
    ]
}

async def notify_james(message: str):
    """Send Telegram notification to James"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "chat_id": JAMES_CHAT_ID,
                "text": f"🥚 COCOON Update:\n\n{message}",
                "parse_mode": "HTML"
            })
    except Exception as e:
        print(f"Telegram notification failed: {e}")

# =============================================================================
# AI Brain Functions
# =============================================================================

async def ask_brain(prompt: str, context: Dict = None) -> str:
    """Ask the AI brain for guidance"""
    system_prompt = f"""You are the intelligent brain behind the {PROJECT_CONFIG['name']} project.

PROJECT GOAL: {PROJECT_CONFIG['goal']}

Your job is to:
1. Analyze the current state of the project
2. Provide clear, actionable guidance  
3. Keep things moving forward
4. Be encouraging but direct

Be concise. Be direct. Focus on the ONE most important next action.
Never suggest things that aren't directly relevant to building the cocoon prototype.
Maximum 2-3 sentences.
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
                    "max_tokens": 300,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            data = response.json()
            return data.get("content", [{}])[0].get("text", "Keep making progress!")
    except Exception as e:
        print(f"Brain error: {e}")
        return "Keep finding fabricators and adding them to the tracker!"

def determine_phase(metrics: Dict) -> Dict:
    """Determine current project phase based on metrics"""
    miami = metrics.get("miami_builders", 0)
    china = metrics.get("china_contacts", 0)
    contacted = metrics.get("contacted", 0)
    total = metrics.get("total_builders", 0)
    replies = metrics.get("replies", 0)
    quotes = metrics.get("quotes", 0)
    
    if miami < 5 or china < 2:
        return PROJECT_CONFIG["phases"][0]  # Research
    elif total > 0 and contacted < total:
        return PROJECT_CONFIG["phases"][1]  # Outreach
    elif replies > 0 and quotes < 2:
        return PROJECT_CONFIG["phases"][2]  # Evaluation
    else:
        return PROJECT_CONFIG["phases"][3]  # Selection

async def generate_guidance_for_event(event_type: str, details: Dict, metrics: Dict) -> str:
    """Generate intelligent guidance based on an event"""
    phase = determine_phase(metrics)
    
    prompt = f"""Event: {event_type}
Details: {json.dumps(details)}

Current state:
- Phase: {phase['name']} ({phase['focus']})
- Miami builders: {metrics.get('miami_builders', 0)}/5
- China contacts: {metrics.get('china_contacts', 0)}/3
- Contacted: {metrics.get('contacted', 0)}/{metrics.get('total_builders', 0)}
- Replies: {metrics.get('replies', 0)}

What should the assistant do next? Give ONE clear action."""

    return await ask_brain(prompt)

# =============================================================================
# App Setup
# =============================================================================

app = FastAPI(title="COCOON Command Center", version="1.0.0")

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
    
    # Builders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS builders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            type TEXT NOT NULL,
            contact TEXT,
            cost_range TEXT,
            timeline TEXT,
            materials TEXT,
            status TEXT DEFAULT 'Not contacted',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week INTEGER NOT NULL,
            day INTEGER NOT NULL,
            description TEXT NOT NULL,
            completed BOOLEAN DEFAULT FALSE,
            completed_at TIMESTAMP,
            time_spent_minutes INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0
        )
    """)
    
    # Add time_spent_minutes column if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN time_spent_minutes INTEGER DEFAULT 0")
    except:
        pass  # Column already exists
    
    # Time entries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clock_in TIMESTAMP NOT NULL,
            clock_out TIMESTAMP,
            duration_minutes INTEGER,
            notes TEXT
        )
    """)
    
    # Weekly reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week INTEGER NOT NULL,
            moved_forward TEXT,
            blocked TEXT,
            needs_decision TEXT,
            recommendation TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Settings table (for current week/day tracking)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Assistants table - track who's working on the project
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assistants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_time_minutes INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            builders_added INTEGER DEFAULT 0
        )
    """)
    
    # Activity log - track all actions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assistant_id INTEGER,
            assistant_name TEXT,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assistant_id) REFERENCES assistants(id)
        )
    """)
    
    # Add assistant tracking columns to existing tables (migrations)
    try:
        cursor.execute("ALTER TABLE builders ADD COLUMN added_by_assistant_id INTEGER")
        cursor.execute("ALTER TABLE builders ADD COLUMN added_by_name TEXT")
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN completed_by_assistant_id INTEGER")
        cursor.execute("ALTER TABLE tasks ADD COLUMN completed_by_name TEXT")
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE time_entries ADD COLUMN assistant_id INTEGER")
        cursor.execute("ALTER TABLE time_entries ADD COLUMN assistant_name TEXT")
    except:
        pass
    
    conn.commit()
    conn.close()

def seed_initial_data():
    """Seed the database with initial tasks from Week 1 checklist"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if tasks already exist
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    # Week 1 Tasks
    tasks = [
        # Day 1
        (1, 1, "Read ASSISTANT_SOP.md (understand mission and boundaries)", 1),
        (1, 1, "Open TRACKER in Command Center", 2),
        (1, 1, "Identify 5 Miami fabricators", 3),
        (1, 1, "Add all 5 Miami fabricators to tracker with contact info", 4),
        (1, 1, "Identify 2-3 China sourcing contacts", 5),
        (1, 1, "Add all China contacts to tracker", 6),
        # Day 2
        (1, 2, "Copy Miami outreach message from Outreach section", 1),
        (1, 2, "Send outreach to all 5 Miami fabricators", 2),
        (1, 2, "Update tracker status to 'Contacted' for Miami", 3),
        (1, 2, "Copy China outreach message from Outreach section", 4),
        (1, 2, "Send outreach to all China contacts", 5),
        (1, 2, "Update tracker status to 'Contacted' for China", 6),
        # Day 3
        (1, 3, "Check for replies from Miami fabricators", 1),
        (1, 3, "Check for replies from China contacts", 2),
        (1, 3, "Update tracker with responses (cost, timeline, materials)", 3),
        (1, 3, "Change status to 'Replied' for responders", 4),
        (1, 3, "Send follow-up to non-responders", 5),
        (1, 3, "Identify top 1-2 Miami builders", 6),
        # Day 4
        (1, 4, "Schedule call with top Miami builder #1", 1),
        (1, 4, "Schedule call with top Miami builder #2 (if applicable)", 2),
        (1, 4, "Schedule call with top China contact", 3),
        (1, 4, "Send calendar invites with brief agenda", 4),
        (1, 4, "Update tracker status to 'Call scheduled'", 5),
        # Day 5
        (1, 5, "Review all tracker data", 1),
        (1, 5, "Write summary: Best Miami builder option(s)", 2),
        (1, 5, "Write summary: Real cost ranges received", 3),
        (1, 5, "Write summary: Real timelines quoted", 4),
        (1, 5, "Write summary: China feasibility + unit cost", 5),
        (1, 5, "Write recommendation (2-3 sentences)", 6),
        (1, 5, "Submit weekly report to James", 7),
    ]
    
    for week, day, desc, order in tasks:
        cursor.execute(
            "INSERT INTO tasks (week, day, description, sort_order) VALUES (?, ?, ?, ?)",
            (week, day, desc, order)
        )
    
    # Set initial settings
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('current_week', '1')")
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('current_day', '1')")
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('start_date', ?)", 
                   (datetime.now().strftime('%Y-%m-%d'),))
    
    conn.commit()
    conn.close()

# Initialize on startup
init_db()
seed_initial_data()

# =============================================================================
# Pydantic Models
# =============================================================================

# =============================================================================
# Models - Assistants & Activity
# =============================================================================

class AssistantRegister(BaseModel):
    name: str
    email: Optional[str] = None

class ActivityCreate(BaseModel):
    assistant_id: Optional[int] = None
    assistant_name: Optional[str] = None
    action: str
    details: Optional[str] = None

# =============================================================================
# Models - Builders & Tasks
# =============================================================================

class Builder(BaseModel):
    name: str
    location: str  # "Miami" or "China"
    type: str  # "Local fabricator" or "Sourcing agent"
    contact: Optional[str] = None
    cost_range: Optional[str] = None
    assistant_id: Optional[int] = None
    assistant_name: Optional[str] = None
    timeline: Optional[str] = None
    materials: Optional[str] = None
    status: str = "Not contacted"
    notes: Optional[str] = None

class BuilderUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    contact: Optional[str] = None
    cost_range: Optional[str] = None
    timeline: Optional[str] = None
    materials: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class TaskUpdate(BaseModel):
    completed: Optional[bool] = None
    time_spent_minutes: Optional[int] = None
    assistant_id: Optional[int] = None
    assistant_name: Optional[str] = None

class TimeEntry(BaseModel):
    notes: Optional[str] = None
    assistant_id: Optional[int] = None
    assistant_name: Optional[str] = None

class WeeklyReport(BaseModel):
    week: int
    moved_forward: str
    blocked: Optional[str] = None
    needs_decision: Optional[str] = None
    recommendation: str

# =============================================================================
# API Routes - Status
# =============================================================================

@app.get("/api/status")
def get_full_status():
    """Get complete current state - for AI director queries"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get settings
    cursor.execute("SELECT key, value FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    
    # Get all builders
    cursor.execute("SELECT * FROM builders ORDER BY location, created_at")
    builders = [dict(row) for row in cursor.fetchall()]
    
    # Get current week tasks
    current_week = int(settings.get('current_week', 1))
    cursor.execute("SELECT * FROM tasks WHERE week = ? ORDER BY day, sort_order", (current_week,))
    tasks = [dict(row) for row in cursor.fetchall()]
    
    # Get time entries for this week
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    cursor.execute("SELECT * FROM time_entries WHERE clock_in >= ?", (week_start.strftime('%Y-%m-%d'),))
    time_entries = [dict(row) for row in cursor.fetchall()]
    
    # Calculate metrics
    total_builders = len(builders)
    miami_builders = [b for b in builders if b['location'] == 'Miami']
    china_builders = [b for b in builders if b['location'] == 'China']
    contacted = len([b for b in builders if b['status'] != 'Not contacted'])
    replied = len([b for b in builders if b['status'] in ['Replied', 'Call scheduled', 'Quoted', 'Selected']])
    calls_scheduled = len([b for b in builders if b['status'] == 'Call scheduled'])
    
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t['completed']])
    task_time_minutes = sum(t.get('time_spent_minutes', 0) or 0 for t in tasks)
    
    total_hours = sum(t.get('duration_minutes', 0) or 0 for t in time_entries) / 60
    
    # Check if currently clocked in
    cursor.execute("SELECT * FROM time_entries WHERE clock_out IS NULL ORDER BY clock_in DESC LIMIT 1")
    active_session = cursor.fetchone()
    
    conn.close()
    
    return {
        "settings": settings,
        "builders": {
            "total": total_builders,
            "miami": miami_builders,
            "china": china_builders,
            "contacted": contacted,
            "replied": replied,
            "calls_scheduled": calls_scheduled
        },
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "progress_percent": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0),
            "total_time_minutes": task_time_minutes,
            "items": tasks
        },
        "time": {
            "hours_this_week": round(total_hours, 1),
            "currently_clocked_in": active_session is not None,
            "active_session_start": dict(active_session)['clock_in'] if active_session else None
        }
    }

# =============================================================================
# API Routes - Assistants
# =============================================================================

@app.post("/api/assistants/register")
async def register_assistant(assistant: AssistantRegister):
    """Register a new assistant or return existing one"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if assistant already exists by name
    cursor.execute("SELECT * FROM assistants WHERE name = ?", (assistant.name,))
    existing = cursor.fetchone()
    
    if existing:
        # Update last_active
        cursor.execute("UPDATE assistants SET last_active = CURRENT_TIMESTAMP WHERE id = ?", (existing['id'],))
        conn.commit()
        conn.close()
        return {"id": existing['id'], "name": existing['name'], "message": "Welcome back!"}
    
    # Create new assistant
    cursor.execute(
        "INSERT INTO assistants (name, email) VALUES (?, ?)",
        (assistant.name, assistant.email)
    )
    conn.commit()
    assistant_id = cursor.lastrowid
    conn.close()
    
    # Log activity
    log_activity(assistant_id, assistant.name, "joined", f"{assistant.name} joined the project")
    
    # Notify James
    await notify_james(f"🆕 New assistant joined: <b>{assistant.name}</b>")
    
    return {"id": assistant_id, "name": assistant.name, "message": "Welcome to COCOON!"}

@app.get("/api/assistants")
def list_assistants():
    """List all assistants with their stats"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, created_at, last_active, 
               total_time_minutes, tasks_completed, builders_added
        FROM assistants 
        ORDER BY last_active DESC
    """)
    assistants = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return assistants

@app.get("/api/assistants/active")
def get_active_assistants():
    """Get assistants active in the last 30 minutes"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM assistants 
        WHERE last_active > datetime('now', '-30 minutes')
        ORDER BY last_active DESC
    """)
    active = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return active

def log_activity(assistant_id: int, assistant_name: str, action: str, details: str):
    """Log an activity to the activity feed"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_log (assistant_id, assistant_name, action, details) VALUES (?, ?, ?, ?)",
        (assistant_id, assistant_name, action, details)
    )
    conn.commit()
    conn.close()

# =============================================================================
# API Routes - Activity Feed
# =============================================================================

@app.get("/api/activity")
def get_activity_feed(limit: int = 50):
    """Get recent activity from all assistants"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM activity_log 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    activities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return activities

@app.post("/api/activity")
def create_activity(activity: ActivityCreate):
    """Log a new activity"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_log (assistant_id, assistant_name, action, details) VALUES (?, ?, ?, ?)",
        (activity.assistant_id, activity.assistant_name, activity.action, activity.details)
    )
    conn.commit()
    conn.close()
    return {"message": "Activity logged"}

# =============================================================================
# API Routes - AI Summary (For Cursor/James to read progress)
# =============================================================================

@app.get("/api/ai/summary")
def get_ai_summary():
    """
    Comprehensive summary for AI (Cursor) to read and help James update the project.
    This endpoint provides everything needed to understand current state.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all builders
    cursor.execute("SELECT * FROM builders ORDER BY created_at DESC")
    builders = [dict(row) for row in cursor.fetchall()]
    
    # Get all tasks with completion status
    cursor.execute("SELECT * FROM tasks ORDER BY week, day, sort_order")
    tasks = [dict(row) for row in cursor.fetchall()]
    
    # Get all assistants
    cursor.execute("SELECT * FROM assistants ORDER BY last_active DESC")
    assistants = [dict(row) for row in cursor.fetchall()]
    
    # Get recent activity
    cursor.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 20")
    recent_activity = [dict(row) for row in cursor.fetchall()]
    
    # Calculate metrics
    miami_builders = [b for b in builders if b['location'] == 'Miami']
    china_builders = [b for b in builders if b['location'] == 'China']
    completed_tasks = [t for t in tasks if t['completed']]
    total_time = sum(t.get('time_spent_minutes', 0) or 0 for t in tasks)
    
    # Current blockers (tasks not progressing)
    day1_tasks = [t for t in tasks if t['day'] == 1]
    day1_incomplete = [t for t in day1_tasks if not t['completed']]
    
    conn.close()
    
    return {
        "summary": {
            "miami_builders_found": len(miami_builders),
            "miami_builders_needed": 5,
            "china_contacts_found": len(china_builders),
            "china_contacts_needed": 3,
            "tasks_completed": len(completed_tasks),
            "tasks_total": len(tasks),
            "total_time_logged_minutes": total_time,
            "active_assistants": len([a for a in assistants if a.get('last_active')]),
        },
        "progress_assessment": {
            "phase": "Research & Sourcing" if len(miami_builders) < 5 else "Outreach",
            "next_milestone": f"Find {5 - len(miami_builders)} more Miami fabricators" if len(miami_builders) < 5 else "Contact all fabricators",
            "blockers": [t['description'] for t in day1_incomplete[:3]] if day1_incomplete else [],
        },
        "recent_activity": recent_activity[:10],
        "all_builders": builders,
        "all_tasks": tasks,
        "all_assistants": assistants,
        "recommendations": generate_recommendations(miami_builders, china_builders, completed_tasks, assistants)
    }

def generate_recommendations(miami_builders, china_builders, completed_tasks, assistants):
    """Generate AI recommendations based on current state"""
    recs = []
    
    if len(miami_builders) < 5:
        recs.append(f"Need {5 - len(miami_builders)} more Miami fabricators. Consider: scenic shops, event prop builders, marine upholstery.")
    
    if len(china_builders) < 2:
        recs.append(f"Need {2 - len(china_builders)} more China contacts. Search Alibaba for 'inflatable dome tent' or 'soft enclosure'.")
    
    contacted = [b for b in miami_builders if b['status'] != 'Not contacted']
    if len(miami_builders) >= 5 and len(contacted) < len(miami_builders):
        recs.append(f"Have {len(miami_builders)} Miami builders but only {len(contacted)} contacted. Time to send outreach!")
    
    if not assistants:
        recs.append("No assistants have registered yet. Share the dashboard link to get started.")
    
    if not recs:
        recs.append("Great progress! Review builders and prepare for next phase.")
    
    return recs

# =============================================================================
# API Routes - Brain (Intelligent Project Guidance)
# =============================================================================

class BrainQuery(BaseModel):
    question: str
    assistant_name: Optional[str] = None

@app.get("/api/brain/status")
async def get_brain_status():
    """Get current brain status and project phase"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT location, status FROM builders")
    builders = cursor.fetchall()
    
    miami = len([b for b in builders if b[0] == 'Miami'])
    china = len([b for b in builders if b[0] == 'China'])
    contacted = len([b for b in builders if b[1] != 'Not contacted'])
    replied = len([b for b in builders if b[1] in ('Replied', 'Call scheduled', 'Quoted', 'Selected')])
    
    conn.close()
    
    metrics = {
        "miami_builders": miami,
        "china_contacts": china,
        "total_builders": len(builders),
        "contacted": contacted,
        "replies": replied
    }
    
    phase = determine_phase(metrics)
    
    return {
        "project": PROJECT_CONFIG["name"],
        "goal": PROJECT_CONFIG["goal"],
        "current_phase": phase,
        "metrics": metrics,
        "brain_active": True
    }

@app.get("/api/brain/next-step")
async def get_next_step(assistant_name: Optional[str] = None):
    """Get AI-generated guidance for the next step"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT location, status FROM builders")
    builders = cursor.fetchall()
    
    miami = len([b for b in builders if b[0] == 'Miami'])
    china = len([b for b in builders if b[0] == 'China'])
    contacted = len([b for b in builders if b[1] != 'Not contacted'])
    replied = len([b for b in builders if b[1] in ('Replied', 'Call scheduled', 'Quoted', 'Selected')])
    
    conn.close()
    
    metrics = {
        "miami_builders": miami,
        "china_contacts": china,
        "total_builders": len(builders),
        "contacted": contacted,
        "replies": replied
    }
    
    phase = determine_phase(metrics)
    
    prompt = f"""Current state:
- Phase: {phase['name']} ({phase['focus']})
- Miami builders: {miami}/5
- China contacts: {china}/3  
- Contacted: {contacted}/{len(builders)}
- Replies: {replied}

What is the ONE most important next action? Be specific and actionable."""

    guidance = await ask_brain(prompt)
    
    return {
        "phase": phase["name"],
        "guidance": guidance,
        "metrics": metrics
    }

class ChatMessage(BaseModel):
    message: str
    assistant_name: Optional[str] = None
    conversation_id: Optional[str] = None

@app.post("/api/brain/ask")
async def ask_brain_question(query: BrainQuery):
    """Ask the brain a question about the project"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM builders")
    builders = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM tasks WHERE completed = 1")
    completed = cursor.fetchall()
    
    conn.close()
    
    context_prompt = f"""Question from {query.assistant_name or 'an assistant'}: {query.question}

Project context:
- {len([b for b in builders if b['location'] == 'Miami'])} Miami fabricators found
- {len([b for b in builders if b['location'] == 'China'])} China contacts found
- {len(completed)} tasks completed

Answer helpfully and concisely."""

    answer = await ask_brain(context_prompt)
    
    return {"answer": answer, "asked_by": query.assistant_name}

@app.post("/api/brain/chat")
async def chat_with_brain(chat: ChatMessage):
    """
    Conversational chat with the project AI.
    The AI knows everything about the project and can help with any question.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Get full project context
    cursor.execute("SELECT * FROM builders ORDER BY created_at DESC")
    builders = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM tasks ORDER BY week, day")
    tasks = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM assistants ORDER BY last_active DESC LIMIT 5")
    assistants = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 10")
    recent_activity = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Calculate metrics
    miami = [b for b in builders if b['location'] == 'Miami']
    china = [b for b in builders if b['location'] == 'China']
    contacted = [b for b in builders if b['status'] != 'Not contacted']
    replied = [b for b in builders if b['status'] in ('Replied', 'Call scheduled', 'Quoted')]
    completed_tasks = [t for t in tasks if t['completed']]
    
    phase = determine_phase({
        "miami_builders": len(miami),
        "china_contacts": len(china),
        "total_builders": len(builders),
        "contacted": len(contacted),
        "replies": len(replied)
    })
    
    # Build rich context for the AI
    builders_summary = "\n".join([
        f"  - {b['name']} ({b['location']}, {b['status']})" + 
        (f" - {b['contact']}" if b.get('contact') else "")
        for b in builders[:10]
    ]) if builders else "  No builders added yet"
    
    activity_summary = "\n".join([
        f"  - {a['assistant_name']}: {a['details']}" 
        for a in recent_activity[:5]
    ]) if recent_activity else "  No recent activity"
    
    system_prompt = f"""You are the AI assistant for the COCOON project.

PROJECT: COCOON - One-person recovery cocoon for 12-minute nervous system resets
GOAL: Get the first cocoon prototype built and into use as fast as possible
CURRENT PHASE: {phase['name']} - {phase['focus']}

CURRENT STATE:
- Miami fabricators: {len(miami)}/5 found, {len([b for b in miami if b['status'] != 'Not contacted'])} contacted
- China contacts: {len(china)}/3 found
- Total builders in tracker: {len(builders)}
- Builders who replied: {len(replied)}
- Tasks completed: {len(completed_tasks)}/{len(tasks)}

BUILDERS IN TRACKER:
{builders_summary}

RECENT ACTIVITY:
{activity_summary}

WHAT THE COCOON IS:
- Soft inflatable dome that goes over someone lying on a mat
- Half-cylinder/tunnel arch shape, open at foot end  
- ~7ft long × 3ft wide × 3ft tall
- LED strips inside for warm amber glow
- NOT medical equipment - just a relaxation enclosure

YOUR ROLE:
- Help assistants understand what to do next
- Answer questions about the project
- Provide specific, actionable guidance
- Know all the context so they don't have to search
- Be encouraging but direct
- If they're stuck, help them get unstuck

Keep responses concise (2-4 sentences) unless they ask for details.
You ARE the project expert - speak with confidence about the cocoon and the plan."""

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
                    "messages": [{"role": "user", "content": chat.message}]
                }
            )
            data = response.json()
            answer = data.get("content", [{}])[0].get("text", "I'm having trouble thinking right now. Try again in a moment!")
    except Exception as e:
        print(f"Chat error: {e}")
        answer = "I'm having a brief connection issue. In the meantime: focus on finding fabricators and adding them to the tracker!"
    
    # Log the chat interaction
    if chat.assistant_name:
        log_activity(None, chat.assistant_name, "asked_brain", f"Asked: {chat.message[:50]}...")
    
    return {
        "response": answer,
        "phase": phase["name"],
        "context": {
            "miami_builders": len(miami),
            "china_contacts": len(china),
            "builders_contacted": len(contacted)
        }
    }

def log_activity(assistant_id, assistant_name, action, details):
    """Helper to log activity"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activity_log (assistant_id, assistant_name, action, details) VALUES (?, ?, ?, ?)",
            (assistant_id, assistant_name, action, details)
        )
        conn.commit()
        conn.close()
    except:
        pass

@app.post("/api/brain/event")
async def brain_event(event_type: str, details: Dict = {}):
    """Notify the brain of an event and get intelligent response"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT location, status FROM builders")
    builders = cursor.fetchall()
    
    miami = len([b for b in builders if b[0] == 'Miami'])
    china = len([b for b in builders if b[0] == 'China'])
    contacted = len([b for b in builders if b[1] != 'Not contacted'])
    replied = len([b for b in builders if b[1] in ('Replied', 'Call scheduled', 'Quoted', 'Selected')])
    
    conn.close()
    
    metrics = {
        "miami_builders": miami,
        "china_contacts": china,
        "total_builders": len(builders),
        "contacted": contacted,
        "replies": replied
    }
    
    guidance = await generate_guidance_for_event(event_type, details, metrics)
    
    # Check for milestone notifications
    notifications = []
    if event_type == "builder_added":
        if miami == 5 and details.get("location") == "Miami":
            notifications.append("🎯 All 5 Miami fabricators found! Moving to Outreach phase.")
            await notify_james("🎯 MILESTONE: All 5 Miami fabricators found!\n\nThe project is advancing to the Outreach phase.")
        elif china == 3 and details.get("location") == "China":
            notifications.append("🌏 All China contacts found!")
            await notify_james("🌏 MILESTONE: All 3 China contacts found!")
    
    return {
        "guidance": guidance,
        "notifications": notifications,
        "current_metrics": metrics
    }

# =============================================================================
# API Routes - Builders
# =============================================================================

@app.get("/api/builders")
def get_builders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM builders ORDER BY location, created_at")
    builders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return builders

@app.post("/api/builders")
async def create_builder(builder: Builder):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO builders (name, location, type, contact, cost_range, timeline, materials, status, notes, added_by_assistant_id, added_by_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (builder.name, builder.location, builder.type, builder.contact, 
          builder.cost_range, builder.timeline, builder.materials, builder.status, builder.notes,
          builder.assistant_id, builder.assistant_name))
    conn.commit()
    builder_id = cursor.lastrowid
    
    # Update assistant stats if we have assistant info
    if builder.assistant_id:
        cursor.execute("""
            UPDATE assistants SET builders_added = builders_added + 1, last_active = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (builder.assistant_id,))
        conn.commit()
    
    # Count total builders for milestone check
    cursor.execute("SELECT COUNT(*) FROM builders WHERE location = ?", (builder.location,))
    count = cursor.fetchone()[0]
    conn.close()
    
    # Log activity
    assistant_name = builder.assistant_name or "Unknown"
    log_activity(builder.assistant_id, assistant_name, "added_builder", 
                 f"Added {builder.location} builder: {builder.name}")
    
    # Notify James on milestones
    if builder.location == 'Miami' and count in [1, 3, 5]:
        await notify_james(f"📍 {assistant_name} added a Miami fabricator: <b>{builder.name}</b>\n\nProgress: {count}/5 Miami builders found!")
    elif builder.location == 'China' and count in [1, 2, 3]:
        await notify_james(f"🌏 {assistant_name} added a China contact: <b>{builder.name}</b>\n\nProgress: {count}/3 China contacts found!")
    
    return {"id": builder_id, "message": "Builder added"}

@app.put("/api/builders/{builder_id}")
def update_builder(builder_id: int, update: BuilderUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    # Build update query dynamically
    updates = []
    values = []
    for field, value in update.dict(exclude_unset=True).items():
        if value is not None:
            updates.append(f"{field} = ?")
            values.append(value)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(builder_id)
        query = f"UPDATE builders SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
    
    conn.close()
    return {"message": "Builder updated"}

@app.delete("/api/builders/{builder_id}")
def delete_builder(builder_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM builders WHERE id = ?", (builder_id,))
    conn.commit()
    conn.close()
    return {"message": "Builder deleted"}

# =============================================================================
# API Routes - Tasks
# =============================================================================

@app.get("/api/tasks")
def get_tasks(week: Optional[int] = None, day: Optional[int] = None):
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM tasks"
    params = []
    conditions = []
    
    if week:
        conditions.append("week = ?")
        params.append(week)
    if day:
        conditions.append("day = ?")
        params.append(day)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY week, day, sort_order"
    cursor.execute(query, params)
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

@app.put("/api/tasks/{task_id}")
async def update_task(task_id: int, update: TaskUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    # Get task description for logging
    cursor.execute("SELECT description FROM tasks WHERE id = ?", (task_id,))
    task_row = cursor.fetchone()
    task_desc = task_row['description'] if task_row else "Unknown task"
    
    # Build dynamic update
    updates = []
    values = []
    
    if update.completed is not None:
        updates.append("completed = ?")
        values.append(update.completed)
        
        if update.completed:
            updates.append("completed_at = ?")
            values.append(datetime.now().isoformat())
            if update.assistant_id:
                updates.append("completed_by_assistant_id = ?")
                values.append(update.assistant_id)
            if update.assistant_name:
                updates.append("completed_by_name = ?")
                values.append(update.assistant_name)
        else:
            updates.append("completed_at = NULL")
    
    if update.time_spent_minutes is not None:
        updates.append("time_spent_minutes = ?")
        values.append(update.time_spent_minutes)
    
    if updates:
        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
    
    # Update assistant stats if completing a task
    if update.completed and update.assistant_id:
        cursor.execute("""
            UPDATE assistants SET 
                tasks_completed = tasks_completed + 1, 
                total_time_minutes = total_time_minutes + ?,
                last_active = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (update.time_spent_minutes or 0, update.assistant_id))
        conn.commit()
        
        # Log activity
        time_str = f" ({update.time_spent_minutes}m)" if update.time_spent_minutes else ""
        log_activity(update.assistant_id, update.assistant_name, "completed_task", 
                     f"Completed: {task_desc[:50]}...{time_str}" if len(task_desc) > 50 else f"Completed: {task_desc}{time_str}")
    
    conn.close()
    return {"message": "Task updated"}

# =============================================================================
# API Routes - Time Tracking
# =============================================================================

@app.get("/api/time")
def get_time_entries():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM time_entries ORDER BY clock_in DESC")
    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return entries

@app.post("/api/time/clock-in")
def clock_in(entry: TimeEntry):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if already clocked in
    cursor.execute("SELECT * FROM time_entries WHERE clock_out IS NULL")
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Already clocked in")
    
    cursor.execute(
        "INSERT INTO time_entries (clock_in, notes) VALUES (?, ?)",
        (datetime.now().isoformat(), entry.notes)
    )
    conn.commit()
    entry_id = cursor.lastrowid
    conn.close()
    return {"id": entry_id, "message": "Clocked in"}

@app.post("/api/time/clock-out")
def clock_out():
    conn = get_db()
    cursor = conn.cursor()
    
    # Find active session
    cursor.execute("SELECT * FROM time_entries WHERE clock_out IS NULL ORDER BY clock_in DESC LIMIT 1")
    session = cursor.fetchone()
    
    if not session:
        conn.close()
        raise HTTPException(status_code=400, detail="Not clocked in")
    
    clock_out_time = datetime.now()
    clock_in_time = datetime.fromisoformat(session['clock_in'])
    duration = int((clock_out_time - clock_in_time).total_seconds() / 60)
    
    cursor.execute(
        "UPDATE time_entries SET clock_out = ?, duration_minutes = ? WHERE id = ?",
        (clock_out_time.isoformat(), duration, session['id'])
    )
    conn.commit()
    conn.close()
    return {"message": "Clocked out", "duration_minutes": duration}

@app.get("/api/time/status")
def get_time_status():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM time_entries WHERE clock_out IS NULL ORDER BY clock_in DESC LIMIT 1")
    session = cursor.fetchone()
    
    if session:
        clock_in_time = datetime.fromisoformat(session['clock_in'])
        elapsed = int((datetime.now() - clock_in_time).total_seconds() / 60)
        conn.close()
        return {"clocked_in": True, "since": session['clock_in'], "elapsed_minutes": elapsed}
    
    conn.close()
    return {"clocked_in": False}

# =============================================================================
# API Routes - Reports
# =============================================================================

@app.get("/api/reports")
def get_reports():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports ORDER BY submitted_at DESC")
    reports = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return reports

@app.post("/api/reports")
def submit_report(report: WeeklyReport):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reports (week, moved_forward, blocked, needs_decision, recommendation)
        VALUES (?, ?, ?, ?, ?)
    """, (report.week, report.moved_forward, report.blocked, report.needs_decision, report.recommendation))
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return {"id": report_id, "message": "Report submitted"}

# =============================================================================
# Static Files & Frontend
# =============================================================================

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serve the main dashboard"""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            return f.read()
    return "<h1>COCOON Command Center</h1><p>Frontend not found. Run deployment to set up static files.</p>"

# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

