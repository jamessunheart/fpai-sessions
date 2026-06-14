# Orchestrator Service
## Central Task Routing for Full Potential AI

**Version:** 1.1.0  
**Status:** Production-ready  
**Language:** Python 3.11+  

---

## Overview

Orchestrator is the central traffic controller for Full Potential AI's distributed droplet mesh. It:

- Routes tasks to target droplets via HTTP
- Automatically retries failed requests with exponential backoff
- Caches droplet registry with fallback to disk
- Tracks task status and metrics
- Provides observability endpoints
- Gracefully degrades if Registry is temporarily unavailable

---

## Architecture

```
┌─────────────────────────────────────────┐
│          External Requests              │
│  (from other services or CLI)           │
└─────────────┬───────────────────────────┘
              │ POST /tasks
              ▼
    ┌─────────────────────┐
    │   Orchestrator      │
    │  (this service)     │
    └──────┬──────────────┘
           │
           ├─ Registry Sync (periodic)
           │  ├─ GET Registry droplets
           │  └─ Cache to disk
           │
           └─ Task Routing (on-demand)
              ├─ Resolve droplet name
              ├─ Retry with backoff (3x)
              └─ Record metrics
```

---

## Quick Start

### Local Development

1. **Clone repository:**
   ```bash
   cd /opt/fpai/agents/services/orchestrator
   ```

2. **Create virtual environment:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # Mac/Linux
   # OR
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults work for localhost)
   ```

5. **Run locally (requires Registry running):**
   ```bash
   # Terminal 1: Start Registry
   cd /opt/fpai/agents/services/registry
   uvicorn app.main:app --port 8000

   # Terminal 2: Start Orchestrator
   uvicorn app.main:app --port 8001 --reload
   ```

6. **Test:**
   ```bash
   # Health check
   curl http://localhost:8001/orchestrator/health

   # Get droplets
   curl http://localhost:8001/orchestrator/droplets

   # Submit task
   curl -X POST http://localhost:8001/orchestrator/tasks \
     -H "Content-Type: application/json" \
     -d '{
       "droplet_name": "registry",
       "method": "GET",
       "path": "/health",
       "payload": null,
       "meta": {"requested_by": "test"}
     }'
   ```

### Docker Deployment

1. **Build and start:**
   ```bash
   cd /opt/fpai/infra
   docker compose build
   docker compose up -d
   ```

2. **Verify:**
   ```bash
   docker compose logs orchestrator
   curl http://localhost:8001/orchestrator/health
   ```

3. **Stop:**
   ```bash
   docker compose down
   ```

---

## API Endpoints

### Health & Info

**GET /orchestrator/health**
```bash
curl http://localhost:8001/orchestrator/health
```
Response:
```json
{
  "status": "ok",
  "service": "orchestrator",
  "version": "1.1.0"
}
```

**GET /orchestrator/info**
```bash
curl http://localhost:8001/orchestrator/info
```

**GET /orchestrator/droplets**
```bash
curl http://localhost:8001/orchestrator/droplets
```

---

### Task Submission

**POST /orchestrator/tasks**

Submit a task to be routed to a droplet:

```bash
curl -X POST http://localhost:8001/orchestrator/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_name": "registry",
    "method": "GET",
    "path": "/health",
    "payload": null,
    "meta": {"requested_by": "test"}
  }'
```

Response (success):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "target_url": "http://localhost:8000/health",
  "response_status": 200,
  "response_body": {"status": "ok", "service": "registry"},
  "retry_count": 0,
  "duration_ms": 45
}
```

Response (error):
```json
{
  "status": "error",
  "error": {
    "code": "DROPLET_NOT_FOUND",
    "message": "Droplet 'unknown' not found in registry",
    "details": {
      "requested_droplet": "unknown",
      "available_droplets": ["registry", "orchestrator"]
    }
  }
}
```

---

### Task History

**GET /orchestrator/tasks**

List submitted tasks:

```bash
# Get all tasks
curl http://localhost:8001/orchestrator/tasks

# Filter by status
curl "http://localhost:8001/orchestrator/tasks?status=success"

# Filter by droplet
curl "http://localhost:8001/orchestrator/tasks?droplet_name=registry"

# Limit results
curl "http://localhost:8001/orchestrator/tasks?limit=50"
```

**GET /orchestrator/tasks/{task_id}**

Get single task:

```bash
curl http://localhost:8001/orchestrator/tasks/550e8400-e29b-41d4-a716-446655440000
```

---

### Metrics

**GET /orchestrator/metrics**

Get operational metrics:

```bash
curl http://localhost:8001/orchestrator/metrics
```

Response:
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

## Configuration

All settings can be customized via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `REGISTRY_URL` | `http://localhost:8000` | Registry service URL |
| `REGISTRY_SYNC_INTERVAL` | `60` | Seconds between Registry syncs |
| `REGISTRY_TIMEOUT` | `5.0` | Seconds to wait for Registry response |
| `REGISTRY_CACHE_DIR` | `/var/cache/fpai` | Directory for disk cache |
| `REGISTRY_CACHE_EXPIRY` | `300` | Seconds before cache expires (5min) |
| `TASK_TIMEOUT` | `30` | Seconds to wait for task response |
| `TASK_MAX_RETRIES` | `3` | Maximum retry attempts |
| `TASK_MAX_HISTORY` | `10000` | Max tasks kept in memory |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

---

## Resilience Features

### Registry Cache

- **Primary:** Fetch droplet list from Registry every 60 seconds
- **Fallback:** Use in-memory cache if Registry unavailable
- **Disk Cache:** Persist cache to `/var/cache/fpai/orchestrator_droplets.json`
- **Graceful Degradation:** Continue with stale cache up to 5 minutes

### Task Retry

- **Max Retries:** 3 attempts per task
- **Backoff:** Exponential (1s, 2s, 4s between attempts)
- **Retry On:** Timeouts, 5xx errors, connection failures
- **Don't Retry On:** 4xx errors (client errors)

### Error Handling

All errors follow UDC format:
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { "context": "specific" }
  }
}
```

---

## Metrics & Monitoring

Orchestrator exposes real-time metrics for:

- **Task Performance:** Success rate, response times, percentiles
- **Retry Stats:** Total retries, success, final failures
- **Registry Health:** Sync attempts, cache age, availability
- **System Status:** Uptime, droplet count, reachability

Dashboard can query `/orchestrator/metrics` for monitoring.

---

## Development

### Code Structure

```
orchestrator/
  app/
    __init__.py              # Package init
    main.py                  # FastAPI routes + startup
    config.py                # Configuration management
    models.py                # Pydantic models
    registry_client.py       # Registry sync + retry logic
    error_handling.py        # UDC error formatting
    metrics.py               # Metrics collection
  Dockerfile                 # Production image
  requirements.txt           # Dependencies
  docker-compose.yml         # Full Track B stack
  .env.example              # Configuration template
  README.md                 # This file
```

### Type Safety

All code uses full type hints for:
- Function parameters
- Return types
- Class attributes
- Collections

Run type checking:
```bash
pip install mypy
mypy app/
```

### Testing

Test locally with curl (examples above).

Run test suite (requires pytest):
```bash
pip install pytest pytest-asyncio httpx
pytest tests/
```

---

## Deployment Checklist

- [ ] Registry service running at `REGISTRY_URL`
- [ ] `.env` configured for your environment
- [ ] Docker image built: `docker build -t fpai-orchestrator .`
- [ ] Volume mounted for cache: `/var/cache/fpai`
- [ ] Port 8001 exposed (or via NGINX reverse proxy)
- [ ] Health check passes: `curl http://localhost:8001/orchestrator/health`
- [ ] Droplets endpoint works: `curl http://localhost:8001/orchestrator/droplets`
- [ ] Test task submission works (see examples above)
- [ ] Metrics endpoint accessible: `curl http://localhost:8001/orchestrator/metrics`

---

## Troubleshooting

### Registry Connection Failed

**Error:** `Connection error: Cannot connect to registry`

**Solution:**
1. Verify Registry is running: `curl http://registry-url/health`
2. Check `REGISTRY_URL` environment variable
3. Check network connectivity between services
4. Orchestrator will fall back to disk cache if available

### Tasks Always Failing

**Error:** All tasks return `status: "error"`

**Solution:**
1. Check task `droplet_name` exists in `/orchestrator/droplets`
2. Verify target droplet is reachable: `curl http://droplet-url/health`
3. Check target droplet logs for errors
4. Verify request payload is valid JSON

### High Latency or Timeouts

**Error:** Tasks take >30 seconds or return TIMEOUT

**Solution:**
1. Check target droplet performance
2. Increase `TASK_TIMEOUT` environment variable if needed
3. Check network latency with: `curl -w "@curl-format.txt" http://droplet/endpoint`
4. Check metrics for p95/p99 latencies: `curl /orchestrator/metrics`

---

## Next Steps

- Add authentication/authorization (UDC security phase)
- Add persistent task database (v1.2)
- Add distributed queues (v2.0)
- Add multi-server orchestration (v2.0)

---

## Support

For issues or questions:
1. Check logs: `docker compose logs orchestrator`
2. Check metrics: `curl http://localhost:8001/orchestrator/metrics`
3. Review SPEC_Orchestrator_TrackB_v1_1_Enhanced.md
4. Contact architecture team

---

**Orchestrator v1.1.0 — Production-ready task routing for Full Potential AI**
