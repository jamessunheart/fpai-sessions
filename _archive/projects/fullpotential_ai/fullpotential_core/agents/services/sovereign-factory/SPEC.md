# SOVEREIGN-FACTORY - Technical Specification

**Service Name:** sovereign-factory
**Version:** 1.0.0



---

## Purpose

Automated assembly line from system intents to deployed services. Manages prioritized intent queue, orchestrates SPEC generation/validation/optimization pipeline, and coordinates with build-executor for complete intent → deployment automation.

The Sovereign Factory is the "master orchestrator" that transforms business requirements into production-ready droplets with minimal human intervention.

---

## Capabilities

This service provides the following capabilities as part of the FPAI droplet mesh:

### Primary Functions

See 'Core Capabilities' section below for detailed descriptions.

## Core Capabilities

- **Intent Queue Management:** Prioritized FIFO queue for new service requests
- **SPEC Assembly Line:** Orchestrates spec-builder → spec-verifier → spec-optimizer pipeline
- **Build Coordination:** Hands validated SPECs to build-executor
- **Quality Gates:** Enforces minimum 90 SPEC score before build
- **Pipeline Monitoring:** Real-time dashboard of all intent → deploy pipelines
- **Retry Logic:** Automatic retry for failed SPEC generation/optimization
- **Status Tracking:** Complete audit trail from intent submission to deployment

---

## UDC Endpoints (5/5)

### 1. GET /health
**Returns:** Service health status
Service health status
```json
{
  "status": "active",
  "service": "sovereign-factory",
  "version": "1.0.0",
  "timestamp": "2025-11-16T00:00:00Z",
  "queue_depth": 5,
  "active_pipelines": 2
}
```

### 2. GET /capabilities
**Returns:** Service capabilities and metadata
Service capabilities
```json
{
  "version": "1.0.0",
  "features": [
    "intent_queue",
    "spec_assembly",
    "build_coordination",
    "quality_gates",
    "pipeline_monitoring"
  ],
  "dependencies": [
    "registry",
    "spec-builder",
    "spec-verifier",
    "spec-optimizer",
    "build-executor"
  ],
  "udc_version": "1.0",
  "metadata": {
    "max_concurrent_pipelines": 5,
    "min_spec_score": 90,
    "supported_service_types": ["infrastructure", "sacred_loop", "domain", "api_gateway", "data"]
  }
}
```

### 3. GET /state
**Returns:** Current service state and metrics
Current service state
```json
{
  "uptime_seconds": 86400,
  "requests_total": 150,
  "errors_last_hour": 2,
  "last_restart": "2025-11-16T00:00:00Z",
  "queue_depth": 5,
  "active_pipelines": 2,
  "completed_today": 12,
  "failed_today": 1
}
```

### 4. GET /dependencies
**Returns:** Service dependency status
Dependency status
```json
{
  "required": [
    {"name": "registry", "status": "available", "url": "http://localhost:8000"},
    {"name": "spec-builder", "status": "available", "url": "http://localhost:8207"},
    {"name": "spec-verifier", "status": "available", "url": "http://localhost:8205"},
    {"name": "spec-optimizer", "status": "available", "url": "http://localhost:8206"},
    {"name": "build-executor", "status": "available", "url": "http://localhost:8211"}
  ],
  "optional": [],
  "missing": []
}
```

### 5. POST /message
**Returns:** Message acknowledgment
Inter-droplet messaging
```json
{
  "trace_id": "uuid",
  "source": "orchestrator",
  "target": "sovereign-factory",
  "message_type": "command",
  "payload": {
    "action": "submit_intent",
    "intent": {...}
  },
  "timestamp": "2025-11-16T00:00:00Z"
}
```

---

## Service Endpoints

### POST /intents/submit
Submit new intent to queue
```json
// Request
{
  "service_name": "payment-processor",
  "service_type": "domain",
  "priority": "high",
  "purpose": "Process customer payments via Stripe",
  "key_features": [
    "Stripe integration",
    "Payment webhooks",
    "Refund handling"
  ],
  "dependencies": ["registry", "user-management"],
  "port": 8350,
  "target_tier": 2,
  "auto_build": true,
  "auto_deploy": false
}

// Response
{
  "intent_id": "uuid",
  "status": "queued",
  "queue_position": 3,
  "estimated_start": "2025-11-16T01:30:00Z",
  "pipeline_url": "/intents/{intent_id}/status"
}
```

### GET /intents/{intent_id}/status
Get intent pipeline status
```json
{
  "intent_id": "uuid",
  "service_name": "payment-processor",
  "status": "spec_optimization",
  "current_phase": "spec_optimizer",
  "progress_percent": 65,
  "phases": {
    "queued": {"status": "completed", "duration_seconds": 10},
    "spec_generation": {"status": "completed", "duration_seconds": 120, "spec_path": "/path/to/SPEC.md"},
    "spec_verification": {"status": "completed", "duration_seconds": 5, "score": 87},
    "spec_optimization": {"status": "running", "progress": 65},
    "build": {"status": "pending"},
    "deployment": {"status": "pending"}
  },
  "spec_score": 87,
  "target_score": 90,
  "estimated_completion": "2025-11-16T02:00:00Z"
}
```

### GET /intents
List all intents with filters
```json
// Query params: ?status=queued&priority=high&limit=20
{
  "intents": [
    {
      "intent_id": "uuid",
      "service_name": "payment-processor",
      "status": "spec_generation",
      "priority": "high",
      "created_at": "2025-11-16T00:00:00Z"
    }
  ],
  "total": 45,
  "queued": 5,
  "in_progress": 2,
  "completed": 35,
  "failed": 3
}
```

### POST /intents/{intent_id}/retry
Retry failed intent
```json
// Request
{
  "retry_from_phase": "spec_generation"
}

// Response
{
  "intent_id": "uuid",
  "status": "queued",
  "retry_count": 2,
  "queue_position": 1
}
```

### DELETE /intents/{intent_id}
Cancel queued or in-progress intent
```json
{
  "intent_id": "uuid",
  "status": "cancelled",
  "cancelled_at": "2025-11-16T01:00:00Z"
}
```

### GET /dashboard
Pipeline dashboard (metrics + active intents)
```json
{
  "summary": {
    "total_intents_today": 25,
    "completed_today": 20,
    "failed_today": 2,
    "success_rate": 0.90,
    "avg_pipeline_duration_minutes": 45
  },
  "active_pipelines": [
    {
      "intent_id": "uuid",
      "service_name": "payment-processor",
      "phase": "spec_optimization",
      "progress": 65
    }
  ],
  "queue": [
    {
      "intent_id": "uuid2",
      "service_name": "analytics-engine",
      "priority": "high",
      "queue_position": 1
    }
  ]
}
```

### POST /intents/batch
Submit multiple intents
```json
// Request
{
  "intents": [
    {...intent1...},
    {...intent2...}
  ]
}

// Response
{
  "submitted": 2,
  "intent_ids": ["uuid1", "uuid2"],
  "queue_depth": 7
}
```

---

## Architecture


### Tech Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite (local), PostgreSQL (production)
- **API:** RESTful + WebSocket
- **Authentication:** JWT tokens
- **Deployment:** Docker + systemd

### Technology Stack
- **Framework:** FastAPI (Python 3.11+)
- **Queue:** In-memory priority queue (v1), Redis (v2)
- **Database:** SQLite (local), PostgreSQL (production)
- **Task Management:** Background tasks with asyncio
- **WebSocket:** Real-time pipeline updates

### Pipeline Flow

```
Intent Submission
      ↓
Priority Queue (FIFO within priority)
      ↓
Phase 1: SPEC Generation (spec-builder)
      ↓
Phase 2: SPEC Verification (spec-verifier)
      ↓
Phase 3: SPEC Optimization (if score < 90)
      ↓
Quality Gate (score >= 90?)
      ↓ YES
Hand-off to build-executor
      ↓
Monitor build status
      ↓
Complete (update audit trail)
```

### Priority Levels
1. **critical** - TIER 0 infrastructure
2. **high** - TIER 1 sacred loop
3. **medium** - TIER 2+ domain services
4. **low** - Experimental/optional services

### Quality Gates
- **SPEC Score >= 90:** Required before build
- **All UDC Endpoints Documented:** Required
- **Dependencies Available:** Verified before build
- **Port Available:** Checked before deployment

---


## File Structure

```
sovereign-factory/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic models
│   ├── config.py         # Configuration
│   ├── endpoints/
│   │   ├── udc.py       # UDC endpoints
│   │   └── service.py   # Business endpoints
│   └── utils/
│       ├── registry.py  # Registry integration
│       └── logger.py    # Logging utilities
├── tests/
│   ├── test_main.py
│   ├── test_udc.py
│   └── test_integration.py
├── SPEC.md
├── README.md
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Dependencies

### Required Services
- **registry** (8000) - Service discovery
- **spec-builder** (8207) - SPEC generation
- **spec-verifier** (8205) - SPEC validation
- **spec-optimizer** (8206) - SPEC enhancement
- **build-executor** (8211) - Build pipeline

### Optional Services
- **orchestrator** (8001) - Task routing (for distributed deployment)

### External APIs
- None (all dependencies are internal FPAI services)

---

## Success Criteria

- [ ] Accept and queue intents with priority
- [ ] Orchestrate complete SPEC pipeline (builder → verifier → optimizer)
- [ ] Enforce 90+ SPEC score quality gate
- [ ] Hand validated SPECs to build-executor
- [ ] Track pipeline status in real-time
- [ ] Dashboard shows active/queued/completed intents
- [ ] Retry logic handles transient failures
- [ ] Complete audit trail for all intents
- [ ] Process 10+ intents per day
- [ ] 90%+ success rate (intent → deployed service)
- [ ] Average pipeline time < 1 hour

---

**Foundation of the autonomous build pipeline - transforms intents into production services!**
