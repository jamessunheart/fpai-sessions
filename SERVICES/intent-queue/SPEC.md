# INTENT-QUEUE - Technical Specification

**Service Name:** intent-queue
**Version:** 1.0.0



---

## Purpose

Unified, persistent, prioritized queue for all system intents. Enables multiple Claude sessions, autonomous agents, and human architects to submit service intents that flow through the assembly line. The single source of truth for "what should be built next."

This service enables the recursive self-building pattern where the system continuously improves itself.

---

## Capabilities

This service provides the following capabilities as part of the FPAI droplet mesh:

### Primary Functions

See 'Core Capabilities' section below for detailed descriptions.

## Core Capabilities

- **Unified Queue:** Single queue accessible by all sessions/agents
- **Persistent Storage:** SQLite/PostgreSQL - survives restarts
- **Priority Management:** 4-level priority (critical/high/medium/low)
- **Multi-Session Safe:** Concurrent submissions without conflicts
- **Intent Deduplication:** Prevent duplicate service intents
- **WebSocket Subscriptions:** Real-time queue updates
- **Governance Integration:** Hand-off to governance for alignment checking
- **Status Tracking:** Complete lifecycle from submission → deployment
- **Audit Trail:** Who submitted what, when, and why

---

## UDC Endpoints (5/5)

### 1. GET /health
**Returns:** Service health status
```json
{
  "status": "active",
  "service": "intent-queue",
  "version": "1.0.0",
  "timestamp": "2025-11-16T00:00:00Z",
  "queue_depth": 12,
  "processing": 3
}
```

### 2. GET /capabilities
**Returns:** Service capabilities and metadata
```json
{
  "version": "1.0.0",
  "features": [
    "unified_queue",
    "priority_management",
    "deduplication",
    "persistence",
    "websocket_subscriptions",
    "governance_integration"
  ],
  "dependencies": ["registry", "governance"],
  "udc_version": "1.0",
  "metadata": {
    "max_queue_size": 1000,
    "supported_priorities": ["critical", "high", "medium", "low"],
    "persistence": "sqlite"
  }
}
```

### 3. GET /state
**Returns:** Current service state and metrics
```json
{
  "uptime_seconds": 86400,
  "requests_total": 500,
  "errors_last_hour": 0,
  "last_restart": "2025-11-16T00:00:00Z",
  "queue_depth": 12,
  "queued": 8,
  "processing": 3,
  "awaiting_approval": 4,
  "completed_today": 45,
  "failed_today": 2
}
```

### 4. GET /dependencies
**Returns:** Service dependency status
```json
{
  "required": [
    {"name": "registry", "status": "available", "url": "http://localhost:8000"}
  ],
  "optional": [
    {"name": "governance", "status": "available", "url": "http://localhost:8213"}
  ],
  "missing": []
}
```

### 5. POST /message
**Returns:** Message acknowledgment
```json
{
  "trace_id": "uuid",
  "source": "unified-chat",
  "target": "intent-queue",
  "message_type": "event",
  "payload": {
    "event": "new_intent_submitted",
    "intent_id": "uuid"
  },
  "timestamp": "2025-11-16T00:00:00Z"
}
```

---

## Service Endpoints

### POST /intents/submit
Submit new intent to queue
```json
// Request
{
  "submitted_by": "session-3",
  "source": "unified-chat",
  "service_name": "analytics-engine",
  "service_type": "domain",
  "priority": "high",
  "purpose": "Real-time user analytics and behavior tracking",
  "key_features": [
    "Event streaming ingestion",
    "Time-series aggregation",
    "Anomaly detection",
    "Real-time dashboards"
  ],
  "dependencies": ["registry", "event-bus"],
  "port": 8350,
  "target_tier": 2,
  "blueprint_context": "Aligns with data-driven decision making goal",
  "auto_build": true,
  "auto_deploy": false,
  "metadata": {
    "estimated_complexity": "medium",
    "business_value": "high"
  }
}

// Response
{
  "intent_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "queue_position": 3,
  "priority": "high",
  "estimated_start": "2025-11-16T01:15:00Z",
  "governance_status": "pending_check",
  "track_url": "/intents/550e8400-e29b-41d4-a716-446655440000",
  "subscribe_url": "ws://localhost:8212/intents/550e8400-e29b-41d4-a716-446655440000/subscribe"
}
```

### GET /intents/{intent_id}
Get specific intent details
```json
{
  "intent_id": "550e8400-e29b-41d4-a716-446655440000",
  "service_name": "analytics-engine",
  "submitted_by": "session-3",
  "submitted_at": "2025-11-16T01:00:00Z",
  "status": "governance_check",
  "priority": "high",
  "queue_position": 3,
  "blueprint_aligned": null,
  "governance_decision": null,
  "spec_path": null,
  "build_id": null,
  "deployment_url": null,
  "lifecycle": [
    {"phase": "submitted", "timestamp": "2025-11-16T01:00:00Z", "status": "completed"},
    {"phase": "governance_check", "timestamp": "2025-11-16T01:00:05Z", "status": "running"},
    {"phase": "spec_generation", "status": "pending"},
    {"phase": "build", "status": "pending"},
    {"phase": "deployment", "status": "pending"}
  ]
}
```

### GET /intents/queue
Get current queue status
```json
{
  "total": 12,
  "by_status": {
    "queued": 8,
    "governance_check": 2,
    "spec_generation": 1,
    "awaiting_approval": 4,
    "building": 3,
    "deploying": 1,
    "completed": 45,
    "failed": 2
  },
  "by_priority": {
    "critical": 2,
    "high": 5,
    "medium": 4,
    "low": 1
  },
  "next_processing": [
    {
      "intent_id": "uuid1",
      "service_name": "payment-processor",
      "priority": "critical",
      "queue_position": 1
    },
    {
      "intent_id": "uuid2",
      "service_name": "analytics-engine",
      "priority": "high",
      "queue_position": 2
    }
  ],
  "processing_rate": {
    "avg_time_to_start_minutes": 12,
    "avg_completion_time_minutes": 45,
    "throughput_per_hour": 2.5
  }
}
```

### GET /intents
List intents with filters
```json
// Query: ?status=queued&priority=high&submitted_by=session-3&limit=20
{
  "intents": [
    {
      "intent_id": "uuid",
      "service_name": "analytics-engine",
      "submitted_by": "session-3",
      "priority": "high",
      "status": "queued",
      "queue_position": 3,
      "submitted_at": "2025-11-16T01:00:00Z"
    }
  ],
  "total": 45,
  "filtered": 8,
  "page": 1,
  "pages": 1
}
```

### PATCH /intents/{intent_id}/priority
Update intent priority
```json
// Request
{
  "priority": "critical",
  "reason": "Business-critical payment issue"
}

// Response
{
  "intent_id": "uuid",
  "old_priority": "high",
  "new_priority": "critical",
  "old_queue_position": 5,
  "new_queue_position": 1,
  "updated_at": "2025-11-16T01:05:00Z"
}
```

### DELETE /intents/{intent_id}
Cancel queued intent
```json
{
  "intent_id": "uuid",
  "status": "cancelled",
  "cancelled_at": "2025-11-16T01:00:00Z",
  "cancelled_by": "user",
  "reason": "Requirements changed"
}
```

### WS /intents/{intent_id}/subscribe
WebSocket subscription for real-time updates
```json
// Connected
{"event": "connected", "intent_id": "uuid"}

// Status updates
{"event": "status_change", "old_status": "queued", "new_status": "governance_check"}
{"event": "governance_decision", "decision": "auto_approve", "aligned": true, "score": 0.95}
{"event": "spec_generated", "spec_path": "/path/to/SPEC.md", "score": 92}
{"event": "build_started", "build_id": "uuid"}
{"event": "deployed", "deployment_url": "http://localhost:8350"}
{"event": "completed", "duration_seconds": 1800}
```

### WS /intents/queue/subscribe
Subscribe to queue-wide events
```json
{"event": "new_intent", "intent_id": "uuid", "service_name": "X", "priority": "high"}
{"event": "intent_completed", "intent_id": "uuid", "service_name": "X"}
{"event": "queue_stats", "queued": 8, "processing": 3, "completed_today": 46}
```

### POST /intents/{intent_id}/duplicate-check
Check if similar intent exists
```json
// Request
{
  "service_name": "analytics-engine",
  "purpose": "Real-time analytics"
}

// Response
{
  "duplicates_found": 1,
  "similar_intents": [
    {
      "intent_id": "uuid-existing",
      "service_name": "analytics-engine",
      "similarity_score": 0.95,
      "status": "deployed",
      "created_at": "2025-11-15T10:00:00Z"
    }
  ],
  "recommendation": "duplicate_detected"
}
```

---

## Architecture


### Tech Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite (local), PostgreSQL (production)
- **API:** RESTful + WebSocket
- **Authentication:** JWT tokens
- **Deployment:** Docker + systemd

### Technology Stack
- **Framework:** FastAPI (Python 3.11+)
- **Database:** SQLite (local), PostgreSQL (production)
- **Queue:** In-memory + persistent (hybrid)
- **WebSocket:** Real-time subscriptions
- **Cache:** Redis (optional, for performance)

### Data Flow

```
Session/Agent submits intent
         ↓
Intent Queue stores (DB + memory)
         ↓
Governance service notified
         ↓
Alignment check performed
         ↓
Decision: auto_approve / requires_approval / blocked
         ↓
If auto_approve:
  → sovereign-factory picks up
  → SPEC assembly begins
If requires_approval:
  → approval-dashboard notified
  → await human decision
If blocked:
  → intent marked blocked
  → submitter notified
```

### Priority Queue Algorithm

```python
# Priority order (highest to lowest)
priorities = {
  "critical": 1,  # TIER 0 infrastructure
  "high": 2,      # TIER 1 sacred loop
  "medium": 3,    # TIER 2+ domain
  "low": 4        # Experimental
}

# Within same priority: FIFO
# Across priorities: critical > high > medium > low
```

### Deduplication Strategy

```python
def is_duplicate(new_intent, existing_intents):
    # Check exact service name match
    if exact_name_match:
        return True
    
    # Check semantic similarity (Claude API)
    similarity_score = check_semantic_similarity(
        new_intent.purpose,
        existing_intent.purpose
    )
    
    if similarity_score > 0.90:
        return True
    
    return False
```

---

## Data Models

```python
class Intent(BaseModel):
    intent_id: str = Field(default_factory=uuid4)
    submitted_by: str  # session-id or user-id
    submitted_at: datetime = Field(default_factory=datetime.now)
    source: str  # unified-chat, api, autonomous-agent
    
    # Service details
    service_name: str
    service_type: str  # infrastructure, sacred_loop, domain, api_gateway, data
    priority: str = "medium"  # critical, high, medium, low
    purpose: str
    key_features: List[str]
    dependencies: List[str] = []
    port: int
    target_tier: int
    
    # Governance
    blueprint_context: str
    blueprint_aligned: Optional[bool] = None
    alignment_score: Optional[float] = None
    governance_decision: Optional[str] = None  # auto_approve, requires_approval, blocked
    governance_reasoning: Optional[str] = None
    
    # Build settings
    auto_build: bool = True
    auto_deploy: bool = False
    
    # Status tracking
    status: str = "queued"  # queued, governance_check, spec_generation, awaiting_approval, building, deploying, completed, failed, cancelled, blocked
    queue_position: Optional[int] = None
    
    # Pipeline references
    spec_path: Optional[str] = None
    spec_score: Optional[int] = None
    build_id: Optional[str] = None
    deployment_url: Optional[str] = None
    
    # Lifecycle tracking
    lifecycle: List[LifecycleEvent] = []
    
    # Metadata
    metadata: dict = {}
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

class LifecycleEvent(BaseModel):
    phase: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str  # running, completed, failed
    duration_seconds: Optional[int] = None
    details: dict = {}
```

---


## File Structure

```
intent-queue/
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
- **registry** (8000) - Service discovery, auto-registration

### Optional Services
- **governance** (8213) - Blueprint alignment checking
- **sovereign-factory** (8210) - Consumes from queue
- **approval-dashboard** (8214) - Human approvals

### External APIs
- None (all dependencies are internal FPAI services)

---

## Deployment

```bash
# Local
cd /Users/jamessunheart/Development/SERVICES/intent-queue
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic sqlalchemy httpx websockets
uvicorn app.main:app --host 0.0.0.0 --port 8212

# Production
docker build -t fpai-intent-queue .
docker run -d --name intent-queue \
  -p 8212:8212 \
  -v /opt/fpai/data:/app/data \
  fpai-intent-queue
```

---

## Success Criteria

- [ ] Accept intents from multiple sessions concurrently
- [ ] Persist intents across service restarts
- [ ] Maintain priority-based FIFO queue
- [ ] Detect and prevent duplicate intents
- [ ] WebSocket subscriptions work for real-time updates
- [ ] Integrate with governance for alignment checks
- [ ] Hand-off to sovereign-factory for approved intents
- [ ] Track complete lifecycle from submission → deployment
- [ ] API response time < 100ms
- [ ] Support 100+ concurrent WebSocket connections
- [ ] Handle 1000+ intents in queue
- [ ] 99.9% uptime

---

## Performance Targets

- **Queue Operations:** < 50ms (add, remove, update)
- **Database Queries:** < 100ms
- **WebSocket Latency:** < 200ms
- **Concurrent Submissions:** 50+ simultaneous
- **Queue Capacity:** 1000 intents
- **WebSocket Connections:** 100+ concurrent
- **Throughput:** 100 intents/hour processing
- **Uptime:** 99.9%

---

## Integration Examples

### From Unified Chat
```bash
# Session submits intent via chat
/propose-intent analytics-engine: Real-time user analytics

# Behind the scenes:
POST http://localhost:8212/intents/submit
{
  "submitted_by": "session-3",
  "source": "unified-chat",
  "service_name": "analytics-engine",
  ...
}
```

### From API
```bash
curl -X POST http://localhost:8212/intents/submit \
  -H "Content-Type: application/json" \
  -d '{
    "submitted_by": "user",
    "service_name": "payment-processor",
    "purpose": "Process payments via Stripe",
    "priority": "critical",
    "blueprint_context": "Required for revenue generation"
  }'
```

### Monitor Queue
```bash
# Get queue status
curl http://localhost:8212/intents/queue | python3 -m json.tool

# Track specific intent
curl http://localhost:8212/intents/{intent_id}

# WebSocket subscription
wscat -c ws://localhost:8212/intents/{intent_id}/subscribe
```

---

## Error Handling

### Duplicate Detection
```json
{
  "error": "duplicate_intent",
  "message": "Similar service already exists or in queue",
  "existing_intent_id": "uuid",
  "similarity_score": 0.95,
  "recommendation": "Use existing service or modify intent"
}
```

### Invalid Priority
```json
{
  "error": "invalid_priority",
  "message": "Priority must be one of: critical, high, medium, low",
  "provided": "urgent"
}
```

### Queue Full
```json
{
  "error": "queue_full",
  "message": "Intent queue at capacity (1000 intents)",
  "recommendation": "Wait for existing intents to complete or cancel some"
}
```

---

## Future Enhancements

- [ ] Redis backend for distributed deployment
- [ ] ML-based priority prediction
- [ ] Auto-intent generation from system monitoring
- [ ] Batch intent submission
- [ ] Intent templates
- [ ] Scheduled intents (build at specific time)
- [ ] Intent dependencies (build X after Y completes)
- [ ] Cost estimation per intent
- [ ] ROI prediction per intent

---

**The foundation of autonomous self-building - every great system starts with a great queue!**
