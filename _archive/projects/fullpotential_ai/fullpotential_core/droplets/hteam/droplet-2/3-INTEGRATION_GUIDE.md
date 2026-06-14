# INTEGRATION_GUIDE.md
**Full Potential AI - Droplet Integration**
**Version:** 1.0
**Last Updated:** November 2025

---

## 🎯 PURPOSE

This guide shows how to integrate your droplet with the Full Potential mesh network. Every droplet connects to Registry (#1) for discovery and Orchestrator (#10) for coordination.

---

## 🗺️ DROPLET MESH OVERVIEW

### Core Coordination Droplets

**Registry (#1)** - Droplet discovery and authentication
- **Steward:** Liban
- **URL:** https://registry.fullpotential.ai
- **Purpose:** Central directory of all droplets, JWT issuer
- **Critical:** Your droplet MUST register here on startup

**Orchestrator (#10)** - Task coordination and workflow management
- **Steward:** Tnsae
- **URL:** https://orchestrator.fullpotential.ai
- **Purpose:** Routes tasks, manages state transitions
- **Critical:** Report your state here every 60s

**Dashboard (#2)** - System monitoring and visualization
- **Steward:** Haythem
- **URL:** https://dashboard.fullpotential.ai
- **Purpose:** Real-time system status display
- **Integration:** Push metrics here for visibility

**Nexus (#13)** - Intelligence coordination hub
- **Steward:** Suresh
- **URL:** https://nexus.fullpotential.ai
- **Purpose:** Routes intelligent tasks across droplets
- **Integration:** Connect if your droplet provides AI capabilities

### Specialized Droplets

**Chat Orchestrator (#12)** - Chat interface coordination
- **Steward:** Zainab
- **Purpose:** Routes chat requests to appropriate handlers

**Memory (#9)** - Persistent memory and learning
- **Status:** Planned
- **Purpose:** System-wide memory and pattern recognition

**Treasury (BrickChain)** - Financial coordination
- **Status:** Planned
- **Purpose:** Payment processing and yield optimization

---

## 🚀 INTEGRATION SEQUENCE

### Step 1: Get Credentials (Before Launch)

**Contact Registry steward (Liban):**
```
Subject: New Droplet Registration - [Your Droplet Name]

Hi Liban,

I'm deploying Droplet #[ID]: [Name]

Please provide:
1. Droplet ID number
2. JWT signing credentials
3. Registry endpoint confirmation

Steward: [Your Name]
Expected launch: [Date]
```

**You'll receive:**
- Your unique droplet ID
- Registry API credentials
- JWT verification key

---

### Step 2: Auto-Register on Startup

**Every droplet MUST auto-register with Registry on startup:**

```python
import httpx
import asyncio

async def register_with_registry():
    """Register this droplet with Registry on startup"""
    
    registration_data = {
        "id": DROPLET_ID,              # From config
        "name": DROPLET_NAME,           # e.g., "Visibility Deck"
        "steward": STEWARD_NAME,        # Your name
        "endpoint": DROPLET_URL,        # Your public URL
        "capabilities": [               # What you can do
            "monitoring",
            "alerts",
            "snapshots"
        ],
        "version": "1.0.0",
        "status": "active"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{REGISTRY_URL}/register",
                json=registration_data,
                headers={
                    "Content-Type": "application/json",
                    "X-Droplet-Secret": DROPLET_SECRET
                }
            )
            
            if response.status_code == 200:
                print(f"✅ Registered with Registry: {DROPLET_NAME}")
                return response.json()
            else:
                print(f"❌ Registration failed: {response.status_code}")
                raise Exception("Registration failed")
                
        except Exception as e:
            print(f"❌ Could not reach Registry: {e}")
            # Retry with exponential backoff
            await asyncio.sleep(5)
            return await register_with_registry()

# Call on startup
@app.on_event("startup")
async def startup_event():
    await register_with_registry()
    await start_heartbeat()
```

---

### Step 3: Maintain Heartbeat

**Report to Orchestrator every 60 seconds:**

```python
import asyncio

async def send_heartbeat():
    """Send regular heartbeat to Orchestrator"""
    
    while True:
        try:
            status_data = {
                "droplet_id": DROPLET_ID,
                "status": "active",  # or "inactive" or "error"
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {
                    "cpu_percent": get_cpu_usage(),
                    "memory_mb": get_memory_usage(),
                    "requests_last_minute": get_request_count(),
                    "errors_last_minute": get_error_count()
                }
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{ORCHESTRATOR_URL}/heartbeat",
                    json=status_data,
                    headers={"Authorization": f"Bearer {get_jwt_token()}"}
                )
                
        except Exception as e:
            print(f"Heartbeat failed: {e}")
        
        await asyncio.sleep(60)  # Every 60 seconds

# Start heartbeat on startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(send_heartbeat())
```

---

### Step 4: Implement UDC Endpoints

**See UDC_COMPLIANCE.md for complete specification.**

**Minimum implementation:**
```python
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI()

@app.get("/health")
async def health():
    """UDC-compliant health check"""
    return {
        "id": DROPLET_ID,
        "name": DROPLET_NAME,
        "steward": STEWARD_NAME,
        "status": "active",
        "endpoint": DROPLET_URL,
        "updated_at": datetime.utcnow().isoformat()
    }

@app.get("/capabilities")
async def capabilities():
    """Declare droplet capabilities"""
    return {
        "version": "1.0.0",
        "features": ["monitoring", "alerts"],
        "dependencies": ["registry", "orchestrator"],
        "udc_version": "1.0"
    }

@app.get("/state")
async def state():
    """Report resource usage"""
    return {
        "cpu_percent": get_cpu_usage(),
        "memory_mb": get_memory_usage(),
        "uptime_seconds": get_uptime(),
        "requests_total": get_total_requests()
    }
```

---

## 🔐 AUTHENTICATION FLOW

### Receiving Requests

**1. Extract JWT from Authorization header:**
```python
from jose import jwt, JWTError
from fastapi import Header, HTTPException

async def verify_jwt(authorization: str = Header(None)):
    """Verify JWT token from another droplet"""
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid token")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Verify with Registry's public key
        payload = jwt.decode(
            token,
            REGISTRY_PUBLIC_KEY,
            algorithms=["RS256"],
            audience="fullpotential.droplets",
            issuer="registry.fullpotential.ai"
        )
        
        return payload  # Contains droplet_id, permissions, etc.
        
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {e}")

# Use in protected endpoints
@app.post("/message")
async def receive_message(
    message: MessageModel,
    token_data: dict = Depends(verify_jwt)
):
    # token_data contains verified droplet info
    source_droplet = token_data["droplet_id"]
    # Process message...
```

### Sending Requests

**2. Include JWT when calling other droplets:**
```python
async def send_to_droplet(target_droplet_id: int, message: dict):
    """Send UDC message to another droplet"""
    
    # Get target droplet info from Registry
    target_info = await get_droplet_info(target_droplet_id)
    
    # Create UDC message
    udc_message = {
        "trace_id": str(uuid.uuid4()),
        "source": DROPLET_ID,
        "target": target_droplet_id,
        "message_type": "event",
        "payload": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send with JWT
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{target_info['endpoint']}/message",
            json=udc_message,
            headers={
                "Authorization": f"Bearer {get_jwt_token()}",
                "Content-Type": "application/json"
            }
        )
        
    return response.json()
```

---

## 🔍 DISCOVERING OTHER DROPLETS

### Query Registry for Droplet List

```python
async def get_all_droplets():
    """Fetch list of all registered droplets"""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REGISTRY_URL}/droplets",
            headers={"Authorization": f"Bearer {get_jwt_token()}"}
        )
        
    return response.json()  # List of all droplets

async def get_droplet_by_id(droplet_id: int):
    """Get specific droplet info"""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REGISTRY_URL}/droplet/{droplet_id}",
            headers={"Authorization": f"Bearer {get_jwt_token()}"}
        )
        
    return response.json()

async def find_droplets_by_capability(capability: str):
    """Find droplets that have specific capability"""
    
    all_droplets = await get_all_droplets()
    
    return [
        d for d in all_droplets
        if capability in d.get("capabilities", [])
    ]
```

---

## 📨 MESSAGE PASSING PATTERNS

### Event Broadcasting

**Notify multiple droplets of an event:**

```python
async def broadcast_event(event_type: str, event_data: dict):
    """Broadcast event to all interested droplets"""
    
    # Get all droplets
    droplets = await get_all_droplets()
    
    # Create tasks for parallel sending
    tasks = []
    for droplet in droplets:
        if droplet["id"] != DROPLET_ID:  # Don't send to self
            task = send_to_droplet(droplet["id"], {
                "event_type": event_type,
                "data": event_data
            })
            tasks.append(task)
    
    # Send in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Log failures
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Failed to send to droplet {droplets[i]['id']}: {result}")
```

### Request-Response Pattern

**Send request and wait for response:**

```python
async def query_droplet(target_id: int, query: dict):
    """Send query and wait for response"""
    
    message = {
        "trace_id": str(uuid.uuid4()),
        "source": DROPLET_ID,
        "target": target_id,
        "message_type": "query",
        "payload": query,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send and wait for response
    response = await send_to_droplet(target_id, message)
    
    return response
```

---

## 🔗 COMMON INTEGRATION PATTERNS

### Integration with Dashboard (#2)

**Push metrics for visualization:**

```python
async def push_metrics_to_dashboard():
    """Send metrics to Dashboard for display"""
    
    metrics = {
        "droplet_id": DROPLET_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "requests_per_minute": calculate_rpm(),
            "average_response_time": calculate_avg_response(),
            "error_rate": calculate_error_rate(),
            "custom_metric": your_custom_metric()
        }
    }
    
    await send_to_droplet(2, {  # Dashboard is droplet #2
        "type": "metrics_update",
        "data": metrics
    })
```

### Integration with Chat Orchestrator (#12)

**Handle chat requests:**

```python
@app.post("/handle-chat")
async def handle_chat_request(
    request: ChatRequest,
    token_data: dict = Depends(verify_jwt)
):
    """Receive chat request from Chat Orchestrator"""
    
    # Process chat message
    response = await process_chat(request.message)
    
    # Return structured response
    return {
        "response": response,
        "confidence": 0.95,
        "context": {}
    }
```

### Integration with Orchestrator (#10)

**Receive task assignments:**

```python
@app.post("/task")
async def receive_task(
    task: TaskModel,
    token_data: dict = Depends(verify_jwt)
):
    """Receive task from Orchestrator"""
    
    # Acknowledge receipt
    await send_to_droplet(10, {
        "type": "task_acknowledged",
        "task_id": task.id
    })
    
    # Process task asynchronously
    asyncio.create_task(process_task(task))
    
    return {"status": "accepted", "task_id": task.id}

async def process_task(task: TaskModel):
    """Process task and report completion"""
    
    try:
        result = await do_work(task)
        
        # Report success
        await send_to_droplet(10, {
            "type": "task_completed",
            "task_id": task.id,
            "result": result
        })
        
    except Exception as e:
        # Report failure
        await send_to_droplet(10, {
            "type": "task_failed",
            "task_id": task.id,
            "error": str(e)
        })
```

---

## 🚨 ERROR HANDLING

### Handling Unreachable Droplets

```python
async def safe_send_to_droplet(target_id: int, message: dict, retries: int = 3):
    """Send with retry logic"""
    
    for attempt in range(retries):
        try:
            return await send_to_droplet(target_id, message)
            
        except httpx.TimeoutException:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                # Report to Orchestrator
                await send_to_droplet(10, {
                    "type": "droplet_unreachable",
                    "target_id": target_id
                })
                raise
                
        except Exception as e:
            print(f"Error sending to droplet {target_id}: {e}")
            raise
```

---

## ✅ INTEGRATION CHECKLIST

**Before going live, verify:**

- [ ] Droplet ID assigned by Registry steward
- [ ] JWT credentials received
- [ ] Auto-registration on startup implemented
- [ ] Heartbeat to Orchestrator every 60s active
- [ ] All UDC endpoints implemented
- [ ] JWT verification working
- [ ] Can discover other droplets via Registry
- [ ] Can send/receive UDC messages
- [ ] Error handling and retries in place
- [ ] Logging includes trace_id for debugging
- [ ] Graceful shutdown notifies Registry

---

## 🆘 TROUBLESHOOTING

### Can't Register with Registry

**Check:**
1. Is REGISTRY_URL correct in config?
2. Do you have valid credentials?
3. Is Registry droplet online? (Check with steward)
4. Are you behind a firewall?

### Messages Not Received

**Check:**
1. Is your `/message` endpoint public?
2. Is JWT verification working?
3. Check logs for authentication errors
4. Verify sender has correct JWT

### Heartbeat Failing

**Check:**
1. Is Orchestrator URL correct?
2. Is heartbeat task actually running? (Check logs)
3. Is JWT token expired? (Refresh if needed)
4. Network connectivity issues?

---

## 📞 SUPPORT CONTACTS

**Registry Issues:** Liban (Registry steward)
**Orchestrator Issues:** Tnsae (Orchestrator steward)
**Dashboard Integration:** Haythem (Dashboard steward)
**General Questions:** James (System architect)

---

**END INTEGRATION_GUIDE.md**
