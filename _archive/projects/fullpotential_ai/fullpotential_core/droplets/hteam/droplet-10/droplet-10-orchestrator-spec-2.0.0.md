# DROPLET_10_ORCHESTRATOR_SPECIFICATION.md
**Task Coordination and Workflow Management System**  
**Version:** 2.0.0  
**Updated:** November 15, 2025  
**Steward:** Tnsae  
**Status:** OPERATIONAL

---

## 1. 🎯 PURPOSE

The Orchestrator is the central nervous system of the Full Potential AI droplet mesh. It coordinates all task routing, manages workflow state transitions, and maintains system-wide operational awareness.

**TIER 1 IMPACT:**
Removes coordination bottleneck by automating task distribution, status tracking, and workflow management across all droplets. Enables autonomous operation at scale (10+ → 100+ droplets).

**CURRENT STATE:** Fully operational (v2.0.0)  
**THIS SPEC:** Documents production implementation

---

## 2. 📋 CORE REQUIREMENTS

### R1: Droplet Discovery & Registration
**As a** Droplet  
**I must be able to** auto-register with Orchestrator on startup  
**So that** I'm immediately available for task routing

**Implementation:** `POST /droplets/register` with capabilities declaration

### R2: Task Queue Management
**As a** Coordinator  
**I must be able to** submit tasks with priorities and requirements  
**So that** work flows through the system efficiently

**Implementation:** `POST /tasks` with priority-based queuing

### R3: Intelligent Task Routing
**As the** Orchestrator  
**I must be able to** route tasks to appropriate droplets based on capabilities  
**So that** work reaches the right executor automatically

**Implementation:** Background scheduler runs task router every 10 seconds

### R4: State Machine Workflow
**As a** System  
**I must be able to** track task states through defined transitions  
**So that** progress is visible and recoverable

**Implementation:** State machine service enforces valid transitions

### R5: Health Monitoring
**As the** Orchestrator  
**I must be able to** monitor all droplet health every 60 seconds  
**So that** failed droplets are detected and tasks rerouted

**Implementation:** Heartbeat monitoring with 90-second timeout

### R6: Real-time Status Updates
**As a** Dashboard  
**I must be able to** receive WebSocket updates on all task changes  
**So that** users see live system state

**Implementation:** WebSocket endpoints at `/ws/tasks` and `/ws/droplets`

### R7: Task Recovery
**As the** Orchestrator  
**I must be able to** reassign tasks from failed droplets  
**So that** work continues despite individual failures

**Implementation:** Automatic task reassignment on droplet failure

### R8: Historical Tracking
**As an** Analyst  
**I must be able to** query completed tasks and performance metrics  
**So that** system optimization is data-driven

**Implementation:** Metrics endpoints with time-based filtering

---

## 3. 🏗️ ARCHITECTURE

### Technology Stack

**Backend Framework:**
- FastAPI (Python 3.11+)
- Uvicorn ASGI server
- asyncio for async operations

**Database:**
- PostgreSQL 15+
- asyncpg driver for high performance

**Task Scheduling:**
- APScheduler (AsyncIOScheduler)
- 5 background jobs for monitoring and routing

**WebSocket:**
- FastAPI native WebSocket support
- Connection manager for broadcast

**Logging:**
- structlog for structured JSON logging
- Trace ID propagation

**Authentication:**
- JWT tokens from Registry (#3)
- Permission-based access control

### Directory Structure

```
app/
├── main.py                      # Application entry point
├── config.py                    # Configuration management
├── database.py                  # Database connection pool
│
├── api/
│   └── routes/
│       ├── auth.py              # JWT token generation
│       ├── health.py            # UDC health endpoints
│       ├── tasks.py             # Task management
│       ├── droplets.py          # Droplet management
│       ├── message.py           # Inter-droplet messaging
│       ├── metrics.py           # Analytics endpoints
│       ├── websocket.py         # Real-time updates
│       └── management.py        # Admin operations
│
├── models/
│   ├── database.py              # Database table models
│   ├── domain.py                # Business logic models
│   └── udc.py                   # UDC protocol models
│
├── services/
│   ├── auth.py                  # Authentication service
│   ├── health_monitor.py        # Droplet health checking
│   ├── registry_client.py       # Registry integration
│   ├── state_machine.py         # Task state transitions
│   ├── task_recovery.py         # Failed task recovery
│   ├── task_router.py           # Intelligent task routing
│   └── websocket_manager.py     # WebSocket connections
│
├── middleware/
│   └── udc_middleware.py        # UDC envelope handling
│
└── utils/
    ├── auth.py                  # JWT verification
    ├── helpers.py               # Utility functions
    ├── logging.py               # Logging configuration
    ├── udc_deps.py              # UDC dependencies
    ├── udc_helpers.py           # UDC wrapper functions
    └── udc_route.py             # UDC route decorator
```

### Component Overview

**Main Application (`main.py`):**
- Lifespan management (startup/shutdown)
- Route registration
- Middleware configuration
- Background scheduler initialization
- Error handlers

**Configuration (`config.py`):**
- Environment variable management
- Database connection settings
- JWT configuration
- Feature flags

**Database Layer (`database.py`):**
- Connection pool management
- Query helpers
- Schema validation

**Route Handlers (`api/routes/`):**
- HTTP endpoint implementations
- Request validation
- UDC envelope handling
- Response formatting

**Business Logic (`services/`):**
- Task routing algorithm
- Health monitoring logic
- State machine enforcement
- Recovery procedures

**Models (`models/`):**
- Pydantic models for validation
- Database table representations
- UDC protocol structures

**Utilities (`utils/`):**
- JWT authentication
- Logging setup
- Helper functions
- UDC protocol utilities

---

## 4. 🗄️ DATABASE SCHEMA

### Tables

#### droplets
Tracks all registered droplets in the mesh.

```sql
CREATE TABLE droplets (
    id SERIAL PRIMARY KEY,
    droplet_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    steward VARCHAR(100),
    endpoint VARCHAR(255) NOT NULL,
    capabilities JSONB DEFAULT '[]',
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'inactive', 'error')),
    last_heartbeat TIMESTAMP,
    registered_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_droplets_status ON droplets(status);
CREATE INDEX idx_droplets_heartbeat ON droplets(last_heartbeat);
CREATE INDEX idx_droplets_capabilities ON droplets USING GIN(capabilities);
```

**Fields:**
- `id`: Auto-increment internal ID
- `droplet_id`: External droplet identifier from Registry
- `name`: Human-readable droplet name
- `steward`: Person responsible for the droplet
- `endpoint`: Base URL for droplet API
- `capabilities`: JSON array of capability strings
- `status`: Current health status
- `last_heartbeat`: Timestamp of most recent heartbeat
- `registered_at`: When droplet first registered
- `updated_at`: Last modification timestamp

#### tasks
Central task management and routing.

```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    trace_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    task_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    payload JSONB NOT NULL,
    
    -- Routing
    required_capability VARCHAR(100),
    assigned_droplet_id INTEGER REFERENCES droplets(id),
    
    -- State machine
    status VARCHAR(20) NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled')),
    
    -- Priority & timing
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    created_at TIMESTAMP DEFAULT NOW(),
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    deadline TIMESTAMP,
    
    -- Results
    result JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Metadata
    created_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_trace_id ON tasks(trace_id);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_assigned_droplet ON tasks(assigned_droplet_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_capability ON tasks(required_capability);
```

**Fields:**
- `id`: Auto-increment task ID
- `trace_id`: UUID for cross-system tracking
- `task_type`: Type of task ("verify", "build", "deploy", etc.)
- `title`: Human-readable task title
- `description`: Detailed task description
- `payload`: JSON object with task-specific data
- `required_capability`: Capability needed to execute task
- `assigned_droplet_id`: FK to assigned droplet
- `status`: Current task status
- `priority`: 1-10 (1=highest priority)
- `created_at`: Task creation timestamp
- `assigned_at`: When task was assigned
- `started_at`: When execution started
- `completed_at`: When task finished
- `deadline`: Optional deadline
- `result`: JSON object with task results
- `error_message`: Error details if failed
- `retry_count`: Number of retry attempts
- `max_retries`: Maximum allowed retries
- `created_by`: Creator identifier
- `updated_at`: Last modification timestamp

#### task_state_history
Audit trail of all state changes.

```sql
CREATE TABLE task_state_history (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    from_status VARCHAR(20),
    to_status VARCHAR(20) NOT NULL,
    changed_by VARCHAR(100),
    reason TEXT,
    metadata JSONB,
    changed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_task_history_task_id ON task_state_history(task_id);
CREATE INDEX idx_task_history_changed_at ON task_state_history(changed_at);
```

**Fields:**
- `id`: Auto-increment history ID
- `task_id`: FK to tasks table
- `from_status`: Previous status (NULL for initial)
- `to_status`: New status
- `changed_by`: Who/what made the change
- `reason`: Optional reason for change
- `metadata`: Additional context
- `changed_at`: When change occurred

#### heartbeats
Recent heartbeat history for health monitoring.

```sql
CREATE TABLE heartbeats (
    id SERIAL PRIMARY KEY,
    droplet_id INTEGER NOT NULL REFERENCES droplets(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    metrics JSONB,
    received_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_heartbeats_droplet_id ON heartbeats(droplet_id);
CREATE INDEX idx_heartbeats_received_at ON heartbeats(received_at DESC);
```

**Fields:**
- `id`: Auto-increment heartbeat ID
- `droplet_id`: FK to droplets table
- `status`: Droplet status at heartbeat time
- `metrics`: JSON object with performance metrics
- `received_at`: When heartbeat was received

**Cleanup:** Old heartbeats (>7 days) are deleted by scheduled job.

---

## 5. 🔌 API ENDPOINTS

### UDC Standard Endpoints (Public)

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "id": 10,
  "name": "Orchestrator",
  "steward": "Tnsae",
  "status": "active",
  "endpoint": "https://drop10.fullpotential.ai",
  "updated_at": "2025-11-15T10:30:00Z",
  "message": "All systems operational"
}
```

#### GET /capabilities
Feature list endpoint.

**Response:**
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

#### GET /state
Resource usage endpoint.

**Response:**
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

#### GET /dependencies
Dependency status endpoint.

**Response:**
```json
{
  "required": [
    {
      "id": 3,
      "name": "Registry v2",
      "status": "connected",
      "last_check": "2025-11-15T10:30:00Z"
    }
  ],
  "optional": [
    {"id": 5, "name": "Dashboard", "status": "unknown", "last_check": null},
    {"id": 8, "name": "Verifier", "status": "unknown", "last_check": null}
  ],
  "missing": []
}
```

### Authentication

#### POST /token
Generate JWT token.

**Request:**
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

### Task Management (JWT Required, UDC Wrapped)

#### POST /tasks
Create new task.

**UDC Request Payload:**
```json
{
  "task_type": "verify",
  "title": "Verify Droplet #14 code",
  "description": "UDC compliance check",
  "required_capability": "code_verification",
  "priority": 3,
  "max_retries": 3,
  "deadline": "2025-11-15T12:00:00Z",
  "payload": {
    "code_url": "https://github.com/fullpotential-ai/droplet-14",
    "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md"
  }
}
```

**UDC Response Payload:**
```json
{
  "task_id": 123,
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2025-11-15T10:30:00Z",
  "estimated_assignment_seconds": 10
}
```

#### GET /tasks
List tasks with filtering.

**Query Parameters:**
- `status`: Filter by status
- `task_type`: Filter by type
- `priority_min`: Minimum priority (1-10)
- `priority_max`: Maximum priority (1-10)
- `assigned_droplet_id`: Filter by assigned droplet
- `limit`: Results per page (1-500, default: 50)
- `offset`: Pagination offset (default: 0)

**UDC Response Payload:**
```json
{
  "tasks": [
    {
      "id": 123,
      "trace_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_type": "verify",
      "title": "Verify Droplet #14 code",
      "status": "in_progress",
      "priority": 3,
      "assigned_droplet_id": 8,
      "assigned_droplet_name": "Verifier",
      "created_at": "2025-11-15T10:30:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

#### GET /tasks/{task_id}
Get task details with state history.

**UDC Response Payload:**
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
    "created_at": "2025-11-15T10:30:00Z",
    "assigned_at": "2025-11-15T10:30:15Z",
    "started_at": "2025-11-15T10:30:20Z",
    "completed_at": "2025-11-15T10:35:30Z",
    "result": {...},
    "error_message": null,
    "state_history": [...]
  }
}
```

#### PATCH /tasks/{task_id}
Update task status (assigned droplet only).

**UDC Request Payload:**
```json
{
  "status": "completed",
  "result": {...},
  "error_message": null
}
```

#### DELETE /tasks/{task_id}
Cancel task (creator or admin only).

**UDC Response Payload:**
```json
{
  "task_id": 123,
  "status": "cancelled",
  "cancelled_at": "2025-11-15T10:32:00Z"
}
```

### Droplet Management (JWT Required, UDC Wrapped)

#### POST /droplets/register
Register new droplet.

**UDC Request Payload:**
```json
{
  "droplet_id": 14,
  "name": "Visibility Deck",
  "steward": "Haythem",
  "endpoint": "https://visibility.fullpotential.ai",
  "capabilities": ["monitoring", "alerts", "snapshots"]
}
```

**UDC Response Payload:**
```json
{
  "droplet_id": 14,
  "name": "Visibility Deck",
  "status": "active",
  "registered_at": "2025-11-15T10:30:00Z",
  "heartbeat_interval_seconds": 60,
  "next_heartbeat_deadline": 1699963860.0
}
```

#### POST /droplets/{droplet_id}/heartbeat
Send heartbeat (every 60 seconds).

**UDC Request Payload:**
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

#### GET /droplets
List all registered droplets.

**Query Parameters:**
- `status`: Filter by status
- `capability`: Filter by capability

#### GET /droplets/{droplet_id}
Get droplet details.

#### POST /droplets/{droplet_id}/activate
Manually activate droplet (admin only).

#### POST /droplets/{droplet_id}/deactivate
Manually deactivate droplet (admin only).

#### GET /droplets/{droplet_id}/capabilities
Get droplet capabilities.

### Inter-Droplet Messaging

#### POST /message
Receive UDC message from another droplet.

**Full UDC Envelope Required:**
```json
{
  "udc_version": "1.0",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-5",
  "target": "droplet-10",
  "message_type": "command",
  "timestamp": "2025-11-15T10:30:00Z",
  "payload": {
    "command": "create_task",
    "task_data": {...}
  }
}
```

**Supported Commands:**
- `create_task`: Create a new task
- `cancel_task`: Cancel existing task

**Supported Queries:**
- `task_status`: Get task status
- `droplet_list`: List droplets
- `system_status`: Get system health

#### POST /send
Send message to another droplet.

**Query Parameters:**
- `target_droplet_id`: Target droplet ID
- `message_type`: Message type
- `payload`: Message payload

#### POST /broadcast
Broadcast message to multiple droplets (admin only).

**Query Parameters:**
- `message_type`: Message type
- `payload`: Message payload
- `capability_filter`: Optional capability filter

### Metrics & Analytics (JWT Required, UDC Wrapped)

#### GET /metrics/summary
System-wide metrics.

#### GET /metrics/tasks/performance
Task performance metrics.

**Query Parameters:**
- `task_type`: Filter by type
- `time_range`: "1h", "24h", "7d", "30d"

#### GET /metrics/tasks/by-type
Task distribution by type.

#### GET /metrics/droplets/{droplet_id}/performance
Droplet-specific performance.

#### GET /metrics/routing
Task routing metrics.

#### GET /metrics/system/health
Detailed system health.

### WebSocket Endpoints (JWT Required via Query Param)

#### WebSocket /ws/tasks
Real-time task events.

**Connection:** `wss://drop10.fullpotential.ai/ws/tasks?token=<JWT>`

**Events:**
- `task_created`
- `task_assigned`
- `task_started`
- `task_completed`
- `task_failed`
- `task_cancelled`

#### WebSocket /ws/droplets
Real-time droplet events.

**Connection:** `wss://drop10.fullpotential.ai/ws/droplets?token=<JWT>`

**Events:**
- `droplet_registered`
- `droplet_health_changed`
- `droplet_heartbeat_missed`

#### GET /ws/status
WebSocket connection statistics.

### Management Endpoints (JWT Required, Admin Permission, UDC Wrapped)

#### POST /management/reload-config
Reload configuration.

#### POST /management/shutdown
Graceful shutdown.

#### POST /management/emergency-stop
Emergency stop.

#### GET /management/version
Version information.

#### GET /management/scheduler/jobs
List background jobs.

#### POST /management/scheduler/jobs/{job_id}/pause
Pause scheduled job.

#### POST /management/scheduler/jobs/{job_id}/resume
Resume scheduled job.

#### POST /management/cache/clear
Clear internal caches.

---

## 6. 🔄 BACKGROUND JOBS

### Health Monitor
- **Frequency:** Every 60 seconds
- **Purpose:** Check droplet heartbeats
- **Action:** Mark droplets as inactive if no heartbeat for 90+ seconds
- **Service:** `services/health_monitor.py::check_droplet_health()`

### Task Router
- **Frequency:** Every 10 seconds
- **Purpose:** Route pending tasks to droplets
- **Action:** Match tasks to droplets based on capabilities and load
- **Service:** `services/task_router.py::route_pending_tasks()`

### Registry Sync
- **Frequency:** Every 5 minutes (300 seconds)
- **Purpose:** Sync droplet directory from Registry
- **Action:** Update local droplet cache
- **Service:** `services/registry_client.py::sync_droplets_from_registry()`

### Heartbeat Cleanup
- **Frequency:** Every 1 hour
- **Purpose:** Remove old heartbeat records
- **Action:** Delete heartbeats older than 7 days
- **Service:** `services/health_monitor.py::cleanup_old_heartbeats()`

### WebSocket Ping
- **Frequency:** Every 30 seconds
- **Purpose:** Keep WebSocket connections alive
- **Action:** Send ping frames to all clients
- **Service:** `services/websocket_manager.py::ping_all_connections()`

---

## 7. 🔒 SECURITY

### Authentication
- JWT tokens from Registry (#3)
- Token validation on all protected endpoints
- Permission-based access control

### Permissions
- `read`: Read access to tasks and droplets
- `write`: Create and update tasks
- `admin`: Full access including management endpoints

### Public Endpoints
The following endpoints do NOT require authentication:
- `GET /health`
- `GET /capabilities`
- `GET /state`
- `GET /dependencies`

### Rate Limiting
- Standard endpoints: 100 requests/minute per droplet
- WebSocket connections: 10 concurrent per droplet
- Broadcast endpoint: 10 requests/minute (admin only)

### Input Validation
- All inputs validated with Pydantic models
- SQL injection prevention via parameterized queries
- UDC envelope validation
- CORS configured restrictively

---

## 8. 📊 STATE MACHINE

### Task States
```
pending → assigned → in_progress → completed
                                 → failed
                  → cancelled
```

### Valid Transitions

| From | To | Allowed By |
|------|-----|-----------|
| pending | assigned | System (task router) |
| pending | cancelled | Creator or admin |
| assigned | in_progress | Assigned droplet |
| assigned | cancelled | Creator or admin |
| in_progress | completed | Assigned droplet |
| in_progress | failed | Assigned droplet |
| failed | pending | System (retry logic) |

### State Descriptions
- **pending**: Task created, awaiting assignment
- **assigned**: Task assigned to droplet, not yet started
- **in_progress**: Task being executed
- **completed**: Task finished successfully
- **failed**: Task failed (may be retried)
- **cancelled**: Task cancelled by user or system

---

## 9. 🔧 CONFIGURATION

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/orchestrator
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# JWT
JWT_SECRET_KEY=<secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_SECONDS=86400

# Registry
REGISTRY_URL=https://registry.fullpotential.ai
REGISTRY_SYNC_INTERVAL=300

# Droplet Identity
DROPLET_ID=10
DROPLET_NAME=Orchestrator
DROPLET_STEWARD=Tnsae
DROPLET_ENDPOINT=https://drop10.fullpotential.ai

# Monitoring
HEARTBEAT_CHECK_INTERVAL=60
HEARTBEAT_TIMEOUT=90
WS_HEARTBEAT_INTERVAL=30

# Features
ENABLE_AUTO_RECOVERY=true
ENABLE_SWAGGER=true
ENABLE_METRICS=true

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=false
LOG_LEVEL=INFO
ENVIRONMENT=production

# CORS
CORS_ORIGINS=["https://dashboard.fullpotential.ai"]
CORS_ALLOW_CREDENTIALS=true
```

---

## 10. 🚀 DEPLOYMENT

### Requirements
- Python 3.11+
- PostgreSQL 15+
- 2GB RAM minimum
- 2 CPU cores minimum

### Installation

```bash
# Clone repository
git clone https://github.com/fullpotential-ai/droplet-10.git
cd droplet-10

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
psql -U postgres -f schema.sql

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations (if any)
# python -m alembic upgrade head

# Start server
python -m app.main
```

### Docker Deployment

```bash
# Build image
docker build -t orchestrator:2.0.0 .

# Run container
docker run -d \
  --name orchestrator \
  -p 8000:8000 \
  --env-file .env \
  orchestrator:2.0.0
```

### Production Checklist
- [ ] PostgreSQL database created and schema applied
- [ ] Environment variables configured
- [ ] JWT secret key set (strong random value)
- [ ] Registry URL configured
- [ ] CORS origins set correctly
- [ ] Log level set to INFO or WARNING
- [ ] Swagger disabled (ENABLE_SWAGGER=false)
- [ ] Database connection pool sized appropriately
- [ ] Monitoring and alerting configured
- [ ] Backup strategy in place
- [ ] SSL/TLS certificates installed
- [ ] Firewall rules configured
- [ ] Health checks configured in load balancer

---

## 11. 🧪 TESTING

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_tasks.py

# Run specific test
pytest tests/test_tasks.py::test_create_task
```

### Test Structure

```
tests/
├── conftest.py              # Pytest fixtures
├── test_health.py           # Health endpoint tests
├── test_tasks.py            # Task management tests
├── test_droplets.py         # Droplet management tests
├── test_message.py          # Messaging tests
├── test_metrics.py          # Metrics tests
├── test_websocket.py        # WebSocket tests
├── test_state_machine.py    # State machine tests
└── test_task_router.py      # Routing logic tests
```

---

## 12. 📝 VERIFICATION CHECKLIST

## FUNCTIONAL REQUIREMENTS (Each item: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL)

TASK MANAGEMENT:
- [✅] POST /tasks creates task with correct priority and payload
- [✅] GET /tasks returns paginated list with filters
- [✅] GET /tasks/{id} returns full task details with state history
- [✅] PATCH /tasks/{id} updates status (only by assigned droplet)
- [✅] DELETE /tasks/{id} cancels task (only by creator or admin)
- [✅] Tasks follow state machine rules (no invalid transitions)
- [✅] Task routing assigns to droplets based on capabilities

DROPLET MANAGEMENT:
- [✅] POST /droplets/register adds new droplet to directory
- [✅] POST /droplets/{id}/heartbeat updates last_heartbeat timestamp
- [✅] GET /droplets returns all registered droplets with filters
- [✅] Droplets marked inactive after 90 seconds without heartbeat
- [✅] Capability-based routing matches tasks to droplets correctly

REAL-TIME UPDATES:
- [✅] WebSocket /ws/tasks broadcasts task events to all clients
- [✅] WebSocket /ws/droplets broadcasts droplet events to all clients
- [✅] WebSocket connections authenticate via JWT
- [✅] Multiple concurrent WebSocket clients supported

UDC COMPLIANCE:
- [✅] GET /health returns valid UDC response
- [✅] GET /capabilities declares features accurately
- [✅] GET /state reports resource usage
- [✅] GET /dependencies lists Registry integration
- [✅] POST /message handles UDC message format
- [✅] All authenticated endpoints wrap responses in UDC envelope

INTEGRATION:
- [✅] Registry client queries droplet directory periodically
- [✅] Registry client caches directory for offline operation
- [✅] JWT verification works correctly
- [✅] All droplet communications use UDC message format

## CODE QUALITY (Each item: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL)

ARCHITECTURE:
- [✅] File structure matches specification
- [✅] Clear separation: routes, services, models, utils
- [✅] Database models match schema exactly
- [✅] Pydantic models for all API requests/responses

ASYNC PATTERNS:
- [✅] All I/O operations use async/await
- [✅] No blocking calls
- [✅] Database queries use asyncpg
- [✅] HTTP clients use httpx AsyncClient

TYPE SAFETY:
- [✅] Type hints on all functions
- [✅] Pydantic validation on all inputs
- [✅] Return types specified
- [✅] No 'Any' types without justification

ERROR HANDLING:
- [✅] Try/except blocks around I/O operations
- [✅] Specific exception types caught
- [✅] HTTPException with appropriate status codes
- [✅] Errors logged with context
- [✅] User-friendly error messages

SECURITY:
- [✅] JWT authentication on protected endpoints
- [✅] Health endpoints are public
- [✅] Environment variables for secrets
- [✅] SQL injection prevention (parameterized queries)
- [✅] Input validation prevents malicious payloads
- [✅] CORS configured restrictively

LOGGING:
- [✅] Structured JSON logs with structlog
- [✅] Trace IDs in all log entries
- [✅] No sensitive data logged
- [✅] Log levels appropriate

DATABASE:
- [✅] Schema matches specification exactly
- [✅] All indexes created as specified
- [✅] Foreign keys with proper ON DELETE behavior
- [✅] Connection pooling configured
- [✅] Schema validation on startup

---

## 13. 🎯 METADATA (For Coordinator)

### COMPLEXITY ASSESSMENT

**Sprint Size:** 3 (Complex - Core infrastructure component)

**Reasoning:**
- Central coordination system (high criticality)
- Multiple integration points
- Real-time WebSocket requirements
- Complex routing and state machine logic
- High performance requirements
- Critical path service

**Difficulty:** Complex

**Reasoning:**
- Requires understanding of mesh architecture
- WebSocket management for real-time updates
- Background task scheduling
- Database design for high-query workload
- Task routing algorithm design
- State machine implementation
- Error recovery and task reassignment logic

### DEPENDENCIES

**Required (Must exist before starting):**
- Registry v2 (#3) - JWT authentication, droplet directory
- PostgreSQL database server

**Optional (Nice to have):**
- Dashboard (#5) - Will consume WebSocket feed
- Verifier (#8) - Will receive task assignments
- Other droplets for integration testing

**Blockers:**
- Registry v2 (#3) MUST be operational first
- Cannot fully test routing without registered droplets

### RECOMMENDED DEVELOPER LEVEL

**Level:** Skilled (or Intermediate with mentoring)

**Reasoning:**
- High complexity and criticality
- Requires architectural understanding
- Real-time systems experience helpful
- Performance optimization skills needed
- Must understand state machines and workflow logic
- Error recovery logic is non-trivial

**Suitable for Apprentice?** No - Too complex for first build

### ESTIMATED TIMELINE

**Build:** 12-16 hours (COMPLETED)
**Verification:** 3-4 hours
**Iteration:** 2-3 cycles
**Total:** 17-23 hours
**vs Traditional:** 80-120 hours
**Time Savings:** 71-81%

---

**END DROPLET_10_ORCHESTRATOR_SPECIFICATION.md**

**Status:** Production Ready  
**Version:** 2.0.0  
**Last Updated:** November 15, 2025
