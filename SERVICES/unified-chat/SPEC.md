# SPEC - Unified Chat (Droplet #8)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 8
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
A centralized chat interface that enables one human to command **12 Claude Code sessions** simultaneously. It aggregates responses from multiple sessions into a single coherent stream, acting as the voice of the collective intelligence.

### 1.2 Position in Ecosystem
This service sits in the **Interface Layer** (Human-to-Machine). It is the primary communication channel for the Architect to interact with the autonomous swarm.

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery
- Nexus Event Bus (droplet #5) - Message routing

**External Dependencies:**
- WebSocket Protocol (Real-time comms)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Multi-Session Broadcasting]** - Send one command, reach 12 sessions.
2. **[Response Aggregation]** - Collects and organizes replies from the swarm.
3. **[Secure Auth]** - Token-based access for the human operator.

### 2.2 Supported Operations
- `broadcast_message` - Send to all active sessions.
- `direct_message` - Target a specific session ID.
- `get_session_status` - See who is online/typing.

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
  "service_name": "unified-chat",
  "droplet_id": 8,
  "capabilities": ["chat", "broadcast", "aggregation"],
  "supported_operations": ["send", "receive"],
  "integration_endpoints": [
    { "path": "/ws/chat", "method": "WEBSOCKET" }
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
  "active_users": 1
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
    { "name": "nexus-event-bus", "status": "connected" }
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

#### Chat Interface
```
GET /chat
```
**Response:** HTML Chat UI

#### WebSocket Stream
`ws://host:8100/ws/chat`

**Protocol:**
- Client: `{"type": "broadcast", "content": "Report status"}`
- Server: `{"type": "reply", "sender": "session-5", "content": "All systems go."}`

---

## 4. DATA MODEL

### 4.1 Chat History (Transient)
Unified Chat currently operates with ephemeral history (persisted only in browser local storage or session memory).

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=unified-chat
SERVICE_PORT=8100
DROPLET_ID=8
REGISTRY_URL=http://registry:8000
NEXUS_URL=ws://nexus-event-bus:8450
AUTH_TOKEN_SECRET=...
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] WebSocket broadcasting implemented
- [x] Registers with Registry
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎
