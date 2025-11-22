# UDC Compliance - Universal Droplet Contract

**All services MUST implement these 6 endpoints**

---

## What is UDC?

**Universal Droplet Contract** ensures all services speak the same language and can discover/communicate with each other.

**The 6 Required Endpoints:**

---

### 1. `/health`
**Purpose:** Service health status

**Returns:**
```json
{
  "status": "active|inactive|degraded",
  "service": "service-name",
  "version": "1.0.0",
  "timestamp": "2025-11-15T23:00:00Z"
}
```

**Implementation:**
```python
@app.get("/health")
async def health():
    return {
        "status": "active",
        "service": "my-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
```

---

### 2. `/capabilities`
**Purpose:** What this service provides

**Returns:**
```json
{
  "version": "1.0.0",
  "features": ["feature1", "feature2"],
  "dependencies": ["service-a", "service-b"],
  "udc_version": "1.0",
  "metadata": {}
}
```

---

### 3. `/state`
**Purpose:** Resource usage and metrics

**Returns:**
```json
{
  "uptime_seconds": 3600,
  "requests_total": 1000,
  "requests_per_minute": 10.5,
  "errors_last_hour": 2,
  "last_restart": "2025-11-15T20:00:00Z"
}
```

---

### 4. `/dependencies`
**Purpose:** Required and optional services

**Returns:**
```json
{
  "required": ["credential-vault", "database"],
  "optional": ["cache"],
  "missing": []
}
```

---

### 5. `/message`
**Purpose:** Receive messages from other services

**Receives:**
```json
{
  "trace_id": "uuid",
  "source": "service-name",
  "target": "this-service",
  "message_type": "status|command|data",
  "payload": {},
  "timestamp": "2025-11-15T23:00:00Z"
}
```

---

### 6. `/send`
**Purpose:** Send messages to other services

**Implementation:** Look up target service in registry, send HTTP POST to target's `/message` endpoint

---

## Verification

**Check UDC compliance:**
```bash
cd /Users/jamessunheart/Development/SERVICES
python3 integrated-registry-system.py
```

**This will:**
- Test all 6 endpoints
- Report compliance status
- Identify missing endpoints

---

## Registration

**Once UDC compliant, register:**

```bash
# In service registry
./docs/coordination/scripts/service-register.sh "my-service" "Description" 8XXX "development"

# Server registry updates automatically via integrated-registry-system.py
```

---

**See UDC_STANDARDS.md in MEMORY/ for complete implementation guide with code templates.**
