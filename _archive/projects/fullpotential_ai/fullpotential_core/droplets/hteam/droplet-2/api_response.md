# Droplet API Response Standards

**Source:** Droplet #42 Endpoints  
**Date:** November 18, 2025  
**Status:** Production Ready

---

## 🎯 Your Droplet Endpoints

All responses follow UDC v1.0 specification for droplet mesh integration.

**Base URL:** `http://localhost:8002`

---

## 🔐 Authentication

**All endpoints now require JWT authentication except /health**

Protected endpoints require:
```
Authorization: Bearer <JWT_TOKEN>
```

---

## 📡 UDC Core Endpoints

### 1. Health Check
**Endpoint:** `GET /health`  
**Auth:** ✅ None required (public endpoint)

**Success Response (200):**
```json
{
  "id": 42,
  "name": "droplet0",
  "steward": "Haythem",
  "status": "active",
  "endpoint": "http://localhost:8002",
  "proof": "sha256_hash_of_last_update",
  "cost_usd": 0.05,
  "yield_usd": 0.00,
  "updated_at": "2025-11-18T01:30:00Z"
}
```

---

### 2. Capabilities
**Endpoint:** `GET /capabilities`  
**Auth:** 🔒 Bearer JWT token required

**Success Response (200):**
```json
{
  "version": "1.0.0",
  "features": [
    "udc_compliance",
    "health_monitoring",
    "message_handling",
    "metrics_collection"
  ],
  "dependencies": ["registry", "orchestrator"],
  "udc_version": "1.0",
  "metadata": {
    "build_date": "2025-11-08",
    "commit_hash": "dev",
    "environment": "development"
  }
}
```

---

### 3. State
**Endpoint:** `GET /state`  
**Auth:** 🔒 Bearer JWT token required

**Success Response (200):**
```json
{
  "cpu_percent": 23.4,
  "memory_mb": 512,
  "uptime_seconds": 86400,
  "requests_total": 15234,
  "requests_per_minute": 42,
  "errors_last_hour": 0,
  "last_restart": "2025-11-17T12:00:00Z"
}
```

---

### 4. Dependencies
**Endpoint:** `GET /dependencies`  
**Auth:** 🔒 Bearer JWT token required

**Success Response (200):**
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

### 5. Version
**Endpoint:** `GET /version`  
**Auth:** 🔒 Bearer JWT token required

**Success Response (200):**
```json
{
  "version": "1.0.0",
  "build_date": "2025-11-08",
  "commit_hash": "dev",
  "environment": "development",
  "deployed_by": "Haythem"
}
```

---

## 📨 UDC Messaging Endpoints

### 6. Send Message
**Endpoint:** `POST /send`  
**Auth:** 🔒 Bearer JWT token required  
**Content-Type:** `application/json`

**⚠️ IMPORTANT:** This is a POST request. Data must be in the request body, NOT query parameters.

**Request Body:**
```json
{
  "target": droplet_id_or_name,
  "message_type": "event",
  "payload": {
    "action": "ping",
    "from": "droplet42"
  },
  "priority": "normal",
  "retry_count": 3
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8002/send \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target": 1, "message_type": "event", "payload": {}}'
```

**Success Response (200):**
```json
{
  "sent": true,
  "target": 1,
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "delivered"
}
```

**Error Response (500):**
```json
{
  "sent": false,
  "target": 1,
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "error",
  "error": "No valid JWT token"
}
```

---

### 7. Receive Message
**Endpoint:** `POST /message`  
**Auth:** 🔒 Bearer JWT token required

**Request Body:**
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "droplet-1",
  "target": "droplet-42",
  "message_type": "event",
  "payload": {
    "action": "status_update",
    "data": {}
  },
  "timestamp": "2025-11-18T01:30:00Z",
  "signature": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Note:** UDC requires BOTH Authorization header AND signature field (dual authentication)

**Success Response (200):**
```json
{
  "received": true,
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "processed_at": "2025-11-18T01:30:01Z",
  "result": "success"
}
```

---

## 🔧 UDC Management Endpoints

### 8. Reload Config
**Endpoint:** `POST /reload-config`  
**Auth:** 🔒 Bearer JWT token required

**Request Body:**
```json
{
  "config_path": "/path/to/config.json"
}
```

**Success Response (200):**
```json
{
  "reloaded": true,
  "config_path": "/path/to/config.json",
  "timestamp": "2025-11-08T03:00:00Z"
}
```

---

### 9. Shutdown
**Endpoint:** `POST /shutdown`  
**Auth:** 🔒 Bearer JWT token required

**Request Body:**
```json
{
  "delay_seconds": 10,
  "reason": "maintenance"
}
```

**Success Response (200):**
```json
{
  "shutdown_scheduled": true,
  "delay_seconds": 10,
  "reason": "maintenance",
  "scheduled_at": "2025-11-08T03:00:00Z"
}
```

---

## 🔍 Common Issues & Troubleshooting

### Error: `"loc": ["query", "target"]` - Different Implementation
**Situation:** Some servers (including Registry drop18.fullpotential.ai) expect query parameters instead of request body.

**Two Implementation Patterns:**

**Pattern A - Query Parameters (Registry/drop18):**
```bash
curl -X POST "https://drop18.fullpotential.ai/send?target=1&message_type=event" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payload": {}}'
```

**Pattern B - Request Body (This droplet):**
```bash
curl -X POST http://localhost:8002/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"target": 1, "message_type": "event", "payload": {}}'
```

**Conclusion:** All project documentation (UDC spec, Postman collection, Integration guide) specifies request body. However, Registry (drop18) uses query parameters. Your droplet follows the documented standard. Consider matching Registry's implementation for compatibility.

### Error: "Could not validate credentials"
**Problem:** Missing or invalid JWT token  
**Solution:** Include valid JWT in Authorization header:
```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Error: "Message signature required"
**Problem:** POST /message requires signature field  
**Solution:** Include signature in request body (dual authentication per UDC)

---

## ❌ Standard Error Responses

### Authentication Errors
**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**403 Forbidden:**
```json
{
  "detail": "Not enough permissions"
}
```

### Validation Errors
**422 Unprocessable Entity:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "target"],
      "msg": "Field required",
      "input": {...}
    }
  ]
}
```

**Note:** If `"loc"` shows `["query", "target"]`, the server expects query parameters. If `["body", "target"]`, it expects request body.

### Server Errors
**500 Internal Server Error:**
```json
{
  "detail": "Internal server error"
}
```

---

## 📋 Postman Collection Setup

### Environment Variables
```json
{
  "DROPLET_URL": "http://localhost:8002",
  "JWT_TOKEN": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJyZWdpc3RyeS5mdWxscG90ZW50aWFsLmFpIiwic3ViIjoiNDIiLCJhdWQiOiJmdWxscG90ZW50aWFsLmRyb3BsZXRzIiwiaWF0IjoxNzYzNDI5ODEyLCJleHAiOjE3NjM1MTYyMTIsInJvbGUiOiJkcm9wbGV0Iiwic2NvcGUiOlsicmVnaXN0cnk6aGVhcnRiZWF0IiwicmVnaXN0cnk6cmVnaXN0ZXIiXX0.pWB3Y7bxjXYzzbVmyIByxlBeMa_pnX8JgnKHrLebq3LMoHZ2VQXcpR9wOPJi25imEFVrZr6Qoo3Cxro_YBNI8LeVAcLZEdX1pHWoVIDU3YeezFBJKT9TIQvNV_NEUGgI2DezdjMxKIzfNiaWWpnh4yvTLzLC6TqzC4R3tz3rJGi98kMFj4-YTG0N337WCkh2jaRuflzA6ps9nvaI31TgZ3y1EbzT8QQO4UMngj4piP-S48AQ3r-L1lsMxl_RxzKtQKq7F46oKx9QfKj4ngen80P9IEP8nIAB7LWjXVXhEKU4JlIgce7QKyFezut5hZao1c5UncpZBIMGxGcHQdV7S8egHquoiebwOQ6gKI0Vx9uyshz8btrgsVLCaSgG8kNI2KcW5s0Om8jGvmJ5NIuGI_3luusFznonVAbKILdzA1jYo2EMX4Oxqjkm_pfYTLonTV4wnQyZm8er6W0z_LI9IvM-BkqKJpO2CDESG65wbvPLl5hsRK0xxN2KhfWOEXGt_VHRjRMZvhWlAnSwgYvnjyRsSiU2Hpw4fhG_WFF9pPDjtmqRbRkTahECU-bJBFv7YKMbnVeYgo0HBBvIlJCKg8dHXNWDhyZ3phLOGkbqY-vh4QIAOk0ZSd6vNYFgAGPc0upgOLiM46L6Bahz3RJ6V_G5m9E2zQqeYFayOB1QMGw",
  "TRACE_ID": "{{$guid}}"
}
```

### Headers for Protected Endpoints
```
Authorization: Bearer {{JWT_TOKEN}}
Content-Type: application/json
```

### Test Scripts
```javascript
// Save response data
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// Extract trace_id for chaining
if (pm.response.json().trace_id) {
    pm.environment.set("TRACE_ID", pm.response.json().trace_id);
}
```

---

**Source:** Droplet #42 API Implementation  
**UDC Version:** 1.0  
**Last Updated:** November 18, 2025