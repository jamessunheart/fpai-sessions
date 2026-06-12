#!/usr/bin/env python3
"""
VA Interface Portal
Secure web interface for VAs to submit credentials and receive instructions
"""

from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
from datetime import datetime
from typing import Dict
from credential_vault import CredentialVault
from blocker_delegation import BlockerDelegation

app = FastAPI(title="VA Task Portal", description="Secure credential submission for VAs")
templates = Jinja2Templates(directory="templates")

vault = CredentialVault()
delegation = BlockerDelegation()


@app.get("/task/{task_id}", response_class=HTMLResponse)
async def get_task_instructions(task_id: str, request: Request):
    """Display task instructions to VA"""

    task_file = delegation.tasks_dir / f"{task_id}.json"

    if not task_file.exists():
        raise HTTPException(status_code=404, detail="Task not found")

    with open(task_file) as f:
        task = json.load(f)

    # Load instruction markdown
    instructions_file = delegation.tasks_dir / f"{task_id}_instructions.md"
    instructions = ""
    if instructions_file.exists():
        instructions = instructions_file.read_text()

    return templates.TemplateResponse("task_view.html", {
        "request": request,
        "task_id": task_id,
        "task": task,
        "instructions": instructions
    })


@app.post("/task/{task_id}/submit")
async def submit_credentials(
    task_id: str,
    credentials: str = Form(...),
    va_name: str = Form(...),
    notes: str = Form(default="")
):
    """VA submits credentials for a task"""

    task_file = delegation.tasks_dir / f"{task_id}.json"

    if not task_file.exists():
        raise HTTPException(status_code=404, detail="Task not found")

    with open(task_file) as f:
        task = json.load(f)

    if task['status'] == 'completed':
        raise HTTPException(status_code=400, detail="Task already completed")

    # Parse credentials JSON
    try:
        credentials_data = json.loads(credentials)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for credentials")

    # Store in vault with metadata
    credentials_data['_submitted_by'] = va_name
    credentials_data['_submitted_at'] = datetime.now().isoformat()
    credentials_data['_notes'] = notes

    # Mark task as complete and store credentials
    delegation.mark_blocker_complete(task_id, credentials_data)

    return JSONResponse({
        "status": "success",
        "message": "Credentials received and stored securely",
        "task_id": task_id,
        "next_steps": "Payment will be released within 24 hours after verification"
    })


@app.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """Check task status"""

    task_file = delegation.tasks_dir / f"{task_id}.json"

    if not task_file.exists():
        raise HTTPException(status_code=404, detail="Task not found")

    with open(task_file) as f:
        task = json.load(f)

    return {
        "task_id": task_id,
        "status": task['status'],
        "created_at": task['created_at'],
        "completed_at": task.get('completed_at'),
        "credentials_stored": task.get('credentials_stored', False)
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """VA portal home page"""

    # Get all pending tasks
    pending = delegation.get_pending_blockers()

    return templates.TemplateResponse("portal_home.html", {
        "request": request,
        "pending_tasks": pending
    })


# HTML Templates (embedded for simplicity)
TASK_VIEW_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Task: {{ task.blocker }}</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 16px;
        }
        .instructions {
            background: #f8f9fa;
            padding: 24px;
            border-radius: 8px;
            margin: 24px 0;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 14px;
            line-height: 1.6;
        }
        .form-group {
            margin: 20px 0;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #555;
        }
        input, textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        textarea {
            font-family: monospace;
            min-height: 200px;
        }
        button {
            background: #667eea;
            color: white;
            padding: 14px 32px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }
        button:hover {
            background: #5568d3;
        }
        .status {
            padding: 12px 20px;
            border-radius: 6px;
            margin: 20px 0;
            font-weight: 600;
        }
        .status.pending {
            background: #fff3cd;
            color: #856404;
        }
        .status.completed {
            background: #d4edda;
            color: #155724;
        }
        .security-note {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 16px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Task: {{ task.blocker }}</h1>

        <div class="status {{ task.status }}">
            Status: {{ task.status }}
        </div>

        {% if task.status == 'pending' %}

        <h2>Instructions</h2>
        <div class="instructions">{{ instructions }}</div>

        <div class="security-note">
            <strong>⚠️ Security Note:</strong>
            <ul>
                <li>These credentials are monitored and logged</li>
                <li>Use ONLY for this specific task</li>
                <li>Do NOT share with anyone</li>
                <li>Submit in JSON format as shown in instructions</li>
            </ul>
        </div>

        <h2>Submit Credentials</h2>
        <form id="submitForm">
            <div class="form-group">
                <label>Your Name:</label>
                <input type="text" id="va_name" required placeholder="e.g., John Smith">
            </div>

            <div class="form-group">
                <label>Credentials (JSON format):</label>
                <textarea id="credentials" required placeholder='{
  "account_email": "ops@fullpotential.ai",
  "account_password": "your_password_here",
  "api_key": "pk_test_...",
  "secret_key": "sk_test_..."
}'></textarea>
            </div>

            <div class="form-group">
                <label>Notes (optional):</label>
                <textarea id="notes" style="min-height: 80px;" placeholder="Any additional information or issues encountered..."></textarea>
            </div>

            <button type="submit">Submit Credentials</button>
        </form>

        <div id="result" style="margin-top: 20px;"></div>

        {% else %}

        <div class="status completed">
            ✅ This task has been completed!
        </div>

        {% endif %}

    </div>

    <script>
        document.getElementById('submitForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData();
            formData.append('va_name', document.getElementById('va_name').value);
            formData.append('credentials', document.getElementById('credentials').value);
            formData.append('notes', document.getElementById('notes').value);

            try {
                const response = await fetch('/task/{{ task_id }}/submit', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    document.getElementById('result').innerHTML = `
                        <div style="background: #d4edda; color: #155724; padding: 16px; border-radius: 6px;">
                            <strong>✅ Success!</strong><br>
                            ${result.message}<br>
                            ${result.next_steps}
                        </div>
                    `;
                    document.getElementById('submitForm').style.display = 'none';
                } else {
                    throw new Error(result.detail || 'Submission failed');
                }
            } catch (error) {
                document.getElementById('result').innerHTML = `
                    <div style="background: #f8d7da; color: #721c24; padding: 16px; border-radius: 6px;">
                        <strong>❌ Error:</strong> ${error.message}
                    </div>
                `;
            }
        });
    </script>
</body>
</html>
"""

PORTAL_HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>VA Task Portal</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            max-width: 1000px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 30px;
        }
        .task-card {
            background: white;
            padding: 24px;
            border-radius: 8px;
            margin: 16px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .task-card h3 {
            margin-top: 0;
            color: #667eea;
        }
        .btn {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 10px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
        }
        .btn:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 VA Task Portal</h1>
        <p>Secure platform for task completion and credential submission</p>
    </div>

    <h2>Available Tasks ({{ pending_tasks|length }})</h2>

    {% if pending_tasks %}
        {% for task in pending_tasks %}
        <div class="task-card">
            <h3>{{ task.blocker }}</h3>
            <p><strong>Task ID:</strong> {{ task.id }}</p>
            <p><strong>Created:</strong> {{ task.created_at }}</p>
            <a href="/task/{{ task.id }}" class="btn">View Instructions & Submit</a>
        </div>
        {% endfor %}
    {% else %}
        <p>No pending tasks at the moment.</p>
    {% endif %}

</body>
</html>
"""

# Save templates to files
def setup_templates():
    """Create template directory and files"""
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)

    (templates_dir / "task_view.html").write_text(TASK_VIEW_TEMPLATE)
    (templates_dir / "portal_home.html").write_text(PORTAL_HOME_TEMPLATE)

    print("✅ Templates created")


if __name__ == "__main__":
    import uvicorn

    # Setup templates
    setup_templates()

    print("\n🚀 VA INTERFACE PORTAL")
    print("=" * 70)
    print()
    print("Starting server on http://0.0.0.0:8010")
    print()
    print("VAs can:")
    print("  • View task instructions")
    print("  • Submit credentials securely")
    print("  • Track task status")
    print()
    print("=" * 70)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8010)
