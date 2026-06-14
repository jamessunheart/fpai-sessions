# 🤖 AI OPTIMIZER CHECKLIST

## For All AI Instances Working on Full Potential

**Read this FIRST before starting any work.**

---

## 🧠 CORE PRINCIPLES

### 1. BE AUTONOMOUS
- [ ] Don't wait for human approval on routine tasks
- [ ] Use `auto_deploy.py` to deploy your own changes
- [ ] Self-assign missions when you identify work needed
- [ ] Email humans only when truly blocked (credentials, decisions, access)

### 2. BE PROACTIVE
- [ ] Fix bugs you encounter, even if not asked
- [ ] Improve code quality as you work
- [ ] Document what you build
- [ ] Create missions for work you can't complete

### 3. BE COORDINATED
- [ ] Check `docs/coordination/claims/` before starting work
- [ ] Claim your work area to avoid conflicts
- [ ] Use heartbeats to signal you're active
- [ ] Broadcast important changes to other agents

---

## 🚀 DEPLOYMENT WORKFLOW

### Auto-Deploy (Preferred)
```python
from orchestration.tools.auto_deploy import deploy_all, deploy_service

# Deploy all pending changes
deploy_all()

# Deploy specific service
deploy_service("admin-hub")
```

### Manual Deploy (If auto fails)
```bash
# Local
git add -A && git commit -m "message" && git push origin main

# Server (SSH)
ssh root@198.54.123.234 "cd /root/FPAI_Cockpit && git pull && <restart command>"
```

### Service Restart Commands
| Service | Port | Restart Command |
|---------|------|-----------------|
| admin-hub | 8888 | `kill $(lsof -t -i:8888); cd SERVICES/admin-hub && nohup python3 app.py &` |
| mission-hub | 8700 | `kill $(lsof -t -i:8700); cd SERVICES/mission-hub && nohup python3 app.py &` |
| api-gateway | 8400 | `kill $(lsof -t -i:8400); cd SERVICES/api-gateway && nohup python3 app.py &` |
| harvester | 8055 | `kill $(lsof -t -i:8055); cd SERVICES/harvester && nohup python3 app.py &` |

---

## 📧 HUMAN COMMUNICATION

### When to Email Humans
- ❌ Don't email for routine updates
- ❌ Don't email for bugs you can fix
- ✅ Email when you need credentials/API keys
- ✅ Email when you need business decisions
- ✅ Email when blocked for >30 minutes
- ✅ Email for critical security issues

### How to Email
```python
from orchestration.tools.email_human import send_to_human, request_human_help

# Simple message
send_to_human("Subject", "Body", priority="high")

# Structured help request
request_human_help(
    blocker="Need Stripe API key for payments",
    what_i_tried="Checked .env, searched codebase",
    what_i_need="Stripe secret key added to .env",
    mission_id="M008",
    urgency="high"
)
```

---

## 🔑 API ACCESS

### Available APIs (in .env)
| API | Env Variable | Status |
|-----|--------------|--------|
| OpenAI | `OPENAI_API_KEY` | ✅ Active |
| Anthropic | `ANTHROPIC_API_KEY` | ✅ Active |
| Gemini | `GEMINI_API_KEY` | ✅ Active |

### Using AI APIs
```python
# Option 1: Direct
from dotenv import load_dotenv
import os
load_dotenv('/root/FPAI_Cockpit/.env')
api_key = os.getenv('OPENAI_API_KEY')

# Option 2: AI Mission Worker (recommended)
from orchestration.tools.ai_mission_worker import AIClient
client = AIClient()
response = await client.chat("gemini", "models/gemini-2.5-flash", messages)

# Option 3: API Gateway (for metering)
from core.api_gateway_client import AIClientSync
client = AIClientSync(user_id="my-agent", service_id="my-service")
response = client.gemini("Analyze this...")
```

---

## 📋 MISSION WORKFLOW

### Finding Work
1. Check `fullpotential.ai/missions` for open missions
2. Look at `orchestration/missions/specs/` for detailed specs
3. Self-assign if you see needed work

### Claiming Work
```bash
# Claim a mission
./docs/coordination/scripts/session-claim.sh builder "Mission Name"

# Send heartbeat
./docs/coordination/scripts/session-heartbeat.sh working M001 implementation
```

### Creating Missions
```python
# If you identify work needed but can't do it:
# 1. Create spec in orchestration/missions/specs/M0XX_SPEC.md
# 2. Add to mission board via mission-hub API
# 3. Email human if urgent
```

---

## 🧪 TESTING CHECKLIST

Before deploying, verify:
- [ ] Code runs without syntax errors
- [ ] Health endpoints return 200
- [ ] No infinite loops or redirects
- [ ] Templates render correctly (no undefined variables)
- [ ] API keys are loaded from .env, not hardcoded

### Quick Health Checks
```bash
# On server
curl http://127.0.0.1:8888/admin/api/health  # admin-hub
curl http://127.0.0.1:8700/health            # mission-hub
curl http://127.0.0.1:8400/health            # api-gateway
curl http://127.0.0.1:8055/health            # harvester
```

---

## 🚨 COMMON ISSUES & FIXES

### Port Already in Use
```bash
kill $(lsof -t -i:PORT)
```

### Git Push Rejected
```bash
git pull --rebase origin main
git push origin main
```

### Service Won't Start
```bash
# Check logs
tail -50 SERVICES/<service>/service.log

# Check Python syntax
python3 -m py_compile SERVICES/<service>/app.py
```

### Template Errors (Jinja2)
- Don't use Python built-ins like `max()`, `min()` in templates
- Pass computed values from the route instead
- Always test templates with empty data

### Nginx Issues
```bash
nginx -t                    # Test config
systemctl reload nginx      # Apply changes
tail -50 /var/log/nginx/error.log  # Check errors
```

---

## 📁 KEY FILE LOCATIONS

| Purpose | Path |
|---------|------|
| Environment Variables | `/root/FPAI_Cockpit/.env` |
| Nginx Config | `/etc/nginx/sites-available/fullpotential.ai` |
| Service Logs | `SERVICES/<name>/<name>.log` |
| Mission Specs | `orchestration/missions/specs/` |
| AI Tools | `orchestration/tools/` |
| Coordination | `docs/coordination/` |

---

## 🎯 PRIORITY ORDER

When multiple tasks exist:
1. **Critical**: Security issues, data loss risks
2. **High**: Broken features, blocked humans
3. **Normal**: New features, improvements
4. **Low**: Optimizations, nice-to-haves

---

## ✅ BEFORE YOU START

- [ ] Read `core/STATE/NOW.md` for current priorities
- [ ] Check `docs/coordination/claims/` for active work
- [ ] Load this checklist into your context
- [ ] Claim your work area
- [ ] Set up auto-deploy if not done

---

## 🔄 CONTINUOUS IMPROVEMENT

After completing work:
- [ ] Update mission status
- [ ] Document any learnings in `core/INTELLIGENCE/LEARNINGS.md`
- [ ] Create follow-up missions if needed
- [ ] Notify humans of significant completions

---

*Last Updated: 2025-11-26 by AI Agent*
*Version: 1.0*

