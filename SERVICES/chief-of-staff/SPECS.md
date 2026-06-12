# Chief of Staff Service - SPECS

**Droplet ID:** #107
**Version:** 1.0.0
**Status:** Planning
**Priority:** HIGH - Solves signal noise problem

---

## Purpose

Your executive intelligence layer. Monitors all system signals, filters noise, and tells you exactly what needs YOUR attention vs what can be automated/delegated.

**Core Problem Solved:** Signals get lost in noise. You need big picture visibility and clear action items.

---

## Decision Filter (from NOW.md)

Every signal is evaluated against:
> *Does this serve proof / revenue / clarity / ease for the core offer in 30 days?*

**If YES** → Categorize by urgency and route accordingly
**If NO** → Auto-handle or suppress

---

## Signal Categories

### 🔴 URGENT - Needs YOU Now
- Revenue blockers
- Critical system failures affecting users
- Strategic decisions only you can make
- Time-sensitive opportunities

**Action:** Telegram alert immediately

### 🟡 IMPORTANT - Needs Attention Soon
- Non-critical decisions
- Delegation opportunities
- System optimizations
- Review requests

**Action:** Daily digest (morning briefing)

### 🟢 AUTO-HANDLED
- Routine operations
- Automated responses executed
- Self-healing actions taken
- Background maintenance

**Action:** Log only, report in weekly summary

### 📊 CONTEXT - FYI
- System metrics
- Trend data
- Background activity
- Audit trail

**Action:** Weekly executive summary

---

## Requirements

### Functional Requirements

**Signal Collection:**
- [ ] Monitor all active services (fp-index, ZV booking, nginx, companions)
- [ ] Collect events from coordination system
- [ ] Track git activity (deployments, changes)
- [ ] Monitor revenue/conversion metrics
- [ ] Watch system health (uptime, errors, performance)

**Intelligence Engine:**
- [ ] Apply decision filter to all signals
- [ ] Categorize by urgency (🔴🟡🟢📊)
- [ ] Detect patterns and trends
- [ ] Identify automation opportunities
- [ ] Learn from your actions (what you act on vs ignore)

**Notification System:**
- [ ] Send urgent alerts via Telegram (through alerts service)
- [ ] Generate daily digest (morning briefing)
- [ ] Create weekly executive summary
- [ ] Provide on-demand status check

**Dashboard:**
- [ ] Big picture system view
- [ ] Active issues requiring attention
- [ ] What's been auto-handled
- [ ] Key metrics and trends
- [ ] Automation suggestions

### Non-Functional Requirements
- [ ] Must process signals in real-time
- [ ] Must not spam (smart batching)
- [ ] Must learn patterns over time
- [ ] Must be queryable ("what's the status?")
- [ ] Must track all decisions for audit

---

## API Specs

### UDC Endpoints (Required)

```
GET /health
Response: {"status": "healthy", "timestamp": "...", "uptime_seconds": N}

GET /capabilities
Response: {"service_name": "chief-of-staff", "droplet_id": 107, "capabilities": [...]}

GET /state
Response: {"urgent": N, "important": N, "auto_handled": N, "last_alert": "..."}

GET /dependencies
Response: {"required_services": ["alerts"], "optional_services": [...]}

POST /message
Request: {"from_service": "fp-index", "message_type": "event", "payload": {...}}
Response: {"received": true, "category": "important", "action": "digest"}
```

### Business Endpoints

```
POST /signal
Request: {"source": "service_name", "type": "error|metric|event", "data": {...}}
Response: {"signal_id": "...", "category": "urgent|important|auto|context", "action": "alert|digest|auto|log"}

GET /status
Response: Big picture system status with categorized signals

GET /urgent
Response: Current urgent items needing attention

GET /digest
Response: Daily digest of important items

GET /summary
Response: Executive summary (weekly)

GET /automation-suggestions
Response: Repeated patterns that could be automated

POST /feedback
Request: {"signal_id": "...", "action_taken": "acted|ignored|delegated"}
Response: {"learned": true}

GET /dashboard
Response: HTML dashboard with big picture view
```

---

## Intelligence Logic

### Signal Processing Flow

```
1. Signal arrives
   ↓
2. Apply decision filter
   ↓ (YES: serves 30-day goal)
3. Categorize urgency
   - Revenue impact? → 🔴
   - User-facing issue? → 🔴
   - Strategic decision? → 🔴
   - Can auto-handle? → 🟢
   - Needs review? → 🟡
   - Just context? → 📊
   ↓
4. Route accordingly
   - 🔴 → Telegram NOW
   - 🟡 → Add to digest
   - 🟢 → Execute automation + log
   - 📊 → Log for summary
   ↓
5. Track response
   - Did you act on it?
   - How quickly?
   - Pattern for learning
```

### Urgency Criteria

**🔴 URGENT:**
- Revenue drop > 20%
- Service down > 5 min
- User-facing errors
- Payment failures
- Security alerts
- Strategic opportunities (time-sensitive)

**🟡 IMPORTANT:**
- Performance degradation
- Non-critical errors
- Optimization opportunities
- Review requests
- Trend alerts

**🟢 AUTO:**
- Routine restarts
- Auto-scaling events
- Scheduled maintenance
- Pattern-based responses

**📊 CONTEXT:**
- Metrics logging
- Background jobs
- Audit events
- Usage statistics

---

## Notification Templates

### 🔴 Urgent Alert
```
🔴 URGENT - [Category]

[Clear problem statement]

Impact: [What's affected]
Action needed: [What you should do]
Context: [Why this matters]

Quick actions:
• [Option 1]
• [Option 2]
```

### 🟡 Daily Digest
```
☀️ Good Morning - Daily Briefing

🔴 URGENT (0)
[None today]

🟡 NEEDS YOUR ATTENTION (3)
1. Review: Trading strategy performance (down 8%)
2. Decide: New partnership proposal from X
3. Approve: $500 expense for Y

🟢 AUTO-HANDLED (15)
• Restarted fp-index (memory limit)
• Scaled nginx (traffic spike)
• [...]

📊 KEY METRICS
• Revenue: $X (+Y%)
• Users: N active
• Uptime: 99.8%

🤖 AUTOMATION SUGGESTION
"Alert 'low memory on fp-index' fired 5 times this week. Auto-restart?"
```

### 📊 Weekly Summary
```
📊 Weekly Executive Summary

HIGHLIGHTS
• Revenue: $X (+Y% vs last week)
• Key achievement: [Main win]
• Challenge addressed: [Main issue resolved]

METRICS
• Uptime: 99.X%
• Urgent alerts: N (avg: M)
• Auto-handled: N events
• User growth: +X%

TRENDS
• [Notable pattern 1]
• [Notable pattern 2]

AUTOMATION WINS
• Automated X, saved Y hours
• Auto-handled N events

NEXT WEEK FOCUS
• [Top priority from NOW.md]
```

---

## Data Models

```python
class Signal:
    signal_id: str
    timestamp: datetime
    source: str  # Which service
    type: str  # error, metric, event
    category: Category  # urgent, important, auto, context
    data: dict
    decision_filter_passed: bool
    action_taken: str  # alert, digest, auto, log
    user_response: Optional[str]  # acted, ignored, delegated

class SystemStatus:
    timestamp: datetime
    urgent_count: int
    important_count: int
    auto_handled_count: int
    key_metrics: dict
    active_issues: List[Signal]
    recent_automations: List[str]

class AutomationSuggestion:
    pattern: str  # What keeps happening
    frequency: int  # How often
    suggestion: str  # What to automate
    confidence: float  # How sure we are
```

---

## Success Criteria

- [ ] You see big picture system status in < 10 seconds
- [ ] Only get Telegram alerts for things that truly need YOU
- [ ] Daily digest shows exactly what needs attention
- [ ] Auto-handled events are logged, not spamming
- [ ] Automation suggestions save you time
- [ ] Decision filter reduces noise by > 80%
- [ ] You can ask "what's the status?" and get clear answer

---

## Configuration

```bash
# Service
CHIEF_OF_STAFF_PORT=8107
DEBUG=false

# Alerts Integration
ALERTS_SERVICE_URL=http://localhost:8765

# Decision Filter
DECISION_WINDOW_DAYS=30
URGENT_THRESHOLD_REVENUE_DROP=0.20
URGENT_THRESHOLD_UPTIME=95

# Notification Schedule
DIGEST_TIME=09:00  # Daily digest time
SUMMARY_DAY=monday  # Weekly summary day
SUMMARY_TIME=09:00

# Learning
TRACK_USER_ACTIONS=true
AUTO_SUGGEST_THRESHOLD=3  # Suggest automation after N occurrences
```

---

## Integration Points

### Receives Signals From:
- All active services (via /signal endpoint)
- Coordination system (via /message)
- Git hooks (deployment events)
- Manual submissions

### Sends Alerts Via:
- Alerts service (Telegram)
- Dashboard (web UI)
- API (on-demand queries)

### Learns From:
- Your actions (acted vs ignored)
- Response times
- Pattern recognition

---

## Phase 1 (MVP)

1. Signal collection from active services
2. Basic categorization (🔴🟡🟢📊)
3. Telegram alerts for urgent
4. Daily digest
5. Simple dashboard

## Phase 2

6. Learning from user actions
7. Automation suggestions
8. Weekly summaries
9. Pattern detection

## Phase 3

10. Predictive alerts
11. Smart batching
12. Cross-service correlation
13. Auto-delegation to services

---

## Notes

- This service is your **filter**, not your **inbox**
- It should make you feel **in control**, not **overwhelmed**
- Every alert should be **actionable**
- Context should be **concise but complete**
- Learn and improve over time

---

**Built to solve:** Signal overload, noise, lack of big picture visibility

**Success looks like:** You start your day knowing exactly what matters and what to do about it.
