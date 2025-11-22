# BUILD-EXECUTOR - Technical Specification

**Service Name:** build-executor
**Version:** 1.0.0



---

## Purpose

Build assembly line that takes validated SPECs and executes the complete build → test → verify → deploy → register pipeline with rollback capabilities. This is the "execution engine" that transforms SPECs into running production services.

---

## Capabilities

This service provides the following capabilities as part of the FPAI droplet mesh:

### Primary Functions

See 'Core Capabilities' section below for detailed descriptions.

## Core Capabilities

- **Code Generation:** Generate complete service code from SPEC
- **Test Generation:** Create unit and integration tests automatically
- **Build Automation:** Package service with dependencies
- **UDC Verification:** Validate all 5 UDC endpoints
- **Deployment:** Deploy to local + production environments
- **Registry Integration:** Auto-register deployed services
- **Health Verification:** Confirm service is operational
- **Rollback:** Automatic rollback on deployment failure
- **Artifact Management:** Store build artifacts and logs

---

## UDC Endpoints (5/5)

### 1. GET /health
**Returns:** Service health status
Service health status
```json
{
  "status": "active",
  "service": "build-executor",
  "version": "1.0.0",
  "timestamp": "2025-11-16T00:00:00Z",
  "active_builds": 2,
  "claude_api": "connected"
}
```

### 2. GET /capabilities
**Returns:** Service capabilities and metadata
Service capabilities
```json
{
  "version": "1.0.0",
  "features": [
    "code_generation",
    "test_generation",
    "build_automation",
    "udc_verification",
    "deployment",
    "rollback"
  ],
  "dependencies": [
    "registry",
    "verifier",
    "orchestrator"
  ],
  "udc_version": "1.0",
  "metadata": {
    "max_concurrent_builds": 3,
    "supported_languages": ["python"],
    "deployment_targets": ["local", "production"],
    "claude_model": "claude-sonnet-4-5-20250929"
  }
}
```

### 3. GET /state
**Returns:** Current service state and metrics
Current service state
```json
{
  "uptime_seconds": 86400,
  "requests_total": 50,
  "errors_last_hour": 1,
  "last_restart": "2025-11-16T00:00:00Z",
  "active_builds": 2,
  "queued_builds": 1,
  "completed_today": 8,
  "failed_today": 1
}
```

### 4. GET /dependencies
**Returns:** Service dependency status
Dependency status
```json
{
  "required": [
    {"name": "registry", "status": "available", "url": "http://localhost:8000"},
    {"name": "verifier", "status": "available", "url": "http://localhost:8200"}
  ],
  "optional": [
    {"name": "orchestrator", "status": "available", "url": "http://localhost:8001"}
  ],
  "missing": []
}
```

### 5. POST /message
**Returns:** Message acknowledgment
Inter-droplet messaging
```json
{
  "trace_id": "uuid",
  "source": "sovereign-factory",
  "target": "build-executor",
  "message_type": "command",
  "payload": {
    "action": "build",
    "spec_path": "/path/to/SPEC.md"
  },
  "timestamp": "2025-11-16T00:00:00Z"
}
```

---

## Service Endpoints

### POST /builds/submit
Submit new build from SPEC
```json
// Request
{
  "spec_path": "/Users/jamessunheart/Development/agents/services/payment-processor/SPEC.md",
  "approval_mode": "auto",
  "deploy_local": true,
  "deploy_production": false,
  "auto_register": true
}

// Response
{
  "build_id": "uuid",
  "status": "queued",
  "queue_position": 1,
  "estimated_start": "2025-11-16T01:00:00Z",
  "status_url": "/builds/{build_id}/status",
  "stream_url": "ws://localhost:8211/builds/{build_id}/stream"
}
```

### GET /builds/{build_id}/status
Get build status
```json
{
  "build_id": "uuid",
  "service_name": "payment-processor",
  "status": "building",
  "current_phase": "code_generation",
  "progress_percent": 35,
  "phases": {
    "queued": {"status": "completed", "duration_seconds": 5},
    "code_generation": {"status": "running", "progress": 35},
    "test_generation": {"status": "pending"},
    "build": {"status": "pending"},
    "verification": {"status": "pending"},
    "deployment": {"status": "pending"},
    "registration": {"status": "pending"},
    "health_check": {"status": "pending"}
  },
  "spec_path": "/path/to/SPEC.md",
  "artifacts": [],
  "estimated_completion": "2025-11-16T01:45:00Z"
}
```

### GET /builds
List all builds with filters
```json
// Query params: ?status=running&service_name=payment-processor&limit=20
{
  "builds": [
    {
      "build_id": "uuid",
      "service_name": "payment-processor",
      "status": "building",
      "current_phase": "code_generation",
      "progress_percent": 35,
      "created_at": "2025-11-16T01:00:00Z"
    }
  ],
  "total": 30,
  "queued": 1,
  "running": 2,
  "completed": 25,
  "failed": 2
}
```

### POST /builds/{build_id}/approve
Approve build at checkpoint
```json
// Request
{
  "approved": true,
  "notes": "Code looks good, proceed with deployment"
}

// Response
{
  "build_id": "uuid",
  "status": "running",
  "next_phase": "deployment",
  "approval_recorded": "2025-11-16T01:30:00Z"
}
```

### POST /builds/{build_id}/cancel
Cancel in-progress build
```json
{
  "build_id": "uuid",
  "status": "cancelled",
  "cancelled_at": "2025-11-16T01:00:00Z",
  "cancellation_reason": "User requested"
}
```

### POST /builds/{build_id}/rollback
Rollback failed deployment
```json
{
  "build_id": "uuid",
  "rollback_status": "success",
  "previous_version_restored": true,
  "service_health": "active"
}
```

### WS /builds/{build_id}/stream
WebSocket stream of build progress
```json
// Example events
{
  "event_type": "phase_start",
  "build_id": "uuid",
  "phase": "code_generation",
  "timestamp": "2025-11-16T01:05:00Z"
}

{
  "event_type": "progress",
  "build_id": "uuid",
  "phase": "code_generation",
  "progress_percent": 50,
  "message": "Generated main.py and models.py",
  "timestamp": "2025-11-16T01:10:00Z"
}

{
  "event_type": "phase_complete",
  "build_id": "uuid",
  "phase": "code_generation",
  "duration_seconds": 180,
  "timestamp": "2025-11-16T01:15:00Z"
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
- **AI:** Claude API (Anthropic) for code generation
- **Queue:** Async background tasks (asyncio)
- **Database:** SQLite (local), PostgreSQL (production)
- **WebSocket:** Real-time progress streaming
- **Docker:** Service containerization (v2)

### Build Pipeline Phases

```
Phase 1: Code Generation
  ├─ Parse SPEC
  ├─ Generate main.py (FastAPI app)
  ├─ Generate models.py (Pydantic models)
  ├─ Generate config.py
  ├─ Generate requirements.txt
  └─ Generate README.md

Phase 2: Test Generation
  ├─ Generate unit tests (pytest)
  ├─ Generate integration tests
  └─ Generate UDC endpoint tests

Phase 3: Build
  ├─ Create virtual environment
  ├─ Install dependencies
  ├─ Run linters (optional)
  └─ Run tests

Phase 4: Verification
  ├─ Start service locally
  ├─ Test all 5 UDC endpoints
  ├─ Run verifier service check
  └─ Stop service

Phase 5: Deployment
  ├─ Deploy local (if requested)
  ├─ Deploy production (if requested)
  ├─ SSH to production server
  ├─ Transfer files
  ├─ Install dependencies
  └─ Start service

Phase 6: Registration
  ├─ Register with Registry
  ├─ Verify registration
  └─ Update service directory

Phase 7: Health Check
  ├─ Wait for startup (30s)
  ├─ Test /health endpoint
  ├─ Verify status = "active"
  └─ Complete build

Rollback (on failure):
  ├─ Stop new service
  ├─ Restore previous version
  ├─ Restart previous service
  └─ Verify health
```

### Approval Modes
- **auto:** Full automation, no checkpoints
- **checkpoints:** Approve after code gen, before deploy
- **final:** Approve only before deployment

---

## Data Models

```python
class BuildRequest(BaseModel):
    spec_path: str
    approval_mode: str = "auto"  # auto, checkpoints, final
    deploy_local: bool = True
    deploy_production: bool = False
    auto_register: bool = True
    metadata: dict = {}

class BuildJob(BaseModel):
    build_id: str
    service_name: str
    spec_path: str
    approval_mode: str
    status: str  # queued, running, awaiting_approval, completed, failed, cancelled
    current_phase: str
    progress_percent: int
    phases: Dict[str, PhaseStatus]
    artifacts: List[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    deployment_urls: Dict[str, str]  # {"local": "http://localhost:8350", "production": "http://..."}
    error: Optional[str]
    rollback_available: bool

class PhaseStatus(BaseModel):
    status: str  # pending, running, completed, failed, skipped
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    progress: int = 0
    details: dict = {}
    error: Optional[str]
    retry_count: int = 0
```

---

## Code Generation Prompts

### Main Service Code
```
Generate a FastAPI service implementing the following SPEC:
{SPEC_CONTENT}

Requirements:
- All 5 UDC endpoints (/health, /capabilities, /state, /dependencies, /message)
- All business endpoints from SPEC
- Pydantic models for request/response
- Error handling and validation
- Auto-registration with Registry on startup
- Logging and monitoring
- Following Python best practices

Generate main.py, models.py, config.py
```

### Test Code
```
Generate comprehensive tests for the service defined in:
{SPEC_CONTENT}

Generate:
- Unit tests for all endpoints
- Integration tests for workflows
- UDC compliance tests
- Mock dependencies where needed
- Use pytest framework

Generate tests/test_main.py, tests/test_integration.py
```

---


## File Structure

```
build-executor/
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
- **registry** (8000) - Service registration
- **verifier** (8200) - UDC compliance verification

### Optional Services
- **orchestrator** (8001) - Task coordination

### External APIs
- **Anthropic Claude API:** Code generation
- **SSH:** Production deployment

---

## Deployment

```bash
# Local
cd /Users/jamessunheart/Development/agents/services/build-executor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=your-key" > .env
uvicorn app.main:app --host 0.0.0.0 --port 8211

# Production
docker build -t fpai-build-executor .
docker run -d --name build-executor \
  -p 8211:8211 \
  -v /opt/fpai/data:/app/data \
  -v /opt/fpai/builds:/app/builds \
  --env-file .env \
  fpai-build-executor
```

---

## Success Criteria

- [ ] Accept SPEC and generate complete service code
- [ ] Generate working unit and integration tests
- [ ] Build service with all dependencies
- [ ] Verify UDC compliance (all 5 endpoints)
- [ ] Deploy to local environment
- [ ] Deploy to production environment (when requested)
- [ ] Auto-register with Registry
- [ ] Health check confirms service operational
- [ ] Rollback works on deployment failure
- [ ] Real-time progress via WebSocket
- [ ] Complete 5+ successful builds
- [ ] 90%+ build success rate
- [ ] Average build time < 45 minutes

---

## Performance Targets

- **Code Generation:** < 5 minutes
- **Test Generation:** < 2 minutes
- **Build Time:** < 5 minutes
- **Verification:** < 2 minutes
- **Deployment:** < 5 minutes (local), < 10 minutes (production)
- **Total Pipeline:** < 30 minutes (avg)
- **Concurrent Builds:** 3 simultaneous
- **API Response Time:** < 200ms
- **Uptime:** 99.5%

---

## Error Handling

### Retry Strategy
- **Code Generation Failure:** Retry with refined prompt (up to 3 times)
- **Build Failure:** Attempt auto-fix, then retry (up to 2 times)
- **Test Failure:** Review test code, regenerate if needed
- **Deployment Failure:** Rollback, retry with validated code
- **Health Check Failure:** Wait 60s, retry, then rollback

### Error States
- **failed_code_generation:** Claude API error or invalid code
- **failed_build:** Dependency or syntax errors
- **failed_verification:** UDC endpoints missing or broken
- **failed_deployment:** SSH, Docker, or startup errors
- **failed_health_check:** Service started but not responding

---

## Rollback Process

When deployment fails:
1. Stop new service instance
2. Identify previous version (if exists)
3. Restore previous version files
4. Restart previous service
5. Verify health of restored service
6. Update Registry with rollback status
7. Notify sovereign-factory of failure
8. Archive failed build artifacts for debugging

---

## Integration Examples

### Submit Build
```bash
curl -X POST http://localhost:8211/builds/submit \
  -H "Content-Type: application/json" \
  -d '{
    "spec_path": "/Users/jamessunheart/Development/agents/services/payment-processor/SPEC.md",
    "approval_mode": "auto",
    "deploy_local": true,
    "deploy_production": false
  }'
```

### Monitor Build
```bash
# Get status
curl http://localhost:8211/builds/{build_id}/status | python3 -m json.tool

# Stream progress (WebSocket)
wscat -c ws://localhost:8211/builds/{build_id}/stream
```

### Approve Checkpoint
```bash
curl -X POST http://localhost:8211/builds/{build_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "notes": "Looks good!"}'
```

---

## Future Enhancements

- **Docker Support:** Containerized builds and deployments
- **Multi-Language:** Support for TypeScript, Go, Rust
- **Parallel Testing:** Run tests concurrently
- **Canary Deployment:** Gradual rollout with monitoring
- **A/B Testing:** Deploy multiple versions
- **Cost Tracking:** Track Claude API costs per build
- **Build Caching:** Reuse unchanged dependencies
- **Blue-Green Deployment:** Zero-downtime deployments

---

**The execution engine that brings SPECs to life - code → test → verify → deploy → live!**
