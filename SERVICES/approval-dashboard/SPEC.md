# APPROVAL-DASHBOARD - Technical Specification

**Service Name:** approval-dashboard
**Version:** 1.0.0



---

## Purpose

Beautiful, real-time web dashboard for reviewing and approving system intents. The human oversight interface that makes autonomous governance practical - spend 5 minutes reviewing 50 decisions instead of 4 hours building services manually.

Your command center for the self-building system.

---

## Capabilities

This service provides the following capabilities as part of the FPAI droplet mesh:

### Primary Functions

See 'Core Capabilities' section below for detailed descriptions.

## Core Capabilities

- **Real-Time Dashboard:** Live view of intent queue and pipeline status
- **One-Click Approval:** Approve/reject intents with single click
- **Batch Operations:** Approve multiple aligned intents at once
- **Detailed Reviews:** See alignment scores, risk factors, SPEC previews
- **Filtering & Search:** Find specific intents quickly
- **Governance Controls:** Switch modes, edit policies
- **Mobile-Friendly:** Review approvals on phone
- **WebSocket Updates:** No refresh needed, updates push automatically
- **Analytics:** Daily/weekly stats on system building activity

---

## UDC Endpoints (5/5)

### 1. GET /health
**Returns:** Service health status
```json
{
  "status": "active",
  "service": "approval-dashboard",
  "version": "1.0.0",
  "timestamp": "2025-11-16T00:00:00Z",
  "websocket_connections": 3,
  "pending_approvals": 5
}
```

### 2. GET /capabilities
**Returns:** Service capabilities and metadata
```json
{
  "version": "1.0.0",
  "features": [
    "real_time_dashboard",
    "one_click_approval",
    "batch_operations",
    "governance_controls",
    "mobile_friendly",
    "websocket_updates",
    "analytics"
  ],
  "dependencies": ["registry", "intent-queue", "governance"],
  "udc_version": "1.0",
  "metadata": {
    "ui_framework": "React",
    "websocket_support": true,
    "mobile_responsive": true
  }
}
```

### 3. GET /state
**Returns:** Current service state and metrics
```json
{
  "uptime_seconds": 86400,
  "requests_total": 1000,
  "errors_last_hour": 0,
  "last_restart": "2025-11-16T00:00:00Z",
  "active_users": 1,
  "websocket_connections": 3,
  "approvals_today": 45,
  "rejections_today": 2
}
```

### 4. GET /dependencies
**Returns:** Service dependency status
```json
{
  "required": [
    {"name": "registry", "status": "available", "url": "http://localhost:8000"},
    {"name": "intent-queue", "status": "available", "url": "http://localhost:8212"},
    {"name": "governance", "status": "available", "url": "http://localhost:8213"}
  ],
  "optional": [
    {"name": "sovereign-factory", "status": "available", "url": "http://localhost:8210"}
  ],
  "missing": []
}
```

### 5. POST /message
**Returns:** Message acknowledgment
```json
{
  "trace_id": "uuid",
  "source": "intent-queue",
  "target": "approval-dashboard",
  "message_type": "event",
  "payload": {
    "event": "new_approval_needed",
    "intent_id": "uuid"
  },
  "timestamp": "2025-11-16T00:00:00Z"
}
```

---

## Service Endpoints

### GET /
Serve dashboard web app (HTML/JS/CSS)
```html
<!DOCTYPE html>
<html>
<head>
  <title>FPAI Approval Dashboard</title>
</head>
<body>
  <div id="root">
    <!-- React app renders here -->
  </div>
</body>
</html>
```

### GET /api/dashboard/summary
Dashboard summary data
```json
{
  "pending_approvals": {
    "total": 5,
    "by_priority": {
      "critical": 1,
      "high": 2,
      "medium": 2,
      "low": 0
    },
    "by_tier": {
      "tier_0": 1,
      "tier_1": 2,
      "tier_2_plus": 2
    }
  },
  "today_stats": {
    "intents_submitted": 50,
    "auto_approved": 40,
    "manually_approved": 8,
    "rejected": 2,
    "avg_alignment_score": 0.88,
    "services_deployed": 45
  },
  "pipeline_status": {
    "queued": 8,
    "spec_generation": 3,
    "building": 2,
    "deploying": 1,
    "completed": 45
  },
  "governance": {
    "current_mode": "autonomous",
    "active_policies": 4,
    "next_mode_change": "2025-11-16T08:00:00Z"
  }
}
```

### GET /api/approvals/pending
List pending approvals
```json
{
  "approvals": [
    {
      "intent_id": "uuid",
      "service_name": "payment-processor",
      "submitted_by": "session-3",
      "submitted_at": "2025-11-16T01:00:00Z",
      "priority": "critical",
      "tier": 0,
      "purpose": "Process customer payments via Stripe",
      "alignment_score": 0.95,
      "alignment_reasoning": "Critical for revenue generation, aligns perfectly with business goals",
      "risk_level": "medium",
      "risk_factors": ["handles financial data", "external API dependency"],
      "governance_recommendation": "requires_approval",
      "estimated_build_time": "30 minutes",
      "estimated_cost": "$0.20"
    }
  ],
  "total": 5
}
```

### POST /api/approvals/{intent_id}/approve
Approve intent
```json
// Request
{
  "notes": "Approved - critical for revenue goals",
  "approved_by": "user"
}

// Response
{
  "intent_id": "uuid",
  "status": "approved",
  "approved_at": "2025-11-16T01:05:00Z",
  "approved_by": "user",
  "next_action": "forwarded_to_spec_assembly"
}
```

### POST /api/approvals/{intent_id}/reject
Reject intent
```json
// Request
{
  "reason": "Duplicates existing analytics service",
  "rejected_by": "user"
}

// Response
{
  "intent_id": "uuid",
  "status": "rejected",
  "rejected_at": "2025-11-16T01:05:00Z",
  "rejected_by": "user"
}
```

### POST /api/approvals/batch
Batch approve/reject
```json
// Request
{
  "action": "approve",
  "intent_ids": ["uuid1", "uuid2", "uuid3"],
  "notes": "All aligned with Q4 goals",
  "approved_by": "user"
}

// Response
{
  "processed": 3,
  "succeeded": 3,
  "failed": 0,
  "results": [
    {"intent_id": "uuid1", "status": "approved"},
    {"intent_id": "uuid2", "status": "approved"},
    {"intent_id": "uuid3", "status": "approved"}
  ]
}
```

### GET /api/approvals/history
Approval history
```json
// Query: ?days=7&approved_by=user
{
  "approvals": [
    {
      "intent_id": "uuid",
      "service_name": "analytics-engine",
      "action": "approved",
      "approved_by": "user",
      "approved_at": "2025-11-15T14:00:00Z",
      "notes": "Good fit for data strategy"
    }
  ],
  "total": 45,
  "time_range": "7 days"
}
```

### GET /api/analytics/daily
Daily analytics
```json
{
  "date": "2025-11-16",
  "intents_submitted": 50,
  "auto_approved": 40,
  "manually_approved": 8,
  "rejected": 2,
  "avg_alignment_score": 0.88,
  "services_deployed": 45,
  "total_build_time_minutes": 1350,
  "total_cost": "$9.00",
  "by_tier": {
    "tier_0": 2,
    "tier_1": 8,
    "tier_2_plus": 38
  },
  "top_submitters": [
    {"session_id": "session-3", "count": 15},
    {"session_id": "session-1", "count": 12}
  ]
}
```

### GET /api/governance/settings
Get governance settings
```json
{
  "mode": "autonomous",
  "active_policies": [
    {
      "policy_id": "auto_approve_tier2_aligned",
      "name": "Auto-approve aligned TIER 2+",
      "active": true
    }
  ],
  "schedule": {
    "supervised_hours": "08:00-18:00 PST",
    "autonomous_hours": "18:00-08:00 PST"
  },
  "user_presence": {
    "detected": false,
    "last_activity": "2025-11-16T17:55:00Z"
  }
}
```

### POST /api/governance/mode
Change governance mode
```json
// Request
{
  "mode": "supervised"
}

// Response
{
  "mode": "supervised",
  "previous_mode": "autonomous",
  "changed_at": "2025-11-16T08:00:00Z"
}
```

### WS /api/dashboard/ws
WebSocket connection for real-time updates
```json
// Connected
{"event": "connected", "message": "Dashboard connected"}

// New approval needed
{
  "event": "new_approval",
  "intent_id": "uuid",
  "service_name": "analytics-engine",
  "priority": "high"
}

// Auto-approval happened
{
  "event": "auto_approved",
  "intent_id": "uuid",
  "service_name": "notification-service",
  "alignment_score": 0.92
}

// Service deployed
{
  "event": "service_deployed",
  "service_name": "payment-processor",
  "url": "http://localhost:8350"
}

// Queue stats update
{
  "event": "queue_update",
  "queued": 7,
  "processing": 3
}
```

---

## UI Screens

### Main Dashboard
```
┌──────────────────────────────────────────────────────────────┐
│  FPAI Approval Dashboard    Mode: Autonomous 🤖    [Settings] │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 Today's Activity                                         │
│  ┌─────────────┬─────────────┬─────────────┬────────────┐  │
│  │ Submitted   │ Auto-Approved│ Deployed   │ Success Rate│  │
│  │    50       │     40       │    45      │    96%     │  │
│  └─────────────┴─────────────┴─────────────┴────────────┘  │
│                                                               │
│  ⏳ Awaiting Your Approval (3)                   [Batch Approve]│
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 🔴 payment-processor (TIER 0)                         │ │
│  │    Stripe payment integration                          │ │
│  │    📈 Alignment: 95%    ⚠️  Risk: Medium             │ │
│  │    Submitted by: session-3 • 5 minutes ago            │ │
│  │    Est: 30 min • $0.20                                 │ │
│  │                                                         │ │
│  │    Governance says: TIER 0 requires manual approval   │ │
│  │    Risk factors: Financial data, external API         │ │
│  │                                                         │ │
│  │    [✅ Approve] [❌ Reject] [📄 View Full SPEC]       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 🟡 analytics-engine (TIER 2)                          │ │
│  │    Real-time user analytics                            │ │
│  │    📈 Alignment: 92%    ✅ Risk: Low                  │ │
│  │    [✅ Approve] [❌ Reject] [Details]                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ✅ Auto-Approved Today (40)           [View All]           │
│  • notification-service ✅ (Aligned: 91%)                   │
│  • audit-logger ✅ (Aligned: 89%)                           │
│  • data-sync-service ✅ (Aligned: 94%)                      │
│                                                               │
│  🏗️  Currently Building (3)                                │
│  • email-service → Deploying (90%)                          │
│  • cache-manager → Building (45%)                           │
│  • webhook-handler → SPEC generation (10%)                  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Settings Panel
```
┌──────────────────────────────────────────┐
│  Governance Settings                     │
├──────────────────────────────────────────┤
│  Mode: [Supervised] [Autonomous] [Aggressive]│
│  Currently: Autonomous 🤖                │
│                                          │
│  Schedule:                               │
│  • Supervised: 08:00-18:00 PST          │
│  • Autonomous: 18:00-08:00 PST          │
│  [Edit Schedule]                         │
│                                          │
│  Active Policies (4):                    │
│  ☑ Auto-approve TIER 2+ aligned         │
│  ☑ Auto-approve TIER 1 while away       │
│  ☑ Require approval for TIER 0          │
│  ☑ Block misaligned intents             │
│  [Edit Policies]                         │
│                                          │
│  Blueprint:                              │
│  Focus: Revenue optimization, data-driven│
│  [View Full Blueprint]                   │
│                                          │
└──────────────────────────────────────────┘
```

---

## Architecture


### Tech Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI + React
- **Database:** SQLite (local), PostgreSQL (production)
- **API:** RESTful + WebSocket
- **Authentication:** JWT tokens
- **Deployment:** Docker + systemd

### Technology Stack
- **Frontend:** React 18+ with TypeScript
- **Backend:** FastAPI (Python 3.11+)
- **UI Library:** Tailwind CSS + shadcn/ui
- **State Management:** React Query + Zustand
- **WebSocket:** Socket.IO
- **Charts:** Recharts
- **Build:** Vite

### Frontend Structure
```
/frontend
  /src
    /components
      Dashboard.tsx          # Main dashboard
      ApprovalCard.tsx       # Individual approval card
      StatsOverview.tsx      # Stats widgets
      GovernancePanel.tsx    # Governance settings
      IntentDetails.tsx      # Detailed intent view
    /hooks
      useWebSocket.ts        # WebSocket hook
      useApprovals.ts        # Approval data hook
    /services
      api.ts                 # API client
    /types
      index.ts               # TypeScript types
    App.tsx
    main.tsx
```

---

## Data Models

```python
class ApprovalItem(BaseModel):
    intent_id: str
    service_name: str
    submitted_by: str
    submitted_at: datetime
    priority: str
    tier: int
    purpose: str
    key_features: List[str]
    alignment_score: float
    alignment_reasoning: str
    risk_level: str
    risk_factors: List[str]
    governance_recommendation: str
    estimated_build_time: str
    estimated_cost: str

class DashboardSummary(BaseModel):
    pending_approvals: dict
    today_stats: dict
    pipeline_status: dict
    governance: dict

class ApprovalAction(BaseModel):
    action: str  # approve, reject
    notes: Optional[str] = None
    approved_by: str
    timestamp: datetime = Field(default_factory=datetime.now)
```

---


## File Structure

```
approval-dashboard/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic models
│   ├── config.py         # Configuration
│   ├── endpoints/
│   │   ├── udc.py       # UDC endpoints
│   │   └── service.py   # Business endpoints
│   └── utils/
│       ├── registry.py  # Registry integration
│       └── logger.py    # Logging utilities
├── tests/
│   ├── test_main.py
│   ├── test_udc.py
│   └── test_integration.py
├── SPEC.md
├── README.md
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Dependencies

### Required Services
- **registry** (8000) - Service discovery
- **intent-queue** (8212) - Intent data
- **governance** (8213) - Governance settings

### Optional Services
- **sovereign-factory** (8210) - Pipeline status

---

## Deployment

```bash
# Build frontend
cd /Users/jamessunheart/Development/SERVICES/approval-dashboard/frontend
npm install
npm run build

# Run backend
cd /Users/jamessunheart/Development/SERVICES/approval-dashboard
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic httpx websockets
uvicorn app.main:app --host 0.0.0.0 --port 8214

# Production
docker build -t fpai-approval-dashboard .
docker run -d --name approval-dashboard \
  -p 8214:8214 \
  fpai-approval-dashboard
```

---

## Success Criteria

- [ ] Beautiful, intuitive dashboard UI
- [ ] Real-time updates via WebSocket
- [ ] One-click approve/reject
- [ ] Batch operations work
- [ ] Mobile-responsive design
- [ ] < 2 second page load
- [ ] Governance controls functional
- [ ] Analytics charts display correctly
- [ ] Keyboard shortcuts (optional)
- [ ] Dark mode support (optional)
- [ ] Review 50 approvals in < 5 minutes

---

## Performance Targets

- **Page Load:** < 2 seconds
- **API Response:** < 200ms
- **WebSocket Latency:** < 100ms
- **UI Responsiveness:** 60 FPS
- **Concurrent Users:** 10+
- **Mobile Performance:** Smooth on 3G
- **Uptime:** 99.9%

---

## User Experience

### Morning Routine (5 minutes)
1. Open dashboard: http://localhost:8214
2. See overnight activity summary
3. Review 3 pending critical approvals
4. Batch approve 15 aligned TIER 2 services
5. Check deployed services list
6. Done!

### Throughout Day (2 minutes every 2 hours)
1. Dashboard auto-updates in browser
2. Notification shows new approval needed
3. Review intent card
4. One-click approve
5. Watch it build in real-time
6. Done!

### Evening (1 minute)
1. Switch to autonomous mode
2. System builds itself overnight
3. Close browser
4. Come back to 20 new deployed services!

---

## Integration Examples

### Access Dashboard
```bash
# Open in browser
open http://localhost:8214

# Or production
open http://198.54.123.234:8214
```

### API Usage
```bash
# Get pending approvals
curl http://localhost:8214/api/approvals/pending

# Approve intent
curl -X POST http://localhost:8214/api/approvals/{intent_id}/approve \
  -d '{"notes": "Looks good!", "approved_by": "user"}'

# Batch approve
curl -X POST http://localhost:8214/api/approvals/batch \
  -d '{"action": "approve", "intent_ids": ["uuid1", "uuid2"]}'
```

---

## Future Enhancements

- [ ] Slack integration (approve via Slack)
- [ ] Email notifications for approvals
- [ ] Mobile app (iOS/Android)
- [ ] Voice commands (approve via voice)
- [ ] AI assistant chatbot
- [ ] Approval delegation (to other users)
- [ ] Custom dashboards per user
- [ ] Export reports (PDF/CSV)
- [ ] Integration with project management tools

---

**Your 5-minute daily interface to a self-building system!**
