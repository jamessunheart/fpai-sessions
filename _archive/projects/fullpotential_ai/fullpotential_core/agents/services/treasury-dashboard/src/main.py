"""
Treasury Dashboard - Visualize the $373K → $5T Journey
Live tracking of capital, vision, and progress toward paradise on Earth
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import re

app = FastAPI(title="Treasury Dashboard", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
TREASURY_DATA = BASE_DIR / "treasury_data.json"
CAPITAL_VISION = BASE_DIR / "docs" / "coordination" / "CAPITAL_VISION_SSOT.md"
TREASURY_JSON = BASE_DIR / "docs" / "coordination" / "treasury.json"

def load_treasury_data() -> Dict[str, Any]:
    """Load real-time treasury positions"""
    try:
        with open(TREASURY_DATA) as f:
            return json.load(f)
    except:
        return {"summary": {"total": {"capital": 373261, "pnl": -31041, "pnl_percent": -8.32}}}

def load_capital_vision() -> Dict[str, Any]:
    """Parse CAPITAL_VISION_SSOT.md for milestones and metrics"""
    try:
        with open(CAPITAL_VISION) as f:
            content = f.read()

        # Extract key metrics using regex
        vision_data = {
            "tam": "5.21 trillion",
            "current_capital": 373261,
            "target_month_6": 500000,
            "target_year_1": 5000000,
            "target_year_2": 100000000,
            "target_year_4": 3000000000,
            "target_year_7": 150000000000,
            "target_year_10": 1000000000000,
            "phases": [
                {"name": "Proof", "duration": "Months 1-6", "capital": "373K → 5M", "target": "100 matches, proven economics"},
                {"name": "Expand", "duration": "Months 7-18", "capital": "5M → 100M", "target": "5-10 categories, 10K matches"},
                {"name": "Super-App", "duration": "Years 2-4", "capital": "100M → 3B", "target": "10+ categories, 10M users"},
                {"name": "Network Effects", "duration": "Years 4-7", "capital": "3B → 150B", "target": "100M+ users, dominance"},
                {"name": "New Paradigm", "duration": "Years 7-10+", "capital": "150B → 1-5T", "target": "1B+ users, paradise"}
            ],
            "current_phase": "Phase 1 - Proof",
            "phase_progress": 0,
            "days_in_phase": 0,
            "total_phase_days": 180
        }

        # Extract milestones
        milestones_section = re.search(r'### Phase 1 Milestones.*?(?=###|\Z)', content, re.DOTALL)
        if milestones_section:
            milestone_matches = re.findall(r'- \[([ x])\] \*\*(.+?):\*\* (.+)', milestones_section.group())
            vision_data["milestones"] = [
                {"completed": m[0] == "x", "name": m[1], "description": m[2]}
                for m in milestone_matches
            ]

        return vision_data
    except Exception as e:
        return {"error": str(e)}

def load_revenue_data() -> Dict[str, Any]:
    """Load revenue projections"""
    try:
        with open(TREASURY_JSON) as f:
            data = json.load(f)
            return data.get("projections", {})
    except:
        return {}

def calculate_progress() -> Dict[str, Any]:
    """Calculate current progress toward goals"""
    treasury = load_treasury_data()
    vision = load_capital_vision()

    current_capital = treasury.get("summary", {}).get("total", {}).get("capital", 373261)
    target_m6 = vision.get("target_month_6", 500000)
    target_y1 = vision.get("target_year_1", 5000000)

    progress_to_m6 = min(100, (current_capital / target_m6) * 100)
    progress_to_y1 = min(100, (current_capital / target_y1) * 100)

    return {
        "current_capital": current_capital,
        "target_month_6": target_m6,
        "target_year_1": target_y1,
        "progress_to_m6_percent": round(progress_to_m6, 2),
        "progress_to_y1_percent": round(progress_to_y1, 2),
        "days_active": 0,  # Will calculate from first deployment
        "matches_completed": 0,  # Will integrate with I MATCH
        "matches_target": 100
    }

@app.get("/")
async def root():
    """Redirect to dashboard"""
    return {"message": "Treasury Dashboard API", "dashboard": "/dashboard"}

@app.get("/api/metrics", response_class=JSONResponse)
async def get_metrics():
    """Get all dashboard metrics"""
    treasury = load_treasury_data()
    vision = load_capital_vision()
    revenue = load_revenue_data()
    progress = calculate_progress()

    return {
        "treasury": treasury.get("summary", {}),
        "vision": vision,
        "revenue": revenue,
        "progress": progress,
        "updated_at": datetime.utcnow().isoformat()
    }

@app.get("/api/phases", response_class=JSONResponse)
async def get_phases():
    """Get all phases of the journey"""
    vision = load_capital_vision()
    return {"phases": vision.get("phases", [])}

@app.get("/api/milestones", response_class=JSONResponse)
async def get_milestones():
    """Get Phase 1 milestones"""
    vision = load_capital_vision()
    return {"milestones": vision.get("milestones", [])}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Beautiful visual dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Treasury Dashboard - $373K → $5T Journey</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
                color: #e0e6ed;
                padding: 2rem;
                min-height: 100vh;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 {
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .subtitle {
                color: #a0aec0;
                font-size: 1.2rem;
                margin-bottom: 2rem;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
            .card {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 1.5rem;
                backdrop-filter: blur(10px);
            }
            .card h2 {
                font-size: 1.2rem;
                margin-bottom: 1rem;
                color: #a0aec0;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .metric-value {
                font-size: 2.5rem;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }
            .metric-label {
                color: #718096;
                font-size: 0.9rem;
            }
            .progress-bar {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                height: 20px;
                overflow: hidden;
                margin: 1rem 0;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                transition: width 0.5s ease;
                display: flex;
                align-items: center;
                justify-content: flex-end;
                padding-right: 10px;
                font-size: 0.8rem;
                font-weight: bold;
            }
            .phases {
                display: flex;
                gap: 1rem;
                overflow-x: auto;
                padding: 1rem 0;
            }
            .phase {
                min-width: 250px;
                background: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-radius: 12px;
                padding: 1.5rem;
            }
            .phase.active {
                border-color: #667eea;
                background: rgba(102, 126, 234, 0.1);
            }
            .phase h3 {
                color: #667eea;
                margin-bottom: 0.5rem;
            }
            .phase .duration {
                color: #a0aec0;
                font-size: 0.9rem;
                margin-bottom: 1rem;
            }
            .phase .capital {
                font-size: 1.5rem;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }
            .phase .target {
                color: #718096;
                font-size: 0.9rem;
            }
            .positive { color: #48bb78; }
            .negative { color: #f56565; }
            .warning { color: #ed8936; }
            .milestone {
                padding: 0.75rem;
                margin: 0.5rem 0;
                background: rgba(255, 255, 255, 0.03);
                border-left: 3px solid #667eea;
                border-radius: 4px;
            }
            .milestone.completed {
                border-left-color: #48bb78;
                opacity: 0.7;
            }
            .auto-update {
                text-align: center;
                color: #a0aec0;
                font-size: 0.9rem;
                margin-top: 2rem;
            }
            .pulse {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #48bb78;
                animation: pulse 2s infinite;
                margin-right: 8px;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .vision-path {
                background: rgba(255, 255, 255, 0.03);
                border-radius: 12px;
                padding: 2rem;
                margin: 2rem 0;
                text-align: center;
            }
            .vision-path h2 {
                font-size: 1.5rem;
                margin-bottom: 1.5rem;
                color: #667eea;
            }
            .path-steps {
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 1rem;
            }
            .path-step {
                flex: 1;
                min-width: 120px;
            }
            .path-arrow {
                color: #667eea;
                font-size: 2rem;
            }
            .path-value {
                font-size: 1.5rem;
                font-weight: bold;
                margin-bottom: 0.25rem;
            }
            .path-label {
                font-size: 0.8rem;
                color: #a0aec0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌐 Treasury Dashboard</h1>
            <p class="subtitle">The Journey from $373K to $5 Trillion</p>

            <div class="grid">
                <div class="card">
                    <h2>Current Capital</h2>
                    <div class="metric-value" id="current-capital">$373,261</div>
                    <div class="metric-label">
                        P&L: <span id="pnl" class="negative">-$31,041 (-8.32%)</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-m6" style="width: 0%">0%</div>
                    </div>
                    <div class="metric-label">Progress to Month 6 Target ($500K)</div>
                </div>

                <div class="card">
                    <h2>Phase 1 Progress</h2>
                    <div class="metric-value" id="matches">0 / 100</div>
                    <div class="metric-label">Matches Completed</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-matches" style="width: 0%">0%</div>
                    </div>
                    <div class="metric-label">Days Active: <span id="days-active">0</span> / 180</div>
                </div>

                <div class="card">
                    <h2>Revenue (Projected)</h2>
                    <div class="metric-value" id="revenue-m1">$2,500</div>
                    <div class="metric-label">Month 1 Target</div>
                    <div style="margin-top: 1rem;">
                        <div class="metric-label">Month 12: <span id="revenue-m12">$40,000</span></div>
                    </div>
                </div>

                <div class="card">
                    <h2>Total Addressable Market</h2>
                    <div class="metric-value positive">$5.21T</div>
                    <div class="metric-label">By 2030</div>
                    <div style="margin-top: 1rem; font-size: 0.9rem; color: #a0aec0;">
                        10+ matching categories<br>
                        Network effects: n⁴ value growth
                    </div>
                </div>
            </div>

            <div class="vision-path">
                <h2>The 10-Year Path to Paradise</h2>
                <div class="path-steps">
                    <div class="path-step">
                        <div class="path-value positive">$373K</div>
                        <div class="path-label">Now</div>
                    </div>
                    <div class="path-arrow">→</div>
                    <div class="path-step">
                        <div class="path-value">$5M</div>
                        <div class="path-label">Month 6</div>
                    </div>
                    <div class="path-arrow">→</div>
                    <div class="path-step">
                        <div class="path-value">$100M</div>
                        <div class="path-label">Year 2</div>
                    </div>
                    <div class="path-arrow">→</div>
                    <div class="path-step">
                        <div class="path-value">$3B</div>
                        <div class="path-label">Year 4</div>
                    </div>
                    <div class="path-arrow">→</div>
                    <div class="path-step">
                        <div class="path-value">$150B</div>
                        <div class="path-label">Year 7</div>
                    </div>
                    <div class="path-arrow">→</div>
                    <div class="path-step">
                        <div class="path-value positive">$1-5T</div>
                        <div class="path-label">Year 10+</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Journey Phases</h2>
                <div class="phases" id="phases-container">
                    <!-- Populated by JS -->
                </div>
            </div>

            <div class="card">
                <h2>Phase 1 Milestones</h2>
                <div id="milestones-container">
                    <!-- Populated by JS -->
                </div>
            </div>

            <div class="auto-update">
                <span class="pulse"></span>
                Auto-updating every 30 seconds | Last update: <span id="last-update">--:--:--</span>
            </div>
        </div>

        <script>
            async function updateDashboard() {
                try {
                    const response = await fetch('/api/metrics');
                    const data = await response.json();

                    // Update capital
                    const capital = data.treasury?.total?.capital || 373261;
                    const pnl = data.treasury?.total?.pnl || -31041;
                    const pnlPercent = data.treasury?.total?.pnl_percent || -8.32;

                    document.getElementById('current-capital').textContent =
                        '$' + capital.toLocaleString();
                    document.getElementById('pnl').textContent =
                        '$' + pnl.toLocaleString() + ' (' + pnlPercent.toFixed(2) + '%)';
                    document.getElementById('pnl').className = pnl >= 0 ? 'positive' : 'negative';

                    // Update progress
                    const progressM6 = data.progress?.progress_to_m6_percent || 0;
                    const progressFill = document.getElementById('progress-m6');
                    progressFill.style.width = progressM6 + '%';
                    progressFill.textContent = progressM6.toFixed(1) + '%';

                    // Update matches
                    const matches = data.progress?.matches_completed || 0;
                    const matchesTarget = data.progress?.matches_target || 100;
                    document.getElementById('matches').textContent =
                        matches + ' / ' + matchesTarget;
                    const matchProgress = (matches / matchesTarget) * 100;
                    const matchFill = document.getElementById('progress-matches');
                    matchFill.style.width = matchProgress + '%';
                    matchFill.textContent = matchProgress.toFixed(0) + '%';

                    document.getElementById('days-active').textContent =
                        data.progress?.days_active || 0;

                    // Update revenue
                    document.getElementById('revenue-m1').textContent =
                        '$' + (data.revenue?.projected_revenue_m1 || 2500).toLocaleString();
                    document.getElementById('revenue-m12').textContent =
                        '$' + (data.revenue?.projected_revenue_m12 || 40000).toLocaleString();

                    // Update timestamp
                    document.getElementById('last-update').textContent =
                        new Date(data.updated_at).toLocaleTimeString();

                } catch (error) {
                    console.error('Error updating dashboard:', error);
                }
            }

            async function loadPhases() {
                try {
                    const response = await fetch('/api/phases');
                    const data = await response.json();
                    const container = document.getElementById('phases-container');

                    container.innerHTML = data.phases.map((phase, index) => `
                        <div class="phase ${index === 0 ? 'active' : ''}">
                            <h3>${phase.name}</h3>
                            <div class="duration">${phase.duration}</div>
                            <div class="capital">${phase.capital}</div>
                            <div class="target">${phase.target}</div>
                        </div>
                    `).join('');
                } catch (error) {
                    console.error('Error loading phases:', error);
                }
            }

            async function loadMilestones() {
                try {
                    const response = await fetch('/api/milestones');
                    const data = await response.json();
                    const container = document.getElementById('milestones-container');

                    if (data.milestones && data.milestones.length > 0) {
                        container.innerHTML = data.milestones.map(m => `
                            <div class="milestone ${m.completed ? 'completed' : ''}">
                                <strong>${m.completed ? '✅' : '⬜'} ${m.name}:</strong> ${m.description}
                            </div>
                        `).join('');
                    } else {
                        container.innerHTML = '<div class="metric-label">Loading milestones...</div>';
                    }
                } catch (error) {
                    console.error('Error loading milestones:', error);
                }
            }

            // Initial load
            updateDashboard();
            loadPhases();
            loadMilestones();

            // Auto-update every 30 seconds
            setInterval(updateDashboard, 30000);
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "treasury-dashboard", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
