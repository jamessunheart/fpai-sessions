# UDC_COMPLIANCE.md
**Universal Droplet Contract Specification**
**Version:** 1.0
**Last Updated:** November 2025

---

## 🎯 PURPOSE

The Universal Droplet Contract (UDC) ensures all droplets communicate through standardized interfaces, enabling:
- Autonomous discovery and coordination
- Real-time health monitoring
- Secure message passing
- System-wide observability

**Every droplet MUST implement these core endpoints.**

---

## 📡 CORE ENDPOINTS (REQUIRED)

### GET /health
**Purpose:** Report droplet status and dependency health

**Response Schema:**
```json
{
  "id": 14,
  "name": "Visibility Deck",
  "steward": "Haythem",
  "status": "active|inactive|error",
  "endpoint": "https://visibility.fullpotential.ai",
  "proof": "sha256_hash_of_last_update",
  "cost_usd": 0.05,
  "yield_usd": 0.00,
  "updated_at": "2025-11-08T03:00:00Z"
}
```

**Status Values (EXACTLY these three):**
- `active` - Operational and processing
- `inactive` - Online but idle
- `error` - Experiencing issues

**Response Time:** <500ms average

---

### GET /capabilities
**Purpose:** Declare what this droplet can do

**Response Schema:**
```json
{
  "version": "1.0.0",
  "features": [
    "real_time_monitoring",
    "snapshot_generation",
    "alert_management"
  ],
  "dependencies": ["registry", "orchestrator"],
  "udc_version": "1.0",
  "metadata": {
    "build_date": "2025-11-08",
    "commit_hash": "abc123"
  }
}
```

---

### GET /state
**Purpose:** Report resource usage and performance metrics

**Response Schema:**
```json
{
  "cpu_percent": 23.4,
  "memory_mb": 512,
  "uptime_seconds": 86400,
  "requests_total": 15234,
  "requests_per_minute": 42,
  "errors_last_hour": 0,
  "last_restart": "2025-11-07T12:00:00Z"
}
```

---

### GET /dependencies
**Purpose:** List other droplets this one connects to

**Response Schema:**
```json
{
  "required": [
    {"id": 1, "name": "Registry", "status": "connected"},
    {"id": 10, "name": "Orchestrator", "status": "connected"}
  ],
  "optional": [
    {"id": 2, "name": "Dashboard", "status": "available"}
  ],
  "missing": []
}
```

---

### POST /message
**Purpose:** Receive UDC-compliant messages from other droplets

**Request Schema:**
```json
{
  "trace_id": "uuid-v4",
  "source": "droplet_id",
  "target": "droplet_id",
  "message_type": "status|event|command|query",
  "payload": {},
  "timestamp": "2025-11-08T03:00:00Z",
  "signature": "jwt_token"
}
```

**Authentication:** JWT token required in Authorization header

**Response:**
```json
{
  "received": true,
  "trace_id": "uuid-v4",
  "processed_at": "2025-11-08T03:00:01Z",
  "result": "success|queued|error"
}
```

---

### POST /send
**Purpose:** Send messages to other droplets

**Request Schema:**
```json
{
  "target": "droplet_id_or_name",
  "message_type": "status|event|command|query",
  "payload": {},
  "priority": "high|normal|low",
  "retry_count": 3
}
```

---

## 🔧 EXTENDED ENDPOINTS (UDC-X)

### POST /reload-config
**Purpose:** Reload configuration without restart

**Request:**
```json
{
  "config_path": "/path/to/config.json"
}
```

---

### POST /shutdown
**Purpose:** Graceful shutdown with cleanup

**Request:**
```json
{
  "delay_seconds": 10,
  "reason": "maintenance"
}
```

---

### POST /emergency-stop
**Purpose:** Immediate stop without cleanup (emergency only)

---

### GET /version
**Purpose:** Build and deployment information

**Response:**
```json
{
  "version": "1.0.0",
  "build_date": "2025-11-08",
  "commit_hash": "abc123",
  "environment": "production",
  "deployed_by": "haythem"
}
```

---

## 🔐 AUTHENTICATION

**All endpoints except `/health` REQUIRE JWT authentication.**

### JWT Requirements:
1. **Issued by:** Registry (Droplet #1)
2. **Header:** `Authorization: Bearer <token>`
3. **Claims:**
   ```json
   {
     "droplet_id": 14,
     "steward": "haythem",
     "permissions": ["read", "write"],
     "exp": 1699430400,
     "iat": 1699426800
   }
   ```
4. **Verification:** Verify signature using Registry's public key

---

## 📊 RESPONSE STANDARDS

### Success Response (2xx):
```json
{
  "status": "success",
  "data": {},
  "timestamp": "2025-11-08T03:00:00Z"
}
```

### Error Response (4xx/5xx):
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field: trace_id",
    "details": {}
  },
  "timestamp": "2025-11-08T03:00:00Z"
}
```

### Standard Error Codes:
- `INVALID_REQUEST` - Malformed request
- `UNAUTHORIZED` - Missing/invalid JWT
- `FORBIDDEN` - Valid JWT but insufficient permissions
- `NOT_FOUND` - Resource doesn't exist
- `RATE_LIMITED` - Too many requests
- `INTERNAL_ERROR` - Server error
- `DEPENDENCY_UNAVAILABLE` - Required droplet offline

---

## 🎯 COMPLIANCE CHECKLIST

**Before deploying, verify:**

- [ ] `/health` returns valid UDC status response
- [ ] `/capabilities` declares features accurately
- [ ] `/state` reports real resource metrics
- [ ] `/dependencies` lists all connected droplets
- [ ] `/message` accepts UDC message format
- [ ] `/send` can transmit to other droplets
- [ ] JWT authentication on all protected endpoints
- [ ] Error responses follow standard format
- [ ] Response times under target (<500ms for /health)
- [ ] All responses include timestamps
- [ ] Status uses exact enum values: active|inactive|error

---

## 🔄 VERSION COMPATIBILITY

**Two-Version Rule:** Maintain backward compatibility with previous 2 UDC releases.

**Current:** UDC 1.0
**Must support:** UDC 1.0 (no previous versions yet)

---

## 📝 CONFIGURATION FILE

**Every droplet maintains:** `udc_config.json`

```json
{
  "droplet": {
    "id": 14,
    "name": "Visibility Deck",
    "steward": "haythem",
    "version": "1.0.0"
  },
  "registry": {
    "url": "https://registry.fullpotential.ai",
    "auto_register": true,
    "heartbeat_interval": 30
  },
  "orchestrator": {
    "url": "https://orchestrator.fullpotential.ai",
    "report_state": true,
    "report_interval": 60
  },
  "security": {
    "jwt_issuer": "registry.fullpotential.ai",
    "jwt_audience": "fullpotential.droplets",
    "require_auth": true
  }
}
```

---

## ⚡ QUICK REFERENCE

**Minimum viable droplet:**
1. Implement `/health` with valid status response
2. Implement JWT verification
3. Register with Registry (#1) on startup
4. Report to Orchestrator (#10) every 60s
5. Handle graceful shutdown

**That's it.** Everything else can be added incrementally.

---

**END UDC_COMPLIANCE.md**
