# SPEC - Strategic Intelligence Service (Droplet #22)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 22
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The "Brain" of the Assembly Line. Continuously identifies gaps, calculates priorities, and dispatches missions. It transforms prioritization from a static/manual process into a continuous/autonomous loop, ensuring the execution layer always has high-impact work.

### 1.2 Position in Ecosystem
This service sits in the **Orchestration Layer**, above the Executors but below the human Architect. It reads from the Registry and Verification systems to direct the Autonomous Executor.

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery
- Orchestrator (droplet #10) - Task coordination
- Verifier (droplet #8) - Quality reports

**External Dependencies:**
- None (Purely internal logic)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[State Monitoring]** - Aggregates system health, revenue, and staging queue depth.
2. **[Gap Detection]** - Identifies missing components or failing services.
3. **[Mission Dispatch]** - Generates structured Intent files (`.json`) for executors.

### 2.2 Supported Operations
- `get_priorities` - Returns ranked list of system needs.
- `dispatch_mission` - Creates a new mission file.
- `analyze_gaps` - Runs a gap analysis report.

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
  "service_name": "strategic-intelligence",
  "droplet_id": 22,
  "capabilities": ["monitoring", "prioritization", "dispatch"],
  "supported_operations": ["get_priorities", "analyze_gaps"],
  "integration_endpoints": [
    { "path": "/api/v1/priorities", "method": "GET" }
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
  "active_missions": 3,
  "top_priority": "fix_registry"
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

#### Get Priorities
```
GET /api/v1/priorities
```
**Response:**
```json
{
  "ranked_tasks": [
    {
      "id": "fix-registry",
      "score": 95,
      "reason": "Core dependency offline"
    },
    {
      "id": "optimize-db",
      "score": 40,
      "reason": "Performance degraded"
    }
  ]
}
```

#### Analyze Gaps
```
POST /api/v1/analysis/run
```
**Response:**
```json
{
  "gaps_found": 2,
  "report_id": "gap-123"
}
```

---

## 4. DATA MODEL

### 4.1 Logic Engine
Prioritization is calculated on the fly based on:
- **Impact:** Revenue potential or system criticality.
- **Alignment:** Match with `NOW.md` goals.
- **Unblocked:** Are dependencies met?

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=strategic-intelligence
SERVICE_PORT=8500
DROPLET_ID=22
REGISTRY_URL=http://registry:8000
ORCHESTRATOR_URL=http://orchestrator:8001
VERIFIER_URL=http://verifier:8008
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Automated gap detection logic
- [x] Registers with Registry
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎

