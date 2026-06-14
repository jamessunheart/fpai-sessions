# Droplet #10: Orchestrator API Reference

**Version:** 2.0.0  
**Endpoint:** https://drop10.fullpotential.ai  
**Communication Standard:** Unified Droplet Communication (UDC) Protocol  
**Steward:** Tnsae

This document provides comprehensive API reference for the Orchestrator droplet, the central nervous system of the Full Potential AI droplet mesh. It coordinates all task routing, manages workflow state transitions, and maintains system-wide operational awareness.

---

## Table of Contents

1. [Overview](#overview)
2. [UDC Communication Standard](#udc-communication-standard)
3. [Authentication](#authentication)
4. [Health & Status Endpoints](#health--status-endpoints)
5. [Task Management Endpoints](#task-management-endpoints)
6. [Droplet Management Endpoints](#droplet-management-endpoints)
7. [Inter-Droplet Messaging](#inter-droplet-messaging)
8. [Metrics & Analytics](#metrics--analytics)
9. [WebSocket Real-Time Updates](#websocket-real-time-updates)
10. [Management Endpoints](#management-endpoints)
11. [Error Handling](#error-handling)
12. [Rate Limiting](#rate-limiting)

---

## Overview

The Orchestrator serves as the coordination hub for all droplets in the mesh. Key responsibilities:

- **Task Routing**: Automatically routes tasks to appropriate droplets based on capabilities
- **Health Monitoring**: Tracks droplet health via heartbeats every 60 seconds
- **State Management**: Manages task lifecycle through defined state transitions
- **Real-time Updates**: Broadcasts events via WebSocket to connected clients
- **Inter-Droplet Communication**: Facilitates UDC-compliant messaging between droplets
- **Performance Analytics**: Provides metrics on task performance and system health

---

## UDC Communication Standard

All authenticated requests to the Orchestrator **must** wrap their functional data in a UDC (Unified Droplet Communication) JSON envelope.

### UDC Request Envelope Structure

```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-5",
  "target": "droplet-10",
  "message_type": "command",
  "timestamp": "2025-11-14T10:30:00Z",
  "payload": {
    // Actual request data goes here
  }
}
```

### UDC Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `udc_version` | string | Yes | UDC protocol version (currently "1.0") |
| `trace_id` | string (UUID) | Yes | Unique identifier for tracking request across mesh |
| `source` | string | Yes | Identifier of sending droplet (e.g., "droplet-5") |
| `target` | string | Yes | Identifier of target droplet (e.g., "droplet-10") |
| `message_type` | string | Yes | Type of message: "command", "query", "response", "event", "heartbeat" |
| `timestamp` | string (ISO 8601) | Yes | UTC timestamp when message was created |
| `payload` | object | Yes | The actual data structure specific to the endpoint |

### UDC Response Envelope Structure

All responses are automatically wrapped in a UDC envelope:

```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-10",
  "target": "droplet-5",
  "message_type": "response",
  "timestamp": "2025-11-14T10:30:01Z",
  "payload": {
    // Response data
  }
}
```

### Environment Variables Setup

```bash
# Set environment variables for examples
export ENDPOINT="https://drop10.fullpotential.ai"
export TOKEN="<YOUR_JWT_AUTH_TOKEN_HERE>"
export SOURCE_ID=5  # Your droplet ID
```

---

## Authentication

### JWT Token Authentication

Most endpoints require JWT authentication via the `Authorization` header.

#### Token Structure

```
Authorization: Bearer <JWT_TOKEN>
```

#### JWT Claims

```json
{
  "droplet_id": 5,
  "steward": "YourName",
  "permissions": ["read", "write"],
  "exp": 1763213744,
  "iat": 1763127344
}
```

### Obtaining a Token

**Endpoint:** `POST /token`

**Request Body:**
```json
{
  "droplet_id": 5,
  "steward": "YourName",
  "permissions": ["read", "write"]
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/token" \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_id": 5,
    "steward": "YourName",
    "permissions": ["read", "write"]
  }'
```

### Public Endpoints (No Auth Required)

The following endpoints are public and do not require authentication:
- `GET /health`
- `GET /capabilities`
- `GET /state`
- `GET /dependencies`

---

## Health & Status Endpoints

### GET /health

Basic health check endpoint. Returns operational status of the Orchestrator.

**Authentication:** None (Public)

**Response Model:** `HealthResponse`

**Response Fields:**
- `id` (integer): Droplet ID (10)
- `name` (string): Droplet name ("Orchestrator")
- `steward` (string): Steward name
- `status` (string): Current status ("active", "inactive", "error")
- `endpoint` (string): Droplet endpoint URL
- `updated_at` (string): ISO 8601 timestamp
- `message` (string): Status message

**curl Example:**
```bash
curl -X GET "$ENDPOINT/health"
```

**Example Response:**
```json
{
  "id": 10,
  "name": "Orchestrator",
  "steward": "Tnsae",
  "status": "active",
  "endpoint": "https://drop10.fullpotential.ai",
  "updated_at": "2025-11-14T10:30:00Z",
  "message": "All systems operational"
}
```

---

### GET /capabilities

Returns list of features and capabilities supported by the Orchestrator.

**Authentication:** None (Public)

**Response Model:** `CapabilitiesResponse`

**curl Example:**
```bash
curl -X GET "$ENDPOINT/capabilities"
```

**Example Response:**
```json
{
  "version": "2.0.0",
  "features": [
    "task_routing",
    "droplet_discovery",
    "health_monitoring",
    "workflow_management",
    "real_time_updates",
    "task_recovery",
    "state_machine_management",
    "priority_queuing",
    "automatic_retry"
  ],
  "dependencies": ["registry"],
  "udc_version": "1.0"
}
```

---

### GET /state

Returns current system resource usage and operational metrics.

**Authentication:** None (Public)

**Response Model:** `StateResponse`

**curl Example:**
```bash
curl -X GET "$ENDPOINT/state"
```

**Example Response:**
```json
{
  "cpu_percent": 23.4,
  "memory_mb": 512,
  "uptime_seconds": 86400,
  "custom_metrics": {
    "tasks_active": 15,
    "tasks_pending": 8,
    "droplets_active": 12,
    "droplets_total": 15,
    "num_threads": 24
  }
}
```

---

### GET /dependencies

Returns status of all upstream and downstream dependencies.

**Authentication:** None (Public)

**Response Model:** `DependenciesResponse`

**curl Example:**
```bash
curl -X GET "$ENDPOINT/dependencies"
```

**Example Response:**
```json
{
  "required": [
    {
      "id": 3,
      "name": "Registry v2",
      "status": "connected",
      "last_check": "2025-11-14T10:30:00Z"
    }
  ],
  "optional": [
    {
      "id": 5,
      "name": "Dashboard",
      "status": "unknown",
      "last_check": null
    },
    {
      "id": 8,
      "name": "Verifier",
      "status": "unknown",
      "last_check": null
    }
  ],
  "missing": []
}
```

---

## Task Management Endpoints

All task endpoints require JWT authentication and use UDC envelope wrapping.

### POST /tasks

Create a new task in the orchestrator queue.

**Authentication:** Required (JWT)

**Request Payload Structure:**
```json
{
  "task_type": "verify",
  "title": "Verify Droplet #14 code",
  "description": "UDC compliance check",
  "required_capability": "code_verification",
  "priority": 3,
  "max_retries": 3,
  "deadline": "2025-11-14T12:00:00Z",
  "payload": {
    "code_url": "https://github.com/fullpotential-ai/droplet-14",
    "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md"
  }
}
```

**Request Fields:**
- `task_type` (string, required): Type of task ("build", "verify", "deploy", "monitor", etc.)
- `title` (string, required): Human-readable task title
- `description` (string, optional): Detailed task description
- `required_capability` (string, optional): Required droplet capability for routing
- `priority` (integer, optional): Priority 1-10 (1=highest, 10=lowest). Default: 5
- `max_retries` (integer, optional): Maximum retry attempts. Default: 3
- `deadline` (string, optional): ISO 8601 deadline for task completion
- `payload` (object, required): Task-specific data
- `created_by` (string, optional): Creator identifier. Defaults to requesting droplet ID

**Response Payload:**
```json
{
  "task_id": 123,
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2025-11-14T10:30:00Z",
  "estimated_assignment_seconds": 10
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "udc_version": "1.0",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "source": "droplet-'$SOURCE_ID'",
    "target": "droplet-10",
    "message_type": "command",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "payload": {
      "task_type": "verify",
      "title": "Verify Droplet #14 code",
      "description": "UDC compliance check",
      "required_capability": "code_verification",
      "priority": 3,
      "max_retries": 3,
      "deadline": "2025-11-14T12:00:00Z",
      "payload": {
        "code_url": "https://github.com/fullpotential-ai/droplet-14",
        "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md"
      }
    }
  }'
```

---

### GET /tasks

List tasks with optional filtering and pagination.

**Authentication:** Required (JWT)

**Query Parameters:**
- `status` (string, optional): Filter by status ("pending", "assigned", "in_progress", "completed", "failed", "cancelled")
- `task_type` (string, optional): Filter by task type
- `priority_min` (integer, optional): Minimum priority (1-10)
- `priority_max` (integer, optional): Maximum priority (1-10)
- `assigned_droplet_id` (integer, optional): Filter by assigned droplet ID
- `limit` (integer, optional): Number of results (1-500). Default: 50
- `offset` (integer, optional): Pagination offset. Default: 0

**Response Payload:**
```json
{
  "tasks": [
    {
      "id": 123,
      "trace_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_type": "verify",
      "title": "Verify Droplet #14 code",
      "description": "UDC compliance check",
      "payload": {...},
      "status": "in_progress",
      "priority": 3,
      "assigned_droplet_id": 8,
      "assigned_droplet_name": "Verifier",
      "created_at": "2025-11-14T10:30:00Z",
      "assigned_at": "2025-11-14T10:30:15Z",
      "started_at": "2025-11-14T10:30:20Z",
      "completed_at": null
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/tasks?status=pending&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /tasks/{task_id}

Get detailed information about a specific task, including state history.

**Authentication:** Required (JWT)

**Path Parameters:**
- `task_id` (integer, required): Task ID

**Response Payload:**
```json
{
  "task": {
    "id": 123,
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_type": "verify",
    "title": "Verify Droplet #14 code",
    "description": "UDC compliance check",
    "payload": {...},
    "status": "completed",
    "priority": 3,
    "assigned_droplet_id": 8,
    "assigned_droplet_name": "Verifier",
    "created_at": "2025-11-14T10:30:00Z",
    "assigned_at": "2025-11-14T10:30:15Z",
    "started_at": "2025-11-14T10:30:20Z",
    "completed_at": "2025-11-14T10:35:30Z",
    "result": {
      "verification_status": "passed",
      "issues_found": 0
    },
    "error_message": null,
    "state_history": [
      {
        "from_status": null,
        "to_status": "pending",
        "changed_by": "droplet_5",
        "reason": null,
        "changed_at": "2025-11-14T10:30:00Z"
      },
      {
        "from_status": "pending",
        "to_status": "assigned",
        "changed_by": "system",
        "reason": "Assigned to Verifier (#8)",
        "changed_at": "2025-11-14T10:30:15Z"
      },
      {
        "from_status": "assigned",
        "to_status": "in_progress",
        "changed_by": "droplet_8",
        "reason": null,
        "changed_at": "2025-11-14T10:30:20Z"
      },
      {
        "from_status": "in_progress",
        "to_status": "completed",
        "changed_by": "droplet_8",
        "reason": null,
        "changed_at": "2025-11-14T10:35:30Z"
      }
    ]
  }
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/tasks/123" \
  -H "Authorization: Bearer $TOKEN"
```

---

### PATCH /tasks/{task_id}

Update task status. Only the assigned droplet can update task status.

**Authentication:** Required (JWT)

**Path Parameters:**
- `task_id` (integer, required): Task ID

**Request Payload Structure:**
```json
{
  "status": "completed",
  "result": {
    "verification_status": "passed",
    "issues_found": 0
  },
  "error_message": null
}
```

**Request Fields:**
- `status` (string, required): New status ("assigned", "in_progress", "completed", "failed")
- `result` (object, optional): Task result data
- `error_message` (string, optional): Error message if task failed

**Response Payload:**
```json
{
  "task_id": 123,
  "status": "completed",
  "updated_at": "2025-11-14T10:35:30Z"
}
```

**curl Example:**
```bash
curl -X PATCH "$ENDPOINT/tasks/123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "udc_version": "1.0",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "source": "droplet-8",
    "target": "droplet-10",
    "message_type": "command",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "payload": {
      "status": "completed",
      "result": {
        "verification_status": "passed",
        "issues_found": 0
      }
    }
  }'
```

---

### DELETE /tasks/{task_id}

Cancel a pending or in-progress task. Only the task creator or admin can cancel tasks.

**Authentication:** Required (JWT with admin permission or task creator)

**Path Parameters:**
- `task_id` (integer, required): Task ID

**Response Payload:**
```json
{
  "task_id": 123,
  "status": "cancelled",
  "cancelled_at": "2025-11-14T10:32:00Z"
}
```

**curl Example:**
```bash
curl -X DELETE "$ENDPOINT/tasks/123" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Droplet Management Endpoints

### POST /droplets/register

Register a new droplet with the orchestrator. Called automatically on droplet startup.

**Authentication:** Required (JWT)

**Request Payload Structure:**
```json
{
  "droplet_id": 14,
  "name": "Visibility Deck",
  "steward": "Haythem",
  "endpoint": "https://visibility.fullpotential.ai",
  "capabilities": ["monitoring", "alerts", "snapshots"]
}
```

**Request Fields:**
- `droplet_id` (integer, required): Unique droplet identifier
- `name` (string, required): Human-readable droplet name
- `steward` (string, optional): Steward responsible for the droplet
- `endpoint` (string, required): Droplet's base URL
- `capabilities` (array of strings, required): List of capabilities this droplet provides

**Response Payload:**
```json
{
  "droplet_id": 14,
  "name": "Visibility Deck",
  "status": "active",
  "registered_at": "2025-11-14T10:30:00Z",
  "heartbeat_interval_seconds": 60,
  "next_heartbeat_deadline": 1699963860.0
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/droplets/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "udc_version": "1.0",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "source": "droplet-14",
    "target": "droplet-10",
    "message_type": "command",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "payload": {
      "droplet_id": 14,
      "name": "Visibility Deck",
      "steward": "Haythem",
      "endpoint": "https://visibility.fullpotential.ai",
      "capabilities": ["monitoring", "alerts", "snapshots"]
    }
  }'
```

---

### POST /droplets/{droplet_id}/heartbeat

Send a heartbeat to prove droplet liveness. Must be sent every 60 seconds.

**Authentication:** Required (JWT)

**Path Parameters:**
- `droplet_id` (integer, required): Droplet ID

**Request Payload Structure:**
```json
{
  "status": "active",
  "metrics": {
    "cpu_percent": 23.4,
    "memory_mb": 512,
    "requests_per_minute": 42
  }
}
```

**Request Fields:**
- `status` (string, required): Current droplet status ("active", "inactive", "error")
- `metrics` (object, optional): Current resource metrics

**Response Payload:**
```json
{
  "acknowledged": true,
  "next_heartbeat_deadline": 1699963860.0
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/droplets/14/heartbeat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "udc_version": "1.0",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "source": "droplet-14",
    "target": "droplet-10",
    "message_type": "command",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "payload": {
      "status": "active",
      "metrics": {
        "cpu_percent": 23.4,
        "memory_mb": 512,
        "requests_per_minute": 42
      }
    }
  }'
```

---

### GET /droplets

List all registered droplets with optional filtering.

**Authentication:** Required (JWT)

**Query Parameters:**
- `status` (string, optional): Filter by status ("active", "inactive", "error")
- `capability` (string, optional): Filter by capability

**Response Payload:**
```json
{
  "droplets": [
    {
      "droplet_id": 14,
      "name": "Visibility Deck",
      "steward": "Haythem",
      "endpoint": "https://visibility.fullpotential.ai",
      "capabilities": ["monitoring", "alerts", "snapshots"],
      "status": "active",
      "last_heartbeat": "2025-11-14T10:30:00Z",
      "registered_at": "2025-11-14T09:00:00Z",
      "seconds_since_heartbeat": 45.2
    }
  ],
  "total": 1,
  "filters": {
    "status": null,
    "capability": null
  }
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/droplets?status=active" \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /droplets/{droplet_id}

Get detailed information about a specific droplet.

**Authentication:** Required (JWT)

**Path Parameters:**
- `droplet_id` (integer, required): Droplet ID

**Response Payload:**
```json
{
  "droplet": {
    "droplet_id": 14,
    "name": "Visibility Deck",
    "steward": "Haythem",
    "endpoint": "https://visibility.fullpotential.ai",
    "capabilities": ["monitoring", "alerts", "snapshots"],
    "status": "active",
    "last_heartbeat": "2025-11-14T10:30:00Z",
    "registered_at": "2025-11-14T09:00:00Z",
    "seconds_since_heartbeat": 45.2,
    "recent_metrics": {
      "cpu_percent": 23.4,
      "memory_mb": 512,
      "requests_per_minute": 42
    },
    "assigned_tasks_count": 3,
    "completed_tasks_count": 157
  }
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/droplets/14" \
  -H "Authorization: Bearer $TOKEN"
```

---

### POST /droplets/{droplet_id}/activate

Manually activate a droplet. Requires admin permission or self-activation.

**Authentication:** Required (JWT with admin permission)

**Path Parameters:**
- `droplet_id` (integer, required): Droplet ID

**Response Payload:**
```json
{
  "droplet_id": 14,
  "name": "Visibility Deck",
  "old_status": "inactive",
  "new_status": "active",
  "activated_at": "2025-11-14T10:30:00Z",
  "activated_by": "droplet-5"
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/droplets/14/activate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### POST /droplets/{droplet_id}/deactivate

Manually deactivate a droplet. Requires admin permission. Triggers task reassignment if enabled.

**Authentication:** Required (JWT with admin permission)

**Path Parameters:**
- `droplet_id` (integer, required): Droplet ID

**Response Payload:**
```json
{
  "droplet_id": 14,
  "name": "Visibility Deck",
  "old_status": "active",
  "new_status": "inactive",
  "tasks_reassigned": 3,
  "deactivated_at": "2025-11-14T10:30:00Z",
  "deactivated_by": "droplet-5"
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/droplets/14/deactivate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### GET /droplets/{droplet_id}/capabilities

Get capabilities of a specific droplet.

**Authentication:** Required (JWT)

**Path Parameters:**
- `droplet_id` (integer, required): Droplet ID

**Response Payload:**
```json
{
  "droplet_id": 14,
  "name": "Visibility Deck",
  "capabilities": ["monitoring", "alerts", "snapshots"]
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/droplets/14/capabilities" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Inter-Droplet Messaging

### POST /message

Receive UDC-compliant messages from other droplets. This endpoint handles the full UDC envelope.

**Authentication:** Optional (JWT recommended)

**Request Structure:** Full UDC envelope with payload

**Supported Message Types:**
- `command`: Execute a command (e.g., create_task, cancel_task)
- `query`: Query information (e.g., task_status, droplet_list, system_status)
- `heartbeat`: Heartbeat ping
- `response`: Response to a previous message
- `event`: Event notification

**Command Examples:**

#### Create Task Command
```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-5",
  "target": "droplet-10",
  "message_type": "command",
  "timestamp": "2025-11-14T10:30:00Z",
  "payload": {
    "command": "create_task",
    "task_data": {
      "task_type": "verify",
      "title": "Verify Droplet #14",
      "priority": 3,
      "payload": {
        "code_url": "https://github.com/fullpotential-ai/droplet-14",
        "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md"
      }
    }
  }
}
```

#### Cancel Task Command
```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-5",
  "target": "droplet-10",
  "message_type": "command",
  "timestamp": "2025-11-14T10:30:00Z",
  "payload": {
    "command": "cancel_task",
    "task_id": 123
  }
}
```

**Query Examples:**

#### Task Status Query
```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-5",
  "target": "droplet-10",
  "message_type": "query",
  "timestamp": "2025-11-14T10:30:00Z",
  "payload": {
    "query": "task_status",
    "task_id": 123
  }
}
```

#### Droplet List Query
```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-5",
  "target": "droplet-10",
  "message_type": "query",
  "timestamp": "2025-11-14T10:30:00Z",
  "payload": {
    "query": "droplet_list",
    "filter": {
      "status": "active",
      "capability": "monitoring"
    }
  }
}
```

**Response:**
```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-10",
  "target": "droplet-5",
  "message_type": "response",
  "timestamp": "2025-11-14T10:30:01Z",
  "payload": {
    "received": true,
    "processed_at": "2025-11-14T10:30:01Z",
    "result": {
      "command": "create_task",
      "task_id": 123,
      "trace_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "pending"
    },
    "error": null
  }
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/message" \
  -H "Content-Type: application/json" \
  -d '{
    "udc_version": "1.0",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "source": "droplet-5",
    "target": "droplet-10",
    "message_type": "command",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "payload": {
      "command": "create_task",
      "task_data": {
        "task_type": "verify",
        "title": "Verify Droplet #14",
        "priority": 3,
        "payload": {
          "code_url": "https://github.com/fullpotential-ai/droplet-14"
        }
      }
    }
  }'
```

---

### POST /send

Send a UDC message to another droplet via the orchestrator.

**Authentication:** Required (JWT)

**Query Parameters:**
- `target_droplet_id` (integer, required): Target droplet ID
- `message_type` (string, required): Message type
- `payload` (object, required): Message payload

**Response Payload:**
```json
{
  "sent": true,
  "target_droplet": "Visibility Deck",
  "target_droplet_id": 14,
  "message_delivered_at": "2025-11-14T10:30:01Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/send?target_droplet_id=14&message_type=command" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "take_snapshot",
    "parameters": {
      "include_metrics": true
    }
  }'
```

---

### POST /broadcast

Broadcast a UDC message to multiple droplets. Requires admin permission.

**Authentication:** Required (JWT with admin permission)

**Query Parameters:**
- `message_type` (string, required): Message type
- `payload` (object, required): Message payload
- `capability_filter` (string, optional): Only send to droplets with this capability

**Response Payload:**
```json
{
  "broadcast": true,
  "total_droplets": 12,
  "successful": 11,
  "failed": 1,
  "results": [
    {
      "droplet_id": 14,
      "name": "Visibility Deck",
      "status": "sent"
    },
    {
      "droplet_id": 15,
      "name": "Alert Manager",
      "status": "failed",
      "error": "Timeout"
    }
  ],
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/broadcast?message_type=command&capability_filter=monitoring" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "refresh_metrics"
  }'
```

---

## Metrics & Analytics

### GET /metrics/summary

Get system-wide metrics summary.

**Authentication:** Required (JWT)

**Response Payload:**
```json
{
  "tasks": {
    "total_created": 1247,
    "completed": 1189,
    "failed": 23,
    "pending": 15,
    "in_progress": 20,
    "average_completion_seconds": 245.67,
    "success_rate_percent": 98.1
  },
  "droplets": {
    "total_registered": 15,
    "active": 12,
    "inactive": 2,
    "error": 1
  },
  "system": {
    "uptime_seconds": 86400,
    "cpu_percent": 23.4,
    "memory_mb": 512,
    "requests_per_minute": 150
  }
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/metrics/summary" \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /metrics/tasks/performance

Get task performance metrics with time range filtering.

**Authentication:** Required (JWT)

**Query Parameters:**
- `task_type` (string, optional): Filter by task type
- `time_range` (string, optional): Time range ("1h", "24h", "7d", "30d"). Default: "24h"

**Response Payload:**
```json
{
  "task_type": "verify",
  "time_range": "24h",
  "metrics": {
    "count": 156,
    "completed_count": 152,
    "failed_count": 4,
    "success_rate": 97.44,
    "average_duration_seconds": 245.67,
    "p50_duration_seconds": 198.5,
    "p95_duration_seconds": 487.3,
    "p99_duration_seconds": 623.8
  }
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/metrics/tasks/performance?task_type=verify&time_range=24h" \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /metrics/tasks/by-type

Get task distribution by type.

**Authentication:** Required (JWT)

**Query Parameters:**
- `time_range` (string, optional): Time range. Default: "24h"

**Response Payload:**
```json
{
  "time_range": "24h",
  "task_types": [
    {
      "task_type": "verify",
      "count": 156,
      "completed": 152,
      "failed": 4,
      "success_rate": 97.44
    },
    {
      "task_type": "build",
      "count": 89,
      "completed": 85,
      "failed": 4,
      "success_rate": 95.51
    }
  ]
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/metrics/tasks/by-type?time_range=7d" \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /metrics/droplets/{droplet_id}/performance

Get performance metrics for a specific droplet.

**Authentication:** Required (JWT)

**Path Parameters:**
- `droplet_id` (integer, required): Droplet ID

**Query Parameters:**
- `time_range` (string, optional): Time range. Default: "24h"

**Response Payload:**
```json
{
  "droplet_id": 8,
  "droplet_name": "Verifier",
  "time_range": "24h",
  "metrics": {
    "tasks_assigned": 156,
    "tasks_completed": 152,
    "tasks_failed": 4,
    "success_rate": 97.44,
    "average_duration_seconds": 245.67,
    "current_load": 3
  }
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/metrics/droplets/8/performance?time_range=24h" \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /metrics/routing

Get task routing performance metrics.

**Authentication:** Required (JWT)

**Response Payload:**
```json
{
  "routing_metrics": {
    "average_routing_time_seconds": 2.3,
    "successful_routings": 1189,
    "failed_routings": 12,
    "routing_success_rate": 99.0,
    "droplet_utilization": {
      "droplet-8": 78.5,
      "droplet-14": 45.2,
      "droplet-15": 62.1
    }
  }
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/metrics/routing" \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /metrics/system/health

Get detailed system health metrics.

**Authentication:** Required (JWT)

**Response Payload:**
```json
{
  "database": {
    "connected": true,
    "query_latency_ms": 12.5,
    "connections_active": 5,
    "connections_max": 20
  },
  "scheduler": {
    "running": true,
    "jobs_scheduled": 5,
    "jobs_running": 2,
    "next_run_seconds": 15
  },
  "websocket": {
    "connections": 8,
    "messages_sent": 1247,
    "messages_received": 892
  }
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/metrics/system/health" \
  -H "Authorization: Bearer $TOKEN"
```

---

## WebSocket Real-Time Updates

### WebSocket: /ws/tasks

Subscribe to real-time task lifecycle events.

**Authentication:** Required (JWT via query parameter)

**Connection URL:**
```
wss://drop10.fullpotential.ai/ws/tasks?token=<JWT_TOKEN>
```

**Event Types:**
- `task_created`: New task created
- `task_assigned`: Task assigned to droplet
- `task_started`: Task execution started
- `task_completed`: Task completed successfully
- `task_failed`: Task failed
- `task_cancelled`: Task cancelled

**Event Message Format:**
```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-10",
  "target": "broadcast",
  "message_type": "event",
  "timestamp": "2025-11-14T10:30:00Z",
  "payload": {
    "event": "task_created",
    "task": {
      "id": 123,
      "trace_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_type": "verify",
      "title": "Verify Droplet #14 code",
      "priority": 3,
      "status": "pending",
      "created_at": "2025-11-14T10:30:00Z"
    }
  }
}
```

**Example (using wscat):**
```bash
wscat -c "wss://drop10.fullpotential.ai/ws/tasks?token=$TOKEN"
```

**Example (using Python):**
```python
import asyncio
import websockets
import json

async def listen_to_tasks():
    uri = f"wss://drop10.fullpotential.ai/ws/tasks?token={TOKEN}"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            event = json.loads(message)
            print(f"Event: {event['payload']['event']}")
            print(f"Task ID: {event['payload']['task']['id']}")

asyncio.run(listen_to_tasks())
```

---

### WebSocket: /ws/droplets

Subscribe to real-time droplet health events.

**Authentication:** Required (JWT via query parameter)

**Connection URL:**
```
wss://drop10.fullpotential.ai/ws/droplets?token=<JWT_TOKEN>
```

**Event Types:**
- `droplet_registered`: New droplet registered
- `droplet_health_changed`: Droplet health status changed
- `droplet_heartbeat_missed`: Droplet missed heartbeat

**Event Message Format:**
```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-10",
  "target": "broadcast",
  "message_type": "event",
  "timestamp": "2025-11-14T10:30:00Z",
  "payload": {
    "event": "droplet_health_changed",
    "droplet_id": 14,
    "droplet_name": "Visibility Deck",
    "old_status": "active",
    "new_status": "inactive",
    "reason": "Heartbeat timeout"
  }
}
```

**Example (using wscat):**
```bash
wscat -c "wss://drop10.fullpotential.ai/ws/droplets?token=$TOKEN"
```

---

### GET /ws/status

Get WebSocket connection statistics.

**Authentication:** Required (JWT)

**Response Payload:**
```json
{
  "websocket_status": {
    "total_connections": 8,
    "tasks_channel_connections": 5,
    "droplets_channel_connections": 3,
    "messages_sent_total": 1247,
    "messages_sent_per_minute": 42
  }
}
```

**curl Example:**
```bash
curl -X GET "$ENDPOINT/ws/status" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Management Endpoints

All management endpoints require admin permission in JWT.

### POST /management/reload-config

Reload configuration without restarting the service.

**Authentication:** Required (JWT with admin permission)

**Request Payload Structure:**
```json
{
  "config_source": "environment",
  "reason": "Applying new rate limits"
}
```

**Response Payload:**
```json
{
  "config_reloaded": true,
  "reloaded_at": "2025-11-14T10:30:00Z",
  "config_source": "environment"
}
```

**curl Example:**
```bash
curl -X POST "$ENDPOINT/management/reload-config" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "udc_version": "1.0",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "source": "droplet-5",
    "target": "droplet-10",
    "message_type": "command",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "payload": {
      "config_source": "environment",
      "reason": "Applying new rate limits"
    }
  }'
```

---

### POST /management/shutdown

Gracefully shutdown the orchestrator.

**Authentication:** Required (JWT with admin permission)

**Request Payload Structure:**
```json
{
  "reason": "Planned maintenance",
  "delay_seconds": 30
}
```

**Response Payload:**
```json
{
  "shutdown_initiated": true,
  "shutdown_at": "2025-11-14T10:30:30Z",
  "reason": "Planned maintenance"
}
```

---

### POST /management/emergency-stop

Emergency stop all task processing.

**Authentication:** Required (JWT with admin permission)

**Request Payload Structure:**
```json
{
  "reason": "Critical issue detected"
}
```

**Response Payload:**
```json
{
  "emergency_stop": true,
  "stopped_at": "2025-11-14T10:30:00Z",
  "tasks_stopped": 23,
  "scheduler_stopped": true
}
```

---

### GET /management/version

Get orchestrator version and build information.

**Authentication:** Required (JWT with admin permission)

**Response Payload:**
```json
{
  "version": "2.0.0",
  "build_date": "2025-11-13",
  "python_version": "3.11.6",
  "udc_version": "1.0",
  "features": [
    "task_routing",
    "droplet_discovery",
    "health_monitoring"
  ]
}
```

---

### GET /management/scheduler/jobs

Get list of scheduled background jobs.

**Authentication:** Required (JWT with admin permission)

**Response Payload:**
```json
{
  "jobs": [
    {
      "id": "health_monitor",
      "name": "Droplet Health Monitor",
      "next_run": "2025-11-14T10:31:00Z",
      "interval_seconds": 60,
      "last_run": "2025-11-14T10:30:00Z",
      "running": false
    },
    {
      "id": "task_router",
      "name": "Task Router",
      "next_run": "2025-11-14T10:30:10Z",
      "interval_seconds": 10,
      "last_run": "2025-11-14T10:30:00Z",
      "running": false
    }
  ]
}
```

---

### POST /management/scheduler/jobs/{job_id}/pause

Pause a scheduled job.

**Authentication:** Required (JWT with admin permission)

**Path Parameters:**
- `job_id` (string, required): Job ID

**Response Payload:**
```json
{
  "job_id": "health_monitor",
  "status": "paused",
  "paused_at": "2025-11-14T10:30:00Z"
}
```

---

### POST /management/scheduler/jobs/{job_id}/resume

Resume a paused job.

**Authentication:** Required (JWT with admin permission)

**Path Parameters:**
- `job_id` (string, required): Job ID

**Response Payload:**
```json
{
  "job_id": "health_monitor",
  "status": "running",
  "resumed_at": "2025-11-14T10:30:00Z",
  "next_run": "2025-11-14T10:31:00Z"
}
```

---

### POST /management/cache/clear

Clear internal caches.

**Authentication:** Required (JWT with admin permission)

**Response Payload:**
```json
{
  "cache_cleared": true,
  "cleared_at": "2025-11-14T10:30:00Z",
  "caches_cleared": ["routing_cache", "droplet_directory_cache"]
}
```

---

## Error Handling

### Error Response Format

All errors are returned in UDC-compliant format:

```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-10",
  "target": "droplet-5",
  "message_type": "error",
  "timestamp": "2025-11-14T10:30:00Z",
  "payload": {
    "error": true,
    "error_code": "VALIDATION_ERROR",
    "message": "Invalid task type",
    "details": {
      "field": "task_type",
      "reason": "Must be one of: build, verify, deploy, monitor"
    }
  }
}
```

### Common HTTP Status Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request format or parameters |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |
| 502 | Bad Gateway | Error from downstream service |
| 504 | Gateway Timeout | Timeout from downstream service |

### Common Error Codes

| Error Code | Description |
|------------|-------------|
| `INVALID_REQUEST` | Request format is invalid |
| `VALIDATION_ERROR` | Request validation failed |
| `AUTHENTICATION_ERROR` | Authentication failed |
| `PERMISSION_DENIED` | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | Requested resource not found |
| `STATE_TRANSITION_ERROR` | Invalid state transition |
| `ROUTING_ERROR` | Task routing failed |
| `INTERNAL_ERROR` | Internal server error |
| `DOWNSTREAM_ERROR` | Error from downstream service |

---

## Rate Limiting

The Orchestrator implements rate limiting to prevent abuse:

- **Standard endpoints**: 100 requests per minute per droplet
- **WebSocket connections**: 10 concurrent connections per droplet
- **Broadcast endpoint**: 10 requests per minute (admin only)

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1699963860
```

When rate limit is exceeded:
```json
{
  "error": true,
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Try again in 45 seconds.",
  "retry_after": 45
}
```

---

## Background Jobs

The Orchestrator runs several background jobs:

### Health Monitor
- **Frequency**: Every 60 seconds
- **Purpose**: Check droplet heartbeats and mark inactive droplets
- **Action**: Marks droplets as inactive if no heartbeat for 90+ seconds

### Task Router
- **Frequency**: Every 10 seconds
- **Purpose**: Route pending tasks to available droplets
- **Action**: Matches tasks to droplets based on capabilities and load

### Registry Sync
- **Frequency**: Every 5 minutes
- **Purpose**: Sync droplet directory from Registry
- **Action**: Updates local droplet cache from Registry

### Heartbeat Cleanup
- **Frequency**: Every 1 hour
- **Purpose**: Remove old heartbeat records
- **Action**: Deletes heartbeat records older than 7 days

### WebSocket Ping
- **Frequency**: Every 30 seconds
- **Purpose**: Keep WebSocket connections alive
- **Action**: Sends ping frames to all connected clients

---

## Task State Machine

Tasks follow a defined state machine:

```
pending → assigned → in_progress → completed
                                 → failed
                  → cancelled
```

### State Descriptions

- **pending**: Task created, awaiting assignment
- **assigned**: Task assigned to droplet, not yet started
- **in_progress**: Task being executed by droplet
- **completed**: Task finished successfully
- **failed**: Task failed (may be retried)
- **cancelled**: Task cancelled by user or system

### Valid Transitions

| From | To | Allowed By |
|------|-------|-----------|
| pending | assigned | System (task router) |
| pending | cancelled | Task creator or admin |
| assigned | in_progress | Assigned droplet |
| assigned | cancelled | Task creator or admin |
| in_progress | completed | Assigned droplet |
| in_progress | failed | Assigned droplet |
| failed | pending | System (retry logic) |

---

## Support & Contact

For issues, questions, or support:

- **Documentation**: https://docs.fullpotential.ai/orchestrator
- **Steward**: Tnsae
- **Status Page**: https://status.fullpotential.ai
- **Support**: support@fullpotential.ai

---

**Last Updated**: November 15, 2025  
**API Version**: 2.0.0  
**UDC Version**: 1.0
