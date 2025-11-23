# SPEC - Service Discovery (Droplet #3)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 3
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
A specialized utility for scanning, monitoring, and ensuring the visibility of all services in the mesh. Unlike the Registry (which is passive), Service Discovery is active—it probes the network to find running containers and ports, updating the Registry with reality.

### 1.2 Position in Ecosystem
This service sits in the **Foundation Layer**, working alongside the Registry to ensure the "Map" matches the "Territory."

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - To update SSOT

**External Dependencies:**
- Docker Socket (to list containers)
- Network scanning utilities

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Active Scanning]** - Polls local network ranges and Docker processes.
2. **[Health Probing]** - Hits `/health` on found services to verify UDC compliance.
3. **[Auto-Registration]** - Registers discovered (but unregistered) services with the Registry.

### 2.2 Supported Operations
- `scan_network` - Trigger immediate sweep.
- `get_discovered` - List all visible endpoints.

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
  "version": "1.0.0",
  "timestamp": "2025-11-23T12:00:00Z"
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
  "capabilities": ["scanning", "monitoring", "auto_registration"],
  "supported_operations": ["scan"],
  "integration_endpoints": [
    { "path": "/api/v1/scan", "method": "POST" }
  ]
}
```

#### State
```
GET /state
```
**Response:**
```json
{
  "status": "active",
  "services_found": 14,
  "last_scan": "2025-11-23T12:00:00Z"
}
```

#### Dependencies
```
GET /dependencies
```
**Response:**
```json
{
  "required_services": [
    { "name": "registry", "status": "connected" }
  ]
}
```

#### Message
```
POST /message
```
**Response:**
```json
{
  "received": true,
  "status": "processed"
}
```

---

### 3.2 Business Logic Endpoints

#### Trigger Scan
```
POST /api/v1/scan
```
**Response:**
```json
{
  "status": "scanning",
  "job_id": "scan-101"
}
```

---

## 4. DATA MODEL

### 4.1 Ephemeral State
Service Discovery is stateless between restarts. It builds its world model fresh from each scan cycle.

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=service-discovery
SERVICE_PORT=8003
DROPLET_ID=3
REGISTRY_URL=http://registry:8000
SCAN_INTERVAL=60
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Registers with Registry
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎

