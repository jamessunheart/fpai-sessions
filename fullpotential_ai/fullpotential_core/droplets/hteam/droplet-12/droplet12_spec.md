# Droplet #12: Chat Orchestrator UDC API Reference

Endpoint: `https://drop12.fullpotential.ai`

This document details the API for Droplet #12, the Chat Orchestrator. It covers both UDC-compliant endpoints for inter-droplet communication and the public-facing API for client applications.

## 1. 🔑 Authentication

Most endpoints are protected and require a `Bearer` token in the `Authorization` header. This token is a JWT signed with the RS256 algorithm, issued by the Registry (Droplet #1).

For local testing, you can use the token found in the `test_heartbeat.ps1` script or generate a new one if you have the private key, as shown in `test.py`.

## 2. 🧬 Unified Droplet Communication (UDC) Format

Many requests and responses, especially for inter-droplet communication, are wrapped in a UDC JSON envelope.

### A. UDC Request Envelope

| **Field** | **Type** | **Description** |
| --- | --- | --- |
| `udc_version` | `string` | The version of the UDC protocol (e.g., "1.0"). |
| `trace_id` | `string` | A UUID for tracking the request across the mesh. |
| `source` | `string` | The ID of the sending Droplet (e.g., "droplet-1"). |
| `target` | `string` | The ID of the target Droplet (e.g., "droplet-12"). |
| `message_type`| `string` | The type of message (e.g., "command", "query", "response"). |
| `payload` | `object` | The actual data structure for the specific endpoint. |
| `timestamp` | `string` | ISO 8601 timestamp of the request creation. |

### B. Standard `curl` Setup

Use the following variables for the examples:

*   `$ENDPOINT`: `https://drop12.fullpotential.ai`
*   `$TOKEN`: Your valid JWT.

```bash
# Set environment variables for easy copy/paste
export ENDPOINT="https://drop12.fullpotential.ai"
export TOKEN="<YOUR_JWT_AUTH_TOKEN_HERE>" # Use token from test_heartbeat.ps1
```

---

## 3. 💚 UDC Health & Status Endpoints

These endpoints are required for UDC compliance and allow other droplets to monitor this droplet's status and capabilities. All endpoints in this section require JWT authentication.

### 3.1. Basic Health Check (`GET /health`)

Returns the basic operational status of the droplet.

**`curl` Example:**

```bash
curl -X GET "$ENDPOINT/health"
```

### 3.2. Get Capabilities (`GET /capabilities`)

Describes the features and capabilities of this droplet.

**`curl` Example:**

```bash
curl -X GET "$ENDPOINT/capabilities" \
  -H "Authorization: Bearer $TOKEN"
```

### 3.3. Get State (`GET /state`)

Provides current performance metrics and resource usage.

**`curl` Example:**

```bash
curl -X GET "$ENDPOINT/state" \
  -H "Authorization: Bearar $TOKEN"
```

### 3.4. Get Dependencies (`GET /dependencies`)

Lists the droplet's dependencies and their current connection status.

**`curl` Example:**

```bash
curl -X GET "$ENDPOINT/dependencies" \
  -H "Authorization: Bearer $TOKEN"
```

### 3.5. Receive Heartbeat (`POST /heartbeat`)

Receives a heartbeat from another droplet to confirm it's online. **Requires JWT authentication.**

**`curl` Example:**

```bash
curl -X POST "$ENDPOINT/heartbeat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "d2c4fc14-239e-4b84-b2e2-5af33f832e51",
    "source": "6",
    "target": "12",
    "message_type": "command",
    "payload": {
        "status": "active",
        "metrics": {
            "cpu_percent": 50,
            "memory_mb": 100
        }
    },
    "timestamp": "2025-11-15T10:00:00Z"
}'
```

---

## 4. 💬 Public Chat API (`/api`)

These endpoints are designed for direct use by client applications (web, mobile) and generally do not require JWT authentication.

### 4.1. Start or Continue a Chat (`POST /api/chat`)

The main endpoint for sending user messages to the chat orchestrator. It manages session history and routes requests to other droplets based on the user's intent.

**`curl` Example:**

```bash
curl -X POST "$ENDPOINT/api/chat" \
   -H "Authorization: Bearer $TOKEN" \
   -H "Content-Type: application/json" \
  -d '{
    "message": "Please create a verification task for Droplet #14. The code is at https://github.com/fullpotential-ai/droplet-14 and the spec is at https://github.com/fullpotential-ai/specs/droplet-14.md. Set priority to 3.",
    "session_id": "session-12345"
}'
```

---

## 5. 🤝 Inter-Droplet API (`/api`)

This section details endpoints used for communication from other droplets, typically routed through the main Orchestrator (Droplet #10).

### 5.1. Process a Message (`POST /api/process`)

This is the primary entry point for requests from other droplets (like the Voice Droplet #6). It processes a message within the UDC format, performs reasoning, and executes the required actions. **Requires JWT authentication.**

**`curl` Example:**

```bash
curl -X POST "$ENDPOINT/api/process" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "udc_version": "1.0",
    "trace_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "source": "6",
    "target": "12",
    "message_type": "query",
    "route_back": "6",
    "payload": {
        "message": "Get the latest system alerts",
        "metadata": {
            "user_id": "user-voice-77"
        }
    },
    "timestamp": "2025-11-17T14:00:00Z"
}'
```

---

## 6. 🧠 Session Management (`/api/sessions`)

Endpoints for inspecting and managing user conversation sessions. These are useful for debugging and admin purposes. They do not require JWT authentication.

### 6.1. List All Sessions (`GET /api/sessions`)

**`curl` Example:**

```bash
curl -X GET "$ENDPOINT/api/sessions"
```

### 6.2. Get a Specific Session (`GET /api/sessions/{session_id}`)

**`curl` Example:**

```bash
curl -X GET "$ENDPOINT/api/sessions/session-12345"
```

### 6.3. Delete a Specific Session (`DELETE /api/sessions/{session_id}`)

**`curl` Example:**

```bash
curl -X DELETE "$ENDPOINT/api/sessions/session-12345"
```

---

## 7. 🌐 Real-time Updates (`/ws`)

Provides a WebSocket for real-time, bidirectional communication with the chat orchestrator.

### 7.1. WebSocket Connection

Connect to the `/ws` endpoint to initiate a WebSocket session.

**Connection Example (using `wscat`):**

```bash
wscat -c "wss://drop12.fullpotential.ai/ws"
```

**Client Message Format (send to server):**

```json
{
    "type": "message",
    "content": "Hello, what can you do?",
    "session_id": "ws-session-abcde"
}
```

**Server Message Format (receive from server):**

```json
{
    "type": "welcome",
    "content": "👋 **Welcome to Chat Orchestrator!**...",
    "session_id": "ws-session-abcde",
    "timestamp": "2025-11-17T15:00:00Z"
}
```

---

## 8. 📢 Public Endpoints

These endpoints are exempt from authentication and are intended for public access.

### 8.1. Basic Health Check (`GET /health`)

Returns the basic operational status of the droplet. **No Authentication Required.**

**`curl` Example:**

```bash
curl -X GET "$ENDPOINT/health"
```
