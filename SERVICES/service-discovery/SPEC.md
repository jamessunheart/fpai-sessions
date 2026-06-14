# SPEC - Service Discovery (Droplet #3)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 3
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The Service Discovery module (often integrated with Registry) allows droplets to find each other dynamically without hardcoded IPs. It handles DNS resolution, load balancing, and health-based routing.

### 1.2 Position in Ecosystem
- **Upstream:** Reads from Registry.
- **Downstream:** Consumed by all Droplets via client libraries or sidecars.
- **Role:** The Phonebook.

### 1.3 Dependencies
**Required Services:**
- Registry (Droplet #1)

**External Dependencies:**
- CoreDNS / Consul (Optional backends)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **Name Resolution** - Resolve `service-name` to `IP:Port`.
2. **Health Filtering** - Only return healthy instances.
3. **Load Balancing** - Round-robin distribution.

### 2.2 Supported Operations
- `resolve` - Get address for a service.
- `register_instance` - Add a new running instance.

---

## 3. API SPECIFICATION

### 3.1 UDC Endpoints (Required)

#### Health Check
```
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### Capabilities
```
GET /capabilities
```
**Response:**
```json
{
  "service_name": "service-discovery",
  "droplet_id": 3,
  "capabilities": ["service_discovery", "load_balancing"],
  "integration_endpoints": [
    {
      "path": "/api/v1/resolve/{service}",
      "method": "GET"
    }
  ]
}
```

---

### 3.2 Business Logic Endpoints

#### Resolve Service
```
GET /api/v1/resolve/{service_name}
```
**Response:**
```json
{
  "service": "ai-automation",
  "instances": [
    {"host": "10.0.1.5", "port": 8011, "status": "healthy"}
  ]
}
```

---

## 4. DATA MODEL

### 4.1 In-Memory Store
- **Instances:** `Dict[service_name, List[Instance]]`
- **TTL:** 30 seconds (refresh from Registry)

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=service-discovery
SERVICE_PORT=8003
DROPLET_ID=3
REGISTRY_URL=http://registry:8000
REFRESH_INTERVAL=30
```

---

## 6. DEPLOYMENT

### 6.1 Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8003
LABEL droplet.id="3"
LABEL droplet.name="service-discovery"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

---

## 7. COMPLIANCE CHECKLIST
- [x] All 5 UDC endpoints
- [x] Registers with Registry
- [x] Dockerized
