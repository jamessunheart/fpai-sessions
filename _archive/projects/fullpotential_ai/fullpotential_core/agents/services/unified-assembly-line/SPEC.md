# unified-assembly-line - SPEC

**Created:** 2025-11-15
**Status:** SPEC Phase
**Port:** 8950

---

## Purpose

Synchronizes build pipeline across Claude Code and Server AI environments with a unified intent queue, shared assembly line state, and protocol enforcement - enabling seamless cross-environment work distribution and automated build progression.

---

## Requirements

### Functional Requirements
- [ ] Accept build intents via API from both Claude Code and Server AI
- [ ] Maintain unified intent queue accessible to all executors
- [ ] Track assembly line state (SPEC → BUILD → TEST → PRODUCTION phases)
- [ ] Enforce Assembly Line SOP protocol at each phase transition
- [ ] Enforce Verification Protocol before allowing phase advancement
- [ ] Distribute work intelligently to available executors (Claude or Server AI)
- [ ] Provide real-time dashboard showing pipeline state
- [ ] Support both environments pulling work from shared queue
- [ ] Update progress from executors in real-time
- [ ] Auto-advance intents through phases when quality gates pass
- [ ] Register and track executor status (Claude sessions and Server AI)
- [ ] Provide WebSocket for real-time updates

### Non-Functional Requirements
- [ ] Performance: API response time < 200ms
- [ ] Performance: WebSocket updates < 500ms latency
- [ ] Reliability: 99.9% uptime (critical infrastructure)
- [ ] Scalability: Support 50+ concurrent executors
- [ ] Scalability: Handle 100+ intents in queue
- [ ] Data persistence: PostgreSQL for intent history
- [ ] Real-time state: Redis for live executor status
- [ ] Security: Authentication for API access
- [ ] Security: Authorization by executor role
- [ ] Monitoring: Prometheus metrics endpoint
- [ ] Logging: Structured logs for all state changes

---

## API Specs

### Endpoints

**POST /assembly-line/intent**
- Description: Submit new build intent to unified queue
- Body: `{"title": "string", "spec_path": "string", "priority": 1-10, "environment_preference": "server|local|either"}`
- Returns: `{"intent_id": "string", "status": "queued", "estimated_start": "ISO datetime"}`
- Status: 201 Created on success

**GET /assembly-line/work/next?executor_id={id}**
- Description: Get next work item for executor (pulls from queue)
- Parameters: `executor_id` (required) - session ID or "server-ai"
- Returns: `{"intent": {...}, "assigned": true}` or `{"assigned": false}` if no work
- Status: 200 OK

**POST /assembly-line/work/progress**
- Description: Update progress on assigned work
- Body: `{"intent_id": "string", "executor_id": "string", "phase": "string", "progress": 0.0-1.0, "message": "string"}`
- Returns: `{"updated": true, "current_state": "string"}`
- Status: 200 OK

**POST /assembly-line/work/complete**
- Description: Mark work as complete, advance to next phase
- Body: `{"intent_id": "string", "executor_id": "string", "status": "completed", "artifacts": {}}`
- Returns: `{"completed": true, "auto_advanced": bool, "next_phase": "string"}`
- Status: 200 OK

**POST /assembly-line/verify**
- Description: Run verification protocol checks
- Body: `{"intent_id": "string", "verification_level": 1-6, "phase": "string"}`
- Returns: `{"passed": bool, "level": int, "checks": {...}, "can_advance": bool}`
- Status: 200 OK

**GET /assembly-line/state**
- Description: Get current assembly line state
- Returns: `{"queue_depth": int, "in_progress": int, "executors": {...}, "metrics": {...}}`
- Status: 200 OK

**GET /assembly-line/dashboard**
- Description: Serve real-time HTML dashboard
- Returns: HTML page with WebSocket connection
- Status: 200 OK

**GET /health**
- Description: Health check endpoint
- Returns: `{"status": "ok", "service": "unified-assembly-line", "version": "1.0.0", "timestamp": "ISO datetime"}`
- Status: 200 OK

### Data Models

```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class BuildIntent(BaseModel):
    """An intent to build a service"""
    id: str
    title: str
    spec_path: str
    priority: int  # 1-10

    created_by: str
    created_at: datetime

    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None

    environment_preference: str  # "server" | "local" | "either"
    requires_human_review: bool = False

    status: str  # "queued" | "assigned" | "in_progress" | "testing" | "completed" | "failed"
    current_phase: str  # "spec" | "build" | "test" | "production"

    phase_progress: Dict[str, float] = {}
    build_output: Optional[str] = None
    test_results: Optional[Dict] = None
    deployment_url: Optional[str] = None

    verification_level: int = 0  # 0-6
    quality_score: Optional[float] = None

class ExecutorStatus(BaseModel):
    """Status of a build executor"""
    executor_id: str
    executor_type: str  # "claude_code" | "server_ai"
    environment: str  # "local" | "server"

    status: str  # "idle" | "busy" | "offline"
    current_work: Optional[str] = None

    capabilities: List[str] = []
    availability: str  # "always" | "when_active"

    builds_completed: int = 0
    avg_build_time: float = 0.0
    success_rate: float = 1.0

    last_heartbeat: datetime
    is_healthy: bool = True

class AssemblyLineState(BaseModel):
    """Overall assembly line state"""
    intent_queue: List[BuildIntent]
    in_progress: List[BuildIntent]
    completed: List[BuildIntent]
    failed: List[BuildIntent]

    executors: Dict[str, ExecutorStatus]

    metrics: Dict[str, Any]
    last_sync: datetime
```

---

## Dependencies

### Required Services
- **PostgreSQL** - Persistent storage for intent queue, build history
- **Redis** - Real-time state, executor status, caching
- **credential-vault** (Port 8XXX) - For API authentication tokens

### Required APIs
- **None** - Service is self-contained

### Required Infrastructure
- **Server** - 198.54.123.234 for deployment
- **Docker** - Containerization
- **Port 8950** - Must be available

### Integration Points
- **Autonomous Executor** (Port 8400) - Connects as executor to pull work
- **Claude Code Sessions** - Connect via assembly-line-client library
- **Dashboard** (Port 8103) - Can embed assembly line status
- **Service Registry** (Port 8000) - Register this service

---

## Success Criteria

**Phase 1: SPEC → BUILD**
- [x] All required sections complete in SPEC.md
- [x] API endpoints fully documented (8 endpoints)
- [x] Data models defined with types (3 models: BuildIntent, ExecutorStatus, AssemblyLineState)
- [x] Dependencies identified (PostgreSQL, Redis, credential-vault)
- [x] Success criteria defined with checkboxes

**Phase 2: BUILD → TEST**
- [ ] Service starts without errors
- [ ] All API endpoints return expected responses
- [ ] PostgreSQL connection working
- [ ] Redis connection working
- [ ] WebSocket connection working
- [ ] Dashboard renders correctly

**Phase 3: TEST → PRODUCTION**
- [ ] All unit tests pass (>80% coverage)
- [ ] Intent queue operations working (submit, pull, update, complete)
- [ ] Work distribution logic working (routes to correct executor)
- [ ] Protocol enforcement working (blocks invalid phase transitions)
- [ ] Verification checks working (all 6 levels)
- [ ] Cross-environment sync working (Claude Code ↔ Server AI)
- [ ] Real-time updates working (WebSocket publishes state changes)
- [ ] Health endpoint returns 200
- [ ] UDC compliance passed (all 6 required endpoints)

**Phase 4: PRODUCTION**
- [ ] Deployed to 198.54.123.234:8950
- [ ] Registered in SERVICE_REGISTRY.json
- [ ] Dashboard accessible at https://fullpotential.com/assembly-line
- [ ] Both Claude Code and Server AI connected and pulling work
- [ ] At least 1 build completed end-to-end through all phases
- [ ] Monitoring configured (Prometheus metrics)
- [ ] Logs shipping to central logging
- [ ] 99.9% uptime for 7 days

---

## Compliance Notes

### Protocol Compliance
- **Assembly Line SOP** - This service ENFORCES the 4-phase process (SPEC → BUILD → README → PRODUCTION) for all builds
- **Verification Protocol** - This service ENFORCES the 6-level verification before phase transitions
- **UDC Compliance** - This service must implement all 6 UDC endpoints itself

### Legal/Regulatory
- **No user data stored** - Only build metadata (specs, status, executor info)
- **No AI-generated legal content** - Service facilitates builds, doesn't generate legal advice
- **Educational infrastructure** - Part of ministry operations, not commercial product

### Security Considerations
- **Authentication required** - Only registered executors can pull work
- **Authorization by role** - Executors can only access work assigned to them
- **No credential storage** - Delegates to credential-vault service
- **Audit logging** - All state changes logged for accountability

### Operational Constraints
- **Single Point of Failure** - This service becomes critical infrastructure once deployed
  - Mitigation: High availability deployment with failover
  - Mitigation: Redis backup for state recovery
  - Mitigation: PostgreSQL replication for data persistence
- **Network dependency** - Both environments must reach server
  - Mitigation: Graceful degradation if connection lost
  - Mitigation: Local caching in executors

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8950
- **Resource Limits:**
  - Memory: 512MB max
  - CPU: 1 core
  - Storage: 10GB for PostgreSQL data
- **Response Time:** < 200ms for API calls
- **WebSocket Latency:** < 500ms for updates
- **Database:** PostgreSQL 15+
- **Cache:** Redis 7+
- **Concurrent Connections:** Support 100+ WebSocket connections
- **Queue Depth:** Support 1000+ intents in queue

---

## Next Steps

**After SPEC Complete:**
1. Review with architect (Session #12) and user
2. Create BUILD/ directory structure
3. Assign to builder (Server AI or Claude session)
4. Follow Assembly Line SOP for BUILD phase
5. Implement according to this spec
6. Write tests covering all success criteria
7. Deploy to production
8. Connect both environments
9. Migrate existing specs to unified queue

**Estimated Build Time:** 8-10 hours

**Estimated Test Time:** 2 hours

**Estimated Deploy Time:** 1 hour

**Total Time to Production:** 11-13 hours

---

**SPEC Status:** ✅ **COMPLETE** - Ready for BUILD phase

**Last Updated:** 2025-11-15 by Session #12 (Chief Architect)
