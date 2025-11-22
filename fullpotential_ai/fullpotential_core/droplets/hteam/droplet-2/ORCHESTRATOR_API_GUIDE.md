# Orchestrator API Guide - Droplet Registration & Heartbeat

**Orchestrator URL:** https://drop10.fullpotential.ai  
**Version:** 2.0.0  
**UDC Version:** 1.0

---

## 🔐 Authentication

All endpoints require JWT Bearer token except `/health` and `/management/version`.

```bash
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## 📝 Registration Endpoint

### POST /droplets/register

Register your droplet with the Orchestrator.

**Endpoint:** `POST https://drop10.fullpotential.ai/droplets/register`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

**Request Body (UDC Envelope):**
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": 42,
  "target": 10,
  "message_type": "command",
  "payload": {
    "id": 42,
    "name": "droplet0",
    "steward": "Haythem",
    "endpoint": "http://localhost:8002",
    "capabilities": [
      "udc_compliance",
      "health_monitoring",
      "message_handling"
    ],
    "version": "1.0.0",
    "status": "active"
  },
  "timestamp": "2025-01-18T10:00:00Z"
}
```

**cURL Example:**
```bash
curl -X POST "https://drop10.fullpotential.ai/droplets/register" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "source": 42,
    "target": 10,
    "message_type": "command",
    "payload": {
      "id": 42,
      "name": "droplet0",
      "steward": "Haythem",
      "endpoint": "http://localhost:8002",
      "capabilities": ["udc_compliance"],
      "version": "1.0.0",
      "status": "active"
    },
    "timestamp": "2025-01-18T10:00:00Z"
  }'
```

**Response (201 Created):**
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": 10,
  "target": 42,
  "message_type": "response",
  "payload": {
    "registered": true,
    "droplet_id": 42,
    "message": "Droplet registered successfully"
  },
  "timestamp": "2025-01-18T10:00:01Z"
}
```

---

## 💓 Heartbeat Endpoint

### POST /droplets/{droplet_id}/heartbeat

Send regular heartbeat to maintain active status.

**Endpoint:** `POST https://drop10.fullpotential.ai/droplets/42/heartbeat`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

**Request Body (UDC Envelope):**
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440001",
  "source": 42,
  "target": 10,
  "message_type": "heartbeat",
  "payload": {
    "status": "active",
    "metrics": {
      "cpu_percent": 15.5,
      "memory_mb": 256,
      "requests_last_minute": 10,
      "errors_last_minute": 0
    }
  },
  "timestamp": "2025-01-18T10:01:00Z"
}
```

**cURL Example:**
```bash
curl -X POST "https://drop10.fullpotential.ai/droplets/42/heartbeat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "550e8400-e29b-41d4-a716-446655440001",
    "source": 42,
    "target": 10,
    "message_type": "heartbeat",
    "payload": {
      "status": "active",
      "metrics": {
        "cpu_percent": 15.5,
        "memory_mb": 256,
        "requests_last_minute": 10,
        "errors_last_minute": 0
      }
    },
    "timestamp": "2025-01-18T10:01:00Z"
  }'
```

**Response (200 OK):**
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440001",
  "source": 10,
  "target": 42,
  "message_type": "response",
  "payload": {
    "acknowledged": true,
    "droplet_id": 42,
    "next_heartbeat_in": 60
  },
  "timestamp": "2025-01-18T10:01:01Z"
}
```

---

## 📋 UDC Message Format

All requests to Orchestrator must follow UDC envelope format:

```json
{
  "trace_id": "uuid-v4",
  "source": <your_droplet_id>,
  "target": 10,
  "message_type": "command|query|response|event|heartbeat",
  "payload": { /* your data */ },
  "timestamp": "ISO-8601 datetime"
}
```

### Message Types:
- `command` - For registration, actions
- `heartbeat` - For heartbeat updates
- `query` - For requesting information
- `event` - For event notifications
- `response` - For responses (Orchestrator uses this)

---

## 🔍 Query Droplets

### GET /droplets

List all registered droplets.

**Endpoint:** `GET https://drop10.fullpotential.ai/droplets`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Query Parameters:**
- `status` (optional): Filter by status (active, inactive, error, maintenance)
- `capability` (optional): Filter by capability

**cURL Example:**
```bash
curl -X GET "https://drop10.fullpotential.ai/droplets?status=active" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "trace_id": "auto-generated",
  "source": 10,
  "target": 42,
  "message_type": "response",
  "payload": {
    "droplets": [
      {
        "id": 10,
        "name": "Orchestrator",
        "steward": "Tnsae6",
        "status": "active",
        "endpoint": "http://localhost:8000",
        "capabilities": ["task_routing", "droplet_discovery"]
      },
      {
        "id": 42,
        "name": "droplet0",
        "steward": "Haythem",
        "status": "active",
        "endpoint": "http://localhost:8002",
        "capabilities": ["udc_compliance"]
      }
    ],
    "total": 2
  },
  "timestamp": "2025-01-18T10:02:00Z"
}
```

---

## 📊 Get Droplet Details

### GET /droplets/{droplet_id}

Get detailed information about a specific droplet.

**Endpoint:** `GET https://drop10.fullpotential.ai/droplets/42`

**cURL Example:**
```bash
curl -X GET "https://drop10.fullpotential.ai/droplets/42" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## ⚙️ Implementation Example (Python)

```python
import httpx
import uuid
from datetime import datetime

ORCHESTRATOR_URL = "https://drop10.fullpotential.ai"
DROPLET_ID = 42
JWT_TOKEN = "your_jwt_token_here"

async def register_with_orchestrator():
    """Register droplet with Orchestrator"""
    
    payload = {
        "trace_id": str(uuid.uuid4()),
        "source": DROPLET_ID,
        "target": 10,
        "message_type": "command",
        "payload": {
            "id": DROPLET_ID,
            "name": "droplet0",
            "steward": "Haythem",
            "endpoint": "http://localhost:8002",
            "capabilities": ["udc_compliance", "health_monitoring"],
            "version": "1.0.0",
            "status": "active"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/droplets/register",
            json=payload,
            headers={
                "Authorization": f"Bearer {JWT_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        return response.json()

async def send_heartbeat():
    """Send heartbeat to Orchestrator"""
    
    payload = {
        "trace_id": str(uuid.uuid4()),
        "source": DROPLET_ID,
        "target": 10,
        "message_type": "heartbeat",
        "payload": {
            "status": "active",
            "metrics": {
                "cpu_percent": 15.5,
                "memory_mb": 256,
                "requests_last_minute": 10,
                "errors_last_minute": 0
            }
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/droplets/{DROPLET_ID}/heartbeat",
            json=payload,
            headers={
                "Authorization": f"Bearer {JWT_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        return response.json()

# Run every 60 seconds
import asyncio

async def heartbeat_loop():
    while True:
        try:
            await send_heartbeat()
            print("✅ Heartbeat sent")
        except Exception as e:
            print(f"❌ Heartbeat failed: {e}")
        await asyncio.sleep(60)
```

---

## ✅ Integration Checklist

- [ ] Generate JWT token using private key
- [ ] Register droplet on startup
- [ ] Start heartbeat loop (every 60 seconds)
- [ ] Include UDC envelope in all requests
- [ ] Use correct message_type for each operation
- [ ] Handle registration errors with retry
- [ ] Log all Orchestrator communications

---

## 🚨 Error Responses

**401 Unauthorized:**
```json
{"detail": "Not authenticated"}
```

**401 Invalid Credentials:**
```json
{"detail": "Could not validate credentials"}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "trace_id"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

---

## 📝 Notes

1. **All requests must use UDC envelope format**
2. **Heartbeat must be sent every 60 seconds**
3. **trace_id must be unique UUID v4 for each request**
4. **timestamp must be ISO-8601 format with Z suffix**
5. **source is your droplet ID, target is 10 (Orchestrator)**
6. **JWT token must be valid and not expired**
