# SPEC: nexus-event-bus

**Service Name:** nexus-event-bus
**Port:** 8450
**Version:** 1.0.0
**Status:** Design
**TIER:** 1 (Sacred Loop - Coordination)
**Created:** 2025-11-17
**Author:** Session #5 (Nexus - Integration & Infrastructure Hub)

---

## Purpose

NEXUS is a real-time event bus that enables instant communication, coordination, and synchronization between all Claude Code sessions. It transforms file-based polling into live event streaming, allowing sessions to discover each other, broadcast capabilities, claim work, and coordinate autonomously in real-time.

**Problem Solved:** Sessions currently rely on file-based messaging (MESSAGES.md, heartbeat JSONs, SSOT.json polling) which is slow, requires manual syncing, and prevents real-time awareness of what other sessions are doing.

**Value Delivered:**
- Real-time session discovery and capability matching
- Instant work claiming and conflict prevention
- Live status updates across all sessions
- Autonomous coordination without human intervention
- Event-driven architecture for scalability

---

## Core Capabilities

1. **Real-Time Event Streaming** - WebSocket-based pub/sub for instant session communication
2. **Session Discovery** - Find active sessions by capability, role, or availability
3. **Work Coordination** - Atomic work claiming to prevent duplicate effort
4. **SSOT Auto-Sync** - Automatically update SSOT.json and claude_sessions.json on state changes
5. **Event History** - Replay recent events for late-joining sessions
6. **Topic Subscriptions** - Filtered event streams (work.*, help.*, session.*, etc.)
7. **Presence Management** - Real-time tracking of session online/offline status
8. **Capability Matching** - Smart routing of help requests to capable sessions

---

## Dependencies

### Required
- **Registry** (localhost:8000) - Service discovery and registration
- **SSOT Filesystem** - Read/write access to:
  - `/Users/jamessunheart/Development/docs/coordination/SSOT.json`
  - `/Users/jamessunheart/Development/docs/coordination/claude_sessions.json`
  - `/Users/jamessunheart/Development/docs/coordination/heartbeats/`
  - `/Users/jamessunheart/Development/docs/coordination/messages/`

### Optional
- **Redis** (future) - Persistent event storage
- **Unified Chat** (localhost:8100) - Bidirectional integration

---

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI 0.104+ (async support, WebSocket, automatic OpenAPI docs)
- **WebSocket Library:** `websockets` 12.0+
- **Validation:** Pydantic 2.5+ (data models, request validation)
- **HTTP Client:** httpx 0.25+ (async registry communication)
- **Server:** Uvicorn 0.24+ (ASGI server)
- **Testing:** pytest, pytest-asyncio

---

## UDC Endpoints

All 5 required UDC endpoints are implemented:

### 1. GET /health
Returns service health status.

**Response (200 OK):**
```json
{
  "status": "active",
  "service": "nexus-event-bus",
  "version": "1.0.0",
  "timestamp": "2025-11-17T07:50:00Z"
}
```

### 2. GET /capabilities
Returns service features and dependencies.

**Response (200 OK):**
```json
{
  "version": "1.0.0",
  "features": [
    "websocket-streaming",
    "pubsub-topics",
    "session-discovery",
    "work-coordination",
    "ssot-sync",
    "event-history"
  ],
  "dependencies": ["registry", "filesystem-ssot"],
  "udc_version": "1.0",
  "metadata": {
    "max_connections": 50,
    "event_retention": "1 hour",
    "supported_event_types": 9
  }
}
```

### 3. GET /state
Returns service metrics and operational state.

**Response (200 OK):**
```json
{
  "uptime_seconds": 3600,
  "connected_sessions": 5,
  "events_total": 1523,
  "events_per_second": 2.3,
  "errors_last_hour": 0,
  "last_restart": "2025-11-17T07:00:00Z",
  "event_latency_ms": 15
}
```

### 4. GET /dependencies
Returns dependency status and health.

**Response (200 OK):**
```json
{
  "required": [
    {
      "name": "registry",
      "status": "available",
      "url": "http://localhost:8000"
    },
    {
      "name": "ssot-filesystem",
      "status": "available",
      "path": "/Users/jamessunheart/Development/docs/coordination"
    }
  ],
  "optional": [],
  "missing": []
}
```

### 5. POST /message
Receives inter-droplet messages for coordination.

**Request:**
```json
{
  "trace_id": "uuid",
  "source": "registry",
  "target": "nexus-event-bus",
  "message_type": "query",
  "payload": {"query": "connected_sessions"},
  "timestamp": "2025-11-17T07:50:00Z"
}
```

**Response (200 OK):**
```json
{
  "status": "processed",
  "result": {"connected_sessions": 5}
}
```

---

## Architecture

### Service Type
- **Tier:** TIER 1 (Sacred Loop - Coordination)
- **Category:** Infrastructure / Communication
- **Port:** 8450

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                  NEXUS Event Bus (8450)                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                 │
│  │   WebSocket  │    │  Event Store │                 │
│  │   Server     │◄───┤  (In-Memory) │                 │
│  └──────────────┘    └──────────────┘                 │
│         │                    │                          │
│         │            ┌───────▼────────┐                │
│         │            │  Event Router  │                │
│         │            └────────────────┘                │
│         │                    │                          │
│  ┌──────▼───────────────────▼────────┐                │
│  │     Pub/Sub Manager                │                │
│  │  - Session subscriptions           │                │
│  │  - Event filtering                 │                │
│  │  - Broadcast routing               │                │
│  └────────────────────────────────────┘                │
│         │                                               │
│  ┌──────▼──────────────────────┐                      │
│  │   SSOT Sync Engine           │                      │
│  │  - Auto-update SSOT.json     │                      │
│  │  - Update claude_sessions     │                      │
│  │  - Generate heartbeats        │                      │
│  └──────────────────────────────┘                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
         │                                   │
         │ WebSocket                         │ HTTP
         │                                   │
    ┌────▼────┐                         ┌───▼────┐
    │ Session │                         │Registry│
    │   #1    │                         │ (8000) │
    └─────────┘                         └────────┘
    ┌─────────┐
    │ Session │
    │   #2    │
    └─────────┘
    ┌─────────┐
    │ Session │
    │  #3-14  │
    └─────────┘
```

### Communication Patterns

**1. Session → NEXUS (WebSocket)**
- Session connects: `ws://localhost:8450/ws/session/{session_id}`
- Session sends events: `work_claimed`, `task_complete`, `help_needed`, etc.
- NEXUS broadcasts to subscribers

**2. NEXUS → Sessions (WebSocket)**
- Real-time event push to all connected sessions
- Filtered by subscription topics
- JSON event payloads

**3. NEXUS → SSOT (Filesystem)**
- Auto-updates SSOT.json on state changes
- Creates heartbeat files
- Updates claude_sessions.json

---

## 📋 FUNCTIONAL REQUIREMENTS

### FR-1: WebSocket Event Streaming
**Priority:** CRITICAL
**Description:** Sessions connect via WebSocket and receive real-time events

**Acceptance Criteria:**
- Sessions can connect to `ws://localhost:8450/ws/session/{session_id}`
- Connection authenticated with session token
- Events pushed to client within 50ms of occurrence
- Automatic reconnection on disconnect
- Support for 20+ concurrent session connections

**Event Types:**
- `session.connected` - Session joins network
- `session.disconnected` - Session leaves
- `work.claimed` - Session claims work item
- `work.completed` - Session completes task
- `help.needed` - Session requests assistance
- `capability.broadcast` - Session announces capabilities
- `status.update` - Session updates status
- `message.broadcast` - Session sends message to all
- `message.direct` - Session sends direct message

### FR-2: Event Publishing API
**Priority:** CRITICAL
**Description:** Sessions can publish events to the bus

**Acceptance Criteria:**
- POST `/events` endpoint accepts event JSON
- WebSocket `send()` method for connected clients
- Event validation and schema enforcement
- Event timestamping and ID generation
- Rate limiting (100 events/min per session)

**Event Schema:**
```json
{
  "event_id": "uuid",
  "event_type": "work.claimed|work.completed|help.needed|...",
  "session_id": "session-5",
  "timestamp": "2025-11-17T07:50:00Z",
  "payload": {
    "work_item": "Deploy NEXUS",
    "priority": "high",
    "capabilities_needed": ["python", "websocket"],
    "metadata": {}
  }
}
```

### FR-3: Pub/Sub Topic Management
**Priority:** HIGH
**Description:** Sessions subscribe to specific event types

**Acceptance Criteria:**
- Subscribe via WebSocket message: `{"action": "subscribe", "topics": ["work.*", "help.*"]}`
- Unsubscribe from topics
- Wildcard support (`work.*` matches all work events)
- Topic filtering at server-side (reduce bandwidth)

**Default Topics:**
- `session.*` - All session lifecycle events
- `work.*` - All work-related events
- `help.*` - All help requests
- `capability.*` - Capability broadcasts
- `message.*` - All messages
- `broadcast` - Global announcements

### FR-4: Session Discovery
**Priority:** HIGH
**Description:** Find active sessions by capability or availability

**Acceptance Criteria:**
- GET `/sessions/active` - List all connected sessions
- GET `/sessions/capabilities?skill=python` - Find sessions by capability
- GET `/sessions/{id}` - Get specific session details
- Real-time session presence (online/offline)
- Capability matching algorithm

**Session Info Structure:**
```json
{
  "session_id": "session-5",
  "role": "Nexus - Integration & Infrastructure Hub",
  "status": "active",
  "current_work": "Building NEXUS event bus",
  "capabilities": ["python", "fastapi", "websocket", "infrastructure"],
  "connected_at": "2025-11-17T07:40:00Z",
  "last_event": "2025-11-17T07:50:00Z"
}
```

### FR-5: Work Coordination
**Priority:** HIGH
**Description:** Prevent duplicate work through claim/release protocol

**Acceptance Criteria:**
- POST `/work/claim` - Atomically claim work item
- POST `/work/release` - Release claimed work
- GET `/work/claimed` - View all claimed work
- Automatic release on session disconnect
- Conflict detection (two sessions claim same work)

**Work Claim Flow:**
1. Session A broadcasts `help.needed` event
2. Session B sees event, sends `work.claim` with work_id
3. NEXUS verifies unclaimed, grants to Session B
4. NEXUS broadcasts `work.claimed` event to all
5. Other sessions see work is taken

### FR-6: SSOT Auto-Sync
**Priority:** HIGH
**Description:** Automatically update SSOT.json on state changes

**Acceptance Criteria:**
- Update SSOT.json on session connect/disconnect
- Update on work claim/complete events
- Update claude_sessions.json with real-time status
- Create heartbeat JSON files
- Maintain consistency between event bus state and filesystem
- Max 1-second delay between event and file update

**Sync Operations:**
- `session.connected` → Update SSOT.json, add to claude_sessions.json
- `work.claimed` → Update current_work in session file
- `status.update` → Update session status
- Auto-generate heartbeat files every 5 minutes

### FR-7: Event History & Replay
**Priority:** MEDIUM
**Description:** Store recent events for late-joining sessions

**Acceptance Criteria:**
- Store last 1000 events in memory
- GET `/events/history?since={timestamp}` - Retrieve event history
- New sessions can replay missed events
- Configurable retention period (default: 1 hour)
- Event pruning to prevent memory bloat

### FR-8: Health & Monitoring
**Priority:** MEDIUM
**Description:** Monitor event bus health and performance

**Acceptance Criteria:**
- Track events/second throughput
- Monitor WebSocket connection count
- Measure event latency (publish → delivery)
- Alert on high error rates
- Expose metrics via `/state` endpoint

---

## 🔧 TECHNICAL SPECIFICATIONS

### Tech Stack
- **Framework:** FastAPI (async support)
- **WebSocket:** `fastapi.WebSocket` + `websockets` library
- **Storage:** In-memory (Redis optional for persistence)
- **Event Format:** JSON
- **Authentication:** Session tokens (from SSOT)

### API Endpoints (UDC + Custom)

#### 1. GET /health (UDC Required)
**Description:** Health check endpoint

**Response:**
```json
{
  "status": "active",
  "service": "nexus-event-bus",
  "version": "1.0.0",
  "timestamp": "2025-11-17T07:50:00Z"
}
```

#### 2. GET /capabilities (UDC Required)
**Description:** Service capabilities

**Response:**
```json
{
  "version": "1.0.0",
  "features": [
    "websocket-streaming",
    "pubsub-topics",
    "session-discovery",
    "work-coordination",
    "ssot-sync",
    "event-history"
  ],
  "dependencies": ["registry", "filesystem-ssot"],
  "udc_version": "1.0",
  "metadata": {
    "max_connections": 50,
    "event_retention": "1 hour",
    "supported_event_types": 9
  }
}
```

#### 3. GET /state (UDC Required)
**Description:** Service metrics

**Response:**
```json
{
  "uptime_seconds": 3600,
  "connected_sessions": 5,
  "events_total": 1523,
  "events_per_second": 2.3,
  "errors_last_hour": 0,
  "last_restart": "2025-11-17T07:00:00Z",
  "event_latency_ms": 15
}
```

#### 4. GET /dependencies (UDC Required)
**Description:** Dependency status

**Response:**
```json
{
  "required": [
    {
      "name": "registry",
      "status": "available",
      "url": "http://localhost:8000"
    },
    {
      "name": "ssot-filesystem",
      "status": "available",
      "path": "/Users/jamessunheart/Development/docs/coordination"
    }
  ],
  "optional": [],
  "missing": []
}
```

#### 5. POST /message (UDC Required)
**Description:** Receive inter-droplet messages

**Request:**
```json
{
  "trace_id": "uuid",
  "source": "registry",
  "target": "nexus-event-bus",
  "message_type": "query",
  "payload": {"query": "connected_sessions"},
  "timestamp": "2025-11-17T07:50:00Z"
}
```

**Response:**
```json
{
  "status": "processed",
  "result": {"connected_sessions": 5}
}
```

#### 6. WebSocket /ws/session/{session_id}
**Description:** Primary WebSocket connection for sessions

**Connection:**
```
ws://localhost:8450/ws/session/session-5
Headers: {"Authorization": "Bearer {session_token}"}
```

**Client → Server Messages:**
```json
// Subscribe to topics
{"action": "subscribe", "topics": ["work.*", "help.*"]}

// Publish event
{
  "action": "publish",
  "event_type": "work.claimed",
  "payload": {"work_item": "Deploy NEXUS"}
}

// Request help
{
  "action": "publish",
  "event_type": "help.needed",
  "payload": {
    "task": "Need Python expert for debugging",
    "capabilities": ["python", "debugging"],
    "priority": "high"
  }
}
```

**Server → Client Messages:**
```json
// Event notification
{
  "event_id": "uuid",
  "event_type": "work.completed",
  "session_id": "session-1",
  "timestamp": "2025-11-17T07:50:00Z",
  "payload": {"work_item": "Dashboard deployed"}
}

// System notification
{
  "event_type": "system.notification",
  "message": "Session #3 connected",
  "timestamp": "2025-11-17T07:50:00Z"
}
```

#### 7. POST /events
**Description:** HTTP endpoint to publish events (alternative to WebSocket)

**Request:**
```json
{
  "event_type": "status.update",
  "session_id": "session-5",
  "payload": {"status": "working", "task": "Building NEXUS"}
}
```

**Response:**
```json
{
  "event_id": "uuid",
  "status": "published",
  "timestamp": "2025-11-17T07:50:00Z"
}
```

#### 8. GET /sessions/active
**Description:** List all connected sessions

**Response:**
```json
{
  "count": 5,
  "sessions": [
    {
      "session_id": "session-1",
      "role": "Infrastructure Builder",
      "status": "active",
      "connected_at": "2025-11-17T07:29:31Z",
      "current_work": "Registry maintenance"
    },
    {
      "session_id": "session-5",
      "role": "Nexus - Integration & Infrastructure Hub",
      "status": "active",
      "connected_at": "2025-11-17T07:40:00Z",
      "current_work": "Building NEXUS event bus"
    }
  ]
}
```

#### 9. GET /sessions/capabilities
**Description:** Find sessions by capability

**Query Params:** `?skill=python&available=true`

**Response:**
```json
{
  "matches": [
    {
      "session_id": "session-3",
      "role": "Infrastructure Engineer",
      "capabilities": ["python", "fastapi", "deployment"],
      "availability": "idle"
    }
  ]
}
```

#### 10. POST /work/claim
**Description:** Claim a work item

**Request:**
```json
{
  "session_id": "session-5",
  "work_id": "deploy-nexus",
  "work_description": "Deploy NEXUS event bus"
}
```

**Response:**
```json
{
  "status": "claimed",
  "work_id": "deploy-nexus",
  "claimed_by": "session-5",
  "claimed_at": "2025-11-17T07:50:00Z"
}
```

#### 11. GET /events/history
**Description:** Retrieve recent events

**Query Params:** `?since=2025-11-17T07:00:00Z&event_type=work.*&limit=100`

**Response:**
```json
{
  "count": 23,
  "events": [
    {
      "event_id": "uuid",
      "event_type": "work.claimed",
      "session_id": "session-1",
      "timestamp": "2025-11-17T07:45:00Z",
      "payload": {"work_item": "Fix Registry"}
    }
  ]
}
```

### Data Models

**Event Model:**
```python
class Event:
    event_id: str
    event_type: str  # Enum: session.*, work.*, help.*, etc.
    session_id: str
    timestamp: datetime
    payload: dict
    ttl: int = 3600  # seconds to keep in history
```

**Session Model:**
```python
class ConnectedSession:
    session_id: str
    role: str
    websocket: WebSocket
    subscribed_topics: List[str]
    connected_at: datetime
    last_event: datetime
    current_work: Optional[str]
    capabilities: List[str]
    status: str  # active, idle, working, error
```

**WorkClaim Model:**
```python
class WorkClaim:
    work_id: str
    claimed_by: str
    claimed_at: datetime
    description: str
    status: str  # claimed, completed, released
```

### File Structure

```
SERVICES/nexus-event-bus/
├── SPEC.md                    # This file
├── README.md                  # User guide
├── main.py                    # FastAPI application
├── requirements.txt           # Dependencies
├── src/
│   ├── __init__.py
│   ├── models.py              # Data models
│   ├── websocket_manager.py  # WebSocket connection management
│   ├── event_router.py        # Event routing & pub/sub
│   ├── ssot_sync.py          # SSOT.json synchronization
│   ├── work_coordinator.py    # Work claim/release logic
│   ├── session_registry.py    # In-memory session tracking
│   └── config.py              # Configuration
├── tests/
│   ├── test_websocket.py
│   ├── test_events.py
│   └── test_ssot_sync.py
└── client/
    └── nexus_client.py        # Python client library for sessions
```

### Dependencies

**Python Libraries:**
```
fastapi==0.104.1
websockets==12.0
uvicorn==0.24.0
pydantic==2.5.0
python-dateutil==2.8.2
httpx==0.25.0
```

**External Services:**
- Registry (8000) - Service registration
- Filesystem - SSOT.json, claude_sessions.json, heartbeats/

### Performance Requirements

- **Latency:** Event publish to delivery < 100ms (p99)
- **Throughput:** Support 1000 events/minute
- **Connections:** Support 20+ concurrent WebSocket connections
- **Memory:** < 200MB RAM usage
- **CPU:** < 10% on idle, < 50% under load

### Security

- **Authentication:** Session tokens validated against claude_sessions.json
- **Authorization:** Sessions can only publish events as themselves
- **Rate Limiting:** 100 events/minute per session
- **Input Validation:** All event payloads validated against schemas
- **WebSocket:** No CORS issues (localhost only in initial version)

---

## 🧪 TESTING STRATEGY

### Unit Tests
- Event validation and schema enforcement
- Topic matching and wildcard support
- Work claim conflict resolution
- SSOT sync logic

### Integration Tests
- WebSocket connection lifecycle
- Event publish → subscribe flow
- Multi-session coordination
- SSOT.json file updates

### End-to-End Tests
- Two sessions connect, one publishes event, other receives
- Session claims work, other sessions see it's taken
- Session disconnects, work auto-released
- Event history replay for late-joining session

### Performance Tests
- 10 sessions, 1000 events/min throughput
- Measure latency under load
- Memory usage over 1-hour period

---

## 📊 SUCCESS METRICS

**Primary KPIs:**
- **Event Latency:** < 50ms median, < 100ms p99
- **Uptime:** 99.9% availability
- **Session Adoption:** 80%+ of active sessions connected
- **Work Conflicts:** < 1% duplicate claims

**User Experience Metrics:**
- Sessions discover capabilities in < 1 second
- Work coordination prevents duplicate effort
- Real-time status visible to all sessions

---

## 🚀 DEPLOYMENT

### Local Development
```bash
cd /Users/jamessunheart/Development/SERVICES/nexus-event-bus
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8450 --reload
```

### Production
```bash
# On server (198.54.123.234)
cd /opt/fpai/services/nexus-event-bus
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8450 --workers 2
```

### Service Registration
Auto-registers with Registry on startup:
```python
@app.on_event("startup")
async def register_with_registry():
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/register",
            json={
                "name": "nexus-event-bus",
                "id": "nexus-event-bus-001",
                "url": "http://localhost:8450",
                "version": "1.0.0",
                "capabilities": ["event-streaming", "session-coordination"]
            }
        )
```

---

## 📖 USAGE EXAMPLES

### Example 1: Session Connects to NEXUS

**Python Client:**
```python
import asyncio
import websockets
import json

async def connect_to_nexus():
    uri = "ws://localhost:8450/ws/session/session-5"
    async with websockets.connect(uri) as ws:
        # Subscribe to work events
        await ws.send(json.dumps({
            "action": "subscribe",
            "topics": ["work.*", "help.*"]
        }))

        # Listen for events
        async for message in ws:
            event = json.loads(message)
            print(f"Event: {event['event_type']}")
            print(f"From: {event['session_id']}")
            print(f"Payload: {event['payload']}")

asyncio.run(connect_to_nexus())
```

### Example 2: Broadcast Help Request

**Python:**
```python
import httpx

# Session needs help with Python debugging
response = httpx.post("http://localhost:8450/events", json={
    "event_type": "help.needed",
    "session_id": "session-5",
    "payload": {
        "task": "Debug WebSocket connection issue",
        "capabilities_needed": ["python", "websocket", "debugging"],
        "priority": "high",
        "context": "NEXUS WebSocket not receiving messages"
    }
})

# All sessions subscribed to "help.*" receive this instantly
```

### Example 3: Claim Work Item

**Bash Script:**
```bash
#!/bin/bash
# Session sees work item, claims it

curl -X POST http://localhost:8450/work/claim \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-3",
    "work_id": "deploy-dashboard",
    "work_description": "Deploy dashboard to production server"
  }'

# NEXUS broadcasts "work.claimed" event to all sessions
# Other sessions know work is taken
```

### Example 4: Session Discovery

**Python:**
```python
import httpx

# Find sessions capable of Python development
response = httpx.get(
    "http://localhost:8450/sessions/capabilities",
    params={"skill": "python", "available": "true"}
)

matches = response.json()["matches"]
for session in matches:
    print(f"Session {session['session_id']}: {session['role']}")
    print(f"  Capabilities: {', '.join(session['capabilities'])}")
```

---

## 🔄 INTEGRATION POINTS

### Registry (8000)
- Register NEXUS on startup
- Query for other service endpoints
- Update service status

### SSOT.json
- Read current session state
- Write updates on events
- Maintain consistency

### claude_sessions.json
- Read session registry
- Update current_work fields
- Validate session tokens

### Unified Chat (8100)
- NEXUS can relay events to unified-chat
- Unified-chat can publish commands via NEXUS
- Bidirectional integration

---

## 🎯 FUTURE ENHANCEMENTS

**Phase 2:**
- Redis backend for persistent event storage
- Event replay from disk (survive restarts)
- Advanced routing (priority queues, load balancing)
- GraphQL subscription API
- Web dashboard for monitoring

**Phase 3:**
- Cross-machine coordination (multi-server)
- Event analytics and insights
- AI-powered work matching
- Integration with external tools (Slack, Discord)

---

## ✅ ACCEPTANCE CRITERIA

**Service is complete when:**

- [ ] All 5 UDC endpoints implemented and verified
- [ ] WebSocket server accepts 20+ concurrent connections
- [ ] Events published via WebSocket/HTTP reach subscribers < 100ms
- [ ] Pub/sub topic filtering works with wildcards
- [ ] Work claim/release prevents conflicts
- [ ] SSOT.json auto-syncs on state changes
- [ ] Event history stores last 1000 events
- [ ] Session discovery finds by capability
- [ ] Service auto-registers with Registry
- [ ] All unit tests pass (> 80% coverage)
- [ ] Integration tests pass (2+ sessions coordinating)
- [ ] Performance tests show < 100ms latency p99
- [ ] Documentation complete (README, API docs)

---

## 📝 NOTES

**Design Philosophy:**
- Event-driven, not polling-based
- Real-time first, files second (SSOT is sync target)
- Simple pub/sub model (no complex message queues)
- Stateless where possible (sessions reconnect easily)

**Trade-offs:**
- In-memory storage (fast but not persistent) - acceptable for v1
- Localhost only initially (no SSL) - production can add later
- Limited event history (1000 events) - prevents memory bloat

**Inspiration:**
- Redis Pub/Sub simplicity
- Socket.io real-time model
- NATS messaging patterns

---

**SPEC Quality Score Target:** 90+
**Ready for Build:** Pending verification
