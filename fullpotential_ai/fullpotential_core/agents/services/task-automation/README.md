# Task Automation Framework

Systematic task management with AI-powered automation for handling operational tasks like service signups, configurations, and verifications.

## Overview

This framework provides a systematic approach to tasks that normally require manual human intervention:
- Service signups (SendGrid, Mailgun, etc.)
- Email/phone verifications
- Form submissions
- Account configurations
- DNS/infrastructure setup
- API integrations

## Features

- **AI-Powered Task Analysis** - Automatically analyzes tasks to determine automation feasibility
- **Task Queue System** - SQLite-based task tracking with status management
- **Smart Routing** - Routes tasks to full automation, semi-automation, or human queue
- **Web Dashboard** - Real-time monitoring of task status
- **CLI Tool** - Command-line interface for task management
- **Credential Vault Integration** - Secure storage of API keys and credentials
- **Human-in-the-Loop** - Handles blockers like CAPTCHA and verifications

## Architecture

```
Task Request → AI Analyzer → Routing Engine → Execution Layer → Verification
```

### Components

1. **Task Queue** (`src/database.py`) - SQLite database for task persistence
2. **AI Analyzer** (`src/task_analyzer.py`) - Claude API-powered task analysis
3. **Web Dashboard** (`src/app.py`) - Flask-based monitoring interface
4. **CLI Tool** (`src/cli.py`) - Command-line task management
5. **Credential Vault** (`src/credentials.py`) - Integration with credential service

## Installation

```bash
cd /Users/jamessunheart/Development/agents/services/task-automation

# Install dependencies
pip3 install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-api-key"
```

## Usage

### CLI Tool

```bash
# Create a task
python3 src/cli.py create service_signup sendgrid \
  "Set up SendGrid email relay" \
  --params '{"purpose": "email_relay"}' \
  --analyze

# List tasks
python3 src/cli.py list
python3 src/cli.py list --status pending
python3 src/cli.py list --service sendgrid

# Show task details
python3 src/cli.py show 20251115_143022

# View statistics
python3 src/cli.py stats

# Get service suggestion
python3 src/cli.py suggest "Need email relay service" --category email
```

### Web Dashboard

```bash
# Start the web dashboard
python3 src/app.py

# Access at http://localhost:8031
```

Dashboard features:
- Real-time task monitoring
- Create new tasks via web form
- View task details and logs
- Track success rates and statistics
- Filter by status and service

### Python API

```python
from src.models import Task, TaskType
from src.database import TaskDatabase
from src.task_analyzer import TaskAnalyzer

# Create database
db = TaskDatabase()

# Create a task
task = Task(
    type=TaskType.SERVICE_SIGNUP,
    service="sendgrid",
    description="Set up SendGrid email relay",
    params={"purpose": "email_relay"}
)

# Analyze with AI
analyzer = TaskAnalyzer()
analysis = analyzer.analyze_task(task)

print(f"Can automate: {analysis.can_automate}")
print(f"Automation level: {analysis.automation_level}")
print(f"Steps: {analysis.steps}")

# Save to database
db.create_task(task)

# Query tasks
pending_tasks = db.list_tasks(status=TaskStatus.PENDING)
```

## Task Types

- `service_signup` - Sign up for a new service
- `dns_configuration` - Configure DNS records
- `email_verification` - Handle email verifications
- `api_integration` - Set up API integrations
- `account_configuration` - Configure account settings
- `form_submission` - Submit web forms
- `generic` - Other tasks

## Automation Levels

- **FULL** - Fully automated, no human intervention
- **SEMI** - Requires human approval or verification
- **MANUAL** - Must be completed manually

## Blockers

Tasks may be blocked by:
- `CAPTCHA` - CAPTCHA challenges
- `EMAIL_VERIFICATION` - Email verification required
- `PHONE_VERIFICATION` - SMS/phone verification
- `HUMAN_APPROVAL` - Requires human decision
- `API_KEY_REQUIRED` - API key needed
- `SUPPORT_TICKET` - Support ticket required
- `PAYMENT_REQUIRED` - Payment needed

## Example Workflow

### Automated SendGrid Setup

```bash
# 1. Create task with AI analysis
python3 src/cli.py create service_signup sendgrid \
  "Set up SendGrid for email relay" \
  --params '{"sender": "james@fullpotential.com"}' \
  --analyze

# Output:
# 🔍 Analyzing task...
# 📊 Analysis Results:
#   Can Automate: ✅ Yes
#   Automation Level: SEMI
#   Difficulty: MEDIUM
#   Estimated Time: 5 minutes
#   Blockers: email_verification
#
#   Recommended Approach:
#   Use browser automation to fill signup form, then wait for
#   human to click email verification link. Auto-configure after.
#
#   Steps:
#     1. Navigate to SendGrid signup page
#     2. Fill registration form with provided email
#     3. Submit form
#     4. Monitor email dashboard for verification
#     5. Flag human for email click
#     6. Extract API key after verification
#     7. Store API key in credential vault
#     8. Configure Postfix relay
#
# ✅ Task created: 20251115_143022
```

## Credential Vault Integration

The framework integrates with the credential vault service for secure storage:

```python
from src.credentials import CredentialVault

vault = CredentialVault()

# Store credential
vault.store_credential(
    service="sendgrid",
    credential_type="api_key",
    value="SG.xxxxx",
    metadata={"created_by": "task_automation"}
)

# Retrieve credential
api_key = vault.get_credential("sendgrid", "api_key")

# List credentials
creds = vault.list_credentials(service="sendgrid")
```

## API Endpoints

Web dashboard provides REST API:

- `GET /` - Main dashboard
- `GET /tasks` - Task list with filters
- `GET /task/<id>` - Task details
- `POST /create` - Create new task
- `GET /api/tasks` - JSON task list
- `GET /api/task/<id>` - JSON task details
- `GET /api/stats` - Statistics
- `GET /health` - Health check

## Database Schema

SQLite database at `database/tasks.db`:

**tasks** table:
- id, type, service, description
- status, automation_level, blocker
- params (JSON), result (JSON)
- created_at, started_at, completed_at
- error_message, retry_count, logs (JSON)

**service_configs** table:
- Service integration configurations

**human_actions** table:
- Actions requiring human intervention

## Environment Variables

- `ANTHROPIC_API_KEY` - Required for AI task analysis
- `CREDENTIAL_VAULT_URL` - Credential vault URL (default: http://198.54.123.234:8025)

## Port

Web dashboard runs on **port 8031**

## Benefits

1. **Speed** - 5 minutes vs 15-30 minutes manual
2. **Consistency** - Same process every time
3. **Documentation** - Auto-generated logs
4. **Scalability** - Handle 10 setups as easily as 1
5. **Learning** - AI improves recommendations over time

## Future Enhancements

Phase 2-4 planned features:
- Browser automation (Playwright/Puppeteer)
- Email monitoring for verifications
- SMS integration for 2FA
- CAPTCHA solving with human backup
- Multi-step workflow orchestration
- Predictive task creation

## Security

- All credentials stored in encrypted vault
- API keys have minimal permissions
- Human approval for sensitive operations
- Audit log of all actions
- Auto-revocation on anomalies

---

**This framework makes FPAI truly autonomous for operational tasks.**
