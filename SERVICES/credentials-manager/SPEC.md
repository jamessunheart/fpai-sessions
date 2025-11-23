# SPEC - Credentials Manager (Droplet #9)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 9
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The Credentials Manager is the system's secure vault. It stores API keys, private keys, and sensitive configurations, serving them to authorized droplets on demand (or injecting them at runtime).

### 1.2 Position in Ecosystem
- **Upstream:** Admin (manual input) or Orchestrator (key rotation).
- **Downstream:** All services needing secrets.
- **Role:** The Vault.

### 1.3 Dependencies
**Required Services:**
- Registry (Droplet #1) - For identity verification

**External Dependencies:**
- HashiCorp Vault (optional backend)
- AWS Secrets Manager (optional backend)
- Encrypted File Storage (default)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **Secret Storage** - Encrypt and store keys at rest.
2. **Access Control** - Verify which droplet is asking for which key.
3. **Audit Logging** - Track every secret access attempt.

### 2.2 Supported Operations
- `get_secret` - Retrieve a specific key.
- `rotate_secret` - Update a key value.

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
  "service_name": "credentials-manager",
  "droplet_id": 9,
  "capabilities": ["secrets_management", "encryption"],
  "integration_endpoints": [
    {
      "path": "/api/v1/secrets/{key}",
      "method": "GET"
    }
  ]
}
```

---

### 3.2 Business Logic Endpoints

#### Get Secret
```
GET /api/v1/secrets/{key_name}
```
**Headers:**
```
Authorization: Bearer <jwt_token>
```
**Response:**
```json
{
  "value": "sk-12345...",
  "expires_at": "2025-12-31T00:00:00Z"
}
```

#### Set Secret (Admin Only)
```
POST /api/v1/secrets
```
**Request:**
```json
{
  "key": "OPENAI_API_KEY",
  "value": "sk-new-key...",
  "allowed_droplets": [11, 7]
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema

#### Secrets
```sql
CREATE TABLE secrets (
    key_name VARCHAR(100) PRIMARY KEY,
    encrypted_value TEXT NOT NULL,
    allowed_droplets INT[], -- Array of Droplet IDs
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=credentials-manager
SERVICE_PORT=8009
DROPLET_ID=9
REGISTRY_URL=http://registry:8000
MASTER_KEY=... # Used to decrypt the vault
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
EXPOSE 8009
LABEL droplet.id="9"
LABEL droplet.name="credentials-manager"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009"]
```

---

## 7. COMPLIANCE CHECKLIST
- [x] All 5 UDC endpoints
- [x] Registers with Registry
- [x] Dockerized
