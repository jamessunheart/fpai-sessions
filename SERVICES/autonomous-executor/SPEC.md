# SPEC - Autonomous Executor (Droplet #20)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 20
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
Enables true self-optimization by accepting architect intent and executing the entire "Sacred Loop" autonomously—from intent to deployment. It eliminates manual boilerplate and enables the system to build itself.

### 1.2 Position in Ecosystem
This service sits in the **Orchestration Layer** (Acting as the hands of the Architect). It interacts with the Strategic Intelligence Service (brain) and the Deployer (execution arm).

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery
- Orchestrator (droplet #10) - Task queuing
- Verifier (droplet #8) - Quality assurance

**External Dependencies:**
- Claude API (Code Generation)
- GitHub API (Version Control)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Intent-to-Code]** - Transforms high-level requests ("Build X") into runnable services.
2. **[Full-Cycle Automation]** - Handles SPEC -> Package -> Build -> Verify -> Deploy loop.
3. **[Self-Recovery]** - Retries failed steps and requests fixes from Claude.

### 2.2 Supported Operations
- `submit_intent` - Start a new build.
- `track_progress` - WebSocket stream of build steps.
- `approve_checkpoint` - Human-in-the-loop gating.

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
  "version": "1.0.0",
  "timestamp": "2025-11-23T12:00:00Z"
}
```

#### Capabilities
```
GET /capabilities
```
**Response:**
```json
{
  "service_name": "autonomous-executor",
  "droplet_id": 20,
  "capabilities": ["code_gen", "build_automation", "deployment"],
  "supported_operations": ["build", "test", "deploy"],
  "integration_endpoints": [
    { "path": "/api/v1/builds", "method": "POST" }
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
  "status": "active",
  "active_builds": 1,
  "cpu_load": 0.45
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
    { "name": "registry", "status": "connected" },
    { "name": "verifier", "status": "connected" }
  ],
  "external_apis": [
    { "name": "claude", "status": "connected" }
  ]
}
```

#### Message
```
POST /message
```
**Response:**
```json
{
  "received": true,
  "status": "processed"
}
```

---

### 3.2 Business Logic Endpoints

#### Submit Build
```
POST /api/v1/builds
```
**Request:**
```json
{
  "intent": "Create a Twitter bot for daily summaries",
  "approval_mode": "auto"
}
```
**Response:**
```json
{
  "build_id": "build-999",
  "status": "queued"
}
```

#### Get Status
```
GET /api/v1/builds/{build_id}
```
**Response:**
```json
{
  "status": "building",
  "phase": "code_generation",
  "progress": 45
}
```

---

## 4. DATA MODEL

### 4.1 Build State
Tracks the lifecycle of every autonomous intent.

#### `builds`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Build ID |
| intent | Text | Original prompt |
| status | Enum | queued, building, verifying, complete |
| logs | JSON | Step-by-step output |

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=autonomous-executor
SERVICE_PORT=8400
DROPLET_ID=20
REGISTRY_URL=http://registry:8000
ANTHROPIC_API_KEY=sk-...
VERIFIER_URL=http://verifier:8008
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Registers with Registry
- [x] WebSocket progress streaming
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎
