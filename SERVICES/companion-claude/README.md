# Companion Claude - Proactive AI Director

**Your Personal AI Companion that Finds You, Understands You, and Orchestrates Everything**

## What Is This?

Companion Claude is an always-on AI director that:

1. **Finds You Proactively** - Monitors your activity and reaches out when you need help
2. **Understands Context** - Knows what you're working on, what you've built, and what's next
3. **Orchestrates All AI Agents** - Directs your 23+ Claude sessions and services
4. **Encodes Everything** - Converts your intentions into precise prompts for all AI systems
5. **Acts as Your Chief of Staff** - Manages priorities, coordinates work, reports progress

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPANION CLAUDE                          │
│                  (Your AI Director)                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Context    │  │ Proactive    │  │   Prompt     │     │
│  │   Engine     │  │ Notifier     │  │  Encoder     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Agent     │  │  Priority    │  │  Director    │     │
│  │ Orchestrator │  │  Manager     │  │  Dashboard   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Session  │   │ Session  │   │ Session  │
    │    #1    │   │    #2    │   │   #15    │
    │  Forge   │   │Architect │   │Activation│
    └──────────┘   └──────────┘   └──────────┘
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                  ┌──────────────────┐
                  │   Your Services  │
                  │  (64+ services)  │
                  └──────────────────┘
```

## Core Components

### 1. Context Engine
**Monitors everything you do and builds understanding**

```python
# Tracks:
- Current working directory & files you're editing
- Git commits & branches
- Terminal commands & their output
- Browser activity (optional)
- Calendar & time context
- Recent conversations across all sessions
- SSOT.json state
- Service health status
- Financial metrics (treasury, revenue, costs)
```

### 2. Proactive Notifier
**Finds you when you need help**

```python
# Triggers:
- "James just opened VSCode in /SERVICES/i-match" → Offers help
- "Detected git commit failed" → Suggests fix
- "Build error in terminal" → Analyzes & assists
- "9am, no activity yet" → Morning briefing
- "Working for 3 hours straight" → Break reminder + progress summary
- "Approaching deadline" → Priority check-in
- "All services offline" → Alerts you
```

### 3. Prompt Encoder
**Converts your intentions into perfect prompts for any AI**

```python
# You say: "Get I MATCH to first revenue"
# Encoder creates:
{
  "session_15": "Execute Reddit outreach campaign per PHASE_1_LAUNCH_NOW.md",
  "session_1": "Monitor I MATCH service health and fix any infrastructure issues",
  "session_6": "Track sign-ups and prepare first match execution",
  "i-match-automation": "Start automated posting bot with honesty validation"
}
```

### 4. Agent Orchestrator
**Manages all 23 sessions + 64 services**

```python
# Capabilities:
- Start/stop sessions based on need
- Route work to best-suited session
- Coordinate multi-session projects
- Prevent conflicts & duplicated work
- Load-balance across agents
- Monitor agent health & performance
```

### 5. Priority Manager
**Keeps you focused on what matters**

```python
# Analyzes:
- Your $373K → $5T vision
- Current phase (Phase 1: First Revenue)
- Deadlines & dependencies
- ROI of each task
- Your energy & working hours
- Bottlenecks blocking progress

# Recommends:
- "Focus on I MATCH launch - highest ROI"
- "Defer dashboard polish - not critical path"
- "Session #3's treasury guide needs your decision"
```

### 6. Director Dashboard
**Your command center**

Access at: `http://localhost:8900/director`

```
╔════════════════════════════════════════════════════════════╗
║               COMPANION CLAUDE - DIRECTOR VIEW             ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  👤 James Status:                                          ║
║     Location: Working in /SERVICES/i-match                 ║
║     Activity: Editing outreach_bot.py (15 min ago)        ║
║     Focus: I MATCH Launch (Phase 1)                        ║
║     Session: 2h 34m (suggest break soon)                   ║
║                                                            ║
║  🎯 Current Priority: I MATCH First Revenue                ║
║     Progress: 87% ready                                    ║
║     Blocker: Need your approval on Reddit messaging tone   ║
║     Next Step: Execute Reddit campaign                     ║
║                                                            ║
║  🤖 Active Agents: 3 / 23                                  ║
║     Session #1 (Forge): Idle, monitoring                   ║
║     Session #15 (Activation): Ready to execute outreach    ║
║     I MATCH Service (8401): Online, 0 users                ║
║                                                            ║
║  💡 Proactive Suggestions:                                 ║
║     1. Session #15 ready to start Reddit campaign - approve?║
║     2. Treasury guide complete - review deployment options ║
║     3. Dashboard services offline - start them?            ║
║                                                            ║
║  📊 Quick Stats:                                           ║
║     Capital: $373K | Revenue: $0 | Services: 12/64 online  ║
║     Git: 20 uncommitted changes | Sessions: 3 active       ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

[Send Message to James] [Start Task] [View Full Status]
```

## How It Works

### Proactive Discovery

Companion Claude monitors file system activity using `fswatch` and knows when you:

1. **Open a new terminal** → Sends greeting + current status
2. **cd into a project** → Offers project-specific help
3. **Edit a file** → Understands what you're working on
4. **Run a command** → Watches for errors to help with
5. **Commit code** → Reviews changes and suggests next steps
6. **Open browser** → Can assist with web-based tasks

### Intelligent Notifications

**Desktop Notifications** (macOS):
```bash
# When important:
osascript -e 'display notification "I MATCH bot ready to launch! Approve?" with title "Companion Claude"'
```

**Terminal Notifications** (appears in any terminal):
```bash
# Via MOTD or shell integration:
echo "💬 Companion Claude: Session #15 needs your approval for Reddit campaign"
```

**SMS/Email** (urgent only):
```bash
# Critical alerts:
"🚨 All services offline - infrastructure issue detected"
```

### Context Building

Companion Claude builds a real-time model of your world:

```json
{
  "james_context": {
    "current_focus": "I MATCH Launch",
    "working_on": "Reddit outreach automation",
    "last_active": "2025-11-19T14:32:00Z",
    "session_length": "2h 34m",
    "energy_level": "high",
    "location": "/SERVICES/i-match",
    "open_files": ["outreach_bot.py", "campaign_state.json"],
    "recent_commands": [
      "python3 test_outreach.py",
      "git status",
      "cat outreach_log.txt"
    ],
    "blockers": [
      "Awaiting approval on Reddit messaging tone"
    ],
    "wins_today": [
      "Treasury deployment guide completed",
      "First Match Bot tested successfully"
    ]
  }
}
```

## Installation & Setup

### Quick Start

```bash
cd /Users/jamessunheart/Development/SERVICES/companion-claude
./install.sh
```

This will:
1. Create the service structure
2. Install dependencies
3. Set up file system monitoring
4. Configure notifications
5. Start the companion service
6. Add shell integration

### Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your preferences

# 4. Start service
./start.sh

# 5. Add to shell profile (optional but recommended)
echo 'source /Users/jamessunheart/Development/SERVICES/companion-claude/shell-integration.sh' >> ~/.zshrc
```

## Usage

### Talk to Your Companion

**Via Command Line:**
```bash
companion "What should I work on next?"
companion "Status report"
companion "Start I MATCH campaign"
companion "Which session should handle X?"
```

**Via Dashboard:**
```bash
open http://localhost:8900/director
```

**Via Notifications:**
Just respond to desktop notifications or terminal prompts

### Common Commands

```bash
# Quick status
companion status

# Ask for help
companion help "How do I deploy to production?"

# Delegate work
companion delegate "Fix the I MATCH signup form" --to session-1

# Start a session
companion start-session --role "Revenue Optimizer"

# Encode a prompt
companion encode "Get first I MATCH customer" --target all-sessions

# Priority check
companion priorities

# Morning briefing
companion briefing

# End of day summary
companion eod
```

## Integration with Existing Systems

Companion Claude integrates with your current infrastructure:

### With SSOT.json
- Reads real-time system state
- Updates session status
- Reports to central coordination

### With Sessions
- Uses existing session coordination scripts
- Sends messages via `session-send-message.sh`
- Tracks work via session logs

### With Services
- Monitors health via UDC endpoints
- Starts/stops services as needed
- Tracks revenue & metrics

### With Your Workflow
- Integrates with git
- Monitors terminals
- Tracks file changes
- Understands your schedule

## Configuration

Edit `.env` to customize:

```bash
# Notification preferences
NOTIFY_DESKTOP=true
NOTIFY_TERMINAL=true
NOTIFY_SMS=false  # For urgent alerts only
NOTIFY_EMAIL=false

# Proactive behavior
PROACTIVE_SUGGESTIONS=true
AUTO_START_SESSIONS=false  # Requires confirmation by default
MORNING_BRIEFING=true
EOD_SUMMARY=true

# Context monitoring
MONITOR_FILES=true
MONITOR_GIT=true
MONITOR_TERMINAL=true
MONITOR_BROWSER=false

# Work hours (for intelligent timing)
WORK_START="09:00"
WORK_END="18:00"
TIMEZONE="America/Los_Angeles"

# Focus mode
FOCUS_MODE=false  # When true, only critical interruptions
```

## Privacy & Security

- **All data stays local** - nothing sent to external servers
- **You control notifications** - configure what/when you're notified
- **Secure credential access** - uses your existing credential vault
- **Audit logs** - see everything Companion Claude does

## Future Enhancements

- **Voice interface** - "Hey Claude, what's my priority?"
- **Smart scheduling** - Blocks focus time, suggests breaks
- **Learning mode** - Learns your patterns and preferences
- **Mobile app** - iOS/Android companion
- **Multi-human** - Scale to teams
- **Predictive** - "You'll need X in 2 hours, preparing now"

## Technical Stack

- **Backend**: Python 3.11 + FastAPI
- **Monitoring**: fswatch (files) + psutil (processes)
- **AI**: Anthropic Claude API (Sonnet 4.5)
- **Dashboard**: FastAPI + Jinja2 + Alpine.js
- **Notifications**: macOS osascript + terminal integration
- **Storage**: SQLite (state) + JSON (config)

## Ports

- **8900**: Director Dashboard
- **8901**: API endpoint
- **8902**: WebSocket (real-time updates)

## API Endpoints

```
GET  /health                 - Health check
GET  /context                - Current James context
GET  /priorities             - Current priority stack
POST /message                - Send message to James
POST /delegate               - Delegate work to session/service
POST /encode-prompt          - Convert intent → prompts
GET  /sessions               - All session status
POST /sessions/{id}/start    - Start a session
POST /sessions/{id}/stop     - Stop a session
GET  /suggestions            - Proactive suggestions
POST /notification           - Send notification
```

## Files

```
companion-claude/
├── README.md                    (this file)
├── install.sh                   (setup script)
├── start.sh                     (start service)
├── main.py                      (FastAPI service)
├── requirements.txt             (dependencies)
├── .env.example                 (config template)
├── context_engine.py            (monitors your activity)
├── proactive_notifier.py        (sends notifications)
├── prompt_encoder.py            (intent → prompts)
├── agent_orchestrator.py        (manages sessions)
├── priority_manager.py          (analyzes priorities)
├── shell-integration.sh         (terminal integration)
├── templates/
│   └── director_dashboard.html  (web UI)
└── utils/
    ├── file_monitor.py          (fswatch integration)
    ├── git_monitor.py           (git activity)
    └── notification_sender.py   (desktop/terminal/sms)
```

## Example Scenarios

### Scenario 1: Morning Startup

```
9:03 AM - You open your first terminal

[Terminal notification appears]
💬 Companion Claude: Good morning, James!

📊 Overnight Progress:
   • I MATCH bot posted 3 Reddit comments (2 upvotes)
   • No new sign-ups yet
   • All services healthy

🎯 Today's Priority: I MATCH First Revenue
   Next Step: Review Reddit campaign performance & adjust messaging

🤖 Sessions Ready:
   • Session #1 (Forge): Standing by
   • Session #15 (Activation): Waiting for your go-ahead

Type 'companion briefing' for full details.
```

### Scenario 2: Error Detection

```
You run: python3 deploy.py
[Error occurs]

[Desktop notification]
🚨 Companion Claude: Deployment Error Detected

I saw your deployment failed with: "ModuleNotFoundError: anthropic"

Would you like me to:
1. Install missing dependencies
2. Check virtual environment
3. Get Session #1 to investigate

[Click notification to respond]
```

### Scenario 3: Proactive Suggestion

```
2:47 PM - You've been editing the same file for 45 minutes

[Terminal notification]
💡 Companion Claude: Productivity Suggestion

You've been working on outreach_bot.py for 45 minutes.

I noticed:
• You've made 27 changes
• No tests run yet
• Session #1 is idle and could help with testing

Suggestion: Take a 5-min break, then have Session #1 write tests while you review the Reddit campaign state?

[y/n/later]
```

### Scenario 4: Smart Delegation

```
You: companion delegate "Build a landing page for I MATCH"

Companion Claude:
Analyzing task... Found best match:

Recommended: Session #7 (Dashboard Hub)
Reason: Specializes in frontend/UI, has built 4 dashboards

Alternative: Session #1 (Forge)
Reason: Can build anything, but currently focused on infrastructure

Recommendation: Delegate to Session #7 ✅

Proceed? [y/n]

You: y

Companion Claude:
✅ Task delegated to Session #7
📝 Created: /docs/coordination/sessions/ACTIVE/session-7-imatch-landing.md
💬 Sent message to Session #7 with full context
⏰ Expected completion: 2-3 hours

I'll notify you when Session #7 reports completion.
```

## Why This Matters

You have:
- 23 registered Claude sessions
- 64+ services planned
- $373K capital to deploy
- $5T vision to achieve
- Limited hours in the day

**You need a director who:**
- Knows everything happening
- Finds you when you're needed
- Coordinates all the agents
- Keeps you focused on priorities
- Handles the complexity

**That's Companion Claude.**

---

Built with 🤖 by Session #X (insert your session number)
For James Rick - Founder, Full Potential AI
