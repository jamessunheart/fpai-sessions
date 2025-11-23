# SPEC - Credentials Manager (Droplet #25)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 25
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The digital vault of the ecosystem. Securely stores API keys, billing details, and secrets using AES-256 encryption. It issues time-limited, scoped access tokens to other droplets, ensuring no service holds permanent keys to the kingdom.

### 1.2 Position in Ecosystem
This service sits in the **Foundation Layer** (Security). It is a critical dependency for almost every other droplet that needs to talk to the outside world (OpenAI, Stripe, etc.).

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery

**External Dependencies:**
- None (Self-contained vault)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Secure Storage]** - AES-256-GCM encryption for all secrets at rest.
2. **[Access Control]** - Issues short-lived JWTs for specific secrets.
3. **[Audit Logging]** - Immutable record of who accessed what and when.

### 2.2 Supported Operations
- `store_secret` - Encrypt and save a value.
- `retrieve_secret` - Decrypt and return a value (if authorized).
- `rotate_key` - Re-encrypt all secrets with a new master key.

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
  "service_name": "credentials-manager",
  "droplet_id": 25,
  "capabilities": ["vault", "encryption", "audit"],
  "supported_operations": ["store", "retrieve", "audit"],
  "integration_endpoints": [
    { "path": "/api/v1/secrets/{key}", "method": "GET" }
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
  "stored_secrets": 142,
  "last_rotation": "2025-11-01T00:00:00Z"
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

#### Retrieve Secret
```
GET /api/v1/secrets/{key}
```
**Request Header:** `Authorization: Bearer <scoped_token>`
**Response:**
```json
{
  "key": "stripe_api_key",
  "value": "sk_live_...",
  "expires_in": 3600
}
```

#### Audit Log
```
GET /api/v1/audit
```
**Response:**
```json
{
  "events": [
    { "actor": "i-match", "action": "read", "key": "stripe_key", "time": "..." }
  ]
}
```

---

## 4. DATA MODEL

### 4.1 Vault Schema
#### `secrets`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Secret ID |
| key | String | Lookup key |
| value_enc | Binary | Encrypted blob |
| version | Int | Key version |

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=credentials-manager
SERVICE_PORT=8025
DROPLET_ID=25
REGISTRY_URL=http://registry:8000
MASTER_KEY=... (Injected via secure env)
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] AES-256 encryption implemented
- [x] Registers with Registry
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎
