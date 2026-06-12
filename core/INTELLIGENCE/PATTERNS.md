# 🔄 PATTERNS - Reusable Build Patterns

**Purpose:** Proven patterns extracted from successful builds. Apply these automatically.
**Updated:** 2025-12-15

---

## 🏗️ BUILD PATTERNS

### Pattern 1: Shared HTTP Client (Memory Optimization)
**Source:** Consciousness Feeder Memory Leak Fix (2025-12-14)
**When to use:** Any service with continuous HTTP requests

```python
# Create shared client at module level
_shared_client: Optional[httpx.AsyncClient] = None

async def get_shared_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client - prevents connection leaks."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
        )
    return _shared_client

async def close_shared_client():
    """Close on shutdown."""
    global _shared_client
    if _shared_client and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None

# In FastAPI:
@app.on_event("shutdown")
async def shutdown():
    await close_shared_client()
```

**Impact:** Prevents memory leaks in long-running services

---

### Pattern 2: Bounded Collections (Memory Safety)
**Source:** Consciousness Feeder Memory Leak Fix (2025-12-14)
**When to use:** Any list/dict that grows over time

```python
from collections import OrderedDict

class BoundedDict(OrderedDict):
    """Dict with max size - auto-removes oldest entries."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        super().__init__()
    
    def __setitem__(self, key, value):
        if key not in self and len(self) >= self.max_size:
            self.popitem(last=False)  # Remove oldest
        super().__setitem__(key, value)
        self.move_to_end(key)  # Most recent last
```

**Impact:** Prevents unbounded memory growth

---

### Pattern 3: __slots__ for Data Classes
**Source:** Consciousness Feeder Memory Leak Fix (2025-12-14)
**When to use:** Classes that create many instances

```python
class Event:
    """Memory-efficient event class."""
    __slots__ = ('id', 'type', 'data', 'timestamp')
    
    def __init__(self, id, type, data, timestamp):
        self.id = id
        self.type = type
        self.data = data
        self.timestamp = timestamp
```

**Impact:** ~40% memory reduction per instance

---

### Pattern 4: UDC Endpoints (Service Compliance)
**Source:** SPEC Builder, UDC Compliance Protocol
**When to use:** Every service

```python
# All services MUST have these 5 endpoints:

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "my-service"}

@app.get("/capabilities")
async def capabilities():
    return {"version": "1.0.0", "features": [...]}

@app.get("/state")
async def state():
    return {"uptime": ..., "requests": ..., "errors": ...}

@app.get("/dependencies")
async def dependencies():
    return {"required": [...], "optional": [...]}

@app.post("/message")
async def message(msg: dict):
    return {"received": True, "trace_id": msg.get("trace_id")}
```

**Impact:** Enables service discovery and mesh coordination

---

### Pattern 5: Periodic GC for Long-Running Services
**Source:** Consciousness Feeder Memory Leak Fix (2025-12-14)
**When to use:** Services running 24/7

```python
import gc
import asyncio

async def periodic_gc_task():
    """Run GC every 5 minutes to prevent memory buildup."""
    while True:
        await asyncio.sleep(300)
        collected = gc.collect()
        if collected > 0:
            logger.debug(f"GC collected {collected} objects")

# Start on app startup
@app.on_event("startup")
async def startup():
    asyncio.create_task(periodic_gc_task())
```

**Impact:** Prevents gradual memory creep

---

## 📋 COORDINATION PATTERNS

### Pattern 6: Claims with Expiry
**Source:** Multi-Session Coordination (2025-11-14)
**When to use:** Preventing duplicate work

```json
{
  "claimed_by": "session-id",
  "claimed_at": "2025-12-15T00:00:00Z",
  "resource_type": "service|file|mission",
  "resource_name": "service-name",
  "duration_hours": 4,
  "expires_at": "2025-12-15T04:00:00Z",
  "allow_coordination": true
}
```

**Rule:** Claims expire after `duration_hours`. Run cleanup script every 6 hours.

---

### Pattern 7: File-Based Heartbeats
**Source:** Multi-Session Coordination (2025-11-14)
**When to use:** Session liveness tracking

```json
{
  "session_id": "session-123",
  "last_update": "2025-12-15T00:00:00Z",
  "current_work": "Building feature X",
  "status": "active"
}
```

**Rule:** Heartbeats stale after 24 hours. Auto-cleanup removes them.

---

## 🎯 DEPLOYMENT PATTERNS

### Pattern 8: Verification Before Claims
**Source:** Verification Protocol (2025-11-17)
**When to use:** Before claiming anything is "deployed"

```bash
# 1. DNS resolution
nslookup domain.com

# 2. External HTTP test
curl -I https://domain.com/endpoint

# 3. Response content
curl https://domain.com/endpoint | head -20

# 4. Service running
systemctl status service-name
```

**Rule:** ALL checks must pass before saying "deployed"

---

### Pattern 9: API Routing by Server
**Source:** Two-Server Architecture (2025-12-11)
**When to use:** Any service calling another

```python
# Primary (198.54.123.234) - Trading, Revenue, Data
DATA_SERVICE_URL = "http://198.54.123.234:8125"
TRADING_URL = "http://198.54.123.234:8600"
CREDITS_URL = "http://198.54.123.234:8765"

# Secondary (162.0.208.88) - AI, Consciousness
AI_BRAIN_URL = "http://162.0.208.88:8101"
OLLAMA_URL = "http://162.0.208.88:11434"
CONSCIOUSNESS_URL = "http://162.0.208.88:8130"
```

**Rule:** Never use localhost for cross-service calls in production

---

## 📊 APPLICATION

### How to Use This File:

1. **Before building:** Read patterns relevant to your service type
2. **During build:** Apply applicable patterns
3. **After build:** Add new patterns if you discover something reusable
4. **Code review:** Check if patterns were followed

### Pattern Categories:
- 🏗️ **Build Patterns** - Code structures that work well
- 📋 **Coordination Patterns** - Multi-agent collaboration
- 🎯 **Deployment Patterns** - Getting to production safely

---

**Total Patterns:** 9
**Last Updated:** 2025-12-15
**Maintained By:** Builder agents
