"""
COCOON Project Brain - Autonomous Intelligence Layer

This brain monitors project inputs and responds intelligently:
- Analyzes progress and suggests next steps
- Sends guidance to assistants when needed
- Updates the project site dynamically
- Escalates to James when decisions are needed

Can be generalized for any project.
"""

import sqlite3
import json
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# =============================================================================
# Configuration
# =============================================================================

DATABASE_PATH = "cocoon.db"

import os as _os

# AI Configuration (Claude via Anthropic) — keys from env
ANTHROPIC_API_KEY = _os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = _os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Telegram (for sending guidance and escalations)
TELEGRAM_BOT_TOKEN = _os.environ.get("TELEGRAM_BOT_TOKEN", "")
JAMES_CHAT_ID = _os.environ.get("JAMES_CHAT_ID", "1759822075")

# Project Configuration
PROJECT_CONFIG = {
    "name": "COCOON",
    "goal": "Get the first cocoon prototype built and into use as fast as possible",
    "phases": [
        {
            "id": "research",
            "name": "Research & Sourcing",
            "trigger": "miami_builders < 5 or china_contacts < 2",
            "focus": "Find fabricators and add them to tracker"
        },
        {
            "id": "outreach", 
            "name": "Outreach",
            "trigger": "miami_builders >= 5 and china_contacts >= 2 and contacted < total_builders",
            "focus": "Contact all fabricators with outreach messages"
        },
        {
            "id": "evaluation",
            "name": "Evaluation",
            "trigger": "contacted >= total_builders and replies > 0",
            "focus": "Evaluate responses, schedule calls, get quotes"
        },
        {
            "id": "selection",
            "name": "Selection",
            "trigger": "quotes >= 2",
            "focus": "Compare options and select the best fabricator"
        }
    ],
    "milestones": [
        {"metric": "miami_builders", "target": 5, "message": "🎯 All 5 Miami fabricators found!"},
        {"metric": "china_contacts", "target": 3, "message": "🌏 All China contacts found!"},
        {"metric": "contacted", "target_percent": 100, "message": "📨 All fabricators contacted!"},
        {"metric": "replies", "target": 1, "message": "💬 First reply received!"},
    ]
}

# =============================================================================
# Database Functions
# =============================================================================

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_project_state() -> Dict[str, Any]:
    """Get the complete current state of the project"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get builders
    cursor.execute("SELECT * FROM builders ORDER BY created_at DESC")
    builders = [dict(row) for row in cursor.fetchall()]
    
    # Get tasks
    cursor.execute("SELECT * FROM tasks ORDER BY week, day, sort_order")
    tasks = [dict(row) for row in cursor.fetchall()]
    
    # Get assistants
    cursor.execute("SELECT * FROM assistants ORDER BY last_active DESC")
    assistants = [dict(row) for row in cursor.fetchall()]
    
    # Get recent activity
    cursor.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 20")
    activity = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Calculate metrics
    miami_builders = [b for b in builders if b['location'] == 'Miami']
    china_contacts = [b for b in builders if b['location'] == 'China']
    contacted = [b for b in builders if b['status'] != 'Not contacted']
    replied = [b for b in builders if b['status'] in ['Replied', 'Call scheduled', 'Quoted', 'Selected']]
    quoted = [b for b in builders if b['status'] == 'Quoted']
    
    completed_tasks = [t for t in tasks if t['completed']]
    
    return {
        "builders": builders,
        "tasks": tasks,
        "assistants": assistants,
        "activity": activity,
        "metrics": {
            "miami_builders": len(miami_builders),
            "china_contacts": len(china_contacts),
            "total_builders": len(builders),
            "contacted": len(contacted),
            "replies": len(replied),
            "quotes": len(quoted),
            "tasks_completed": len(completed_tasks),
            "tasks_total": len(tasks),
            "active_assistants": len([a for a in assistants if a.get('last_active')])
        }
    }

def determine_current_phase(metrics: Dict) -> Dict:
    """Determine which phase the project is in based on metrics"""
    for phase in PROJECT_CONFIG["phases"]:
        trigger = phase["trigger"]
        # Evaluate the trigger expression with metrics
        if eval(trigger, {"__builtins__": {}}, metrics):
            return phase
    return PROJECT_CONFIG["phases"][-1]  # Default to last phase

# =============================================================================
# AI Brain Functions
# =============================================================================

async def ask_brain(prompt: str, context: Dict) -> str:
    """Ask the AI brain for guidance"""
    system_prompt = f"""You are the intelligent brain behind the {PROJECT_CONFIG['name']} project.

PROJECT GOAL: {PROJECT_CONFIG['goal']}

Your job is to:
1. Analyze the current state of the project
2. Provide clear, actionable guidance
3. Keep things moving forward
4. Escalate to James only when truly needed

Be concise. Be direct. Focus on the ONE most important next action.
Never suggest things that aren't directly relevant to building the cocoon prototype.
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
            return data.get("content", [{}])[0].get("text", "Unable to generate response")
    except Exception as e:
        print(f"Brain error: {e}")
        return f"Brain temporarily unavailable: {e}"

async def generate_next_step_guidance(state: Dict) -> str:
    """Generate intelligent guidance for what to do next"""
    metrics = state["metrics"]
    phase = determine_current_phase(metrics)
    recent_activity = state["activity"][:5]
    
    prompt = f"""Current project state:
- Phase: {phase['name']}
- Miami builders found: {metrics['miami_builders']}/5
- China contacts found: {metrics['china_contacts']}/3
- Builders contacted: {metrics['contacted']}/{metrics['total_builders']}
- Replies received: {metrics['replies']}
- Active assistants: {metrics['active_assistants']}

Recent activity:
{json.dumps(recent_activity, indent=2, default=str)}

Based on this state, what is the ONE most important thing that should happen next?
Provide a short, direct instruction (max 2 sentences).
"""
    
    return await ask_brain(prompt, state)

async def analyze_assistant_progress(assistant_name: str, state: Dict) -> str:
    """Analyze how a specific assistant is doing and provide encouragement or guidance"""
    # Find assistant's contributions
    their_builders = [b for b in state["builders"] if b.get("added_by_name") == assistant_name]
    their_activity = [a for a in state["activity"] if a.get("assistant_name") == assistant_name]
    
    prompt = f"""Assistant "{assistant_name}" progress:
- Builders added: {len(their_builders)}
- Recent actions: {len(their_activity)} in activity log

Project needs: {5 - state['metrics']['miami_builders']} more Miami, {3 - state['metrics']['china_contacts']} more China contacts

Generate a brief (1-2 sentence) encouraging message for this assistant.
If they're doing great, celebrate. If they're stuck, gently guide.
"""
    
    return await ask_brain(prompt, state)

# =============================================================================
# Event Handlers - React to project inputs
# =============================================================================

async def on_builder_added(builder: Dict, assistant_name: str):
    """React when a new builder is added"""
    state = get_project_state()
    metrics = state["metrics"]
    
    responses = []
    
    # Check for milestone completion
    if builder["location"] == "Miami" and metrics["miami_builders"] == 5:
        responses.append({
            "type": "milestone",
            "message": "🎯 ALL 5 MIAMI FABRICATORS FOUND! Time to move to outreach phase.",
            "notify_james": True
        })
        # Could update the site here to show "Phase: Outreach"
        
    elif builder["location"] == "China" and metrics["china_contacts"] == 3:
        responses.append({
            "type": "milestone", 
            "message": "🌏 ALL CHINA CONTACTS FOUND! Great work on sourcing.",
            "notify_james": True
        })
    
    # Generate personalized feedback for the assistant
    encouragement = await analyze_assistant_progress(assistant_name, state)
    responses.append({
        "type": "encouragement",
        "message": encouragement,
        "notify_james": False
    })
    
    return responses

async def on_task_completed(task: Dict, assistant_name: str):
    """React when a task is completed"""
    state = get_project_state()
    
    # Generate next step guidance
    next_step = await generate_next_step_guidance(state)
    
    return [{
        "type": "guidance",
        "message": f"✅ Task done! Next: {next_step}",
        "notify_james": False
    }]

async def on_assistant_idle(assistant_name: str, idle_minutes: int):
    """React when an assistant has been idle for a while"""
    if idle_minutes < 10:
        return []
    
    state = get_project_state()
    
    # Generate a gentle nudge
    nudge = await generate_next_step_guidance(state)
    
    return [{
        "type": "nudge",
        "message": f"👋 Hey {assistant_name}, still there? {nudge}",
        "notify_james": False
    }]

async def on_daily_summary():
    """Generate a daily summary for James"""
    state = get_project_state()
    metrics = state["metrics"]
    phase = determine_current_phase(metrics)
    
    prompt = f"""Generate a brief daily summary for James about the COCOON project.

Current state:
- Phase: {phase['name']}
- Miami: {metrics['miami_builders']}/5
- China: {metrics['china_contacts']}/3
- Contacted: {metrics['contacted']}/{metrics['total_builders']}
- Tasks done: {metrics['tasks_completed']}/{metrics['tasks_total']}
- Active helpers: {metrics['active_assistants']}

Write 3-4 bullet points summarizing progress and what needs attention.
End with one clear recommendation.
"""
    
    summary = await ask_brain(prompt, state)
    
    return [{
        "type": "daily_summary",
        "message": f"📊 COCOON Daily Summary\n\n{summary}",
        "notify_james": True
    }]

# =============================================================================
# Notification Functions
# =============================================================================

async def send_telegram(message: str, chat_id: str = JAMES_CHAT_ID):
    """Send a Telegram notification"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            })
    except Exception as e:
        print(f"Telegram error: {e}")

async def process_brain_responses(responses: List[Dict]):
    """Process responses from the brain and take appropriate actions"""
    for response in responses:
        if response.get("notify_james"):
            await send_telegram(f"🧠 {PROJECT_CONFIG['name']} Brain:\n\n{response['message']}")
        
        # Could also:
        # - Update the website dynamically
        # - Send in-app notifications to assistants
        # - Log to activity feed
        # - Trigger other automations

# =============================================================================
# Main Brain Loop (for continuous monitoring)
# =============================================================================

async def brain_loop():
    """Main loop that continuously monitors and responds to project state"""
    print(f"🧠 {PROJECT_CONFIG['name']} Brain starting...")
    
    last_check = datetime.now()
    last_daily_summary = None
    
    while True:
        try:
            state = get_project_state()
            now = datetime.now()
            
            # Check for idle assistants
            for assistant in state["assistants"]:
                if assistant.get("last_active"):
                    last_active = datetime.fromisoformat(assistant["last_active"])
                    idle_mins = (now - last_active).total_seconds() / 60
                    if 10 <= idle_mins <= 15:  # Nudge once between 10-15 mins
                        responses = await on_assistant_idle(assistant["name"], idle_mins)
                        await process_brain_responses(responses)
            
            # Daily summary at 6pm
            if now.hour == 18 and (last_daily_summary is None or last_daily_summary.date() < now.date()):
                responses = await on_daily_summary()
                await process_brain_responses(responses)
                last_daily_summary = now
            
            last_check = now
            
        except Exception as e:
            print(f"Brain loop error: {e}")
        
        await asyncio.sleep(60)  # Check every minute

# =============================================================================
# API Endpoints (to be added to server.py)
# =============================================================================

"""
Add these endpoints to server.py to enable brain functionality:

@app.get("/api/brain/status")
async def get_brain_status():
    state = get_project_state()
    phase = determine_current_phase(state["metrics"])
    return {
        "project": PROJECT_CONFIG["name"],
        "phase": phase,
        "metrics": state["metrics"],
        "brain_active": True
    }

@app.get("/api/brain/next-step")
async def get_next_step():
    state = get_project_state()
    guidance = await generate_next_step_guidance(state)
    return {"guidance": guidance}

@app.post("/api/brain/ask")
async def ask_brain_endpoint(question: str):
    state = get_project_state()
    answer = await ask_brain(question, state)
    return {"answer": answer}
"""

if __name__ == "__main__":
    # Run the brain loop
    asyncio.run(brain_loop())

