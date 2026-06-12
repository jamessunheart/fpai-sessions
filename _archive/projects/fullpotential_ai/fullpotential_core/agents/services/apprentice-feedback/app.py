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
FEEDBACK_DIR = Path("/Users/jamessunheart/Development/data/apprentice-feedback")
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

class FeedbackSubmission(BaseModel):
    mission_id: str
    status: str  # "completed" or "stuck"
    name: str
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
            .success-message {
                display: none;
                background: #10b981;
                color: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                text-align: center;
            }
            .missions-link {
                display: block;
                text-align: center;
                margin-top: 20px;
                color: #667eea;
                text-decoration: none;
                font-weight: 600;
            }
            .missions-link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Mission Feedback</h1>
            <p>Report completion or get help with your mission</p>

            <div id="successMessage" class="success-message">
                ✅ Feedback submitted! James will review shortly.
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
                    <select id="status" name="status" required>
                        <option value="">Select status...</option>
                        <option value="completed">✅ Completed!</option>
                        <option value="stuck">❌ Got Stuck</option>
                        <option value="question">❓ Have a Question</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="message">Details:</label>
                    <textarea id="message" name="message" required placeholder="If completed: Paste any URLs or results&#10;If stuck: Tell us exactly where and what error you got&#10;If question: Ask away!"></textarea>
                </div>

                <button type="submit">Submit Feedback</button>
            </form>

            <a href="https://fullpotential.ai/missions" class="missions-link">
                ← Back to Missions Portal
            </a>
        </div>

        <script>
            async function submitFeedback(e) {
                e.preventDefault();

                const formData = new FormData(e.target);
                const data = {
                    mission_id: formData.get('mission'),
                    status: formData.get('status'),
                    name: formData.get('name'),
                    message: formData.get('message')
                };

                try {
                    const response = await fetch('/submit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });

                    if (response.ok) {
                        document.getElementById('successMessage').style.display = 'block';
                        document.getElementById('feedbackForm').reset();
                        setTimeout(() => {
                            document.getElementById('successMessage').style.display = 'none';
                        }, 5000);
                    }
                } catch (error) {
                    alert('Error submitting feedback. Please try again.');
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

    return {"status": "success", "message": "Feedback received!"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """View all feedback submissions"""
    log_file = FEEDBACK_DIR / "all_feedback.jsonl"

    submissions = []
    if log_file.exists():
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    submissions.append(json.loads(line))

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
            }
            .completed { border-left-color: #10b981; }
            .stuck { border-left-color: #ef4444; }
            .question { border-left-color: #f59e0b; }
            .meta { color: #666; font-size: 14px; margin-bottom: 10px; }
            .message { color: #333; white-space: pre-wrap; }
            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                margin-left: 10px;
            }
            .status-completed { background: #d1fae5; color: #065f46; }
            .status-stuck { background: #fee2e2; color: #991b1b; }
            .status-question { background: #fef3c7; color: #92400e; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Apprentice Feedback Dashboard</h1>
            <p><strong>Total Submissions:</strong> """ + str(len(submissions)) + """</p>
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
    """

    for sub in submissions:
        status_class = sub['status']
        html += f"""
            <div class="submission {status_class}">
                <div class="meta">
                    <strong>{sub.get('name', 'Anonymous')}</strong>
                    <span class="status-badge status-{status_class}">{sub['status'].upper()}</span>
                    <br>
                    Mission: {sub['mission_id']} | {sub.get('timestamp', 'No timestamp')}
                </div>
                <div class="message">{sub['message']}</div>
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
    uvicorn.run(app, host="0.0.0.0", port=8055)
