# Infrastructure API Test Results

## Overview
The infrastructure screen fetches data from two main sources:
1. **Registry API** - List of all registered droplets
2. **Health Check API** - Individual droplet health status

---

## 1. Get JWT Token (Required for Registry API)

```bash
curl -X POST "https://drop18.fullpotential.ai/auth/token?droplet_id=drop5.fullpotential.ai" \
  -H "X-Registry-Key: a5447df6e4fe34df8c4d0c671ad98ce78de9e55cf152e5d07e5bf221769e31dc"
```

**Response:**
```json
{
  "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "droplet_id": "drop5.fullpotential.ai",
  "algorithm": "RS256"
}
```

**Status:** ✅ 200 OK

---

## 2. Get All Droplets from Registry

```bash
curl -X GET "https://drop18.fullpotential.ai/registry/droplets" \
  -H "Authorization: Bearer <YOUR_TOKEN_HERE>"
```

**Response:**
```json
{
  "droplets": [
    {
      "id": "droplet-12",
      "host": "drop12.fullpotential.ai",
      "ip": "0.0.0.0",
      "status": "active",
      "metadata": {},
      "registered_at": "2025-11-18T04:02:48.555988",
      "last_updated": "2025-11-18T11:20:49.578714",
      "last_heartbeat": 1763464849
    },
    {
      "id": "drop2.fullpotential.ai",
      "host": "drop2.fullpotential.ai",
      "ip": "0.0.0.0",
      "status": "active",
      "metadata": {
        "version": "1.0.0",
        "name": "Airtable Connector",
        "steward": "Haythem",
        "udc_version": "1.0"
      },
      "registered_at": "2025-11-18T17:29:00.802329",
      "last_updated": "2025-11-18T17:35:43.035494",
      "last_heartbeat": 1763487343
    },
    {
      "id": "drop5.fullpotential.ai",
      "host": "drop5.fullpotential.ai",
      "ip": "146.190.145.128",
      "status": "active",
      "metadata": {
        "version": "1.0.0",
        "name": "Full Potential Dashboard",
        "steward": "Haythem",
        "udc_version": "1.0"
      },
      "registered_at": "2025-11-17T16:25:42.488703",
      "last_updated": "2025-11-18T16:25:35.093591",
      "last_heartbeat": 1763483135
    },
    {
      "id": "drop4.fullpotential.ai",
      "host": "drop4.fullpotential.ai",
      "ip": "24.144.86.139",
      "status": "active",
      "metadata": {
        "name": "Multi-Cloud Manager",
        "steward": "Hassan",
        "version": "1.0.0",
        "udc_version": "1.0",
        "endpoint": "https://drop4.fullpotential.ai",
        "capabilities": [
          "multi-cloud-management",
          "digitalocean",
          "hetzner",
          "vultr",
          "udc-v1.0",
          "jwt-jwks"
        ]
      },
      "registered_at": "2025-11-18T08:08:42.248249",
      "last_updated": "2025-11-18T17:35:41.233338",
      "last_heartbeat": 1763487341
    },
    {
      "id": "drop6.fullpotential.ai",
      "host": "drop6.fullpotential.ai",
      "ip": "0.0.0.0",
      "status": "active",
      "metadata": {},
      "registered_at": "2025-11-18T10:42:59.571764",
      "last_updated": "2025-11-18T10:53:18.518191",
      "last_heartbeat": 1763463198
    },
    {
      "id": "vultr-poc-1.vultr.fullpotential.ai",
      "host": "vultr-poc-1.vultr.fullpotential.ai",
      "ip": "0.0.0.0",
      "status": "active",
      "metadata": {
        "name": "vultr-poc-1",
        "provider": "vultr",
        "instance_id": "1a6c078c-70c3-43e6-92f8-c8b7924cdf74",
        "region": "sea",
        "size": "vc2-1c-1gb",
        "role": "compute",
        "env": "production",
        "version": "1.0.0",
        "udc_version": "1.0",
        "created_by": "Multi-Cloud Manager (drop4.fullpotential.ai)",
        "created_at": "2025-11-16T07:57:56.728651",
        "managed_by": "multi-cloud-manager"
      },
      "registered_at": "2025-11-16T07:57:57.448311",
      "last_updated": "2025-11-16T07:57:57.448321"
    },
    {
      "id": "droplet-42",
      "host": "localhost:8001",
      "ip": "0.0.0.0",
      "status": "active",
      "metadata": {},
      "registered_at": "2025-11-18T01:36:53.516030",
      "last_updated": "2025-11-18T04:07:42.343165",
      "last_heartbeat": 1763438862
    }
  ],
  "count": 7
}
```

**Status:** ✅ 200 OK

---

## 3. Check Individual Droplet Health

### Example: Airtable Connector (drop2)

```bash
curl -X GET "https://drop2.fullpotential.ai/health"
```

**Response:**
```json
{
  "id": 2,
  "name": "Airtable Connector",
  "steward": "Haythem",
  "status": "active",
  "endpoint": "https://drop2.fullpotential.ai",
  "proof": "468409d039bfae1709fad0ddc8e4aed46f497bcdf86dbf38de402a07d5c10233",
  "cost_usd": 0.05,
  "yield_usd": 0.0,
  "updated_at": "2025-11-18T17:36:21.433044Z"
}
```

**Status:** ✅ 200 OK

### Example: Dashboard (drop5)

```bash
curl -X GET "https://drop5.fullpotential.ai/health"
```

**Response:**
```html
<html>
<head><title>502 Bad Gateway</title></head>
<body>
<center><h1>502 Bad Gateway</h1></center>
<hr><center>nginx/1.24.0 (Ubuntu)</center>
</body>
</html>
```

**Status:** ❌ 502 Bad Gateway (Service temporarily unavailable)

### Example: Multi-Cloud Manager (drop4)

```bash
curl -X GET "https://drop4.fullpotential.ai/health"
```

---

## Summary

### Working Endpoints ✅
1. **Token Generation** - `POST /auth/token` - Returns JWT for authentication
2. **Registry Droplets** - `GET /registry/droplets` - Returns list of all registered droplets
3. **Health Check (drop2)** - `GET /health` - Returns droplet health status

### Issues Found ⚠️
1. **drop5.fullpotential.ai** - Returns 502 Bad Gateway (nginx error, backend service down)

### Data Flow in Infrastructure Screen
1. Frontend calls `api.getRegistryDroplets()` 
2. This proxies to `/api/proxy?endpoint=/registry/droplets`
3. Proxy fetches JWT token from Registry
4. Proxy calls Registry API with Bearer token
5. For each droplet, frontend calls `/api/health-check?host=<droplet_host>`
6. Health check proxy calls `<droplet_host>/health` endpoint
7. Results are combined and displayed in the UI

### Key Observations
- Registry API requires JWT authentication (RS256)
- Token expires after 24 hours
- Registry returns 7 droplets currently registered
- Health checks are done individually per droplet
- Some droplets may be offline or misconfigured (502 errors)
