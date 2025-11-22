# credentials-manager - SPECS

**Created:** 2025-11-15
**Status:** Production Ready (Droplet #25)
**Port:** 8025

---

## Purpose

Secure storage and management of API keys, billing details, and passwords with AES-256 encryption. Manages helper access with scoped, time-limited tokens. Maintains complete audit trail of all credential access. Foundation for secure Business Operating System.

---

## Requirements

### Functional Requirements
- [ ] Store credentials with AES-256 encryption
- [ ] Support multiple credential types: api_key, credit_card, password, oauth_token
- [ ] Admin authentication with JWT tokens
- [ ] Create, read, update, delete credentials (admin only)
- [ ] Generate scoped access tokens for helpers with time limits
- [ ] Helper access limited to specific credentials only
- [ ] Auto-revoke tokens after expiration time
- [ ] Complete audit logging (who, when, what, IP address)
- [ ] Credential metadata (service name, environment, notes)
- [ ] Credential status (active, inactive, expired)
- [ ] Backup and restore encrypted vault

### Non-Functional Requirements
- [ ] Security: AES-256-GCM encryption, PBKDF2 key derivation (100,000 iterations)
- [ ] Performance: Key retrieval < 50ms, encryption/decryption < 100ms
- [ ] Audit: Every access logged with timestamp, accessor, IP, success/failure
- [ ] Availability: 99.9% uptime
- [ ] Token expiration: Default 24 hours, configurable per token
- [ ] Backup: Encrypted backups every 6 hours

---

## API Specs

### Endpoints

**POST /auth/admin**
- **Purpose:** Admin authentication
- **Input:** username, password (form data)
- **Output:** access_token (JWT), token_type
- **Success:** 200 OK
- **Errors:** 401 if invalid credentials

**POST /credentials**
- **Purpose:** Create new credential (admin only)
- **Input:** name, type, value, service, metadata (optional)
- **Output:** Credential ID, confirmation
- **Success:** 201 Created
- **Errors:** 400 if validation fails, 401 if not admin, 409 if name exists

**GET /credentials**
- **Purpose:** List all credentials (names only, not values)
- **Input:** None
- **Output:** Array of credential metadata
- **Success:** 200 OK
- **Errors:** 401 if not authenticated

**GET /credentials/{id}**
- **Purpose:** Get credential with decrypted value
- **Input:** credential ID
- **Output:** Credential with decrypted value
- **Success:** 200 OK
- **Errors:** 401 if not authenticated, 403 if not authorized, 404 if not found

**PUT /credentials/{id}**
- **Purpose:** Update credential (admin only)
- **Input:** Optional: value, is_active, metadata
- **Output:** Updated credential
- **Success:** 200 OK
- **Errors:** 400 if validation fails, 401 if not admin, 404 if not found

**DELETE /credentials/{id}**
- **Purpose:** Delete credential (admin only)
- **Input:** credential ID
- **Output:** Deletion confirmation
- **Success:** 200 OK
- **Errors:** 401 if not admin, 404 if not found

**POST /tokens**
- **Purpose:** Create helper access token (admin only)
- **Input:** helper_name, credential_ids (array), scope (read_only), expires_hours
- **Output:** token (JWT), expires_at
- **Success:** 201 Created
- **Errors:** 400 if validation fails, 401 if not admin, 404 if credential not found

**GET /tokens**
- **Purpose:** List all access tokens
- **Input:** None
- **Output:** Array of token metadata (not token values)
- **Success:** 200 OK
- **Errors:** 401 if not admin

**DELETE /tokens/{id}**
- **Purpose:** Revoke access token (admin only)
- **Input:** token ID
- **Output:** Revocation confirmation
- **Success:** 200 OK
- **Errors:** 401 if not admin, 404 if not found

**GET /audit**
- **Purpose:** View audit logs (admin only)
- **Input:** Optional: date_range, credential_id, accessor
- **Output:** Array of audit log entries
- **Success:** 200 OK
- **Errors:** 401 if not admin

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "service": "credentials-manager", "encryption": "active"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

### Data Models

```python
class Credential:
    id: int
    name: str
    type: str  # "api_key", "credit_card", "password", "oauth_token"
    encrypted_value: str  # AES-256-GCM encrypted
    service: str
    environment: str  # "production", "staging", "development"
    is_active: bool
    metadata: dict
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_accessed: Optional[datetime]

class AccessToken:
    id: int
    helper_name: str
    credential_ids: List[int]
    scope: str  # "read_only" (only supported scope for now)
    token_hash: str  # Hashed token value
    expires_at: datetime
    created_at: datetime
    revoked: bool
    revoked_at: Optional[datetime]

class AuditLog:
    id: int
    credential_id: int
    action: str  # "access", "create", "update", "delete"
    accessor: str  # Admin username or helper name
    accessor_type: str  # "admin", "helper"
    ip_address: str
    timestamp: datetime
    success: bool
    error: Optional[str]
    details: dict
```

---

## Dependencies

### External Services
- None (self-contained)

### APIs Required
- None (standalone service)

### Data Sources
- PostgreSQL: Credential storage, access tokens, audit logs
- Environment variable: Master encryption key

---

## Success Criteria

How do we know this works?

- [ ] Credentials stored with AES-256 encryption
- [ ] Decryption retrieves original values correctly
- [ ] Admin can CRUD all credentials
- [ ] Helper tokens grant access only to specified credentials
- [ ] Token expiration enforced automatically
- [ ] All access logged in audit trail
- [ ] Encryption key rotation works without data loss
- [ ] Backup and restore preserves encrypted data
- [ ] Performance: key retrieval < 50ms
- [ ] Security: No plaintext credentials in logs or errors

---

## Security Model

### Encryption
```
Plaintext → AES-256-GCM → Encrypted → Base64 → Database
Database → Base64 → Encrypted → AES-256-GCM → Plaintext
```

**Key Derivation:**
- Master key (32 bytes) from environment variable
- PBKDF2 with 100,000 iterations
- Unique salt per credential
- Fernet symmetric encryption (built on AES-256-GCM)

### Access Control

**Admin:**
- Full CRUD on credentials
- Create/revoke access tokens
- View audit logs
- Rotate encryption keys

**Helper (with token):**
- Read-only access to assigned credentials
- Cannot create, update, or delete
- Cannot see other credentials
- Cannot grant access to others

### Audit Trail
Every credential access logged:
- Credential ID
- Accessor (admin username or helper name)
- Timestamp
- IP address
- Success/failure
- Action type

---

## Integration Examples

### Service Retrieves API Key
```python
import httpx

# Service needs SendGrid API key
response = httpx.get(
    "http://credentials-manager:8025/credentials/1",
    headers={"Authorization": f"Bearer {service_token}"}
)
sendgrid_key = response.json()["value"]

# Use for email sending
send_email(sendgrid_key, to, subject, body)
```

### Helper Management Integration
```python
# Helper management creates token for contractor
response = httpx.post(
    "http://credentials-manager:8025/tokens",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={
        "helper_name": "contractor_john",
        "credential_ids": [5],  # SendGrid billing only
        "scope": "read_only",
        "expires_hours": 24
    }
)

token = response.json()["token"]
# Send token to contractor
send_to_contractor(token)
```

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8025
- **Database:** PostgreSQL (with asyncpg)
- **Resource limits:**
  - Memory: 256MB max
  - CPU: 0.5 cores
  - Storage: 1GB for database
- **Response time:** < 50ms for key retrieval
- **Encryption:** AES-256-GCM via Fernet
- **Token expiration:** Checked on every request
- **Audit retention:** 1 year

---

## Security Best Practices

1. Never log credential values
2. Rotate master encryption key every 6-12 months
3. Monitor audit logs for suspicious access patterns
4. Revoke unused tokens immediately
5. Use HTTPS in production
6. Backup database with encryption
7. Limit token lifetime (default 24h, shorter for sensitive)
8. Use strong admin password (bcrypt hashed)

---

**Next Step:** Deploy to production, integrate with helper-management
