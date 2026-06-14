#!/usr/bin/env python3
"""
Apprentice Harvester Portal
Port 8055 - Submit missions, track history, run code reviews
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import settings as app_settings
from core.jobs import registry as job_registry

app = FastAPI(title="Apprentice Harvester", version="2.0")

# Centralized paths
FEEDBACK_DIR = app_settings.feedback_dir
JOBS_DIR = app_settings.jobs_dir

# Mount static files
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class FeedbackSubmission(BaseModel):
    mission_id: str
    status: str  # "completed", "stuck", "submission"
    name: str
    repo_url: str = None
    message: str
    timestamp: str = None

def run_harvest_job(job_id: str, name: str, repo_url: str, mission_id: str = None):
    """Run harvest in background and stream logs to file"""
    job_file = job_registry.job_state_path(job_id)
    
    # Initial state
    state = {
        "status": "running",
        "logs": ["🚀 Job started: Harvesting repository..."],
        "steps": [
            {"name": "Clone Repository", "status": "pending"},
            {"name": "Verify Structure", "status": "pending"},
            {"name": "Run Tests", "status": "pending"},
            {"name": "Security Scan", "status": "pending"},
            {"name": "Quality Score", "status": "pending"}
        ],
        "score": 0
    }
    
    def update_state(new_log=None, step_idx=None, step_status=None, final_score=None, final_status=None):
        if new_log:
            state["logs"].append(new_log)
            job_registry.append_log(job_id, new_log)
        if step_idx is not None:
            state["steps"][step_idx]["status"] = step_status
        if final_score is not None:
            state["score"] = final_score
        if final_status:
            state["status"] = final_status
            
        with open(job_file, "w") as f:
            json.dump(state, f)

    update_state()
    job_registry.update_job(job_id, status="running")
    
    def notify_mission_hub(status: str, score: int = None):
        if not mission_id:
            return
        
        try:
            import requests
            mission_hub_url = "http://127.0.0.1:8700/api/status"
            
            payload = {
                "mission_id": mission_id,
                "status": status,
                "updated_by": name,
                "notes": f"Code submission via Harvester (score: {score}/100)" if score else "Code submission via Harvester",
                "repo_url": repo_url,
                "score": score
            }
            
            requests.post(mission_hub_url, json=payload, timeout=5)
            print(f"✅ Notified Mission Hub: {status}")
        except Exception as e:
            print(f"⚠️ Could not notify Mission Hub: {e}")

    try:
        import subprocess
        import re
        
        notify_mission_hub("submitted")
        
        script_path = Path("/Users/jamessunheart/FPAI_Cockpit/_scripts/harvest-apprentice.py")
        if not script_path.exists():
            script_path = Path("/root/FPAI_Cockpit/_scripts/harvest-apprentice.py")
        
        if not script_path.exists():
            update_state("❌ Error: Harvester script not found!", final_status="failed")
            job_registry.update_job(job_id, status="failed", metadata={"error": "harvester script missing"})
            return

        update_state("📦 Cloning repository...", step_idx=0, step_status="running")
        
        process = subprocess.Popen(
            [str(script_path), name.replace(" ", ""), repo_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        output_buffer = ""
        final_score = 0
        for line in process.stdout:
            line = line.strip()
            if not line: continue
            
            output_buffer += line + "\n"
            update_state(f"> {line}")
            
            if "Running git subtree" in line or "Cloning" in line:
                update_state(step_idx=0, step_status="completed")
                update_state(step_idx=1, step_status="running")
            elif "Verifying" in line:
                update_state(step_idx=1, step_status="completed")
                update_state(step_idx=2, step_status="running")
            elif "Running tests" in line:
                update_state(step_idx=2, step_status="running")
            elif "Scanning" in line:
                update_state(step_idx=2, step_status="completed")
                update_state(step_idx=3, step_status="running")
            elif "Score:" in line:
                update_state(step_idx=3, step_status="completed")
                update_state(step_idx=4, step_status="completed")
                
                score_match = re.search(r'Score:\s*(\d+)', line)
                if score_match:
                    final_score = int(score_match.group(1))
                    update_state(final_score=final_score)

        process.wait()
        
        if process.returncode == 0:
            update_state("✅ Harvest complete!", final_status="completed")
            for i in range(5):
                state["steps"][i]["status"] = "completed"
            with open(job_file, "w") as f:
                json.dump(state, f)
            
            notify_mission_hub("completed", final_score)
            job_registry.update_job(
                job_id,
                status="completed",
                score=final_score,
                metadata={"result": "completed", "mission_id": mission_id},
            )
        else:
            update_state("❌ Harvest failed. See logs.", final_status="failed")
            notify_mission_hub("blocked", 0)
            job_registry.update_job(
                job_id,
                status="failed",
                metadata={"result": "failed", "mission_id": mission_id},
            )
            
    except Exception as e:
        update_state(f"💥 System Error: {str(e)}", final_status="failed")
        notify_mission_hub("blocked", 0)
        job_registry.update_job(
            job_id,
            status="failed",
            metadata={"error": str(e), "mission_id": mission_id},
        )


@app.get("/", response_class=HTMLResponse)
async def home():
    """Show harvester portal"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Harvester | Full Potential AI</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-deep: #0a0a0f;
                --bg-card: #12121a;
                --bg-elevated: #1a1a24;
                --border: #2a2a3a;
                --text: #e4e4e7;
                --text-muted: #71717a;
                --accent-primary: #8b5cf6;
                --accent-secondary: #06b6d4;
                --accent-success: #10b981;
                --accent-warning: #f59e0b;
                --accent-danger: #ef4444;
                --gradient-primary: linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%);
            }
            
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: 'Outfit', -apple-system, sans-serif;
                background: var(--bg-deep);
                color: var(--text);
                min-height: 100vh;
                line-height: 1.6;
            }
            
            .bg-pattern {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: 
                    radial-gradient(circle at 20% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
                    radial-gradient(circle at 80% 20%, rgba(6, 182, 212, 0.08) 0%, transparent 50%),
                    radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.05) 0%, transparent 40%);
                pointer-events: none;
                z-index: 0;
            }
            
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 40px 24px;
                position: relative;
                z-index: 1;
            }
            
            /* Header */
            header {
                text-align: center;
                margin-bottom: 40px;
            }
            
            .logo {
                display: inline-flex;
                align-items: center;
                gap: 16px;
                margin-bottom: 16px;
            }
            
            .logo-icon {
                width: 64px;
                height: 64px;
                background: var(--gradient-primary);
                border-radius: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 32px;
                box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3);
            }
            
            .logo-text h1 {
                font-size: 28px;
                font-weight: 700;
                background: var(--gradient-primary);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .subtitle {
                color: var(--text-muted);
                font-size: 16px;
            }
            
            .subtitle a {
                color: var(--accent-primary);
                text-decoration: none;
            }
            
            .subtitle a:hover {
                text-decoration: underline;
            }
            
            /* Tabs */
            .tabs {
                display: flex;
                gap: 8px;
                background: var(--bg-card);
                padding: 6px;
                border-radius: 12px;
                border: 1px solid var(--border);
                margin-bottom: 24px;
            }
            
            .tab-btn {
                flex: 1;
                padding: 12px 16px;
                border-radius: 8px;
                border: none;
                background: transparent;
                color: var(--text-muted);
                font-family: inherit;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .tab-btn:hover {
                color: var(--text);
            }
            
            .tab-btn.active {
                background: var(--gradient-primary);
                color: white;
            }
            
            .tab-panel {
                display: none;
            }
            
            .tab-panel.active {
                display: block;
            }
            
            /* Card */
            .card {
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 20px;
                padding: 32px;
                margin-bottom: 24px;
            }
            
            .card-title {
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            /* Form */
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }
            
            @media (max-width: 600px) {
                .form-row {
                    grid-template-columns: 1fr;
                }
            }
            
            label {
                display: block;
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 8px;
                color: var(--text);
            }
            
            input, select, textarea {
                width: 100%;
                padding: 14px 16px;
                background: var(--bg-elevated);
                border: 1px solid var(--border);
                border-radius: 12px;
                color: var(--text);
                font-family: inherit;
                font-size: 14px;
                transition: border-color 0.2s, box-shadow 0.2s;
            }
            
            input:focus, select:focus, textarea:focus {
                outline: none;
                border-color: var(--accent-primary);
                box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15);
            }
            
            textarea {
                min-height: 100px;
                resize: vertical;
            }
            
            .btn {
                padding: 14px 28px;
                border-radius: 12px;
                font-family: inherit;
                font-size: 15px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                border: none;
                width: 100%;
            }
            
            .btn-primary {
                background: var(--gradient-primary);
                color: white;
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4);
            }
            
            .btn-primary:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            /* Progress */
            .progress-container {
                display: none;
                margin-top: 24px;
            }
            
            .progress-container.active {
                display: block;
            }
            
            .steps {
                display: flex;
                justify-content: space-between;
                margin-bottom: 24px;
            }
            
            .step {
                display: flex;
                flex-direction: column;
                align-items: center;
                font-size: 12px;
                color: var(--text-muted);
                flex: 1;
                position: relative;
            }
            
            .step-dot {
                width: 14px;
                height: 14px;
                border-radius: 50%;
                background: var(--bg-elevated);
                border: 2px solid var(--border);
                margin-bottom: 8px;
                transition: all 0.3s;
            }
            
            .step.active .step-dot {
                background: var(--accent-primary);
                border-color: var(--accent-primary);
                box-shadow: 0 0 12px rgba(139, 92, 246, 0.5);
            }
            
            .step.completed .step-dot {
                background: var(--accent-success);
                border-color: var(--accent-success);
            }
            
            .step.active {
                color: var(--accent-primary);
                font-weight: 600;
            }
            
            .step.completed {
                color: var(--accent-success);
            }
            
            .log-window {
                background: #0d0d12;
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 16px;
                height: 250px;
                overflow-y: auto;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                line-height: 1.6;
            }
            
            .log-entry {
                color: #22c55e;
                margin-bottom: 4px;
            }
            
            .log-entry.error {
                color: #ef4444;
            }
            
            .result-card {
                display: none;
                margin-top: 24px;
                padding: 32px;
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 16px;
                text-align: center;
            }
            
            .result-card.active {
                display: block;
            }
            
            .result-score {
                font-size: 48px;
                font-weight: 800;
                background: var(--gradient-primary);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .result-status {
                font-size: 18px;
                font-weight: 600;
                margin-top: 8px;
            }
            
            .result-status.success {
                color: var(--accent-success);
            }
            
            .result-status.warning {
                color: var(--accent-warning);
            }
            
            /* Rubric */
            .rubric {
                background: var(--bg-elevated);
                border-radius: 12px;
                padding: 20px;
                margin-top: 24px;
            }
            
            .rubric h4 {
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 12px;
                color: var(--accent-secondary);
            }
            
            .rubric ul {
                list-style: none;
                padding: 0;
            }
            
            .rubric li {
                padding: 8px 0;
                font-size: 13px;
                color: var(--text-muted);
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .rubric li::before {
                content: "✓";
                color: var(--accent-success);
                font-weight: bold;
            }
            
            /* History */
            .history-list {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            
            .history-card {
                background: var(--bg-elevated);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 20px;
                transition: all 0.2s;
            }
            
            .history-card:hover {
                border-color: var(--accent-primary);
            }
            
            .history-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            
            .history-mission {
                font-weight: 600;
                font-size: 15px;
            }
            
            .history-score {
                font-weight: 700;
                font-size: 14px;
            }
            
            .history-score.success {
                color: var(--accent-success);
            }
            
            .history-score.failed {
                color: var(--accent-danger);
            }
            
            .history-meta {
                font-size: 13px;
                color: var(--text-muted);
            }
            
            .history-meta a {
                color: var(--accent-primary);
            }
            
            .view-log-btn {
                margin-top: 12px;
                padding: 8px 16px;
                background: transparent;
                border: 1px solid var(--border);
                border-radius: 8px;
                color: var(--text-muted);
                font-family: inherit;
                font-size: 13px;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .view-log-btn:hover {
                border-color: var(--accent-primary);
                color: var(--accent-primary);
            }
            
            .empty-state {
                text-align: center;
                padding: 40px;
                color: var(--text-muted);
            }
            
            .empty-state .icon {
                font-size: 48px;
                margin-bottom: 16px;
            }
            
            /* Checklist */
            .checklist {
                background: var(--bg-elevated);
                border-radius: 16px;
                padding: 24px;
            }
            
            .checklist h3 {
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .checklist ol {
                padding-left: 24px;
            }
            
            .checklist li {
                padding: 10px 0;
                color: var(--text-muted);
                font-size: 14px;
            }
            
            .checklist code {
                background: var(--bg-card);
                padding: 2px 8px;
                border-radius: 4px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                color: var(--accent-secondary);
            }
            
            .checklist a {
                color: var(--accent-primary);
            }
            
            /* Flash */
            .flash-success {
                display: none;
                background: rgba(16, 185, 129, 0.15);
                border: 1px solid rgba(16, 185, 129, 0.3);
                color: #34d399;
                padding: 16px 20px;
                border-radius: 12px;
                margin-bottom: 24px;
                font-weight: 500;
                text-align: center;
            }
            
            .flash-success.show {
                display: block;
            }
            
            /* Footer */
            footer {
                text-align: center;
                padding: 32px 0;
                color: var(--text-muted);
                font-size: 14px;
            }
            
            footer a {
                color: var(--accent-primary);
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="bg-pattern"></div>
        
        <div class="container">
            <header>
                <div class="logo">
                    <div class="logo-icon">🚜</div>
                    <div class="logo-text">
                        <h1>Harvester</h1>
                    </div>
                </div>
                <p class="subtitle">Submit code • Get reviewed • <a href="/missions">Browse Mission Hub →</a></p>
            </header>
            
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('submit')">📤 Submit</button>
                <button class="tab-btn" onclick="switchTab('history')">📊 History</button>
                <button class="tab-btn" onclick="switchTab('checklist')">✅ Checklist</button>
            </div>
            
            <!-- Submit Tab -->
            <div class="tab-panel active" id="tab-submit">
                <div id="successMessage" class="flash-success">
                    ✅ Submission received! Processing...
                </div>
                
                <div class="card">
                    <h2 class="card-title">🚀 Submit Your Code</h2>
                    
                    <form id="submitForm" onsubmit="handleSubmit(event)">
                        <div class="form-group">
                            <label for="name">Your Name</label>
                            <input type="text" id="name" name="name" required placeholder="e.g., Alex Chen">
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="mission">Mission</label>
                                <select id="mission" name="mission" required>
                                    <option value="">Select a mission...</option>
                                    <option value="mission-1">Mission 1: Reddit Launch</option>
                                    <option value="mission-2">Mission 2: Magnet Trading</option>
                                    <option value="mission-3">Mission 3: Both Missions</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="status">Action</label>
                                <select id="status" name="status" required onchange="toggleRepoField()">
                                    <option value="">Select action...</option>
                                    <option value="submission">📤 Submit Code for Review</option>
                                    <option value="completed">✅ Report Completion</option>
                                    <option value="stuck">❌ Report Blocked</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="form-group" id="repoGroup" style="display: none;">
                            <label for="repo_url">GitHub Repository URL</label>
                            <input type="url" id="repo_url" name="repo_url" placeholder="https://github.com/username/repo">
                        </div>
                        
                        <div class="form-group">
                            <label for="message">Notes</label>
                            <textarea id="message" name="message" required placeholder="Describe your submission..."></textarea>
                        </div>
                        
                        <button type="submit" class="btn btn-primary" id="submitBtn">
                            ⚡ Submit
                        </button>
                    </form>
                    
                    <div class="rubric">
                        <h4>📋 Quality Rubric</h4>
                        <ul>
                            <li>Tests exist (20%)</li>
                            <li>Tests pass (30%)</li>
                            <li>README / documentation (20%)</li>
                            <li>Dependencies declared (15%)</li>
                            <li>No secrets/static keys (15%)</li>
                        </ul>
                    </div>
                </div>
                
                <div class="progress-container" id="progressContainer">
                    <div class="card">
                        <h2 class="card-title">🔄 Processing Submission</h2>
                        
                        <div class="steps" id="stepsContainer">
                            <div class="step">
                                <div class="step-dot"></div>
                                Clone
                            </div>
                            <div class="step">
                                <div class="step-dot"></div>
                                Verify
                            </div>
                            <div class="step">
                                <div class="step-dot"></div>
                                Test
                            </div>
                            <div class="step">
                                <div class="step-dot"></div>
                                Scan
                            </div>
                            <div class="step">
                                <div class="step-dot"></div>
                                Score
                            </div>
                        </div>
                        
                        <div class="log-window" id="logWindow">
                            <div class="log-entry">> Initializing...</div>
                        </div>
                    </div>
                    
                    <div class="result-card" id="resultCard">
                        <div>Quality Score</div>
                        <div class="result-score" id="finalScore">--</div>
                        <div class="result-status" id="finalStatus"></div>
                    </div>
                </div>
            </div>
            
            <!-- History Tab -->
            <div class="tab-panel" id="tab-history">
                <div class="card">
                    <h2 class="card-title">📊 Your Submissions</h2>
                    <p style="color: var(--text-muted); margin-bottom: 16px;" id="historyStatus">Enter your name in the Submit tab to load history.</p>
                    <div id="historyList" class="history-list"></div>
                </div>
            </div>
            
            <!-- Checklist Tab -->
            <div class="tab-panel" id="tab-checklist">
                <div class="card">
                    <div class="checklist">
                        <h3>✅ Preflight Checklist</h3>
                        <ol>
                            <li>Run <code>./_scripts/apprentice-preflight-check.sh</code> locally</li>
                            <li>Ensure tests pass: <code>pytest -v</code></li>
                            <li>Create/Update <code>README.md</code> with overview + setup</li>
                            <li>Declare dependencies (<code>requirements.txt</code> or <code>package.json</code>)</li>
                            <li>Scan for secrets: <code>rg -i "API_KEY|SECRET|TOKEN"</code></li>
                            <li>Clean git status (only intentional files)</li>
                            <li>Push to GitHub before submitting</li>
                        </ol>
                        <p style="margin-top: 16px; font-size: 13px; color: var(--text-muted);">
                            Need help? See the <a href="/missions/contribute">Contribution Guide</a>
                        </p>
                    </div>
                </div>
            </div>
            
            <footer>
                <p>
                    <a href="/missions">Mission Hub</a> · 
                    <a href="https://fullpotential.ai">Full Potential AI</a>
                </p>
            </footer>
        </div>
        
        <script>
            const BASE_PATH = window.location.pathname.startsWith('/harvester') ? '/harvester' : 
                              window.location.pathname.startsWith('/services/harvester') ? '/services/harvester' : '';
            
            // Initialize
            window.onload = function() {
                const urlParams = new URLSearchParams(window.location.search);
                const missionId = urlParams.get('mission');
                const missionTitle = urlParams.get('title');
                const storedName = localStorage.getItem('apprenticeName');
                
                if (storedName) {
                    document.getElementById('name').value = storedName;
                }
                
                if (missionId) {
                    const select = document.getElementById('mission');
                    let found = false;
                    for (let i = 0; i < select.options.length; i++) {
                        if (select.options[i].value === missionId) {
                            select.selectedIndex = i;
                            found = true;
                            break;
                        }
                    }
                    
                    if (!found) {
                        const option = document.createElement('option');
                        option.value = missionId;
                        option.text = missionTitle ? `${missionId}: ${missionTitle}` : missionId;
                        option.selected = true;
                        select.add(option, select.options[1]);
                    }
                    
                    document.getElementById('status').value = 'submission';
                    toggleRepoField();
                }
                
                document.getElementById('name').addEventListener('change', () => {
                    const nameValue = document.getElementById('name').value.trim();
                    if (nameValue) {
                        localStorage.setItem('apprenticeName', nameValue);
                        loadJobHistory();
                    }
                });
                
                if (storedName) {
                    loadJobHistory();
                }
            };
            
            function switchTab(tabId) {
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
                
                event.target.classList.add('active');
                document.getElementById(`tab-${tabId}`).classList.add('active');
                
                if (tabId === 'history') {
                    loadJobHistory();
                }
            }
            
            function toggleRepoField() {
                const status = document.getElementById('status').value;
                const repoGroup = document.getElementById('repoGroup');
                if (status === 'submission') {
                    repoGroup.style.display = 'block';
                    document.getElementById('repo_url').required = true;
                } else {
                    repoGroup.style.display = 'none';
                    document.getElementById('repo_url').required = false;
                }
            }
            
            async function handleSubmit(e) {
                e.preventDefault();
                
                const submitBtn = document.getElementById('submitBtn');
                const isCodeSubmission = document.getElementById('status').value === 'submission';
                
                submitBtn.disabled = true;
                submitBtn.textContent = 'Submitting...';
                
                if (isCodeSubmission) {
                    document.getElementById('progressContainer').classList.add('active');
                    document.getElementById('logWindow').innerHTML = '<div class="log-entry">> Sending submission...</div>';
                }
                
                const formData = new FormData(e.target);
                const data = {
                    mission_id: formData.get('mission'),
                    status: formData.get('status'),
                    name: formData.get('name'),
                    repo_url: formData.get('repo_url'),
                    message: formData.get('message')
                };
                
                localStorage.setItem('apprenticeName', data.name);
                
                try {
                    const response = await fetch(`${BASE_PATH}/submit`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (isCodeSubmission && result.job_id) {
                        pollProgress(result.job_id);
                        loadJobHistory();
                    } else {
                        document.getElementById('successMessage').classList.add('show');
                        document.getElementById('submitForm').reset();
                        submitBtn.disabled = false;
                        submitBtn.textContent = '⚡ Submit';
                        setTimeout(() => {
                            document.getElementById('successMessage').classList.remove('show');
                        }, 5000);
                    }
                    
                } catch (error) {
                    alert('Error submitting. Please try again.');
                    submitBtn.disabled = false;
                    submitBtn.textContent = '⚡ Submit';
                }
            }
            
            async function pollProgress(jobId) {
                const logWindow = document.getElementById('logWindow');
                const stepsContainer = document.getElementById('stepsContainer');
                const steps = stepsContainer.children;
                
                const interval = setInterval(async () => {
                    try {
                        const res = await fetch(`${BASE_PATH}/status/${jobId}`);
                        const data = await res.json();
                        
                        logWindow.innerHTML = data.logs.map(l => `<div class="log-entry">${l}</div>`).join('');
                        logWindow.scrollTop = logWindow.scrollHeight;
                        
                        data.steps.forEach((step, idx) => {
                            if (step.status === 'completed') {
                                steps[idx].classList.add('completed');
                                steps[idx].classList.remove('active');
                            } else if (step.status === 'running') {
                                steps[idx].classList.add('active');
                            }
                        });
                        
                        if (data.status === 'completed' || data.status === 'failed') {
                            clearInterval(interval);
                            document.getElementById('submitBtn').disabled = false;
                            document.getElementById('submitBtn').textContent = '⚡ Submit Another';
                            
                            if (data.status === 'completed') {
                                const resultCard = document.getElementById('resultCard');
                                resultCard.classList.add('active');
                                document.getElementById('finalScore').textContent = data.score + '/100';
                                const statusEl = document.getElementById('finalStatus');
                                if (data.score >= 90) {
                                    statusEl.textContent = 'APPROVED ✅';
                                    statusEl.className = 'result-status success';
                                } else {
                                    statusEl.textContent = 'NEEDS IMPROVEMENT ⚠️';
                                    statusEl.className = 'result-status warning';
                                }
                            }
                            loadJobHistory();
                        }
                    } catch (e) {
                        console.error(e);
                    }
                }, 1000);
            }
            
            async function loadJobHistory() {
                const name = document.getElementById('name').value.trim();
                const historyStatus = document.getElementById('historyStatus');
                const historyList = document.getElementById('historyList');
                
                if (!name) {
                    historyStatus.textContent = 'Enter your name in the Submit tab to load history.';
                    historyList.innerHTML = '';
                    return;
                }
                
                historyStatus.textContent = 'Loading...';
                
                try {
                    const res = await fetch(`${BASE_PATH}/jobs?apprentice=${encodeURIComponent(name)}&limit=10`);
                    const data = await res.json();
                    
                    if (!data.jobs || data.jobs.length === 0) {
                        historyStatus.textContent = 'No submissions yet. Run your first harvest!';
                        historyList.innerHTML = `
                            <div class="empty-state">
                                <div class="icon">📭</div>
                                <p>No submissions found</p>
                            </div>
                        `;
                        return;
                    }
                    
                    historyStatus.textContent = `Showing ${data.jobs.length} recent submissions`;
                    historyList.innerHTML = data.jobs.map(job => renderJobCard(job)).join('');
                } catch (err) {
                    console.error(err);
                    historyStatus.textContent = 'Unable to load history.';
                }
            }
            
            function renderJobCard(job) {
                const score = job.score !== null && job.score !== undefined ? `${job.score}/100` : '—';
                const submitted = job.started_at ? formatTimestamp(job.started_at) : '—';
                const mission = job.mission_id || '—';
                const repo = job.repo_url ? `<a href="${job.repo_url}" target="_blank">${job.repo_url.split('/').slice(-1)[0]}</a>` : '—';
                const statusClass = job.status === 'completed' ? 'success' : (job.status === 'failed' ? 'failed' : '');
                
                return `
                    <div class="history-card">
                        <div class="history-header">
                            <span class="history-mission">Mission: ${mission}</span>
                            <span class="history-score ${statusClass}">${job.status?.toUpperCase()} • ${score}</span>
                        </div>
                        <div class="history-meta">
                            <div><strong>Repo:</strong> ${repo}</div>
                            <div><strong>Started:</strong> ${submitted}</div>
                        </div>
                        <button class="view-log-btn" onclick="window.open('${BASE_PATH}/status/${job.job_id}', '_blank')">View Logs →</button>
                    </div>
                `;
            }
            
            function formatTimestamp(ts) {
                return ts ? ts.replace('T', ' ').slice(0, 19) : '—';
            }
        </script>
    </body>
    </html>
    """

@app.post("/submit")
async def submit_feedback(feedback: FeedbackSubmission, background_tasks: BackgroundTasks):
    """Save feedback submission"""
    feedback.timestamp = datetime.now().isoformat()

    filename = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = FEEDBACK_DIR / filename

    with open(filepath, 'w') as f:
        json.dump(feedback.dict(), f, indent=2)

    log_file = FEEDBACK_DIR / "all_feedback.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps(feedback.dict()) + '\n')
    
    job_id = None
    if feedback.status == "submission" and feedback.repo_url:
        job_id = str(uuid.uuid4())
        job_registry.create_job(
            job_id=job_id,
            apprentice=feedback.name,
            repo_url=feedback.repo_url,
            mission_id=feedback.mission_id,
            mode="gatekeeper",
            source="web",
            status="queued",
            metadata={"submission_type": feedback.status},
        )
        background_tasks.add_task(
            run_harvest_job, 
            job_id, 
            feedback.name, 
            feedback.repo_url,
            feedback.mission_id
        )
    
    return {
        "status": "success", 
        "message": "Feedback received!",
        "job_id": job_id,
    }

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get real-time status of harvest job"""
    job_file = JOBS_DIR / f"{job_id}.json"
    if job_file.exists():
        with open(job_file, 'r') as f:
            return json.load(f)
    return {"status": "unknown", "logs": [], "steps": []}


@app.get("/jobs")
async def list_jobs(
    apprentice: str = Query(..., description="Apprentice name to filter by"),
    limit: int = Query(10, ge=1, le=50),
    mission_id: Optional[str] = Query(None, description="Optional mission filter"),
):
    """Return recent harvest jobs for an apprentice"""
    jobs = job_registry.list_jobs(
        limit=limit,
        apprentice=apprentice if apprentice else None,
        mission_id=mission_id,
        source=None,
    )
    formatted: List[Dict[str, Optional[str]]] = []
    for job in jobs:
        formatted.append({
            "job_id": job.get("job_id"),
            "apprentice": job.get("apprentice"),
            "mission_id": job.get("mission_id"),
            "repo_url": job.get("repo_url"),
            "mode": job.get("mode"),
            "status": job.get("status"),
            "score": job.get("score"),
            "started_at": job.get("started_at"),
            "finished_at": job.get("finished_at"),
            "metadata": job.get("metadata", {}),
        })
    return {"jobs": formatted}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """View all feedback submissions"""
    log_file = FEEDBACK_DIR / "all_feedback.jsonl"
    submissions = []
    if log_file.exists():
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    try: submissions.append(json.loads(line))
                    except: pass
    submissions.reverse()

    rows = ""
    for sub in submissions:
        rows += f"<div style='background:white; padding:15px; margin-bottom:10px; border-radius:8px;'><strong>{sub.get('name')}</strong> - {sub.get('status')} <br> {sub.get('message')}</div>"

    return f"""
    <html><body style="background:#eee; padding:20px; font-family:sans-serif;">
    <h1>Dashboard</h1>
    {rows}
    </body></html>
    """

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "harvester"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8055)
