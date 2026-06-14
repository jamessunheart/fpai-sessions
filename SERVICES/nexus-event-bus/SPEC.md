# SPEC - Nexus Event Bus (Droplet #5)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 5
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
Real-time event bus enabling instant communication, coordination, and synchronization between all droplets. It transforms file-based polling into live event streaming, allowing sessions to discover each other, claim work, and coordinate autonomously.

### 1.2 Position in Ecosystem
This service sits in the **Infrastructure Layer**, acting as the nervous system connecting the "Brain" (Strategic Intelligence) to the "Hands" (Executors) and "Voice" (Unified Chat).

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery
- SSOT Filesystem - Sync target

**External Dependencies:**
- Redis (Optional persistence)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Real-Time Streaming]** - WebSocket-based pub/sub for instant updates.
2. **[Session Discovery]** - Live tracking of online sessions and capabilities.
3. **[Work Coordination]** - Atomic claiming of tasks to prevent conflicts.

### 2.2 Supported Operations
- `subscribe` - Listen for specific topics (`work.*`, `alert.*`).
- `publish` - Broadcast an event.
- `claim_work` - Lock a task ID.

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
  "service_name": "nexus-event-bus",
  "droplet_id": 5,
  "capabilities": ["websocket", "pubsub", "coordination"],
  "supported_operations": ["subscribe", "publish", "claim"],
  "integration_endpoints": [
    { "path": "/ws/session/{id}", "method": "WEBSOCKET" }
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
  "connected_sessions": 12,
  "events_per_sec": 45
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
    { "name": "registry", "status": "connected" }
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

#### WebSocket Connection
`ws://host:8450/ws/session/{session_id}`

**Protocol:**
- Client sends: `{"action": "subscribe", "topics": ["global"]}`
- Server sends: `{"event": "work.claimed", "payload": {...}}`

#### Publish Event (HTTP)
```
POST /api/v1/events
```
**Request:**
```json
{
  "topic": "alert.critical",
  "payload": { "msg": "Disk full" }
}
```

---

## 4. DATA MODEL

### 4.1 Event Schema
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Event ID |
| topic | String | Routing key |
| origin | String | Sender ID |
| payload | JSON | Data |
| timestamp | ISO8601 | Creation time |

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=nexus-event-bus
SERVICE_PORT=8450
DROPLET_ID=5
REGISTRY_URL=http://registry:8000
LOG_LEVEL=INFO
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] WebSocket implementation
- [x] Registers with Registry
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎
