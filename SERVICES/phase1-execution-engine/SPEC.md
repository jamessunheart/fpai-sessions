# SPEC - Phase 1 Execution Engine (Droplet #15)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 15
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The Phase 1 Execution Engine is a specialized workflow runner dedicated to the "Initial Launch" phase. It handles tasks like domain setup, initial outreach scripts, and early revenue verification.

### 1.2 Position in Ecosystem
- **Upstream:** Orchestrator (Droplet #14).
- **Downstream:** Domain registrars, email providers.
- **Role:** The Launchpad.

### 1.3 Dependencies
**Required Services:**
- Registry (Droplet #1)
- Orchestrator (Droplet #14)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **Workflow Orchestration** - Run linear sequences of tasks.
2. **State Persistence** - Resume interrupted workflows.
3. **Verification** - Check if a launch step succeeded (e.g., DNS propagation).

### 2.2 Supported Operations
- `start_workflow` - Begin a launch sequence.
- `get_status` - Check progress.

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
  "status": "healthy",
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
  "service_name": "phase1-execution-engine",
  "droplet_id": 15,
  "capabilities": ["workflow_execution"],
  "integration_endpoints": [
    {
      "path": "/api/v1/workflow",
      "method": "POST"
    }
  ]
}
```

---

### 3.2 Business Logic Endpoints

#### Start Workflow
```
POST /api/v1/workflow
```
**Request:**
```json
{
  "workflow_type": "domain_setup",
  "parameters": {"domain": "fullpotential.ai"}
}
```

---

## 4. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=phase1-execution-engine
SERVICE_PORT=8015
DROPLET_ID=15
REGISTRY_URL=http://registry:8000
```

---

## 6. DEPLOYMENT

### 6.1 Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8015
LABEL droplet.id="15"
LABEL droplet.name="phase1-execution-engine"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8015"]
```

---

## 7. COMPLIANCE CHECKLIST
- [x] All 5 UDC endpoints
- [x] Registers with Registry
- [x] Dockerized
