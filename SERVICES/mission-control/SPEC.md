# SPEC - Mission Control (Droplet #14)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 14
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
Central visual interface and command center for the autonomous enterprise. Aggregates data from all droplets into "Brain," "Muscle," and "Immune" system views, allowing human operators to supervise, intervene, and steer the system.

### 1.2 Position in Ecosystem
This service sits in the **Interface Layer** (internal facing), acting as the primary HUD for the system administrator. It pulls data from the Registry, Orchestrator, and individual droplets.

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery
- Orchestrator (droplet #10) - Task status & control
- Verifier (droplet #8) - Health & compliance data

**External Dependencies:**
- ngrok (for secure tunnel access)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Unified Dashboard]** - Real-time visualization of system health and activity.
2. **[System Steering]** - Controls for pausing, restarting, or modifying autonomy levels.
3. **[Log Aggregation]** - Centralized stream of system-wide events.

### 2.2 Supported Operations
- `get_dashboard_view` - Returns consolidated system state.
- `send_command` - Issues control directives to other droplets.
- `stream_logs` - WebSocket feed of system activity.

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
  "service_name": "mission-control",
  "droplet_id": 14,
  "capabilities": ["dashboard", "steering", "monitoring"],
  "supported_operations": ["view_system", "command_system"],
  "integration_endpoints": [
    { "path": "/", "method": "GET" }
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
  "mode": "monitoring",
  "active_viewers": 1
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
    { "name": "orchestrator", "status": "connected" }
  ],
  "external_apis": [
    { "name": "ngrok", "status": "connected" }
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

### 3.2 Interface Endpoints

#### Dashboard Home
```
GET /
```
**Response:** HTML Dashboard Interface

#### System Status Partial
```
GET /partials/brain
```
**Response:** HTML fragment for Brain/Logic state

---

## 4. DATA MODEL

### 4.1 In-Memory State
Mission Control primarily aggregates ephemeral state from other services rather than maintaining a persistent database of its own. It caches the latest "World State" from the Registry/Orchestrator refresh cycles.

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=mission-control
SERVICE_PORT=8004
DROPLET_ID=14
REGISTRY_URL=http://registry:8000
ORCHESTRATOR_URL=http://orchestrator:8001
NGROK_AUTH_TOKEN=...
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Visualization of all connected droplets
- [x] Registers with Registry
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎

