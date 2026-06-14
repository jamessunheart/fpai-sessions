# TIER 0 + TIER 1 UDC Retrofit Specifications

**Session Date:** 2025-11-15
**Status:** All services 100% UDC compliant and operational
**Total Services:** 6 (4 TIER 0 + 2 TIER 1)

---

## TIER 0: Infrastructure Spine (4 Services)

### 1. Registry (Port 8000)

**Status:** ✅ Already UDC compliant (no changes needed)
**Location:** `/Users/jamessunheart/Development/SERVICES/registry/`

**Purpose:**
- Single Source of Truth (SSOT) for all droplets in the mesh
- Service registration and discovery
- Droplet identity management
- Status tracking

**UDC Endpoints (5/5):**
- `/health` - Health check with status tracking
- `/capabilities` - Service registration, discovery, identity management
- `/state` - Uptime and performance metrics
- `/dependencies` - No dependencies (root service)
- `/message` - Inter-droplet messaging

**Key Files:**
- `app/main.py` - All UDC endpoints already implemented (lines 88-171)
- `app/models.py` - Pydantic models for UDC compliance

**Features:**
- Auto-discovery of droplets
- JWT token management
- Endpoint directory
- Service status tracking
- Metadata storage per droplet

**Optimization Opportunities:**
- Add persistent storage (currently in-memory)
- Add authentication for registration
- Add service health monitoring with auto-deregistration
- Add service versioning and compatibility checks

---

### 2. Orchestrator (Port 8001)

**Status:** ✅ Already UDC compliant (no changes needed)
**Location:** `/Users/jamessunheart/Development/SERVICES/orchestrator/`

**Purpose:**
- Central routing brain for task coordination
- Inter-droplet message routing
- Task distribution and load balancing
- Registry cache fallback

**UDC Endpoints (5/5):**
- `/orchestrator/health` - Health with registry connectivity status
- `/orchestrator/capabilities` - Task routing, messaging, registry sync
- `/orchestrator/state` - Active tasks, cache status
- `/orchestrator/dependencies` - Requires Registry
- `/orchestrator/message` - Message routing between droplets

**Key Files:**
- `app/main.py` - All UDC endpoints (lines 320-456)
- Auto-registration logic (lines 55-80)
- Registry sync on startup

**Features:**
- Auto-registers with Registry on startup
- Syncs droplet cache from Registry
- Task routing with retry logic
- Heartbeat collection
- Cache fallback when Registry unavailable

**Optimization Opportunities:**
- Add task prioritization
- Add task cancellation support
- Add distributed task queuing
- Add metrics collection for task performance
- Add rate limiting per droplet

---

### 3. Proxy Manager (Port 8101)

**Status:** ✅ Retrofitted to 100% UDC compliance
**Location:** `/Users/jamessunheart/Development/SERVICES/proxy-manager/`

**Changes Made:**
- ✅ Added `/message` endpoint (only missing endpoint)
- ✅ Added MessageRequest and MessageResponse models

**Purpose:**
- Automated NGINX reverse proxy management
- SSL certificate automation via Let's Encrypt
- Domain-to-service mapping
- Health check proxying

**UDC Endpoints (5/5):**
- `/proxy-manager/health` - NGINX and certbot status (line 415)
- `/proxy-manager/capabilities` - Proxy, SSL, registry sync (line 455)
- `/proxy-manager/state` - Uptime, proxy count, SSL stats (line 479)
- `/proxy-manager/dependencies` - NGINX, certbot, registry (line 496)
- `/proxy-manager/message` - **ADDED** (lines 532-560)

**Key Files Modified:**
- `app/models.py` - Added MessageRequest, MessageResponse (lines 129-147)
- `app/main.py` - Added /message endpoint and imports (lines 24-25, 532-560)

**Features:**
- NGINX config generation
- SSL certificate issuance/renewal
- Health check validation before proxy activation
- Sync from Registry to auto-configure proxies
- Supports custom domains per droplet

**Optimization Opportunities:**
- Add certificate expiry monitoring
- Add automatic renewal scheduling
- Add NGINX reload without downtime
- Add support for wildcard certificates
- Add proxy performance metrics

---

### 4. Verifier (Port 8200)

**Status:** ✅ Already 100% UDC compliant (no changes needed)
**Location:** `/Users/jamessunheart/Development/SERVICES/verifier/`

**Purpose:**
- Droplet verification and quality assurance
- UDC compliance testing
- Security scanning
- Functionality testing
- Code quality checks

**UDC Endpoints (5/5):**
- `/health` - Service status, job queue size (line 181)
- `/capabilities` - Verification types, testing tools (line 212)
- `/state` - Job statistics, queue metrics (line 239)
- `/dependencies` - pytest, python, registry (line 256)
- `/message` - Verification job commands (line 290)

**Key Files:**
- `app/main.py` - All endpoints already implemented
- Background job processing system
- Pytest integration for testing

**Features:**
- UDC compliance verification
- Security vulnerability scanning
- Functionality testing with pytest
- Structured JSON reports
- Async job queue management

**Optimization Opportunities:**
- Add Docker container testing
- Add performance benchmarking
- Add integration testing between droplets
- Add continuous verification scheduling
- Add verification result history/trends

---

## TIER 1: Sacred Loop + Recruitment (2 Services)

### 5. autonomous-executor (Port 8402)

**Status:** ✅ Retrofitted to 100% UDC compliance
**Location:** `/Users/jamessunheart/Development/SERVICES/autonomous-executor/`

**Changes Made:**
- ✅ Added 5 UDC endpoints (all were missing)
- ✅ Added UDC models (UDCHealthResponse, UDCCapabilitiesResponse, etc.)
- ✅ Fixed syntax error in retry_build function (line 191)
- ✅ Made anthropic_api_key optional for testing

**Purpose:**
- Autonomous Sacred Loop execution
- Accept architect intent → build complete droplet
- Spec generation via Claude API
- Code generation and deployment
- Auto-registration with Registry

**UDC Endpoints (5/5):**
- `/health` - **ADDED** Claude/GitHub API status (lines 269-289)
- `/capabilities` - **ADDED** Sacred Loop features (lines 292-318)
- `/state` - **ADDED** Build statistics, active builds (lines 321-344)
- `/dependencies` - **ADDED** Claude API, GitHub, Registry (lines 347-369)
- `/message` - **ADDED** Build commands, status queries (lines 372-399)

**Key Files Modified:**
1. `app/models.py`:
   - Added Dict, Any to imports (line 4)
   - Added UDC models (lines 119-177)

2. `app/main.py`:
   - Added UDC model imports (lines 25-31)
   - **Fixed bug:** Parameter order in retry_build (line 191)
   - Added 5 UDC endpoints (lines 269-399)

3. `app/config.py`:
   - Made anthropic_api_key Optional (line 15)

**Features:**
- Full Sacred Loop automation (intent → deployed droplet)
- SPEC generation with Claude
- Repository creation and structure
- Code generation for all files
- Test execution and verification
- Deployment to production
- WebSocket progress streaming
- Approval workflows (auto, checkpoints, final)
- Retry logic with step resumption

**Business Logic Endpoints (Non-UDC):**
- `POST /executor/build-droplet` - Start autonomous build
- `GET /executor/builds/{id}/status` - Build progress
- `WS /executor/builds/{id}/stream` - Real-time updates
- `POST /executor/builds/{id}/approve` - Approve checkpoint
- `POST /executor/builds/{id}/retry` - Retry failed build
- `DELETE /executor/builds/{id}` - Cancel build

**Optimization Opportunities:**
- Add parallel build support (multiple builds simultaneously)
- Add build templates/presets
- Add cost tracking per build
- Add build artifact storage
- Add rollback capability
- Add dependency caching for faster builds
- Add build queue prioritization
- Add Claude API rate limiting/retry logic

**Known Limitations:**
- Requires Claude API key for spec/code generation
- Requires GitHub token for deployment
- No persistent build history (in-memory only)
- WebSocket connections not load-balanced

---

### 6. jobs (Port 8008)

**Status:** ✅ Retrofitted to 100% UDC compliance
**Location:** `/Users/jamessunheart/Development/SERVICES/jobs/`

**Changes Made:**
- ✅ Created `app/udc_models.py` with all UDC models
- ✅ Updated `/health` endpoint to UDC standard (was returning "healthy" instead of "active")
- ✅ Added 4 missing UDC endpoints
- ✅ Fixed DATA_PATH filesystem error (changed from /app/data to local)

**Purpose:**
- Sovereign job board
- AI-powered candidate screening
- AI-conducted interviews
- Labor coordination
- Milestone verification
- Social media recruitment automation

**UDC Endpoints (5/5):**
- `/health` - **UPDATED** to UDC format (lines 69-77)
- `/capabilities` - **ADDED** AI screening, interviews, coordination (lines 80-100)
- `/state` - **ADDED** Uptime, active jobs (lines 103-116)
- `/dependencies` - **ADDED** Claude API, database, registry (lines 119-141)
- `/message` - **ADDED** Job commands, recruitment queries (lines 144-169)

**Key Files Modified/Created:**
1. `app/udc_models.py` - **CREATED NEW FILE**
   - All UDC-compliant models
   - MessageRequest/Response for inter-droplet messaging

2. `app/main.py`:
   - Added imports (lines 12-22)
   - Added start_time tracking (line 62)
   - Updated /health to UDC format (lines 69-77)
   - Added 4 new UDC endpoints (lines 80-169)

3. `app/routers/jobs_api.py`:
   - **Fixed bug:** Changed DATA_PATH from /app/data to local (line 22)

**Features:**
- Job posting and browsing
- Application submission
- AI screening (Claude-powered scoring)
- AI interview conductor
- Labor coordinator (daily check-ins, code review)
- Milestone verification with quality checklist
- Social media recruitment (Twitter, LinkedIn, Reddit)
- Helper onboarding materials generation
- Performance tracking and analytics

**Business Logic Endpoints (Non-UDC):**
- `GET /jobs` - Job board UI
- `POST /api/jobs` - Post new job
- `GET /api/jobs/{id}` - Job details
- `POST /api/jobs/{id}/apply` - Submit application
- `POST /api/jobs/{id}/screen` - AI screening
- `POST /api/jobs/{id}/interview` - AI interview

**Optimization Opportunities:**
- Add database persistence (currently file-based JSON)
- Add authentication/authorization
- Add email notifications
- Add Slack/Discord integration
- Add payment/escrow for job completion
- Add reputation system for helpers
- Add automated job posting from templates
- Add multi-language support
- Add analytics dashboard

**Known Limitations:**
- Data stored in JSON files (not scalable)
- No authentication (open access)
- No email integration (manual follow-up needed)
- Social media automation not yet implemented

---

## UDC Standard Compliance Summary

### All Services Implement:

**5 Required Endpoints:**
1. `GET /health` - Returns {"status": "active|inactive|error", "service": "name", "version": "x.x.x", "timestamp": "ISO8601"}
2. `GET /capabilities` - Returns {"version", "features": [], "dependencies": [], "udc_version": "1.0", "metadata": {}}
3. `GET /state` - Returns {"uptime_seconds", "requests_total", "errors_last_hour", "last_restart"}
4. `GET /dependencies` - Returns {"required": [], "optional": [], "missing": []}
5. `POST /message` - Accepts {"trace_id", "source", "target", "message_type": "status|event|command|query", "payload": {}, "timestamp"}

**Standard Response Model:**
```python
class UDCMessageResponse(BaseModel):
    received: bool = True
    trace_id: str
    processed_at: str
    result: Optional[str] = "success"
```

---

## Registry Integration

**All Services Can:**
- Register with Registry via `POST /register`
- Be discovered by other droplets
- Receive messages via UDC `/message` endpoint
- Report health via `/health`

**Currently Registered:**
1. orchestrator (ID: 2) - Auto-registered on startup
2. proxy-manager (ID: 3) - Manually registered
3. verifier (ID: 4) - Manually registered
4. autonomous-executor (ID: 5) - Manually registered
5. jobs (ID: 6) - Manually registered

---

## Next Steps for Optimization

### Priority 1: Auto-Registration
Add auto-registration on startup for all services (like Orchestrator):
```python
@app.on_event("startup")
async def register_with_registry():
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/register",
            json={"name": "service-name", "id": X, "url": "http://localhost:PORT", "version": "1.0.0"}
        )
```

### Priority 2: Health Monitoring
- Add periodic health checks from Registry
- Auto-deregister unhealthy services
- Add service restart notifications

### Priority 3: Metrics Collection
- Add request/response time tracking
- Add error rate monitoring
- Add resource usage metrics
- Dashboard for mesh health

### Priority 4: Message Routing
- Implement full message routing through Orchestrator
- Add message persistence/retry
- Add message tracing across services

### Priority 5: Security
- Add authentication between services
- Add message signing/verification
- Add rate limiting
- Add API key rotation

---

## Files Modified Summary

### TIER 0 (Proxy Manager only)
- `proxy-manager/app/models.py` - Added UDC message models
- `proxy-manager/app/main.py` - Added /message endpoint

### TIER 1 (Both services)
**autonomous-executor:**
- `app/models.py` - Added UDC models
- `app/main.py` - Added 5 UDC endpoints + bug fix
- `app/config.py` - Made API key optional

**jobs:**
- `app/udc_models.py` - Created new file with all UDC models
- `app/main.py` - Added imports + 5 UDC endpoints
- `app/routers/jobs_api.py` - Fixed DATA_PATH

---

## Testing Verification

**All services verified with:**
1. Health endpoint responding
2. UDC message acceptance (trace_id verification)
3. Registry registration successful
4. Service discovery working
5. Inter-service messaging functional

**Test Commands:**
```bash
# Check health
curl http://localhost:{PORT}/health | python3 -m json.tool

# Test messaging
curl -X POST http://localhost:{PORT}/message \
  -H "Content-Type: application/json" \
  -d '{"trace_id":"test","source":"test","target":"service","message_type":"status","timestamp":"2025-11-16T00:00:00Z","payload":{}}'

# Verify registration
curl http://localhost:8000/droplets | python3 -m json.tool
```

---

**End of Specifications**
