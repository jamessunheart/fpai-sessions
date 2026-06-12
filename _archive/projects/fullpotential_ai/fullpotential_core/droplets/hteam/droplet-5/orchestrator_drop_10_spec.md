
# Droplet #10: Orchestrator UDC API Reference

Endpoint: https://drop10.fullpotential.ai

I recommend you to visit the swagger at https://drop10.fullpotential.ai/docs for better understanding while reading this, 

temporarly use: https://drop10.fullpotential.ai/auth/token

{
  "droplet_id": 4,
  "secret_key": "xEx0PgTl08v7hHvFr4oRDhkkGIU2F9fZh5NzXiDJhRwO4_oI9j3O3yg1-lJsRBjbQ42T97TOXqPy6Etj6P9SnQ"
}

to get token for authentication

Communication Standard: Unified Droplet Communication (UDC) Protocol

This document details the required UDC payload structure for inter-droplet communication and core Orchestrator functions, alongside `curl` examples.

## 1. 🧬 Unified Droplet Communication (UDC) Format

All authenticated requests to the Orchestrator **must** wrap their functional data (the `payload`) inside a UDC JSON envelope.

### A. UDC Request Envelope

| **Field**                | **Type** | **Description**                                                                                   |
| ------------------------------ | -------------- | ------------------------------------------------------------------------------------------------------- |
| `metadata`                   | `object`     | Contains routing and trace information.                                                                 |
| `metadata.source_droplet_id` | `integer`    | The ID of the sending Droplet (must match the ID in the JWT).                                           |
| `metadata.timestamp`         | `string`     | ISO 8601 timestamp of the request creation.                                                             |
| `metadata.trace_id`          | `string`     | A UUID for tracking the request across the mesh.**Always include this.**                          |
| `payload`                    | `object`     | The actual data structure (e.g., a `TaskCreate`model,`DropletHeartbeat`data, or a generic message). |

### B. Standard `curl` Setup

Use the following variables for the examples:

* `$ENDPOINT`: `https://drop10.fullpotential.ai`
* `$TOKEN`: Your valid JWT.
* `$SOURCE_ID`: Your Droplet ID.

```
# Set environment variables for easy copy/paste
export ENDPOINT="[https://drop10.fullpotential.ai](https://drop10.fullpotential.ai)"
export TOKEN="<YOUR_JWT_AUTH_TOKEN_HERE>"
export SOURCE_ID=42

```

## 2. 🎯 Task Management (`/tasks`)

### 2.1. Create a New Task (`POST /tasks`)

Used by any Droplet (or the Coordinator) to submit a new work item.

**`curl` Example:**

```
curl -X 'POST' \
  'https://drop10.fullpotential.ai/tasks' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkcm9wbGV0X2lkIjo0LCJzdGV3YXJkIjoiVG5zYWU2IiwicGVybWlzc2lvbnMiOlsicmVhZCIsIndyaXRlIl0sImV4cCI6MTc2MzIxMzc0NCwiaWF0IjoxNzYzMTI3MzQ0fQ.NJUX14ImrKUxqd3nNF28rKB3QzGgqq6k9Kd1I6bxgRw' \
  -H 'Content-Type: application/json' \
  -d '{
  "message_type": "command",
  "payload": {
    "deadline": "2025-11-14T12:00:00Z",
    "description": "UDC compliance check",
    "max_retries": 3,
    "priority": 3,
    "required_capability": "code_verification",
    "task_type": "verify",
    "title": "Verify Droplet #14 code",
    "payload": {
      "code_url": "https://github.com/fullpotential-ai/droplet-14",
      "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md"
    }
  },
  "source": "droplet-5",
  "target": "droplet-10",
  "timestamp": "2025-11-14T10:30:00Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "udc_version": "1.0"
}'
```

## 3. 💧 Droplet Management (`/droplets`)

### 3.1. Register Droplet (`POST /droplets/register`)

Used by a new Droplet on startup to announce its capabilities and location.

**`curl` Example:**

```
curl -X 'POST' \
  'https://drop10.fullpotential.ai/droplets/register' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkcm9wbGV0X2lkIjo0LCJzdGV3YXJkIjoiVG5zYWU2IiwicGVybWlzc2lvbnMiOlsicmVhZCIsIndyaXRlIl0sImV4cCI6MTc2MzIxMzc0NCwiaWF0IjoxNzYzMTI3MzQ0fQ.NJUX14ImrKUxqd3nNF28rKB3QzGgqq6k9Kd1I6bxgRw' \
  -H 'Content-Type: application/json' \
  -d '{
  "message_type": "command",
  "payload": {
    "capabilities": [
      "monitoring",
      "alerts",
      "snapshots"
    ],
    "droplet_id": 14,
    "endpoint": "https://visibility.fullpotential.ai",
    "name": "Visibility Deck",
    "steward": "Haythem"
  },
  "source": "droplet-14",
  "target": "droplet-10",
  "timestamp": "2025-11-14T10:30:00Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "udc_version": "1.0"
}'

```

### 3.2. Send Heartbeat (`POST /droplets/heartbeat`)

Used periodically by active Droplets to prove liveness and report current load.

**`curl` Example:**

```
curl -X 'POST' \
  'https://drop10.fullpotential.ai/droplets/4/heartbeat' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkcm9wbGV0X2lkIjo0LCJzdGV3YXJkIjoiVG5zYWU2IiwicGVybWlzc2lvbnMiOlsicmVhZCIsIndyaXRlIl0sImV4cCI6MTc2MzIxMzc0NCwiaWF0IjoxNzYzMTI3MzQ0fQ.NJUX14ImrKUxqd3nNF28rKB3QzGgqq6k9Kd1I6bxgRw' \
  -H 'Content-Type: application/json' \
  -d '{
  "message_type": "command",
  "payload": {
    "metrics": {
      "cpu_percent": 23.4,
      "memory_mb": 512,
      "requests_per_minute": 42
    },
    "status": "active"
  },
  "source": "droplet-14",
  "target": "droplet-10",
  "timestamp": "2025-11-14T10:31:00Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "udc_version": "1.0"
}'
```

## 4. 🤝 Inter-Droplet Messaging (`/message`)

This is the standard for one Droplet to communicate directly with another *via* the Orchestrator. The Orchestrator acts as the router/broker.

### 4.1. Send Message(`POST /message/`)

Used by Droplet A to send a message.

**`curl` Example (Sending a request to Droplet ID 15):**

```
curl -X 'POST' \
  'https://drop10.fullpotential.ai/message' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkcm9wbGV0X2lkIjo0LCJzdGV3YXJkIjoiVG5zYWU2IiwicGVybWlzc2lvbnMiOlsicmVhZCIsIndyaXRlIl0sImV4cCI6MTc2MzIxMzc0NCwiaWF0IjoxNzYzMTI3MzQ0fQ.NJUX14ImrKUxqd3nNF28rKB3QzGgqq6k9Kd1I6bxgRw' \
  -H 'Content-Type: application/json' \
  -d '{
  "message_type": "command",
  "payload": {
    "command": "create_task",
    "task_data": {
      "payload": {
        "code_url": "https://github.com/fullpotential-ai/droplet-14",
        "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md"
      },
      "priority": 3,
      "task_type": "verify",
      "title": "Verify Droplet #14"
    }
  },
  "source": 5,
  "target": 10,
  "timestamp": "2025-11-14T10:30:00Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}'
```

### 4.2. Send Message to Specific Droplet (`POST /send?target_droplet_id=15&message_type=command`)

Used by Droplet A to send a message to Droplet B.

**`curl` Example (Sending a request to Droplet ID 15):**

```
curl -X 'POST' \
  'https://drop10.fullpotential.ai/send?target_droplet_id=15&message_type=command' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkcm9wbGV0X2lkIjo0LCJzdGV3YXJkIjoiVG5zYWU2IiwicGVybWlzc2lvbnMiOlsicmVhZCIsIndyaXRlIl0sImV4cCI6MTc2MzIxMzc0NCwiaWF0IjoxNzYzMTI3MzQ0fQ.NJUX14ImrKUxqd3nNF28rKB3QzGgqq6k9Kd1I6bxgRw' \
  -H 'Content-Type: application/json' \
  -d '{
  "message_type": "command",
  "payload": {
    "command": "create_task",
    "task_data": {
      "payload": {
        "code_url": "https://github.com/fullpotential-ai/droplet-14",
        "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md"
      },
      "priority": 3,
      "task_type": "verify",
      "title": "Verify Droplet #14"
    }
  },
  "source": 5,
  "target": 10,
  "timestamp": "2025-11-14T10:30:00Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}'
```

## 5. ⚙️ Management & Metrics

### 5.1. Reload Configuration (`POST /management/reload-config`)

**Requires `admin` permission in the JWT.** Used to trigger a soft reload of configuration without full service restart.

**Payload Structure (inside UDC `payload`):**

**`curl` Example:**

```
# Replace $ADMIN_TOKEN with a JWT that has 'admin' permission
export ADMIN_TOKEN="<YOUR_ADMIN_JWT_HERE>"

curl -X POST "$ENDPOINT/management/reload-config" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "source_droplet_id": '$SOURCE_ID',
      "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")'",
      "trace_id": "'$(uuidgen)'"
    },
    "payload": {
      "config_source": "environment",
      "reason": "Applying new rate limits"
    }
}'

```

### 5.2. Get Metrics Summary (`GET /metrics/summary`)

Used to retrieve overall system performance metrics.

**Note:** Since this is a `GET` request, the UDC data is **not** in the request body. The Orchestrator will automatically construct a response UDC envelope for the returned metrics data.

**`curl` Example:**

```
curl -X GET "$ENDPOINT/metrics/summary" \
  -H "Authorization: Bearer $TOKEN"

```

## 6. 💚 Health & Status (Public Endpoints)

These endpoints are **exempt** from the full UDC *request* envelope requirement and return Pydantic models (which are UDC-compliant response structures) directly.

### 6.1. Basic Health Check (`GET /health`)

**No Authentication Required.**

```
curl -X GET "$ENDPOINT/health"

```

**Expected Response (Example, not UDC-wrapped):**

```
{
  "id": 10,
  "name": "Orchestrator",
  "status": "active",
  "version": "2.0.0",
  "endpoint": "[https://drop10.fullpotential.ai](https://drop10.fullpotential.ai)"
}

```

## 7. 🌐 Real-time Updates (`/ws`)

WebSockets bypass the standard HTTP/UDC request model. Authentication is handled via a query parameter. All *messages* streamed over the WebSocket are UDC-wrapped by the Orchestrator's internal manager.

### 7.1. WebSocket Connection Example

**Channel:** `/ws/tasks` (For task lifecycle updates)

```
# Example connection using wscat (or a browser/code client)
wscat -c "wss://drop10.fullpotential.ai/ws/tasks?token=$TOKEN"

```

**Expected Streamed Message (UDC-Wrapped Event):**

```
{
  "metadata": {
    "event_type": "task_created",
    "timestamp": "2025-11-14T10:30:00.000Z",
    "trace_id": "...",
    "source_droplet_id": 10
  },
  "payload": {
    "task_id": "new-task-a1",
    "status": "pending",
    "task_type": "data_processing",
    "created_by": 42
    // ... other task details
  }
}

```
