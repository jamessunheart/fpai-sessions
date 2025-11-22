# SPEC - [Service Name] (Droplet #[XX])

**Version:** 1.0
**Created:** [Date]
**Droplet ID:** [XX]
**Status:** Draft | In Development | Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
[1-2 sentences describing what this service does and why it exists]

### 1.2 Position in Ecosystem
[How this service fits into the Full Potential AI system]

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Authentication & service discovery
- [Other required services]

**Optional Services:**
- [Services that enhance but aren't required]

**External Dependencies:**
- [External APIs, databases, etc.]

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Capability 1]** - [Brief description]
2. **[Capability 2]** - [Brief description]
3. **[Capability 3]** - [Brief description]

### 2.2 Supported Operations
- `[operation_1]` - [What it does]
- `[operation_2]` - [What it does]
- `[operation_3]` - [What it does]

---

## 3. API SPECIFICATION

### 3.1 UDC Endpoints (Required)

#### Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "timestamp": "2025-11-15T12:00:00Z",
  "uptime_seconds": 86400,
  "version": "1.0.0"
}
```

#### Capabilities
```
GET /capabilities
```

**Response:**
```json
{
  "service_name": "[service-name]",
  "droplet_id": [XX],
  "capabilities": ["capability1", "capability2"],
  "supported_operations": ["operation1", "operation2"],
  "integration_endpoints": [
    {
      "path": "/api/endpoint",
      "method": "POST",
      "description": "Description"
    }
  ]
}
```

#### State
```
GET /state
```

**Response:**
```json
{
  "status": "active" | "inactive" | "error",
  "mode": "production" | "development" | "maintenance",
  "[metric_name]": [value],
  "metrics": {
    "requests_per_minute": 45.2,
    "average_response_time_ms": 23
  }
}
```

#### Dependencies
```
GET /dependencies
```

**Response:**
```json
{
  "required_services": [
    {
      "name": "service-name",
      "type": "database | api | service",
      "status": "connected" | "disconnected",
      "host": "hostname:port"
    }
  ],
  "optional_services": [],
  "external_apis": []
}
```

#### Message
```
POST /message
```

**Request:**
```json
{
  "from_service": "sender-name",
  "message_type": "task_assignment" | "status_update" | "query",
  "payload": {},
  "reply_to": "http://sender:port/callback"
}
```

**Response:**
```json
{
  "received": true,
  "message_id": "msg-123",
  "status": "processing" | "completed" | "failed",
  "result": {}
}
```

---

### 3.2 Business Logic Endpoints

#### [Endpoint 1 Name]
```
[METHOD] /api/v1/[endpoint]
```

**Purpose:** [What this endpoint does]

**Authentication:** Required (JWT)

**Request:**
```json
{
  "field1": "value",
  "field2": 123
}
```

**Response (200 OK):**
```json
{
  "data": {
    "id": 1,
    "field": "value"
  },
  "meta": {
    "timestamp": "2025-11-15T12:00:00Z"
  }
}
```

**Errors:**
- 400 Bad Request - Invalid input
- 401 Unauthorized - Missing/invalid JWT
- 404 Not Found - Resource doesn't exist
- 500 Internal Server Error - Server failure

---

#### [Endpoint 2 Name]
[Repeat pattern above for each endpoint]

---

## 4. DATA MODEL

### 4.1 Database Schema

#### [Table 1 Name]
```sql
CREATE TABLE [table_name] (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `idx_[table]_[field]` on `[field]`

**Constraints:**
- Unique on `name`

---

### 4.2 Pydantic Models

```python
from pydantic import BaseModel, Field

class [ModelName]Create(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None

class [ModelName]Response(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True
```

---

## 5. BUSINESS LOGIC

### 5.1 Core Workflows

#### [Workflow 1 Name]
**Trigger:** [What initiates this workflow]

**Steps:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Result:** [What happens]

**Error Handling:**
- If [error condition], then [action]

---

### 5.2 Integration Patterns

#### Registry Integration
```python
# Register on startup
async def register_with_registry():
    response = await httpx.post(
        "http://registry:8000/register",
        json={
            "name": "[service-name]",
            "droplet_id": [XX],
            "port": [XXXX],
            "capabilities": ["capability1"]
        }
    )
    return response.json()["token"]
```

#### Orchestrator Integration
```python
# Send heartbeat every 60s
async def send_heartbeat():
    await httpx.post(
        "http://orchestrator:8001/heartbeat",
        headers={"Authorization": f"Bearer {jwt_token}"},
        json={"service_id": service_id, "status": "active"}
    )
```

---

## 6. CONFIGURATION

### 6.1 Environment Variables

```bash
# Service Identity
SERVICE_NAME=[service-name]
SERVICE_PORT=[XXXX]
DROPLET_ID=[XX]

# Infrastructure
REGISTRY_URL=http://registry:8000
ORCHESTRATOR_URL=http://orchestrator:8001
DATABASE_URL=postgresql://user:pass@localhost/db

# External APIs
[API_NAME]_API_KEY=[if needed]

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 6.2 Settings Class

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "[service-name]"
    service_port: int = [XXXX]
    droplet_id: int = [XX]
    database_url: str
    registry_url: str = "http://registry:8000"

    class Config:
        env_file = ".env"
```

---

## 7. DEPLOYMENT

### 7.1 Docker Configuration

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE [XXXX]

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import requests; requests.get('http://localhost:[XXXX]/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "[XXXX]"]
```

**Docker Labels:**
```dockerfile
LABEL droplet.id="[XX]"
LABEL droplet.name="[service-name]"
LABEL droplet.version="1.0.0"
LABEL droplet.udc_compliant="true"
```

---

### 7.2 Deployment Command

```bash
# Build
docker build -t fpai/[service-name]:1.0.0 .

# Run
docker run -d \
  --name [service-name] \
  --network fpai-network \
  -p [XXXX]:[XXXX] \
  -e DATABASE_URL=postgresql://... \
  -e REGISTRY_URL=http://registry:8000 \
  fpai/[service-name]:1.0.0
```

---

## 8. TESTING

### 8.1 Test Coverage Requirements

- UDC endpoints: 100%
- Business logic: >80%
- Error cases: >60%

### 8.2 Test Structure

```
tests/
├── test_health.py      # UDC endpoints
├── test_api.py         # Business logic
├── test_integration.py # Integration with other services
└── conftest.py         # Fixtures
```

### 8.3 Example Tests

```python
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded", "unhealthy"]

def test_create_resource():
    response = client.post(
        "/api/v1/resource",
        headers=auth_headers,
        json={"name": "test"}
    )
    assert response.status_code == 201
    assert response.json()["data"]["name"] == "test"
```

---

## 9. SECURITY

### 9.1 Authentication
- All endpoints (except /health) require JWT
- JWT verified against Registry public key
- Token expiration checked

### 9.2 Input Validation
- All inputs validated with Pydantic
- SQL queries parameterized (no string concatenation)
- File paths validated (no path traversal)

### 9.3 Secrets Management
- No secrets in code or git
- Environment variables for configuration
- credentials-manager for sensitive data

---

## 10. MONITORING

### 10.1 Metrics
- Request count (by endpoint, status)
- Request duration (by endpoint)
- Error rate
- [Service-specific metrics]

### 10.2 Logging
- Structured JSON logging
- Security events logged
- No secrets in logs

---

## 11. COMPLIANCE CHECKLIST

- [ ] All 5 UDC endpoints implemented
- [ ] Registers with Registry on startup
- [ ] Sends heartbeat to Orchestrator
- [ ] JWT authentication implemented
- [ ] Pydantic validation on all inputs
- [ ] Dockerfile with proper labels
- [ ] Tests with >80% coverage
- [ ] README documentation
- [ ] Foundation Files followed

---

## 12. OPEN QUESTIONS

[List any unresolved questions or decisions needed]

---

**This SPEC is the contract. Build matches SPEC exactly.**

🌐⚡💎
