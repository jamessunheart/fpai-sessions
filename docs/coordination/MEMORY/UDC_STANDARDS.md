# UDC Standards - Universal Droplet Contract

**Building standards for all services**

---

## What is UDC?

**Universal Droplet Contract** is the architecture standard for all services (droplets) in the Full Potential AI ecosystem.

**Philosophy:**
- Every service is a "droplet"
- All droplets follow same contract
- Services can discover and communicate with each other
- Uniform interface enables orchestration

---

## The 6 Required Endpoints

**Every service MUST implement these endpoints:**

### 1. `/health`
**Purpose:** Service health status

**Returns:**
```json
{
  "status": "active|inactive|degraded",
  "service": "service-name",
  "version": "1.0.0",
  "timestamp": "2025-11-15T23:00:00Z"
}
```

**Implementation:**
```python
@app.get("/health")
async def health():
    return {
        "status": "active",
        "service": "my-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
```

---

### 2. `/capabilities`
**Purpose:** What this service provides

**Returns:**
```json
{
  "version": "1.0.0",
  "features": ["feature1", "feature2"],
  "dependencies": ["service-a", "service-b"],
  "udc_version": "1.0",
  "metadata": {}
}
```

**Implementation:**
```python
@app.get("/capabilities")
async def capabilities():
    return {
        "version": "1.0.0",
        "features": ["email-sending", "template-rendering"],
        "dependencies": ["credential-vault"],
        "udc_version": "1.0"
    }
```

---

### 3. `/state`
**Purpose:** Resource usage and metrics

**Returns:**
```json
{
  "uptime_seconds": 3600,
  "requests_total": 1000,
  "requests_per_minute": 10.5,
  "errors_last_hour": 2,
  "last_restart": "2025-11-15T20:00:00Z"
}
```

**Implementation:**
```python
start_time = time.time()
request_count = 0

@app.get("/state")
async def state():
    return {
        "uptime_seconds": int(time.time() - start_time),
        "requests_total": request_count,
        "requests_per_minute": calculate_rpm(),
        "errors_last_hour": error_count
    }
```

---

### 4. `/dependencies`
**Purpose:** Required and optional services

**Returns:**
```json
{
  "required": ["credential-vault", "database"],
  "optional": ["cache"],
  "missing": []
}
```

**Implementation:**
```python
@app.get("/dependencies")
async def dependencies():
    required = ["credential-vault"]
    missing = check_missing(required)

    return {
        "required": required,
        "optional": ["redis-cache"],
        "missing": missing
    }
```

---

### 5. `/message`
**Purpose:** Receive messages from other services

**Receives:**
```json
{
  "trace_id": "uuid",
  "source": "service-name",
  "target": "this-service",
  "message_type": "status|command|data",
  "payload": {},
  "timestamp": "2025-11-15T23:00:00Z"
}
```

**Implementation:**
```python
@app.post("/message")
async def message(msg: MessageRequest):
    logger.info(f"Received {msg.message_type} from {msg.source}")

    # Handle message based on type
    if msg.message_type == "status":
        handle_status_update(msg.payload)

    return {
        "received": True,
        "trace_id": msg.trace_id,
        "processed_at": datetime.utcnow().isoformat() + "Z"
    }
```

---

### 6. `/send`
**Purpose:** Send messages to other services

**Receives:**
```json
{
  "target": "service-name",
  "message_type": "status|command|data",
  "payload": {}
}
```

**Implementation:**
```python
@app.post("/send")
async def send_message(request: SendRequest):
    trace_id = str(uuid.uuid4())

    # Look up target service in registry
    target = get_service(request.target)

    # Send via HTTP to target's /message endpoint
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{target.endpoint}/message",
            json={
                "trace_id": trace_id,
                "source": "this-service",
                "target": request.target,
                "message_type": request.message_type,
                "payload": request.payload,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )

    return {
        "sent": response.status_code == 200,
        "trace_id": trace_id
    }
```

---

## Service Template

**Use:** `/Users/jamessunheart/Development/SERVICES/_TEMPLATE/`

### Structure:
```
my-service/
├── src/
│   ├── main.py          # FastAPI app with UDC endpoints
│   ├── models.py        # Pydantic models
│   └── services/        # Business logic
├── tests/
│   └── test_udc.py      # Test all 6 endpoints
├── docs/
│   ├── README.md        # Service documentation
│   └── SPEC.md          # Technical specification
├── deploy/
│   ├── Dockerfile       # Containerization
│   └── deploy.sh        # Deployment script
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variables
```

---

## Quick Start Template

```python
from fastapi import FastAPI
from datetime import datetime
import time

app = FastAPI(title="My Service", version="1.0.0")

start_time = time.time()
request_count = 0

@app.middleware("http")
async def track_requests(request, call_next):
    global request_count
    request_count += 1
    return await call_next(request)

@app.get("/health")
async def health():
    return {
        "status": "active",
        "service": "my-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/capabilities")
async def capabilities():
    return {
        "version": "1.0.0",
        "features": ["feature1"],
        "dependencies": [],
        "udc_version": "1.0"
    }

@app.get("/state")
async def state():
    return {
        "uptime_seconds": int(time.time() - start_time),
        "requests_total": request_count
    }

@app.get("/dependencies")
async def dependencies():
    return {
        "required": [],
        "optional": [],
        "missing": []
    }

@app.post("/message")
async def message(msg: dict):
    return {
        "received": True,
        "trace_id": msg.get("trace_id")
    }

@app.post("/send")
async def send_message(request: dict):
    return {
        "sent": True,
        "trace_id": "generated-uuid"
    }
```

---

## Verification

**Check UDC compliance:**
```bash
cd /Users/jamessunheart/Development/SERVICES
python3 integrated-registry-system.py
```

**This will:**
- Test all 6 endpoints
- Report compliance status
- Identify missing endpoints

---

## Registration

**Once UDC compliant, register:**

```bash
# In service registry
./docs/coordination/scripts/service-register.sh "my-service" "Description" 8XXX "development"

# In server registry (automatic via integrated-registry-system.py)
# Or manual:
curl -X POST http://198.54.123.234:8000/droplets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-service",
    "endpoint": "http://localhost:8XXX",
    "steward": "session-X"
  }'
```

---

## Benefits of UDC

**Standardization:**
- All services look the same
- Easy to understand any service
- Consistent patterns

**Discoverability:**
- Services register themselves
- Registry knows all services
- Auto-discovery possible

**Communication:**
- Services message each other
- Trace requests across services
- Coordinated orchestration

**Monitoring:**
- Health checks built-in
- Metrics standardized
- Easy observability

**Orchestration:**
- Services can orchestrate each other
- Dependency tracking
- Automatic coordination

---

## Common Patterns

### Service Registration on Startup

```python
@app.on_event("startup")
async def register_to_registry():
    """Register this service to central registry"""
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://198.54.123.234:8000/droplets",
            json={
                "name": "my-service",
                "endpoint": "http://localhost:8500",
                "steward": "session-5"
            }
        )
```

### Health Check with Dependencies

```python
@app.get("/health")
async def health():
    # Check dependencies
    vault_healthy = await check_service("credential-vault")

    status = "active" if vault_healthy else "degraded"

    return {
        "status": status,
        "service": "my-service",
        "version": "1.0.0"
    }
```

### Inter-Service Messaging

```python
# Send message to another service
await send_to_service(
    target="email-service",
    message_type="command",
    payload={"action": "send_email", "to": "user@example.com"}
)
```

---

## Testing UDC Compliance

```python
# tests/test_udc.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_capabilities_endpoint():
    response = client.get("/capabilities")
    assert response.status_code == 200
    assert "version" in response.json()

# Test all 6 endpoints...
```

---

## Summary

**To build a UDC-compliant service:**

1. Use _TEMPLATE/ structure
2. Implement 6 required endpoints
3. Test compliance
4. Register in service registry
5. Deploy and monitor

**Follow UDC → Services work together seamlessly** 🔗
