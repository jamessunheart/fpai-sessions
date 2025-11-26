#!/usr/bin/env python3
"""
Simple Apprentice Feedback System
Port 8055 - Allows apprentices to report mission completion/issues
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
from core.jobs import registry as job_registry  # noqa: E402

app = FastAPI(title="Apprentice Feedback", version="1.0")

# Centralized paths
FEEDBACK_DIR = app_settings.feedback_dir
JOBS_DIR = app_settings.jobs_dir

# Mount static files
app.mount("/static", StaticFiles(directory="SERVICES/landing-page/app/static"), name="static")

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

    update_state() # Save initial
    job_registry.update_job(job_id, status="running")
    
    # Update Mission Hub if mission_id provided
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
        
        # Notify that submission is in progress
        notify_mission_hub("submitted")
        
        script_path = Path("/Users/jamessunheart/FPAI_Cockpit/_scripts/harvest-apprentice.py")
        # Adjust path for production server if needed
        if not script_path.exists():
                script_path = Path("/root/FPAI_Cockpit/_scripts/harvest-apprentice.py")
        
        if not script_path.exists():
            update_state("❌ Error: Harvester script not found!", final_status="failed")
            job_registry.update_job(job_id, status="failed", metadata={"error": "harvester script missing"})
            return

        update_state("📦 Cloning repository...", step_idx=0, step_status="running")
        
        # Run the command unbuffered
        process = subprocess.Popen(
            [str(script_path), name.replace(" ", ""), repo_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1 # Line buffered
        )
        
        # Stream output
        output_buffer = ""
        final_score = 0
        for line in process.stdout:
            line = line.strip()
            if not line: continue
            
            output_buffer += line + "\n"
            update_state(f"> {line}")
            
            # Heuristic step updating based on log output
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
                
                # Extract score
                score_match = re.search(r'Score:\s*(\d+)', line)
                if score_match:
                    final_score = int(score_match.group(1))
                    update_state(final_score=final_score)

        process.wait()
        
        if process.returncode == 0:
            update_state("✅ Harvest complete!", final_status="completed")
            # Ensure all steps marked complete
            for i in range(5):
                state["steps"][i]["status"] = "completed"
            with open(job_file, "w") as f:
                json.dump(state, f)
            
            # Notify Mission Hub of completion
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
    """Show feedback form"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Apprentice Portal | Full Potential AI</title>
        <style>
            :root {
                --primary: #667eea;
                --secondary: #764ba2;
                --bg: #f3f4f6;
                --text: #1f2937;
                --card-bg: #ffffff;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--bg);
                color: var(--text);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 40px 20px;
            }
            .logo {
                width: 80px;
                height: 80px;
                margin-bottom: 20px;
                background: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                font-size: 40px;
            }
            .container {
                background: var(--card-bg);
                border-radius: 16px;
                padding: 40px;
                max-width: 600px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            }
            h1 {
                color: var(--secondary);
                margin-bottom: 10px;
                font-size: 24px;
                text-align: center;
            }
            p.subtitle {
                color: #666;
                margin-bottom: 30px;
                text-align: center;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                color: #333;
                font-weight: 600;
                margin-bottom: 8px;
            }
            input, select, textarea {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                font-family: inherit;
                transition: border-color 0.3s;
            }
            input:focus, select:focus, textarea:focus {
                outline: none;
                border-color: var(--primary);
            }
            textarea {
                min-height: 100px;
                resize: vertical;
            }
            button {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }
            button:disabled {
                opacity: 0.7;
                cursor: not-allowed;
                transform: none;
            }
            
            /* Progress & Logs */
            .progress-container {
                display: none;
                margin-top: 30px;
                border-top: 1px solid #eee;
                padding-top: 20px;
            }
            .steps {
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
                font-size: 12px;
            }
            .step {
                display: flex;
                flex-direction: column;
                align-items: center;
                color: #aaa;
                position: relative;
                flex: 1;
            }
            .step.active { color: var(--primary); font-weight: bold; }
            .step.completed { color: #10b981; }
            .step-dot {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #eee;
                margin-bottom: 5px;
                border: 2px solid white;
                box-shadow: 0 0 0 1px #ddd;
            }
            .step.active .step-dot { background: var(--primary); box-shadow: 0 0 0 2px var(--primary); }
            .step.completed .step-dot { background: #10b981; box-shadow: 0 0 0 1px #10b981; }
            
            .log-window {
                background: #1e1e1e;
                color: #00ff00;
                font-family: monospace;
                padding: 15px;
                border-radius: 8px;
                height: 200px;
                overflow-y: auto;
                font-size: 12px;
                line-height: 1.5;
                margin-top: 10px;
            }
            .log-entry { margin-bottom: 2px; }
            .log-entry.error { color: #ff4444; }
            
            .result-card {
                display: none;
                margin-top: 20px;
                padding: 20px;
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 8px;
                text-align: center;
            }
            .result-score { font-size: 32px; font-weight: bold; color: #166534; }
            
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }
            .tab-link {
                flex: 1;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
                background: #fff;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }
            .tab-link.active {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white;
                border-color: transparent;
            }
            .tab-panels .tab-panel { display: none; }
            .tab-panel.active { display: block; }

            .two-column {
                display: flex;
                gap: 16px;
                flex-wrap: wrap;
            }
            .two-column > div { flex: 1 1 200px; }

            .rubric-card {
                margin-top: 24px;
                background: #f8fafc;
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #e2e8f0;
            }
            .rubric-card h3 { margin-bottom: 12px; color: var(--secondary); }
            .rubric-card ul { padding-left: 20px; margin-bottom: 10px; }
            .rubric-card li { margin-bottom: 6px; }
            .note { font-size: 12px; color: #64748b; margin-top: 8px; }

            .flash-success {
                background: #ecfdf5;
                border: 1px solid #bbf7d0;
                color: #166534;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 16px;
                font-weight: 600;
                text-align: center;
            }

            .history-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            .history-status { font-size: 13px; color: #64748b; }
            .history-list { display: flex; flex-direction: column; gap: 12px; }
            .history-card {
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 16px;
                background: white;
            }
            .history-card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            .history-mission { font-weight: 600; color: #1f2937; }
            .history-score { font-weight: 600; color: #1f2937; }
            .history-status-success { color: #15803d; }
            .history-status-error { color: #b91c1c; }
            .history-card-body { font-size: 14px; color: #475569; line-height: 1.5; }
            .history-card-body a { color: var(--primary); }
            .history-card-footer { text-align: right; margin-top: 12px; }
            .view-log-btn {
                background: none;
                border: 1px solid var(--primary);
                color: var(--primary);
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
            }
            .view-log-btn:hover {
                background: var(--primary);
                color: white;
            }

            .checklist-card {
                background: #f8fafc;
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #e2e8f0;
                line-height: 1.6;
            }
            .checklist-card ol { padding-left: 20px; }
            .checklist-card li { margin-bottom: 10px; }
            .checklist-card a { color: var(--primary); }

        </style>
    </head>
    <body>
        <div class="logo">⚡</div>
        
        <div class="container">
            <h1>Apprentice Portal</h1>
            <p class="subtitle">Submit missions • Track history • <a href="/missions" style="color: var(--primary);">Browse Mission Hub →</a></p>

            <div class="tabs">
                <button class="tab-link active" id="tab-submit-btn" onclick="switchTab('submit')">Submit</button>
                <button class="tab-link" id="tab-history-btn" onclick="switchTab('history')">History</button>
                <button class="tab-link" id="tab-checklist-btn" onclick="switchTab('checklist')">Checklist</button>
            </div>

            <div class="tab-panels">
                <div class="tab-panel active" id="tab-submit">
                    <div id="successMessage" class="flash-success" style="display:none;">
                        ✅ Submission Received!
            </div>

            <form id="feedbackForm" onsubmit="submitFeedback(event)">
                <div class="form-group">
                    <label for="name">Your Name:</label>
                    <input type="text" id="name" name="name" required placeholder="e.g., Alex">
                </div>

                        <div class="form-group two-column">
                            <div>
                    <label for="mission">Mission:</label>
                    <select id="mission" name="mission" required>
                        <option value="">Select a mission...</option>
                        <option value="mission-1">Mission 1: Reddit Launch</option>
                        <option value="mission-2">Mission 2: Magnet Trading Keys</option>
                        <option value="mission-3">Mission 3: Both Missions</option>
                        <option value="other">Other</option>
                    </select>
                </div>
                            <div>
                                <label for="status">Action:</label>
                    <select id="status" name="status" required onchange="toggleRepoField()">
                                    <option value="">Select action...</option>
                                    <option value="submission">📤 Submit Code for Review</option>
                                    <option value="completed">✅ Report Completion (No Code)</option>
                                    <option value="stuck">❌ Report Blocked/Stuck</option>
                                    <option value="question">❓ Ask Question</option>
                    </select>
                            </div>
                </div>

                <div class="form-group" id="repoGroup" style="display: none;">
                            <label for="repo_url">GitHub Repository URL:</label>
                    <input type="url" id="repo_url" name="repo_url" placeholder="https://github.com/username/repo">
                </div>

                <div class="form-group">
                            <label for="message">Notes:</label>
                            <textarea id="message" name="message" required placeholder="Details..."></textarea>
                        </div>

                        <button type="submit" id="submitBtn">Submit</button>
                    </form>

                    <div class="rubric-card">
                        <h3>Quality Rubric</h3>
                        <ul>
                            <li>✅ Tests exist (20%)</li>
                            <li>✅ Tests pass (30%)</li>
                            <li>✅ README / documentation (20%)</li>
                            <li>✅ Dependencies declared (15%)</li>
                            <li>✅ No secrets/static keys (15%)</li>
                        </ul>
                        <p class="note">Tip: run <code>./_scripts/apprentice-preflight-check.sh</code> before submitting.</p>
                    </div>
                    
                    <div id="progressContainer" class="progress-container">
                        <h3>🚜 Auto-Harvest in Progress...</h3>
                        
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
                            <div class="log-entry">> Initialization complete.</div>
                        </div>
                        
                        <div id="resultCard" class="result-card">
                            <div>Quality Score</div>
                            <div class="result-score" id="finalScore">--</div>
                            <div id="finalStatus"></div>
                        </div>
                    </div>
                </div>

                <div class="tab-panel" id="tab-history">
                    <div class="history-header">
                        <h3>Recent Harvests</h3>
                        <span id="historyStatus" class="history-status">Enter your name to load history.</span>
                    </div>
                    <div id="historyList" class="history-list"></div>
                </div>

                <div class="tab-panel" id="tab-checklist">
                    <div class="checklist-card">
                        <h3>Preflight Checklist</h3>
                        <ol>
                            <li>Run <code>./_scripts/apprentice-preflight-check.sh</code> locally.</li>
                            <li>Ensure tests pass: <code>pytest -v</code>.</li>
                            <li>Create/Update <code>README.md</code> with overview + setup.</li>
                            <li>Declare dependencies (<code>requirements.txt</code> or <code>package.json</code>).</li>
                            <li>Scan for secrets: <code>rg -i "API_KEY|SECRET|TOKEN"</code>.</li>
                            <li>Clean git status (`git status` should only show intentional files).</li>
                            <li>Push to GitHub before submitting here.</li>
                        </ol>
                        <p class="note">Need help? See <a href="/_guides/operations/APPRENTICE_SUBMISSION_GUIDE.html" target="_blank">Apprentice Submission Guide</a>.</p>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const BASE_PATH = window.location.pathname.startsWith('/harvester') ? '/harvester' : '';

            // Initialize form from URL params
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
                    
                    // Check if option exists, if not add it
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
                        // Insert after default option
                        select.add(option, select.options[1]);
                    }
                    
                    // If mission is present, assume submission intent
                    const statusSelect = document.getElementById('status');
                    statusSelect.value = 'submission';
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
                document.querySelectorAll('.tab-link').forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
                document.getElementById(`tab-${tabId}-btn`).classList.add('active');
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

            async function submitFeedback(e) {
                e.preventDefault();
                
                const submitBtn = document.getElementById('submitBtn');
                const isCodeSubmission = document.getElementById('status').value === 'submission';
                
                submitBtn.disabled = true;
                
                if (isCodeSubmission) {
                    document.getElementById('progressContainer').style.display = 'block';
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

                try {
                    const response = await fetch(`${BASE_PATH}/submit`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });

                        const result = await response.json();
                    localStorage.setItem('apprenticeName', data.name);
                    
                    if (isCodeSubmission && result.job_id) {
                        // Start polling for progress
                        pollProgress(result.job_id);
                        loadJobHistory();
                    } else {
                        document.getElementById('successMessage').style.display = 'block';
                        document.getElementById('feedbackForm').reset();
                        submitBtn.disabled = false;
                            setTimeout(() => {
                            document.getElementById('successMessage').style.display = 'none';
                            }, 5000);
                    }
                    
                } catch (error) {
                    alert('Error submitting feedback. Please try again.');
                    submitBtn.disabled = false;
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
                        
                        // Update Logs
                        logWindow.innerHTML = data.logs.map(l => `<div class="log-entry">${l}</div>`).join('');
                        logWindow.scrollTop = logWindow.scrollHeight;
                        
                        // Update Steps
                        data.steps.forEach((step, idx) => {
                            if (step.status === 'completed') {
                                steps[idx].classList.add('completed');
                                steps[idx].classList.remove('active');
                            } else if (step.status === 'running') {
                                steps[idx].classList.add('active');
                            }
                        });
                        
                        // Check completion
                        if (data.status === 'completed' || data.status === 'failed') {
                            clearInterval(interval);
                            document.getElementById('submitBtn').disabled = false;
                            document.getElementById('submitBtn').innerText = "Submit Another";
                            
                       if (data.status === 'completed') {
                                document.getElementById('resultCard').style.display = 'block';
                                document.getElementById('finalScore').innerText = data.score + '/100';
                                document.getElementById('finalStatus').innerText = data.score >= 90 ? "APPROVED ✅" : "NEEDS IMPROVEMENT ⚠️";
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
                historyStatus.innerText = "Enter your name to load history.";
                historyList.innerHTML = '';
                return;
            }

            historyStatus.innerText = "Loading history...";
            try {
                const res = await fetch(`${BASE_PATH}/jobs?apprentice=${encodeURIComponent(name)}&limit=10`);
                const data = await res.json();
                if (!data.jobs || data.jobs.length === 0) {
                    historyStatus.innerText = "No submissions yet. Run your first harvest!";
                    historyList.innerHTML = '';
                    return;
                }
                historyStatus.innerText = `Showing ${data.jobs.length} recent submissions.`;
                historyList.innerHTML = data.jobs.map(job => renderJobCard(job)).join('');
            } catch (err) {
                console.error(err);
                historyStatus.innerText = "Unable to load history.";
            }
        }

        function renderJobCard(job) {
            const score = job.score !== null && job.score !== undefined ? `${job.score}/100` : '—';
            const submitted = job.started_at ? formatTimestamp(job.started_at) : '—';
            const mission = job.mission_id || '—';
            const repo = job.repo_url ? `<a href="${job.repo_url}" target="_blank">${job.repo_url}</a>` : '—';
            const statusClass = job.status === 'completed' ? 'history-status-success' : (job.status === 'failed' ? 'history-status-error' : '');
            return `
                <div class="history-card">
                    <div class="history-card-header">
                        <span class="history-mission">Mission: ${mission}</span>
                        <span class="history-score ${statusClass}">${job.status?.toUpperCase()} • Score ${score}</span>
                    </div>
                    <div class="history-card-body">
                        <div><strong>Repo:</strong> ${repo}</div>
                        <div><strong>Started:</strong> ${submitted}</div>
                        ${job.finished_at ? `<div><strong>Finished:</strong> ${formatTimestamp(job.finished_at)}</div>` : ''}
                    </div>
                    <div class="history-card-footer">
                        <button class="view-log-btn" onclick="window.open('${BASE_PATH}/status/${job.job_id}', '_blank')">View Logs →</button>
                    </div>
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
    # Add timestamp
    feedback.timestamp = datetime.now().isoformat()

    # Save to file
    filename = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = FEEDBACK_DIR / filename

    with open(filepath, 'w') as f:
        json.dump(feedback.dict(), f, indent=2)

    # Also append to master log
    log_file = FEEDBACK_DIR / "all_feedback.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps(feedback.dict()) + '\n')
    
    # NEW: Trigger Harvest if this is a code submission
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
        # Run as background task so we can return job_id immediately
        background_tasks.add_task(
            run_harvest_job, 
            job_id, 
            feedback.name, 
            feedback.repo_url,
            feedback.mission_id  # Pass mission ID for status updates
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
    """Return recent harvest jobs for an apprentice (optionally filtered by mission)."""
    jobs = job_registry.list_jobs(
        limit=limit,
        apprentice=apprentice if apprentice else None,
        mission_id=mission_id,
        source=None,
    )
    formatted: List[Dict[str, Optional[str]]] = []
    for job in jobs:
        formatted.append(
            {
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
            }
        )
    return {"jobs": formatted}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """View all feedback submissions"""
    # (Existing dashboard code remains mostly same, just simpler for brevity in this snippet)
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
    return {"status": "healthy", "service": "apprentice-feedback"}

if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 to allow external access on server
    uvicorn.run(app, host="0.0.0.0", port=8055)
