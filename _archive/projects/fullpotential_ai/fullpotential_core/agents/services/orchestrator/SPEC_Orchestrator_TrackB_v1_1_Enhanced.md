# SPEC: Orchestrator (Track B – Genesis Node)
## Enhanced Production Version v1.1

**Droplet ID:** B-2  
**Name:** Orchestrator  
**Location:** b.fullpotential.ai (same server as Registry)  
**Stack:** Python 3.11, FastAPI, Docker, docker compose, NGINX reverse proxy  
**Status:** New build (Track B – Enhanced)

---

## 1. INTENT

Create a central Orchestrator service that:
1. Receives tasks (jobs) via API
2. Knows which droplets exist (via Registry + local cache)
3. Routes tasks to the correct droplet endpoint with automatic retry
4. Tracks task status (queued, running, done, error)
5. Exposes metrics for system observability

This is the "traffic controller" for all Track B droplets on the Genesis server, designed for production reliability.

---

## 2. REQUIRED OUTCOMES

- REST API running at: `http://b.fullpotential.ai/orchestrator/...` (via NGINX → port 8001)
- Orchestrator can:
  1. List known droplets (from Registry, with local cache fallback)
  2. Register/update its own entry in Registry
  3. Accept tasks and route them to downstream droplets via HTTP
  4. Automatically retry failed tasks with exponential backoff
  5. Record task states in memory
  6. Expose health + metrics endpoints
  7. Return UDC-compliant error responses
  8. Gracefully degrade if Registry is temporarily unavailable

No background queue, DB, or pub/sub yet — keep it simple and in-process.

---

## 3. API DESIGN

**Base path:** `/orchestrator`

### 3.1 Health

```
GET /orchestrator/health
```

Response 200:
```json
{
  "status": "ok",
  "service": "orchestrator",
  "version": "1.1.0"
}
```

---

### 3.2 Self-info

```
GET /orchestrator/info
```

Returns orchestrator config and Registry status:

```json
{
  "id": 2,
  "name": "orchestrator",
  "version": "1.1.0",
  "registry_url": "http://localhost:8000",
  "registered": true,
  "last_registry_sync": 1731595000.123,
  "cache_status": "active|stale|unavailable",
  "cache_age_seconds": 45
}
```

---

### 3.3 Droplet map (from Registry with cache)

```
GET /orchestrator/droplets
```

Behavior:
1. Try to fetch from Registry: `GET http://localhost:8000/registry`
2. If successful: update cache, return droplets
3. If Registry unreachable and cache exists: return cached droplets with `cache_status: "stale"`
4. If both fail: return 503 with error

Returns normalized list:

```json
{
  "droplets": [
    {
      "id": 1,
      "name": "registry",
      "url": "http://localhost:8000",
      "version": "0.1.0"
    },
    {
      "id": 2,
      "name": "orchestrator",
      "url": "http://localhost:8001",
      "version": "1.1.0"
    }
  ],
  "cache_status": "active|stale",
  "served_from": "registry|cache"
}
```

---

### 3.4 Submit task (with automatic retry)

```
POST /orchestrator/tasks
```

Request body:

```json
{
  "droplet_name": "registry",
  "method": "GET",
  "path": "/health",
  "payload": null,
  "meta": {
    "requested_by": "architect",
    "reason": "test"
  }
}
```

Behavior:
1. Resolve droplet_name → droplet URL using droplet map (try Registry first, fallback to cache)
2. Construct target URL: `<droplet.url><path>` (e.g., `http://localhost:8000/health`)
3. Make HTTP request with given method + payload
4. **On failure: Auto-retry with exponential backoff** (1s, 2s, 4s max)
5. Store task record in memory with full lifecycle:

```json
{
  "id": "uuid4",
  "droplet_name": "registry",
  "target_url": "http://localhost:8000/health",
  "status": "success|error|timeout",
  "response_status": 200,
  "retry_count": 0,
  "created_at": 1731595000.1,
  "completed_at": 1731595000.3,
  "duration_ms": 200,
  "error_message": null
}
```

Response 200 (success):

```json
{
  "task_id": "uuid-here",
  "status": "success",
  "target_url": "http://localhost:8000/health",
  "response_status": 200,
  "response_body": {"status": "ok", "service": "registry"},
  "retry_count": 0,
  "duration_ms": 45
}
```

Response on failure (400/500):

```json
{
  "status": "error",
  "error": {
    "code": "DROPLET_UNREACHABLE|DROPLET_NOT_FOUND|TIMEOUT|INVALID_REQUEST",
    "message": "Failed to route task after 3 retries",
    "details": {
      "droplet_name": "registry",
      "target_url": "http://localhost:8000/health",
      "retry_count": 3,
      "last_error": "Connection refused",
      "duration_ms": 12000
    }
  }
}
```

---

### 3.5 List tasks

```
GET /orchestrator/tasks
```

Optional query params:
- `status` (queued|running|success|error|timeout)
- `droplet_name` (filter by target droplet)
- `limit` (default 100, max 1000)

Response:

```json
{
  "tasks": [
    {
      "id": "uuid",
      "droplet_name": "registry",
      "status": "success",
      "response_status": 200,
      "retry_count": 0,
      "created_at": 1731595000.1,
      "completed_at": 1731595000.3,
      "duration_ms": 200
    }
  ],
  "total": 42,
  "limit": 100
}
```

---

### 3.6 Get single task

```
GET /orchestrator/tasks/{task_id}
```

Returns full record including response_body if stored and response_status:

```json
{
  "id": "uuid",
  "droplet_name": "registry",
  "target_url": "http://localhost:8000/health",
  "method": "GET",
  "status": "success",
  "response_status": 200,
  "response_body": {"status": "ok", "service": "registry"},
  "retry_count": 0,
  "created_at": 1731595000.1,
  "completed_at": 1731595000.3,
  "duration_ms": 45
}
```

---

### 3.7 Metrics (NEW)

```
GET /orchestrator/metrics
```

Returns operational metrics for monitoring:

```json
{
  "service": "orchestrator",
  "version": "1.1.0",
  "uptime_seconds": 3600,
  "tasks": {
    "total": 250,
    "success": 238,
    "error": 8,
    "timeout": 4,
    "success_rate_percent": 95.2,
    "avg_response_time_ms": 234,
    "p95_response_time_ms": 1200,
    "p99_response_time_ms": 4500
  },
  "retry": {
    "total_retries": 12,
    "retry_success_count": 8,
    "retry_final_fail_count": 4
  },
  "registry": {
    "syncs_total": 145,
    "syncs_success": 143,
    "syncs_error": 2,
    "last_sync": 1731595000.1,
    "last_sync_duration_ms": 45,
    "cache_age_seconds": 30,
    "cache_status": "active"
  },
  "droplets_known": 5,
  "droplets_reachable": 5
}
```

---

## 4. INTERNAL BEHAVIOR

### 4.1 Registry Integration (with resilience)

**Registry base URL (internal):** `http://localhost:8000`

**On startup:**
1. Fetch `GET /registry` to build initial droplet map
2. Store in memory cache (File: `~/.cache/orchestrator/droplets.json` optional)
3. Register itself via `POST /register`:
   ```json
   {
     "name": "orchestrator",
     "id": 2,
     "url": "http://localhost:8001",
     "version": "1.1.0"
   }
   ```

**Periodic refresh (every 60 seconds):**
- Background task calls Registry to refresh droplet map
- On success: update cache + reset cache age
- On timeout/failure: log error, keep existing cache
- If cache is >5min old AND Registry still down: log warning but continue using stale cache
- Never block on Registry — always have fallback

**Cache file (optional but recommended):**
- Location: `/var/cache/fpai/orchestrator_droplets.json`
- Updated after every successful Registry sync
- Used if Registry unreachable during startup
- Expires after 5 minutes of Registry downtime

---

### 4.2 Task Retry Logic (NEW)

**Retry strategy:**
- Max retries: 3
- Backoff: exponential (1s, 2s, 4s)
- Retry on: timeout, 5xx status, connection refused, DNS failure
- Don't retry on: 4xx errors (client error, not transient)

**Implementation:**
```python
async def call_droplet_with_retry(url, method, payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = await httpx.AsyncClient(timeout=5.0).request(method, url, json=payload)
            if response.status_code < 500:
                return response  # Success or client error (don't retry 4xx)
            # 5xx — retry
        except (httpx.TimeoutException, httpx.ConnectError):
            pass  # Retry on timeout/connection failure
        
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)
    
    raise TaskFailureError(f"Failed after {max_retries} attempts")
```

---

### 4.3 Error Handling & Standardization (NEW)

All error responses follow UDC error pattern:

```json
{
  "status": "error",
  "error": {
    "code": "[ERROR_CODE]",
    "message": "[Human-readable message]",
    "details": {
      "[context-specific fields]"
    }
  }
}
```

**Standard error codes:**
- `DROPLET_NOT_FOUND` — droplet_name doesn't exist in registry
- `DROPLET_UNREACHABLE` — all retries failed (timeout/connection refused)
- `INVALID_REQUEST` — malformed task request (missing fields, bad payload)
- `REGISTRY_ERROR` — Registry error (when trying to sync droplets)
- `TIMEOUT` — task took >30 seconds total
- `INTERNAL_ERROR` — unexpected server error

**Error response examples:**

```json
{
  "status": "error",
  "error": {
    "code": "DROPLET_NOT_FOUND",
    "message": "Droplet 'unknown-service' not found in registry",
    "details": {
      "requested_droplet": "unknown-service",
      "available_droplets": ["registry", "orchestrator"]
    }
  }
}
```

```json
{
  "status": "error",
  "error": {
    "code": "DROPLET_UNREACHABLE",
    "message": "Target droplet did not respond after 3 retries",
    "details": {
      "droplet_name": "registry",
      "target_url": "http://localhost:8000/health",
      "retry_count": 3,
      "last_error": "Connection refused",
      "total_duration_ms": 7000
    }
  }
}
```

**Never raise unhandled exceptions** — always return JSON with structured error.

---

### 4.4 Task Store

**Simple in-memory dict:** `Dict[str, Task]`

**Task model includes:**
- id, droplet_name, target_url, method, status
- response_status, response_body (optional, limited to 10KB)
- retry_count, created_at, completed_at, duration_ms
- error_message (if failed)

**Memory management:**
- Keep last 10,000 tasks in memory
- Older tasks auto-expire after 24 hours
- Optional: persist to JSON file `/var/cache/fpai/orchestrator_tasks.json` (not required v1.1)

**Metrics calculated from task history:**
- Success rate, avg response time, p95/p99 latencies
- Retry success vs final failure rates
- Per-droplet performance

---

### 4.5 Observability & Metrics (NEW)

**Track these counters:**
- `tasks_total` — all tasks ever submitted
- `tasks_success` — returned 2xx
- `tasks_error` — returned 4xx or failed after retries
- `tasks_timeout` — exceeded total timeout
- `retries_total` — count of all retry attempts
- `retries_success` — retries that eventually succeeded
- `retries_final_fail` — retries that all failed
- `registry_syncs_total`, `registry_syncs_success`, `registry_syncs_error`
- Latency histogram: min, avg, p95, p99, max response times

**Expose via `/orchestrator/metrics` endpoint** (see section 3.7)

---

## 5. ARCHITECTURE & FILE STRUCTURE

```
/opt/fpai/agents/services/orchestrator

orchestrator/
  app/
    __init__.py
    main.py                 # FastAPI app, routes, startup tasks
    models.py              # Pydantic models (Droplet, Task, Error)
    registry_client.py     # Registry interaction + caching + retry logic
    metrics.py             # Metrics collection and aggregation
    error_handling.py      # UDC-compliant error formatting
    config.py              # Config (Registry URL, timeouts, etc.)
  Dockerfile
  requirements.txt
  docker-compose.override.yml  # Optional local dev overrides
```

### Key modules:

**main.py:**
- FastAPI app initialization
- Route handlers for all endpoints
- Startup: fetch Registry, start metrics collection
- Background task: periodic Registry sync

**registry_client.py:**
- `async def sync_registry()` — fetch droplet map with retry + cache
- `async def get_droplets()` — return current droplet map (cache if needed)
- `async def call_droplet_with_retry()` — HTTP call with exponential backoff

**models.py:**
```python
class Droplet(BaseModel):
    id: int
    name: str
    url: str
    version: str

class Task(BaseModel):
    id: str
    droplet_name: str
    target_url: str
    method: str
    status: Literal["queued", "success", "error", "timeout"]
    response_status: Optional[int]
    response_body: Optional[dict]
    retry_count: int
    created_at: float
    completed_at: Optional[float]
    duration_ms: Optional[int]
    error_message: Optional[str]

class ErrorResponse(BaseModel):
    status: Literal["error"]
    error: dict  # {code, message, details}
```

**metrics.py:**
```python
class Metrics:
    tasks_total: int
    tasks_success: int
    tasks_error: int
    tasks_timeout: int
    retries_total: int
    retries_success: int
    response_times: List[int]  # For p95/p99
    
    def get_summary(self) -> dict:
        return {
            "tasks": {...},
            "retry": {...},
            "registry": {...}
        }
```

---

## 6. DOCKER & DEPLOYMENT

### 6.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ app/

# Create cache directory
RUN mkdir -p /var/cache/fpai

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/orchestrator/health', timeout=2)"

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 6.2 requirements.txt

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
httpx==0.25.1
```

### 6.3 docker-compose.yml (updated)

```yaml
version: '3.8'

services:
  registry:
    build: agents/services/registry
    container_name: fpai-registry
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
    restart: unless-stopped

  orchestrator:
    build: agents/services/orchestrator
    container_name: fpai-orchestrator
    ports:
      - "8001:8001"
    depends_on:
      - registry
    environment:
      - REGISTRY_URL=http://registry:8000
      - CACHE_DIR=/var/cache/fpai
      - REGISTRY_SYNC_INTERVAL=60
      - TASK_TIMEOUT=30
      - LOG_LEVEL=INFO
    volumes:
      - orchestrator_cache:/var/cache/fpai
    restart: unless-stopped

volumes:
  orchestrator_cache:
```

### 6.4 NGINX routing (b.conf)

```nginx
location /orchestrator/ {
    proxy_pass http://127.0.0.1:8001/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Allow longer timeouts for task operations
    proxy_connect_timeout 30s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;
}
```

Then:
```bash
nginx -t
systemctl reload nginx
```

---

## 7. NON-GOALS (v1.1)

- ❌ Authentication/authorization (wait for UDC security phase)
- ❌ Persistent task database (wait for v1.2)
- ❌ Distributed queues or workers (wait for v2.0)
- ❌ Multi-server orchestration (single node only)
- ❌ Task scheduling or delayed execution

These will be added in later versions.

---

## 8. TEST PLAN

### 8.1 Local container tests (on server)

```bash
cd /opt/fpai/infra

docker compose up -d --build

# Wait for startup
sleep 5

# Test Registry
curl http://localhost:8000/health

# Test Orchestrator
curl http://localhost:8001/orchestrator/health
curl http://localhost:8001/orchestrator/info
curl http://localhost:8001/orchestrator/droplets
curl http://localhost:8001/orchestrator/metrics
```

### 8.2 External tests (from laptop)

```bash
http://b.fullpotential.ai/health                    # Registry
http://b.fullpotential.ai/orchestrator/health
http://b.fullpotential.ai/orchestrator/droplets
http://b.fullpotential.ai/orchestrator/metrics
```

### 8.3 Task submission test

```bash
curl -X POST http://b.fullpotential.ai/orchestrator/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_name": "registry",
    "method": "GET",
    "path": "/health",
    "payload": null,
    "meta": {"requested_by": "architect"}
  }'
```

Response should be:
```json
{
  "task_id": "...",
  "status": "success",
  "target_url": "http://localhost:8000/health",
  "response_status": 200,
  "retry_count": 0,
  "duration_ms": 45
}
```

### 8.4 Error handling tests

**Test droplet not found:**
```bash
curl -X POST http://b.fullpotential.ai/orchestrator/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_name": "nonexistent",
    "method": "GET",
    "path": "/health",
    "payload": null
  }'
```

Should return 400 with code: `DROPLET_NOT_FOUND`

**Test retry (stop Registry briefly):**
```bash
# Stop Registry
docker stop fpai-registry

# Submit task
curl -X POST http://localhost:8001/orchestrator/tasks \
  -H "Content-Type: application/json" \
  -d '{"droplet_name": "registry", "method": "GET", "path": "/health"}'

# Should retry 3x (takes ~7 seconds)
# Eventually returns error with retry_count: 3

# Restart Registry
docker start fpai-registry
```

### 8.5 Metrics test

```bash
curl http://b.fullpotential.ai/orchestrator/metrics

# Should show:
# - tasks_total > 0
# - tasks_success, tasks_error counts
# - registry sync stats
# - response time percentiles
```

---

## 9. DEFINITION OF DONE

- ✅ Dockerized FastAPI service deployed as `fpai-orchestrator` on port 8001
- ✅ Orchestrator registers itself with Registry on startup
- ✅ `GET /orchestrator/health` reachable via `http://b.fullpotential.ai/orchestrator/health`
- ✅ `GET /orchestrator/droplets` returns droplet list from Registry
- ✅ Registry cache works: droplets returned even if Registry temporarily unavailable
- ✅ `POST /orchestrator/tasks` routes to target droplets with automatic retry (3x with backoff)
- ✅ `GET /orchestrator/tasks` and `/tasks/{id}` reflect correct status + retry_count
- ✅ All error responses follow UDC error format (status: error, error: {code, message, details})
- ✅ `GET /orchestrator/metrics` exposes task success rates, latencies, retry stats
- ✅ Code is clean, type-hinted, documented
- ✅ docker-compose.yml and NGINX config updated
- ✅ All test scenarios (3.1-3.7, 8.1-8.5) pass

---

## 10. PROMPTS FOR APPRENTICE BUILD

### PROMPT A: Builder (Claude)

```
Generate complete production-ready code for Orchestrator Track B v1.1.

SPECIFICATION:
[Paste this entire SPEC_Orchestrator_TrackB_v1_1_Enhanced.md]

CONTEXT FILES UPLOADED:
- UDC_COMPLIANCE.md
- TECH_STACK.md
- SECURITY_REQUIREMENTS.md
- CODE_STANDARDS.md
- INTEGRATION_GUIDE.md

GENERATE ALL FILES:
1. app/main.py — FastAPI app + routes + startup
2. app/models.py — Pydantic models (Droplet, Task, ErrorResponse)
3. app/registry_client.py — Registry sync + cache + retry logic
4. app/metrics.py — Metrics collection
5. app/error_handling.py — UDC error formatting
6. app/config.py — Configuration
7. app/__init__.py — Package init
8. Dockerfile — Production image
9. requirements.txt — Dependencies
10. docker-compose.override.yml — Local dev

REQUIREMENTS:
- All UDC endpoints from section 3.1-3.7 implemented
- Registry caching with 5-minute fallback
- Exponential backoff retry (1s, 2s, 4s)
- UDC-compliant error responses with code + message + details
- Metrics endpoint with success rates, latencies, p95/p99
- Full type hints (no Any types)
- Comprehensive docstrings
- No TODOs or placeholders
- Production-ready error handling

OUTPUT:
Generate each file as separate code block with path + full content.
```

### PROMPT B: Verifier (Gemini)

```
Verify this Orchestrator Track B v1.1 code against specification.

SPECIFICATION:
[Paste this entire SPEC_Orchestrator_TrackB_v1_1_Enhanced.md]

GENERATED CODE:
[Upload or paste all generated files]

VERIFY CHECKLIST:

ENDPOINTS (Section 3):
[ ] GET /orchestrator/health returns UDC format
[ ] GET /orchestrator/info includes cache_status + age
[ ] GET /orchestrator/droplets returns droplets + cache_status
[ ] GET /orchestrator/droplets includes "served_from" field
[ ] POST /orchestrator/tasks accepts all fields from spec
[ ] POST /orchestrator/tasks returns task_id + retry_count
[ ] POST /orchestrator/tasks includes duration_ms
[ ] GET /orchestrator/tasks supports status + droplet_name filters
[ ] GET /orchestrator/tasks/{id} returns full task record
[ ] GET /orchestrator/metrics returns all fields from section 3.7

RESILIENCE (Section 4.1):
[ ] Registry cache file location: /var/cache/fpai/orchestrator_droplets.json
[ ] Cache age tracked and returned
[ ] If Registry down: falls back to cache
[ ] Cache expires after 5 min of Registry downtime
[ ] Startup works if Registry unavailable (uses cache)

RETRY LOGIC (Section 4.2):
[ ] Max retries: 3
[ ] Backoff: 1s, 2s, 4s (exponential)
[ ] Retries on: timeout, 5xx, connection error
[ ] Does NOT retry on: 4xx errors
[ ] Task record includes retry_count field

ERRORS (Section 4.3):
[ ] All errors follow UDC pattern: {status: "error", error: {code, message, details}}
[ ] Error codes: DROPLET_NOT_FOUND, DROPLET_UNREACHABLE, TIMEOUT, INVALID_REQUEST, REGISTRY_ERROR, INTERNAL_ERROR
[ ] Error response includes details object with context

METRICS (Section 4.4):
[ ] Metrics endpoint returns all fields from section 3.7
[ ] Success rate calculated correctly
[ ] Retry stats tracked (total, success, final_fail)
[ ] Response time percentiles (p95, p99) calculated
[ ] Registry sync stats included

CODE QUALITY:
[ ] All functions type-hinted (no Any types)
[ ] Docstrings on public functions
[ ] Error handling: no unhandled exceptions
[ ] Async/await used for all I/O
[ ] No hardcoded secrets or URLs (use config)
[ ] No print() statements (use logging)

DOCKER & DEPLOYMENT (Section 6):
[ ] Dockerfile includes HEALTHCHECK
[ ] requirements.txt has correct versions
[ ] docker-compose.yml sets REGISTRY_URL env var
[ ] NGINX config has extended timeouts (30s)
[ ] docker-compose volumes defined for cache

COMPLETENESS:
[ ] All 10 files generated (no missing files)
[ ] No TODO or FIXME comments
[ ] No placeholder functions
[ ] Requirements.txt includes all imports used
[ ] .env handling for config

OUTPUT:
Format as PASS/FAIL checklist with âœ… for each item.
List all issues found (CRITICAL/MAJOR/MINOR).
PASS = all critical checks + 90%+ major checks.
FAIL = any critical failures or <80% major checks.
```

---

## 11. DEPLOYMENT INSTRUCTIONS

When ready to deploy on new server:

```bash
# 1. Clone/pull repo
cd /opt/fpai/infra
git pull

# 2. Build both images
docker compose build

# 3. Start containers
docker compose up -d

# 4. Verify startup
docker compose logs orchestrator

# 5. Test endpoints
curl http://localhost:8001/orchestrator/health
curl http://localhost:8001/orchestrator/droplets

# 6. Update NGINX (if not already done)
# Edit /etc/nginx/sites-available/b.conf
# Add orchestrator location block from section 6.4
nginx -t
systemctl reload nginx

# 7. Test external
curl http://b.fullpotential.ai/orchestrator/health

# Done!
```

---

**END SPEC_Orchestrator_TrackB_v1_1_Enhanced.md**

*This spec is production-ready. Hand to Claude to generate complete implementation.*
