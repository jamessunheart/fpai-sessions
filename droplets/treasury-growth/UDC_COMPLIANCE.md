# 🌐 UDC COMPLIANCE - Universal Droplet Contract

**Version:** 1.0
**Last Updated:** 2025-11-15
**Purpose:** Standard interface for all Full Potential AI droplets

---

## 1. OVERVIEW

The Universal Droplet Contract (UDC) defines the standard interface that ALL droplets must implement.

**Why this matters:**
- Enables automatic discovery and monitoring
- Allows Dashboard to visualize any droplet
- Lets Orchestrator route tasks to any service
- Makes the system self-documenting
- Ensures consistent integration patterns

**Bottom line:** If a service implements UDC, it plugs into the Full Potential AI ecosystem automatically.

---

## 2. REQUIRED ENDPOINTS

Every droplet MUST implement these 5 endpoints:

### 2.1 Health Check
```
GET /health
```

**Purpose:** Liveness and readiness check

**Response:**
```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "timestamp": "2025-11-15T12:00:00Z",
  "uptime_seconds": 86400,
  "version": "1.0.0"
}
```

**Status Definitions:**
- `healthy`: All systems operational
- `degraded`: Partial functionality (e.g., DB slow but working)
- `unhealthy`: Critical failure (should restart)

**Requirements:**
- Must respond in <100ms
- Must not perform expensive operations
- Should check critical dependencies only

---

### 2.2 Capabilities
```
GET /capabilities
```

**Purpose:** Declare what this droplet can do

**Response:**
```json
{
  "service_name": "registry",
  "droplet_id": 1,
  "capabilities": [
    "service_registration",
    "jwt_issuer",
    "service_discovery"
  ],
  "supported_operations": [
    "register_service",
    "get_service",
    "list_services",
    "issue_token"
  ],
  "integration_endpoints": [
    {
      "path": "/register",
      "method": "POST",
      "description": "Register a new service"
    },
    {
      "path": "/services/{id}",
      "method": "GET",
      "description": "Get service details"
    }
  ]
}
```

**Requirements:**
- Must list all major capabilities
- Must document all public endpoints
- Should include version information
- Static response (can be cached)

---

### 2.3 State
```
GET /state
```

**Purpose:** Current operational state

**Response:**
```json
{
  "status": "active" | "inactive" | "error",
  "mode": "production" | "development" | "maintenance",
  "registered_services": 3,
  "active_connections": 12,
  "last_activity": "2025-11-15T12:00:00Z",
  "metrics": {
    "requests_per_minute": 45.2,
    "average_response_time_ms": 23,
    "error_rate_percent": 0.1
  }
}
```

**Status Values:**
- `active`: Currently processing requests
- `inactive`: Running but idle
- `error`: In error state (check /health for details)

**Requirements:**
- Must reflect current runtime state
- Should include key metrics
- Must update in real-time (<5s lag)

---

### 2.4 Dependencies
```
GET /dependencies
```

**Purpose:** What this droplet depends on

**Response:**
```json
{
  "required_services": [
    {
      "name": "postgres",
      "type": "database",
      "status": "connected",
      "host": "localhost:5432"
    }
  ],
  "optional_services": [
    {
      "name": "redis",
      "type": "cache",
      "status": "disconnected",
      "impact": "Performance degraded but functional"
    }
  ],
  "external_apis": [
    {
      "name": "anthropic",
      "status": "healthy",
      "last_check": "2025-11-15T12:00:00Z"
    }
  ]
}
```

**Requirements:**
- Must list all critical dependencies
- Must check dependency health
- Should include impact if dependency fails
- Updated periodically (30-60s)

---

### 2.5 Message
```
POST /message
```

**Purpose:** Inter-droplet communication

**Request:**
```json
{
  "from_service": "orchestrator",
  "message_type": "task_assignment" | "status_update" | "query",
  "payload": {
    "task_id": "task-123",
    "action": "verify_code",
    "data": {}
  },
  "reply_to": "http://orchestrator:8001/callback"
}
```

**Response:**
```json
{
  "received": true,
  "message_id": "msg-456",
  "status": "processing" | "completed" | "failed",
  "result": {}
}
```

**Requirements:**
- Must accept messages from any registered service
- Must validate sender (JWT from Registry)
- Should process asynchronously for long operations
- Must support reply_to callback pattern

**Message Types:**
- `task_assignment`: New work to perform
- `status_update`: Notification of state change
- `query`: Request for information

---

## 3. AUTHENTICATION

### JWT Authentication
All UDC endpoints (except /health) must support JWT authentication.

**Header:**
```
Authorization: Bearer <jwt_token>
```

**JWT Verification:**
1. Get public key from Registry at `/auth/public-key`
2. Verify JWT signature using RS256
3. Check `exp` (expiration) claim
4. Extract `service_id` from payload

**Example JWT Payload:**
```json
{
  "service_id": 10,
  "service_name": "orchestrator",
  "capabilities": ["task_routing", "messaging"],
  "exp": 1700000000,
  "iat": 1699999000
}
```

**Security Requirements:**
- /health endpoint: Public (no auth required)
- All other UDC endpoints: JWT required
- Business logic endpoints: JWT required + role-based access

---

## 4. RESPONSE STANDARDS

### Status Codes
```
200 OK          - Success
201 Created     - Resource created
400 Bad Request - Invalid input
401 Unauthorized - Missing/invalid JWT
403 Forbidden   - Valid JWT but insufficient permissions
404 Not Found   - Resource doesn't exist
500 Internal Server Error - Server failure
503 Service Unavailable - Temporarily down
```

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Service name is required",
    "details": {
      "field": "service_name",
      "constraint": "required"
    }
  }
}
```

### Success Response Format
```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2025-11-15T12:00:00Z",
    "version": "1.0.0"
  }
}
```

---

## 5. REGISTRATION PROTOCOL

Every droplet must register with Registry on startup:

```python
import requests

def register_with_registry():
    response = requests.post(
        "http://registry:8000/register",
        json={
            "name": "my-service",
            "droplet_id": 10,
            "port": 8010,
            "health_endpoint": "/health",
            "capabilities": ["task_routing"],
            "version": "1.0.0"
        }
    )
    jwt_token = response.json()["token"]
    return jwt_token
```

**Registration Flow:**
1. Service starts up
2. Calls /register on Registry
3. Receives JWT token
4. Uses token for all UDC calls
5. Sends heartbeat every 60s to Orchestrator

---

## 6. HEARTBEAT PROTOCOL

Every droplet must send heartbeat to Orchestrator every 60 seconds:

```python
import requests
import time

def send_heartbeat(jwt_token):
    while True:
        requests.post(
            "http://orchestrator:8001/heartbeat",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={
                "service_name": "my-service",
                "status": "active",
                "metrics": {
                    "cpu_percent": 15.2,
                    "memory_mb": 256
                }
            }
        )
        time.sleep(60)
```

**Heartbeat Requirements:**
- Interval: Every 60 seconds (±5s acceptable)
- Timeout: If no heartbeat for 180s, mark service as dead
- Status: Include current operational status
- Metrics: Optional but recommended

---

## 7. DOCKER LABELS

Every droplet's Dockerfile must include these labels:

```dockerfile
LABEL droplet.id="10"
LABEL droplet.name="orchestrator"
LABEL droplet.version="1.0.0"
LABEL droplet.udc_compliant="true"
LABEL droplet.capabilities="task_routing,messaging"
```

**Why:** Enables automatic discovery via Docker API

---

## 8. ENVIRONMENT VARIABLES

Standard environment variables all droplets should support:

```bash
# Registry connection
REGISTRY_URL=http://registry:8000

# Orchestrator connection
ORCHESTRATOR_URL=http://orchestrator:8001

# Service identity
SERVICE_NAME=my-service
SERVICE_PORT=8010
DROPLET_ID=10

# Environment
ENVIRONMENT=production  # production | development | staging

# Logging
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR
```

---

## 9. LOGGING STANDARDS

All droplets must use structured logging:

```python
import logging
import json

logger = logging.getLogger(__name__)

# Good: Structured logging
logger.info(json.dumps({
    "event": "request_received",
    "service": "registry",
    "path": "/register",
    "duration_ms": 23.4,
    "status": 200
}))

# Bad: Unstructured logging
print("Request received")  # Never use print()
logger.info("Request took 23ms")  # Hard to parse
```

**Log Levels:**
- DEBUG: Development/troubleshooting only
- INFO: Normal operations (request handling, etc.)
- WARNING: Degraded but functional (slow DB, retries)
- ERROR: Failures that need attention

---

## 10. TESTING REQUIREMENTS

Every droplet must include tests for all UDC endpoints:

```python
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded", "unhealthy"]

def test_capabilities_endpoint():
    response = client.get("/capabilities")
    assert response.status_code == 200
    assert "capabilities" in response.json()

def test_state_endpoint():
    response = client.get("/state", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] in ["active", "inactive", "error"]

def test_dependencies_endpoint():
    response = client.get("/dependencies", headers=auth_headers)
    assert response.status_code == 200
    assert "required_services" in response.json()

def test_message_endpoint():
    response = client.post(
        "/message",
        headers=auth_headers,
        json={"from_service": "test", "message_type": "query", "payload": {}}
    )
    assert response.status_code == 200
```

**Coverage Requirements:**
- All 5 UDC endpoints: 100% coverage
- Business logic: >80% coverage
- Error cases: >60% coverage

---

## 11. COMPLIANCE CHECKLIST

Use this checklist to verify UDC compliance:

- [ ] Implements GET /health endpoint
- [ ] Implements GET /capabilities endpoint
- [ ] Implements GET /state endpoint
- [ ] Implements GET /dependencies endpoint
- [ ] Implements POST /message endpoint
- [ ] All endpoints return correct JSON format
- [ ] JWT authentication implemented (except /health)
- [ ] Registers with Registry on startup
- [ ] Sends heartbeat to Orchestrator every 60s
- [ ] Dockerfile includes UDC labels
- [ ] Supports standard environment variables
- [ ] Uses structured logging (no print statements)
- [ ] Tests cover all UDC endpoints
- [ ] README documents all UDC endpoints

---

## 12. EXAMPLES

### FastAPI Implementation

```python
from fastapi import FastAPI, Header
from datetime import datetime
import time

app = FastAPI()

# Track startup time for uptime calculation
startup_time = time.time()

@app.get("/health")
def health():
    """Public endpoint - no auth required"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": int(time.time() - startup_time),
        "version": "1.0.0"
    }

@app.get("/capabilities")
def capabilities():
    """Public capabilities declaration"""
    return {
        "service_name": "my-service",
        "droplet_id": 10,
        "capabilities": ["example_capability"],
        "supported_operations": ["operation1", "operation2"],
        "integration_endpoints": [
            {
                "path": "/api/v1/resource",
                "method": "GET",
                "description": "Get resource"
            }
        ]
    }

@app.get("/state")
def state(authorization: str = Header(None)):
    """Requires JWT authentication"""
    # Verify JWT here
    return {
        "status": "active",
        "mode": "production",
        "metrics": {
            "requests_per_minute": 45.2
        }
    }

@app.get("/dependencies")
def dependencies(authorization: str = Header(None)):
    """Requires JWT authentication"""
    # Verify JWT here
    return {
        "required_services": [
            {
                "name": "postgres",
                "type": "database",
                "status": "connected"
            }
        ],
        "optional_services": [],
        "external_apis": []
    }

@app.post("/message")
def message(msg: dict, authorization: str = Header(None)):
    """Requires JWT authentication"""
    # Verify JWT here
    return {
        "received": True,
        "message_id": f"msg-{int(time.time())}",
        "status": "processing"
    }
```

---

## 13. VERIFICATION

To verify UDC compliance automatically:

```bash
# Use the Verifier droplet
curl -X POST http://verifier:8008/verify \
  -H "Content-Type: application/json" \
  -d '{
    "service_url": "http://my-service:8010",
    "check_type": "udc_compliance"
  }'
```

Or manually:
```bash
# Test all 5 endpoints
curl http://my-service:8010/health
curl http://my-service:8010/capabilities
curl -H "Authorization: Bearer $JWT" http://my-service:8010/state
curl -H "Authorization: Bearer $JWT" http://my-service:8010/dependencies
curl -X POST -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"from_service":"test","message_type":"query","payload":{}}' \
  http://my-service:8010/message
```

---

**This document defines the contract. All droplets must comply.**

🌐⚡💎
