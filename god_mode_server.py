#!/usr/bin/env python3
"""
God Mode Web Dashboard
The unified visual command center for Full Potential OS.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
import uvicorn
import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

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
STAGING_DIR = Path("STAGING/incoming")

# Ensure templates dir exists
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR.mkdir(parents=True)

TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_DIR))

# --- Dashboard HTML Template ---
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#020617">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="https://fav.farm/🏛️">
    <link rel="icon" href="https://fav.farm/🏛️">
    <title>🏛️ GOD MODE</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;500;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #020617;
            --panel: #0f172a;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --accent: #fbbf24; /* Gold for God Mode */
            --blue: #38bdf8;
            --red: #ef4444;
            --green: #22c55e;
            --border: #1e293b;
        }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            min-height: 100vh;
            -webkit-tap-highlight-color: transparent;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            padding-bottom: 6rem; /* Space for bottom nav on mobile if needed */
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.5rem;
        }
        h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2rem;
            margin: 0;
            color: var(--accent);
            letter-spacing: -0.02em;
        }
        .subtitle {
            color: var(--text-dim);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }
        
        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
        }
        
        /* Cards */
        .card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: transform 0.2s, border-color 0.2s;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .card:active {
            transform: scale(0.98);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.2rem;
        }
        .card-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .status-badge {
            font-size: 0.7rem;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.1);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        .status-active { background: rgba(34, 197, 94, 0.15); color: var(--green); border: 1px solid rgba(34, 197, 94, 0.3); }
        .status-idle { background: rgba(148, 163, 184, 0.1); color: var(--text-dim); }
        
        /* Lists */
        .item-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .item {
            padding: 1rem;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid rgba(255,255,255,0.03);
        }
        .item-title { font-weight: 500; font-size: 0.95rem; }
        .item-meta { color: var(--text-dim); font-size: 0.8rem; }
        
        /* Actions */
        .actions {
            display: flex;
            gap: 0.75rem;
            margin-top: 1.5rem;
        }
        .btn {
            background: var(--accent);
            color: #0f172a;
            border: none;
            padding: 0.8rem 1.5rem;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: opacity 0.2s;
            font-size: 0.95rem;
            width: auto;
        }
        .btn:hover { opacity: 0.9; }
        .btn-outline {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text);
        }
        .btn-outline:hover {
            border-color: var(--text);
            background: rgba(255,255,255,0.03);
        }
        
        /* Stats */
        .stat-row {
            display: flex;
            gap: 1.5rem;
            margin-bottom: 2rem;
            overflow-x: auto;
            padding-bottom: 0.5rem; /* Scrollbar space */
        }
        .stat {
            background: var(--panel);
            padding: 1.25rem;
            border-radius: 12px;
            flex: 1;
            min-width: 140px; /* Prevent squishing on mobile */
            text-align: center;
            border: 1px solid var(--border);
        }
        .stat-val {
            font-size: 2rem;
            font-weight: 700;
            font-family: 'Space Grotesk', sans-serif;
            color: var(--text);
        }
        .stat-label {
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.7rem;
            margin-top: 0.4rem;
        }

        /* Mobile Optimization */
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            header {
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }
            header .btn {
                width: 100%;
            }
            .grid {
                grid-template-columns: 1fr;
            }
            .stat-row {
                gap: 1rem;
            }
            .stat-val {
                font-size: 1.75rem;
            }
            .card {
                padding: 1.25rem;
            }
            .btn {
                width: 100%;
                padding: 1rem; /* Larger touch target */
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🏛️ THE COUNCIL</h1>
                <div class="subtitle">God Mode Control Center • {{ timestamp }}</div>
            </div>
            <div>
                <a href="/librarian" target="_blank" class="btn">
                    📚 Manage Library
                </a>
                <a href="/research" target="_blank" class="btn btn-outline" style="margin-left: 0.5rem;">
                    🌐 Public Site
                </a>
            </div>
        </header>

        <div class="stat-row">
            <div class="stat">
                <div class="stat-val">{{ stats.intents }}</div>
                <div class="stat-label">Active Missions</div>
            </div>
            <div class="stat">
                <div class="stat-val">{{ stats.claims }}</div>
                <div class="stat-label">Agents Working</div>
            </div>
            <div class="stat">
                <div class="stat-val">{{ stats.papers }}</div>
                <div class="stat-label">Papers Indexed</div>
            </div>
        </div>

        <div class="grid">
            <!-- BRAIN -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🧠 Strategy (Brain)</div>
                    <span class="status-badge {{ 'status-active' if stats.intents > 0 else 'status-idle' }}">
                        {{ 'Active' if stats.intents > 0 else 'Idle' }}
                    </span>
                </div>
                <ul class="item-list">
                    {% for intent in intents %}
                    <li class="item">
                        <div class="item-title">{{ intent.name }}</div>
                        <div class="item-meta">Priority: {{ intent.score }}</div>
                    </li>
                    {% else %}
                    <li class="item" style="justify-content:center; color:var(--text-dim);">No active missions</li>
                    {% endfor %}
                </ul>
                <div class="actions">
                    <button class="btn btn-outline" style="width:100%" onclick="dispatchMission()">+ Dispatch New Mission</button>
                </div>
            </div>

            <!-- MUSCLE -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">💪 Execution (Muscle)</div>
                    <span class="status-badge {{ 'status-active' if stats.claims > 0 else 'status-idle' }}">
                        {{ 'Working' if stats.claims > 0 else 'Resting' }}
                    </span>
                </div>
                <ul class="item-list">
                    {% for claim in claims %}
                    <li class="item">
                        <div class="item-title">{{ claim.name }}</div>
                        <div class="item-meta">Active</div>
                    </li>
                    {% else %}
                    <li class="item" style="justify-content:center; color:var(--text-dim);">All agents idle</li>
                    {% endfor %}
                </ul>
            </div>

            <!-- KNOWLEDGE -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🛡️ Knowledge (Immunity)</div>
                    <span class="status-badge status-active">Secure</span>
                </div>
                <div style="text-align:center; padding: 1rem 0;">
                    <p style="color:var(--text-dim); margin-bottom:1.5rem; font-size: 0.9rem;">
                        Review incoming research, classify documents, and synthesize new insights.
                    </p>
                    <a href="/librarian" class="btn btn-outline" style="width:100%">Manage Library →</a>
                </div>
            </div>
        </div>
    </div>

    <script>
        function dispatchMission() {
            const name = prompt("Mission Name (e.g. optimize-db):");
            if(name) {
                fetch('/api/dispatch', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name})
                }).then(() => window.location.reload());
            }
        }
    </script>
</body>
</html>
"""

# Write template
with open(TEMPLATES_DIR / "god_mode.html", "w") as f:
    f.write(DASHBOARD_HTML)

@app.get("/manifest.json")
async def manifest():
    return {
        "name": "God Mode",
        "short_name": "The Council",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#020617",
        "theme_color": "#020617",
        "icons": [
            {
                "src": "https://fav.farm/🏛️",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    }

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Gather Stats
    intents = []
    if INTENTS_DIR.exists():
        for f in INTENTS_DIR.glob("*.json"):
            try:
                with open(f) as json_file:
                    data = json.load(json_file)
                    intents.append({"name": f.stem, "score": data.get("score", 50)})
            except:
                pass
    
    claims = []
    if CLAIMS_DIR.exists():
        claims = [{"name": f.stem} for f in CLAIMS_DIR.glob("*.claim")]

    # Count papers (approx)
    papers_count = 0
    index_path = BASE_DIR / "fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/papers.json"
    if index_path.exists():
        with open(index_path) as f:
            data = json.load(f)
            papers_count = len(data.get("papers", []))

    return TEMPLATES.TemplateResponse("god_mode.html", {
        "request": request,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "stats": {
            "intents": len(intents),
            "claims": len(claims),
            "papers": papers_count
        },
        "intents": intents,
        "claims": claims
    })

@app.get("/librarian")
async def open_librarian():
    # If mounted, redirect to the internal app path
    if LIBRARIAN_AVAILABLE:
        return RedirectResponse(url="/librarian_app/")
    # Fallback to expected port if running separately
    return RedirectResponse(url="http://localhost:8081")

@app.get("/research")
async def open_research_page():
    # Adjust path if the file moved or serve content directly
    research_path = BASE_DIR / "fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/research.html"
    
    # Fallback: Search for it if path structure is different in dev
    if not research_path.exists():
        # Try to find it in the workspace relative to root
        # Assuming we are in root/god_mode_server.py
        research_path = Path("fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/research.html")
    
    if research_path.exists():
        return FileResponse(research_path)
        
    return HTMLResponse("Research page not found. Please ensure 'research.html' exists.")

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
    return {"status": "ok"}

if __name__ == "__main__":
    print("🏛️  GOD MODE WEB SERVER running at http://localhost:8085")
    uvicorn.run(app, host="0.0.0.0", port=8085)
