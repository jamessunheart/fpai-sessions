#!/usr/bin/env python3
"""
Simple Apprentice Feedback System
Port 8055 - Allows apprentices to report mission completion/issues
"""

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
import json
import os
from pathlib import Path

app = FastAPI(title="Apprentice Feedback", version="1.0")

# Create feedback directory if it doesn't exist
# Use a path inside the workspace to avoid permission issues
FEEDBACK_DIR = Path("data/apprentice-feedback")
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

class FeedbackSubmission(BaseModel):
    mission_id: str
    status: str  # "completed", "stuck", "submission"
    name: str
    repo_url: str = None
    message: str
    timestamp: str = None

@app.get("/", response_class=HTMLResponse)
async def home():
    """Show feedback form"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mission Feedback - Full Potential</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 16px;
                padding: 40px;
                max-width: 600px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 {
                color: #667eea;
                margin-bottom: 10px;
                font-size: 28px;
            }
            p {
                color: #666;
                margin-bottom: 30px;
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
                border-color: #667eea;
                background-color: #fff;
            }
            textarea {
                min-height: 120px;
                resize: vertical;
            }
            button {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            button:active {
                transform: translateY(0);
            }
            .spinner {
                display: none;
                width: 40px;
                height: 40px;
                margin: 20px auto;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .verification-result {
                display: none;
                margin-top: 20px;
                padding: 20px;
                border-radius: 8px;
                background: #f8fafc;
                border: 1px solid #e2e8f0;
            }
            .score-badge {
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Mission Feedback</h1>
            <p>Report completion or get help with your mission</p>

            <div id="loadingSpinner" class="spinner"></div>
            <div id="statusText" style="text-align: center; display: none; color: #666; margin-bottom: 20px;">Processing...</div>

            <div id="successMessage" class="success-message">
                ✅ Feedback submitted!
            </div>

            <div id="verificationResult" class="verification-result">
                <h3>🔍 Verification Results</h3>
                <div id="scoreDisplay"></div>
                <pre id="feedbackDetails" style="white-space: pre-wrap; margin-top: 10px; font-family: monospace; font-size: 13px; color: #333;"></pre>
            </div>

            <form id="feedbackForm" onsubmit="submitFeedback(event)">
                <div class="form-group">
                    <label for="name">Your Name:</label>
                    <input type="text" id="name" name="name" required placeholder="e.g., Alex">
                </div>

                <div class="form-group">
                    <label for="mission">Mission:</label>
                    <select id="mission" name="mission" required>
                        <option value="">Select a mission...</option>
                        <option value="mission-1">Mission 1: Reddit Launch</option>
                        <option value="mission-2">Mission 2: Magnet Trading Keys</option>
                        <option value="mission-3">Mission 3: Both Missions</option>
                        <option value="other">Other</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="status">Status:</label>
                    <select id="status" name="status" required onchange="toggleRepoField()">
                        <option value="">Select status...</option>
                        <option value="submission">📤 Submitting Code</option>
                        <option value="completed">✅ Completed!</option>
                        <option value="stuck">❌ Got Stuck</option>
                        <option value="question">❓ Have a Question</option>
                    </select>
                </div>

                <div class="form-group" id="repoGroup" style="display: none;">
                    <label for="repo_url">Repository URL (GitHub):</label>
                    <input type="url" id="repo_url" name="repo_url" placeholder="https://github.com/username/repo">
                </div>

                <div class="form-group">
                    <label for="message">Details:</label>
                    <textarea id="message" name="message" required placeholder="If submitting code: Paste any additional notes here&#10;If stuck: Tell us exactly where and what error you got"></textarea>
                </div>

                <button type="submit">Submit Feedback</button>
            </form>

            <a href="https://fullpotential.ai/missions" class="missions-link">
                ← Back to Missions Portal
            </a>
        </div>

        <script>
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
                
                const submitBtn = e.target.querySelector('button[type="submit"]');
                const isCodeSubmission = document.getElementById('status').value === 'submission';
                
                submitBtn.disabled = true;
                submitBtn.innerText = isCodeSubmission ? 'Running Verification...' : 'Submitting...';
                
                if (isCodeSubmission) {
                    document.getElementById('loadingSpinner').style.display = 'block';
                    document.getElementById('statusText').style.display = 'block';
                    document.getElementById('statusText').innerText = "🚜 Harvesting repo & running tests...";
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
                    const response = await fetch('/submit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });

                    if (response.ok) {
                        const result = await response.json();
                        
                        // Hide spinner
                        document.getElementById('loadingSpinner').style.display = 'none';
                        document.getElementById('statusText').style.display = 'none';
                        
                        // Show success message
                        const msgDiv = document.getElementById('successMessage');
                        msgDiv.innerText = '✅ ' + result.message;
                        msgDiv.style.display = 'block';
                        
                        // If we have verification results, show them
                        if (result.harvest_result) {
                            const vDiv = document.getElementById('verificationResult');
                            vDiv.style.display = 'block';
                            
                            const score = result.harvest_result.score || 0;
                            let icon = score >= 90 ? '🏆' : (score >= 80 ? '✅' : '⚠️');
                            
                            document.getElementById('scoreDisplay').innerHTML = `
                                <div class="score-badge">${icon} Quality Score: ${score}/100</div>
                                <div style="margin-top: 5px; font-weight: bold; color: ${score >= 80 ? '#10b981' : '#f59e0b'}">
                                    Status: ${result.harvest_result.status}
                                </div>
                            `;
                            
                            // Format feedback nicely
                            let details = "";
                            if (result.harvest_result.path) details += `📂 Location: ${result.harvest_result.path}\n`;
                            if (result.harvest_result.error) details += `❌ Error: ${result.harvest_result.error}\n`;
                            
                            document.getElementById('feedbackDetails').innerText = details;
                        }
                        
                        document.getElementById('feedbackForm').reset();
                        document.getElementById('repoGroup').style.display = 'none';
                        submitBtn.innerText = "Submit Feedback";
                        submitBtn.disabled = false;
                        
                        // Only hide success message after delay if it's NOT a code submission
                        // We want code results to stay visible
                        if (!isCodeSubmission) {
                            setTimeout(() => {
                                msgDiv.style.display = 'none';
                            }, 5000);
                        }
                    }
                } catch (error) {
                    alert('Error submitting feedback. Please try again.');
                    submitBtn.disabled = false;
                    submitBtn.innerText = "Submit Feedback";
                    document.getElementById('loadingSpinner').style.display = 'none';
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/submit")
async def submit_feedback(feedback: FeedbackSubmission):
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
    if feedback.status == "submission" and feedback.repo_url:
        try:
            import subprocess
            import re
            
            # Run harvest script SYNCHRONOUSLY to capture output
            script_path = Path("/Users/jamessunheart/FPAI_Cockpit/_scripts/harvest-apprentice.py")
            # Adjust path for production server if needed
            if not script_path.exists():
                 script_path = Path("/root/FPAI_Cockpit/_scripts/harvest-apprentice.py")
            
            if script_path.exists():
                cmd = [
                    str(script_path),
                    feedback.name.replace(" ", ""),
                    feedback.repo_url
                ]
                
                # Run with timeout
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True,
                    timeout=300 # 5 min max
                )
                
                # Parse output for score
                output = result.stdout
                score = 0
                score_match = re.search(r'Score:\s*(\d+)', output)
                if score_match:
                    score = int(score_match.group(1))
                
                status = "APPROVED" if "SUCCESS" in output else "FAILED"
                path = ""
                path_match = re.search(r'Location:\s*(.+)', output)
                if path_match:
                    path = path_match.group(1).strip()
                
                return {
                    "status": "success", 
                    "message": "Verification Complete!",
                    "harvest_result": {
                        "status": status,
                        "score": score,
                        "path": path,
                        "output": output[-500:] if len(output) > 500 else output
                    }
                }
                
        except Exception as e:
            print(f"Failed to auto-harvest: {e}")
            return {
                "status": "success", 
                "message": "Submission received but verification failed.",
                "harvest_result": {"error": str(e), "status": "ERROR"}
            }

    return {"status": "success", "message": "Feedback received! We will review it shortly."}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """View all feedback submissions"""
    log_file = FEEDBACK_DIR / "all_feedback.jsonl"

    submissions = []
    if log_file.exists():
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        submissions.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    # Reverse to show newest first
    submissions.reverse()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Feedback Dashboard</title>
        <style>
            body { font-family: system-ui; padding: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 { color: #333; }
            .submission {
                background: white;
                padding: 20px;
                margin-bottom: 15px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .completed { border-left-color: #10b981; }
            .stuck { border-left-color: #ef4444; }
            .question { border-left-color: #f59e0b; }
            .submission-type { border-left-color: #8b5cf6; }
            
            .meta { color: #666; font-size: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
            .message { color: #333; white-space: pre-wrap; margin-top: 10px; }
            .repo-link { 
                display: inline-block; 
                margin-top: 8px; 
                padding: 6px 12px; 
                background: #f3f4f6; 
                border-radius: 4px; 
                color: #4b5563; 
                text-decoration: none;
                font-family: monospace;
                border: 1px solid #e5e7eb;
            }
            .repo-link:hover { background: #e5e7eb; }
            
            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            .status-completed { background: #d1fae5; color: #065f46; }
            .status-stuck { background: #fee2e2; color: #991b1b; }
            .status-question { background: #fef3c7; color: #92400e; }
            .status-submission { background: #ddd6fe; color: #5b21b6; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Apprentice Feedback Dashboard</h1>
            <p><strong>Total Submissions:</strong> """ + str(len(submissions)) + """</p>
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
    """

    for sub in submissions:
        status = sub.get('status', 'unknown')
        status_class = status if status in ['completed', 'stuck', 'question'] else 'submission-type'
        
        repo_html = ""
        if sub.get('repo_url'):
            repo_html = f'<a href="{sub["repo_url"]}" target="_blank" class="repo-link">📦 {sub["repo_url"]}</a>'

        html += f"""
            <div class="submission {status_class}">
                <div class="meta">
                    <div>
                        <strong>{sub.get('name', 'Anonymous')}</strong>
                        <span class="status-badge status-{status_class}">{status.upper().replace('_', ' ')}</span>
                    </div>
                    <span>{sub.get('timestamp', '').split('T')[0]}</span>
                </div>
                <div style="font-size: 0.9em; color: #666;">Mission: {sub.get('mission_id', 'N/A')}</div>
                {repo_html}
                <div class="message">{sub.get('message', '')}</div>
            </div>
        """

    html += """
        </div>
    </body>
    </html>
    """

    return html

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "apprentice-feedback"}

if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 to allow external access on server
    uvicorn.run(app, host="0.0.0.0", port=8055)

