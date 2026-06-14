# SPEC - Mission Control (Droplet #14)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 14
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
Mission Control is the tactical interface for human operators to view, approve, and intervene in autonomous operations. It hosts the "God Mode" dashboard and acts as the primary HMI (Human-Machine Interface).

### 1.2 Position in Ecosystem
- **Upstream:** Consumes data from Registry, Orchestrator, and all active droplets.
- **Downstream:** Sends approval/rejection signals to Orchestrator.
- **Role:** Command Center.

### 1.3 Dependencies
**Required Services:**
- Registry (Droplet #1)
- Orchestrator (Droplet #14)
- Dashboard (Droplet #2)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **System Visualization** - See the mesh in real-time (via Registry Map).
2. **Task Approval** - Review queued autonomous actions (high-risk).
3. **Override** - Manually stop/start services or missions.

### 2.2 Supported Operations
- `get_pending_approvals` - List tasks needing human eyes.
- `approve_task` / `reject_task` - Signal decision.
- `emergency_stop` - Halt specific droplets.

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
  "service_name": "mission-control",
  "droplet_id": 14,
  "capabilities": ["approval_workflow", "system_override"],
  "integration_endpoints": [
    {
      "path": "/api/v1/approvals",
      "method": "GET"
    }
  ]
}
```

---

### 3.2 Business Logic Endpoints

#### List Approvals
```
GET /api/v1/approvals
```
**Response:**
```json
{
  "tasks": [
    {"id": "t-123", "description": "Post to LinkedIn", "risk_level": "medium"}
  ]
}
```

#### Submit Decision
```
POST /api/v1/approvals/{task_id}
```
**Request:**
```json
{
  "decision": "approve",
  "comment": "Looks good"
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema

#### Decisions
```sql
CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100),
    decision VARCHAR(20), -- 'approve', 'reject'
    operator_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=mission-control
SERVICE_PORT=8014
DROPLET_ID=14
REGISTRY_URL=http://registry:8000
ORCHESTRATOR_URL=http://orchestrator:8001
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
EXPOSE 8014
LABEL droplet.id="14"
LABEL droplet.name="mission-control"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8014"]
```

---

## 7. COMPLIANCE CHECKLIST
- [x] All 5 UDC endpoints
- [x] Registers with Registry
- [x] Dockerized
