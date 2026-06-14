#!/usr/bin/env python3
"""
FPAI Memory Dashboard - Visual interface to system learnings
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import json
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Memory Dashboard")

LEARNINGS_FILE = Path("/opt/fpai/learnings.json")
WISDOM_FILE = Path("/opt/fpai/aria/data/wdc/james/wisdom.json")

def load_learnings():
    if LEARNINGS_FILE.exists():
        return json.loads(LEARNINGS_FILE.read_text())
    return {"learnings": [], "patterns": []}

def load_wisdom():
    if WISDOM_FILE.exists():
        return json.loads(WISDOM_FILE.read_text())
    return []

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    data = load_learnings()
    wisdom = load_wisdom()
    learnings = data.get("learnings", [])
    patterns = data.get("patterns", [])
    
    # Build learnings HTML
    learnings_html = ""
    for l in sorted(learnings, key=lambda x: x.get("date", ""), reverse=True):
        severity_color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}.get(l.get("severity", "medium"), "#6b7280")
        learnings_html += f'''
        <div class="card">
            <div class="card-header">
                <span class="severity" style="background: {severity_color}">{l.get("severity", "?").upper()}</span>
                <span class="date">{l.get("date", "Unknown")}</span>
                <span class="id">{l.get("id", "")}</span>
            </div>
            <h3>{l.get("error", "Unknown Error")}</h3>
            <div class="detail"><strong>Symptom:</strong> {l.get("symptom", "N/A")}</div>
            <div class="detail"><strong>Root Cause:</strong> {l.get("root_cause", "N/A")}</div>
            <div class="detail why-missed"><strong>Why Missed:</strong> {l.get("why_missed", "N/A")}</div>
            <div class="detail fix"><strong>Fix:</strong> {l.get("fix", "N/A")}</div>
            <div class="meta">
                <span class="category">{l.get("category", "general")}</span>
                <span class="test">Test: {l.get("test_added", "none")}</span>
            </div>
        </div>
        '''
    
    # Build patterns HTML
    patterns_html = ""
    for p in patterns:
        patterns_html += f'''
        <div class="pattern">
            <div class="pattern-name">🔄 {p.get("pattern", "Unknown")}</div>
            <div class="pattern-solution">→ {p.get("solution", "No solution")}</div>
            <div class="pattern-count">{p.get("occurrences", 0)} occurrences</div>
        </div>
        '''
    
    # Build wisdom HTML
    wisdom_html = ""
    for w in wisdom[:10]:
        wisdom_html += f'''
        <div class="wisdom-item">
            <span class="wisdom-cat">{w.get("category", "general")}</span>
            {w.get("wisdom", "Unknown")}
        </div>
        '''
    
    no_learnings = '<p class="empty">No learnings yet</p>'
    no_patterns = '<p class="empty">No patterns yet</p>'
    no_wisdom = '<p class="empty">No wisdom stored</p>'
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FPAI Memory Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --bg-hover: #1a1a25;
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.3);
            --text: #e2e8f0;
            --text-dim: #64748b;
            --success: #22c55e;
            --warning: #f59e0b;
            --error: #ef4444;
            --border: #2a2a3a;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            padding: 2rem;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: linear-gradient(135deg, var(--bg-card) 0%, #1a1a2e 100%);
            border-radius: 16px;
            border: 1px solid var(--border);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            background: linear-gradient(135deg, var(--accent) 0%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        
        .header .subtitle {{
            color: var(--text-dim);
            font-size: 1.1rem;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent);
        }}
        
        .stat-label {{
            color: var(--text-dim);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
        }}
        
        @media (max-width: 1024px) {{
            .grid {{ grid-template-columns: 1fr; }}
        }}
        
        .section {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
        }}
        
        .section-title {{
            font-size: 1.25rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .card {{
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            transition: all 0.2s;
        }}
        
        .card:hover {{
            border-color: var(--accent);
            box-shadow: 0 0 20px var(--accent-glow);
        }}
        
        .card-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }}
        
        .severity {{
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            color: white;
        }}
        
        .date {{
            color: var(--text-dim);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }}
        
        .id {{
            color: var(--accent);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            margin-left: auto;
        }}
        
        .card h3 {{
            font-size: 1.1rem;
            margin-bottom: 0.75rem;
            color: var(--text);
        }}
        
        .detail {{
            font-size: 0.9rem;
            color: var(--text-dim);
            margin-bottom: 0.5rem;
            line-height: 1.4;
        }}
        
        .detail strong {{
            color: var(--text);
        }}
        
        .why-missed {{
            background: rgba(239, 68, 68, 0.1);
            padding: 0.5rem;
            border-radius: 6px;
            border-left: 3px solid var(--error);
        }}
        
        .fix {{
            background: rgba(34, 197, 94, 0.1);
            padding: 0.5rem;
            border-radius: 6px;
            border-left: 3px solid var(--success);
        }}
        
        .meta {{
            display: flex;
            gap: 1rem;
            margin-top: 0.75rem;
            font-size: 0.8rem;
        }}
        
        .category {{
            background: var(--accent);
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }}
        
        .test {{
            color: var(--text-dim);
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .pattern {{
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.75rem;
        }}
        
        .pattern-name {{
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}
        
        .pattern-solution {{
            color: var(--success);
            font-size: 0.9rem;
        }}
        
        .pattern-count {{
            color: var(--text-dim);
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }}
        
        .wisdom-item {{
            padding: 0.75rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
        }}
        
        .wisdom-item:last-child {{
            border-bottom: none;
        }}
        
        .wisdom-cat {{
            background: #a855f7;
            color: white;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-size: 0.7rem;
            margin-right: 0.5rem;
        }}
        
        .empty {{
            color: var(--text-dim);
            font-style: italic;
        }}
        
        .refresh-btn {{
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--accent);
            color: white;
            border: none;
            padding: 1rem 1.5rem;
            border-radius: 50px;
            cursor: pointer;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1rem;
            box-shadow: 0 4px 20px var(--accent-glow);
            transition: all 0.2s;
        }}
        
        .refresh-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 30px var(--accent-glow);
        }}
        
        .last-updated {{
            text-align: center;
            color: var(--text-dim);
            font-size: 0.85rem;
            margin-top: 2rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 FPAI Memory Dashboard</h1>
        <div class="subtitle">Central learning repository • System intelligence • Pattern recognition</div>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{len(learnings)}</div>
            <div class="stat-label">Learnings Captured</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len(patterns)}</div>
            <div class="stat-label">Patterns Detected</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len(wisdom)}</div>
            <div class="stat-label">Wisdom Entries</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len([l for l in learnings if l.get("severity") == "high"])}</div>
            <div class="stat-label">High Severity</div>
        </div>
    </div>
    
    <div class="grid">
        <div class="section">
            <h2 class="section-title">📝 Recent Learnings</h2>
            {learnings_html if learnings_html else no_learnings}
        </div>
        
        <div>
            <div class="section" style="margin-bottom: 1.5rem;">
                <h2 class="section-title">🔄 Detected Patterns</h2>
                {patterns_html if patterns_html else no_patterns}
            </div>
            
            <div class="section">
                <h2 class="section-title">💡 James Wisdom</h2>
                {wisdom_html if wisdom_html else no_wisdom}
            </div>
        </div>
    </div>
    
    <div class="last-updated">
        Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}
    </div>
    
    <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
</body>
</html>'''
    return HTMLResponse(content=html)

@app.get("/api/learnings")
async def api_learnings():
    return load_learnings()

@app.get("/api/wisdom")
async def api_wisdom():
    return load_wisdom()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "memory-dashboard"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8780)








