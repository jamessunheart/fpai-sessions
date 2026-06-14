# autonomous-executor - SPECS

**Created:** 2025-11-15
**Status:** MVP (Droplet #20)
**Port:** 8400

---

## Purpose

Enables true self-optimization by accepting architect intent and executing the entire Sacred Loop autonomously from intent to deployment. Eliminates manual copy-paste commands and enables the system to build itself without human intervention in the loop.

---

## Requirements

### Functional Requirements
- [ ] Accept architect intent via API (text description of what to build)
- [ ] Generate detailed SPEC using Claude API
- [ ] Create repository structure (coordinator step)
- [ ] Generate complete service code using Claude API (apprentice step)
- [ ] Run tests and verification automatically
- [ ] Deploy to production server
- [ ] Register service with Registry
- [ ] Track build progress with real-time status updates
- [ ] Support approval modes: auto (full autonomy), checkpoints (guided), final (review before deploy)
- [ ] Stream progress via WebSocket
- [ ] Retry failed steps with auto-recovery
- [ ] Maximum 10 retry attempts per step
- [ ] UDC compliance endpoints (health, capabilities)

### Non-Functional Requirements
- [ ] Performance: SPEC generation < 2 minutes, full build < 2 hours
- [ ] Reliability: Retry logic for all external API calls, graceful failure handling
- [ ] Progress tracking: Real-time updates via WebSocket and status endpoint
- [ ] Concurrency: Support multiple concurrent builds (queue-based)
- [ ] Persistence: Database storage for build state (planned: SQLite/PostgreSQL)

---

## API Specs

### Endpoints

**POST /executor/build-droplet**
- **Purpose:** Submit architect intent to build new droplet
- **Input:** JSON with architect_intent, optional droplet_id, droplet_name, approval_mode, auto_deploy
- **Output:** build_id, status, estimated_completion, stream_url, status_url
- **Success:** 202 Accepted
- **Errors:** 400 if invalid input, 500 if job creation fails

**GET /executor/builds/{build_id}/status**
- **Purpose:** Get current status of build job
- **Input:** build_id
- **Output:** Build status, current_phase, progress_percent, estimated_time_remaining
- **Success:** 200 OK
- **Errors:** 404 if build not found

**WS /executor/builds/{build_id}/stream**
- **Purpose:** WebSocket stream of real-time build progress
- **Input:** build_id (in URL)
- **Output:** Stream of progress events (phase_start, phase_progress, phase_complete, error)
- **Success:** WebSocket connection
- **Errors:** 404 if build not found

**GET /executor/builds**
- **Purpose:** List all build jobs
- **Input:** Optional filters (status, date_range)
- **Output:** Array of build job summaries
- **Success:** 200 OK
- **Errors:** 500 if query fails

**POST /executor/builds/{build_id}/approve**
- **Purpose:** Approve a build at checkpoint or for final deployment
- **Input:** build_id, approved (boolean), notes
- **Output:** Approval result, next steps
- **Success:** 200 OK
- **Errors:** 404 if build not found, 409 if not awaiting approval

**POST /executor/builds/{build_id}/cancel**
- **Purpose:** Cancel an in-progress build
- **Input:** build_id
- **Output:** Cancellation confirmation
- **Success:** 200 OK
- **Errors:** 404 if build not found, 409 if already completed

**GET /executor/health**
- **Purpose:** UDC health check
- **Input:** None
- **Output:** {"status": "healthy", "active_builds": 2, "claude_api": "connected"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

**GET /executor/capabilities**
- **Purpose:** UDC capabilities endpoint
- **Input:** None
- **Output:** Supported approval modes, max concurrent builds, Claude model info
- **Success:** 200 OK
- **Errors:** 500 if unavailable

### Data Models

```python
class BuildRequest:
    architect_intent: str
    droplet_id: Optional[int]
    droplet_name: Optional[str]
    approval_mode: str  # "auto", "checkpoints", "final"
    auto_deploy: bool = True

class BuildPhase:
    phase_name: str  # "SPEC Generation", "Package", "Build", "Verify", "Deploy", "Register"
    status: str  # "pending", "running", "completed", "failed", "skipped"
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    progress_percent: int
    details: dict
    error: Optional[str]

class BuildJob:
    build_id: str
    architect_intent: str
    droplet_id: Optional[int]
    droplet_name: str
    approval_mode: str
    status: str  # "queued", "running", "awaiting_approval", "completed", "failed", "cancelled"
    current_phase: str
    progress_percent: int
    phases: List[BuildPhase]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    final_decision: Optional[str]
    deployment_url: Optional[str]
    error: Optional[str]

class ProgressEvent:
    event_type: str  # "phase_start", "phase_progress", "phase_complete", "error"
    build_id: str
    phase_name: str
    progress_percent: int
    message: str
    timestamp: datetime
    data: Optional[dict]
```

---

## Dependencies

### External Services
- Claude API (Anthropic): SPEC generation, code generation, decision making
- Verifier (Port 8200): Service verification
- Auto-Fix Engine (Port 8300): Auto-fixing failed verifications
- Deployer (Port 8007): Production deployment
- Registry (Port 8000): Service registration

### APIs Required
- Anthropic Claude API: For SPEC and code generation
- Verifier API: POST /verify, GET /verify/{job_id}
- Auto-Fix API: POST /fix (optional, for auto-recovery)
- Deployer API: POST /deploy
- Registry API: POST /register

### Data Sources
- Foundation Files: Templates and base code
- Sacred Loop scripts: For orchestration
- Git repository: For version control

---

## Success Criteria

How do we know this works?

- [ ] Accepts architect intent via API
- [ ] Generates valid SPEC using Claude API
- [ ] Creates complete repository structure
- [ ] Generates working code using Claude API
- [ ] Tests pass on first attempt OR auto-fix resolves issues
- [ ] Deploys successfully to server
- [ ] Registers with Registry
- [ ] Progress tracking works in real-time
- [ ] WebSocket streaming functions correctly
- [ ] All approval modes work as expected
- [ ] Error recovery and retry logic prevents permanent failures
- [ ] Complete at least 1 full autonomous build from intent to deployment

---

## Sacred Loop Automation

### Step-by-Step Automation

**Step 1: Intent (API)**
- User submits architect_intent via POST /executor/build-droplet
- System creates build job with unique build_id

**Step 2: SPEC Generation (Claude API)**
- Claude generates detailed SPEC based on intent
- SPEC saved to repository
- If approval_mode = checkpoints: Wait for human approval

**Step 3: Package (Coordinator)**
- Create repository structure
- Copy Foundation Files
- Initialize git repository

**Step 4: Build (Claude API)**
- Claude generates complete code (main.py, models.py, tests, Dockerfile, etc.)
- Write files to repository
- This is the breakthrough: Programmatic code generation

**Step 5: Verify (Verifier API)**
- Submit to Verifier
- Wait for verification results
- If FIXES_REQUIRED and auto_deploy: Trigger Auto-Fix Engine

**Step 6: Deploy (Deployer API)**
- Submit to Deployer
- Deployer handles SSH, Docker, health checks
- If approval_mode = final: Wait for human approval before deploying

**Step 7: Register (Registry API)**
- Register service with Registry
- Update service directory

**Step 8: Complete**
- Notify architect of completion
- Return deployment URL and status

---

## Approval Modes

### Auto Mode (Full Autonomy)
- No human intervention required
- System makes all decisions
- Builds, tests, deploys automatically
- Best for: Well-defined services, trusted process

### Checkpoints Mode (Guided Autonomy)
- Human approves after SPEC generation
- Human approves before deployment
- System executes between checkpoints
- Best for: Important services, learning the system

### Final Mode (Review Before Deploy)
- System builds and tests autonomously
- Human approves final deployment
- Best for: Production systems, risk mitigation

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8400
- **Resource limits:**
  - Memory: 1GB max
  - CPU: 2 cores (for parallel Claude API calls)
  - Storage: 5GB for build artifacts
- **Response time:** SPEC generation < 2 min, full build < 2 hours
- **Concurrency:** Max 3 concurrent builds
- **Claude API:** Uses claude-sonnet-4-5-20250929, max 4096 tokens per request
- **Timeout:** 2 hours per build job
- **Persistence:** In-memory (v1), database (v2)

---

## Time Savings

**Before:** 3-4 hours architect hands-on time per droplet
- Manual SPEC writing: 30-60 min
- Manual coding: 2-3 hours
- Manual testing: 30 min
- Manual deployment: 30 min

**After:** 5 minutes architect time (submit intent + review result)
- SPEC generation: 2 min (autonomous)
- Code generation: 10-30 min (autonomous)
- Testing: 3-5 min (autonomous)
- Deployment: 2-5 min (autonomous)

**Time Savings: 95%+**

---

**Next Step:** Complete database persistence, test with real build, integrate with all Sacred Loop services
