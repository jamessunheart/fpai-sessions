# Integration Guide

**How to integrate your service with the Full Potential AI ecosystem**

---

## Overview

All services in the FPAI ecosystem:
1. **Register** with the service registry
2. **Implement** UDC endpoints
3. **Communicate** via messaging protocol
4. **Report** status to SSOT
5. **Coordinate** with other sessions

---

## Step 1: Register Your Service

### Local Registry
```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts

./service-register.sh \
  "my-service" \
  "Brief description of what this does" \
  8500 \
  "development"
```

**This creates entry in:** `SERVICE_REGISTRY.json`

### Server Registry
**Automatic:** The `integrated-registry-system.py` syncs local → server every 5 minutes

**Manual:**
```bash
cd /Users/jamessunheart/Development/SERVICES
python3 integrated-registry-system.py
```

---

## Step 2: Implement UDC Endpoints

**Required 6 endpoints:** `/health`, `/capabilities`, `/state`, `/dependencies`, `/message`, `/send`

**Quick template:**
```python
from fastapi import FastAPI
from datetime import datetime
import time

app = FastAPI(title="My Service", version="1.0.0")

start_time = time.time()
request_count = 0

@app.middleware("http")
async def track_requests(request, call_next):
    global request_count
    request_count += 1
    return await call_next(request)

@app.get("/health")
async def health():
    return {
        "status": "active",
        "service": "my-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/capabilities")
async def capabilities():
    return {
        "version": "1.0.0",
        "features": ["feature1"],
        "dependencies": [],
        "udc_version": "1.0"
    }

@app.get("/state")
async def state():
    return {
        "uptime_seconds": int(time.time() - start_time),
        "requests_total": request_count
    }

@app.get("/dependencies")
async def dependencies():
    return {
        "required": [],
        "optional": [],
        "missing": []
    }

@app.post("/message")
async def message(msg: dict):
    return {
        "received": True,
        "trace_id": msg.get("trace_id")
    }

@app.post("/send")
async def send_message(request: dict):
    return {
        "sent": True,
        "trace_id": "generated-uuid"
    }
```

**See:** `MEMORY/UDC_COMPLIANCE.md` for full details

---

## Step 3: Connect to Service Registry

**On startup, register with server registry:**
```python
import httpx

@app.on_event("startup")
async def register_to_registry():
    """Register this service to central registry."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                "http://198.54.123.234:8000/droplets",
                json={
                    "name": "my-service",
                    "endpoint": "http://localhost:8500",
                    "steward": "session-5"
                }
            )
        except Exception as e:
            logger.error(f"Failed to register: {e}")
```

---

## Step 4: Communicate with Other Services

### Discover Services
```python
async def get_available_services():
    """Get all registered services from registry."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://198.54.123.234:8000/droplets")
        return response.json()
```

### Send Message to Service
```python
async def send_to_service(target: str, message_type: str, payload: dict):
    """Send message to another service."""
    import uuid

    trace_id = str(uuid.uuid4())

    # Get service endpoint from registry
    services = await get_available_services()
    target_service = next((s for s in services if s["name"] == target), None)

    if not target_service:
        raise ValueError(f"Service {target} not found")

    # Send message
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{target_service['endpoint']}/message",
            json={
                "trace_id": trace_id,
                "source": "my-service",
                "target": target,
                "message_type": message_type,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )

    return response.json()
```

---

## Step 5: Access Credential Vault

**Never ask user for credentials - use vault:**

```bash
# In your deployment script
export ANTHROPIC_API_KEY=$(./docs/coordination/scripts/session-get-credential.sh anthropic_api_key)
export OPENAI_API_KEY=$(./docs/coordination/scripts/session-get-credential.sh openai_api_key)
```

**In Python:**
```python
import os

# Credentials loaded from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

**Available credentials:**
- anthropic_api_key
- openai_api_key
- server_admin_password
- stripe_api_key
- +more

**Vault API:**
- URL: https://fullpotential.com/vault
- Docs: https://fullpotential.com/vault/docs
- Health: https://fullpotential.com/vault/health

---

## Step 6: Report to SSOT

**SSOT (Single Source of Truth) tracks all services and sessions:**

**Automatic:** The `ssot-watcher.sh` background process merges data every 5 seconds

**Your service auto-updates when:**
- You register via `service-register.sh`
- `integrated-registry-system.py` runs

**Manual update:**
```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./update-ssot.sh
```

---

## Step 7: Coordinate with Sessions

### Register Your Session
```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts

./claude-session-register.sh 12 "Your Role" "Your Goal"
```

### Send Messages to Other Sessions
```bash
# Broadcast to all
./session-send-message.sh "broadcast" "Subject" "Message" "normal"

# Direct message
./session-send-message.sh "session-5" "Subject" "Message" "urgent"
```

### Check Your Messages
```bash
./session-check-messages.sh
```

---

## Integration Checklist

**Before going live:**

- [ ] Service registered in SERVICE_REGISTRY.json
- [ ] All 6 UDC endpoints implemented
- [ ] Startup registration to server registry
- [ ] Health check returns correct status
- [ ] Dependencies declared in /dependencies
- [ ] Messaging endpoints working
- [ ] Credentials from vault (not hardcoded)
- [ ] Service port doesn't conflict
- [ ] Tests pass (pytest)
- [ ] Deployed to server OR running locally

---

## Common Integration Patterns

### Pattern 1: Service Discovery
```python
async def find_service(capability: str):
    """Find service that provides capability."""
    services = await get_available_services()

    for service in services:
        caps = await get_capabilities(service["endpoint"])
        if capability in caps.get("features", []):
            return service

    return None
```

### Pattern 2: Health Monitoring
```python
async def check_all_services():
    """Check health of all services."""
    services = await get_available_services()
    health_status = {}

    for service in services:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service['endpoint']}/health")
                health_status[service["name"]] = response.json()
        except Exception as e:
            health_status[service["name"]] = {"status": "offline", "error": str(e)}

    return health_status
```

### Pattern 3: Orchestration
```python
async def orchestrate_task(task_data: dict):
    """Distribute task across services."""
    # Find appropriate service
    service = await find_service("task-processing")

    # Send task
    result = await send_to_service(
        target=service["name"],
        message_type="command",
        payload={"action": "process_task", "data": task_data}
    )

    return result
```

---

## Troubleshooting

### Service Not Showing in Registry
1. Check if registered: `cat /Users/jamessunheart/Development/docs/coordination/SERVICE_REGISTRY.json`
2. Run sync: `python3 integrated-registry-system.py`
3. Check SSOT: `cat /Users/jamessunheart/Development/docs/coordination/SSOT.json | python3 -m json.tool`

### Can't Reach Other Service
1. Check service is running: `curl http://localhost:PORT/health`
2. Check firewall/ports
3. Verify endpoint in registry
4. Check network connectivity

### Credentials Not Found
1. List available: `./scripts/session-list-credentials.sh`
2. Check vault health: `curl https://fullpotential.com/vault/health`
3. Verify credential name spelling

---

## Next Steps

**After integration:**
1. Monitor service health in dashboards
2. Coordinate with other sessions
3. Share learnings in `shared-knowledge/learnings.md`
4. Update service status as you progress
5. Help other services integrate

---

**Integration Resources:**
- UDC Standards: `MEMORY/UDC_COMPLIANCE.md`
- Tech Stack: `MEMORY/TECH_STACK.md`
- Security: `MEMORY/SECURITY_REQUIREMENTS.md`
- Protocols: `MEMORY/PROTOCOLS_INDEX.md`

**You're now part of the unified FPAI ecosystem!**
