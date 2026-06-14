# Chief of Staff Service

**Droplet ID:** #107
**Version:** 1.0.0
**Status:** Ready to Deploy
**Priority:** HIGH - Solves signal noise problem

---

## Overview

Your **executive intelligence layer**. Cuts through system noise and shows you exactly what needs YOUR attention vs what can be automated/delegated.

### The Problem It Solves

Signals get lost in noise. You need:
- Big picture visibility
- Clear action items
- Less overwhelm, more control

### How It Works

```
All Signals → Decision Filter → Categorize → Route → You
                    ↓              ↓          ↓
              30-day goal    🔴 Urgent    Telegram
              relevance      🟡 Important  Digest
                            🟢 Auto       Log
                            📊 Context    Summary
```

---

## Decision Filter

Every signal is evaluated:
> **Does this serve proof / revenue / clarity / ease for the core offer in 30 days?**

**If YES** → Categorize by urgency
**If NO** → Log as context only

---

## Signal Categories

### 🔴 URGENT - Telegram Alert NOW
- Revenue blockers
- Critical system failures
- Strategic decisions only YOU can make
- Time-sensitive opportunities

### 🟡 IMPORTANT - Daily Digest (9 AM)
- Non-critical decisions
- Delegation opportunities
- System optimizations
- Review requests

### 🟢 AUTO-HANDLED - Logged Only
- Routine operations completed
- Self-healing actions taken
- Background maintenance
- Auto-scaled events

### 📊 CONTEXT - Weekly Summary
- System metrics
- Trend data
- Background activity
- Audit trail

---

## Quick Start

### 1. Prerequisites

Make sure **alerts service** is running:
```bash
cd ../alerts
python -m app.main
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env - should work with defaults
```

### 3. Run Locally

```bash
pip install -r requirements.txt
python -m app.main
```

Visit: `http://localhost:8107/docs`

---

## Usage

### Send a Signal

```bash
curl -X POST http://localhost:8107/signal \
  -H "Content-Type: application/json" \
  -d '{
    "source": "fp-index",
    "type": "error",
    "title": "High error rate detected",
    "description": "Error rate jumped to 8% in last 5 minutes",
    "data": {
      "error_rate": 0.08,
      "user_facing": true
    }
  }'
```

### Check Status

```bash
# Big picture status
curl http://localhost:8107/status

# Current urgent items
curl http://localhost:8107/urgent

# Daily digest
curl http://localhost:8107/digest
```

### Send Daily Digest

```bash
curl -X POST http://localhost:8107/digest/send
```

You'll get a Telegram message like:
```
☀️ Daily Briefing
Tuesday, April 29

🔴 URGENT (0)
All clear

🟡 NEEDS ATTENTION (2)
1. Review: FP-Index usage up 40%
2. Decide: Partnership inquiry

🟢 AUTO-HANDLED (8)
• Restarted nginx (memory)
• Scaled fp-index
...

🤖 AUTOMATION IDEAS
• Nginx restarts 4x this week - auto-scale?
```

### View Dashboard

Open browser: `http://localhost:8107/dashboard`

---

## API Endpoints

### UDC Endpoints
```
GET  /health             - Health check
GET  /capabilities       - Service capabilities
GET  /state              - Current state
GET  /dependencies       - Dependencies
```

### Signal Processing
```
POST /signal             - Process a signal
POST /feedback           - Provide feedback on signal
```

### Status & Visibility
```
GET  /status             - Big picture status
GET  /urgent             - Current urgent items
GET  /digest             - Daily digest
POST /digest/send        - Send digest via Telegram
GET  /summary            - Weekly summary
GET  /automation-suggestions  - Automation opportunities
```

### Dashboard
```
GET  /dashboard          - HTML dashboard
```

---

## Integration Example

From any service, send signals:

```python
import httpx

# Send urgent signal
async def alert_chief_of_staff(issue):
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8107/signal",
            json={
                "source": "my-service",
                "type": "error",
                "title": "Critical issue detected",
                "description": issue.description,
                "data": {
                    "severity": "high",
                    "user_facing": True,
                    "impact": "Users cannot complete checkout"
                }
            }
        )
```

The Chief of Staff will:
1. Apply decision filter
2. Categorize urgency
3. Send Telegram alert if urgent
4. Track in digest if important
5. Log if auto-handled/context

---

## Notification Examples

### Urgent Alert
```
🔴 URGENT - Booking conversion drop

Conversions down 25% (last 2 hours)

Impact: Lost ~$300 potential bookings
Action needed: Check booking flow / pricing

Quick actions:
• Check site status
• Review recent changes
• Pause ads if broken

Source: fp-index
```

### Daily Digest
```
☀️ Daily Briefing
Wednesday, April 30

🔴 URGENT (1)
• Payment processor intermittent failures

🟡 NEEDS ATTENTION (3)
1. Review: Server costs up 15%
2. Decide: New feature request from user
3. Approve: $200 ad spend increase

🟢 AUTO-HANDLED (12)
• Restarted fp-index
• Scaled nginx
• Fixed broken link

📊 METRICS
• Signals Processed: 45
• Urgent Alerts: 1
• Auto Handled: 12

🤖 AUTOMATION IDEAS
• "low memory restart" happened 5 times - automate?
```

---

## Configuration

Key settings in `.env`:

| Setting | Purpose | Default |
|---------|---------|---------|
| `ALERTS_SERVICE_URL` | Alerts service endpoint | http://localhost:8765 |
| `DECISION_FILTER_KEYWORDS` | Keywords for relevance | revenue,booking,user... |
| `URGENT_THRESHOLD_REVENUE_DROP` | Revenue drop % for urgent | 0.20 (20%) |
| `DIGEST_TIME` | Daily digest time | 09:00 |
| `AUTO_SUGGEST_THRESHOLD` | Pattern freq for automation | 3 occurrences |

---

## Learning & Improvement

The system learns from your actions:

```bash
# Tell it how you responded
curl -X POST http://localhost:8107/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "signal_id": "abc123",
    "action_taken": "acted"
  }'
```

Over time, it learns:
- What you act on vs ignore
- What's truly urgent vs noise
- What can be automated

---

## Automation Suggestions

The system detects patterns:

```bash
curl http://localhost:8107/automation-suggestions
```

Example response:
```json
{
  "suggestions": [
    {
      "pattern": "low memory restart nginx",
      "frequency": 5,
      "suggestion": "Occurred 5 times - consider auto-scaling memory",
      "confidence": 0.8
    }
  ]
}
```

---

## Architecture

```
Services → Chief of Staff → Intelligence Engine → Action
                ↓               ↓                   ↓
           Signals      Categorize            🔴 Alert
                        Filter                🟡 Digest
                        Learn                 🟢 Auto
                                             📊 Log
```

**Components:**
- `categorizer.py` - Decision filter & urgency logic
- `storage.py` - Signal history & retrieval
- `patterns.py` - Pattern detection for automation
- `digest.py` - Generate briefings & summaries
- `alerts_client.py` - Send via alerts service

---

## Deployment

### Docker

```bash
docker build -t chief-of-staff:latest .
docker run -p 8107:8107 --env-file .env chief-of-staff:latest
```

### With Alerts Service

```yaml
version: '3.8'
services:
  alerts:
    build: ../alerts
    ports:
      - "8765:8765"
    env_file:
      - ../alerts/.env

  chief-of-staff:
    build: .
    ports:
      - "8107:8107"
    env_file:
      - .env
    depends_on:
      - alerts
    environment:
      - ALERTS_SERVICE_URL=http://alerts:8765
```

---

## Testing

```bash
# Run tests
pytest

# Test signal processing
python -c "
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        # Send test signal
        response = await client.post(
            'http://localhost:8107/signal',
            json={
                'source': 'test',
                'type': 'event',
                'title': 'Test signal',
                'description': 'Testing the system',
                'data': {'test': True}
            }
        )
        print(response.json())

asyncio.run(test())
"
```

---

## Success Metrics

You'll know it's working when:
- ✅ You see big picture in < 10 seconds (dashboard)
- ✅ Only get Telegram for things that truly need YOU
- ✅ Daily digest shows exactly what matters
- ✅ Auto-handled events logged, not spamming
- ✅ Automation suggestions save you time
- ✅ Noise reduced by > 80%

---

## Roadmap

**Phase 1 (Current):**
- Signal processing ✅
- Decision filter ✅
- Categorization ✅
- Urgent alerts ✅
- Daily digest ✅
- Dashboard ✅

**Phase 2:**
- Learning from feedback
- Predictive alerts
- Smart batching
- Cross-service correlation

**Phase 3:**
- Auto-delegation to services
- Conversational interface
- Mobile app integration

---

## Support

For issues or questions, check:
- API docs: `/docs`
- Dashboard: `/dashboard`
- Logs: Check service logs
- Alerts service: Make sure it's running

---

**Built to solve:** Signal overload, noise, lack of big picture

**Success looks like:** You start each day knowing exactly what matters and what to do about it.
