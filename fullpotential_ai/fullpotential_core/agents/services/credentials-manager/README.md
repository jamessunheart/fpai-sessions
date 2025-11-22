# Credentials Manager - Droplet #25

**Secure Storage for API Keys, Billing Details, and Helper Access**

## Overview

The Credentials Manager is the secure foundation of the Business Operating System. It stores sensitive credentials (API keys, credit cards, passwords) with AES-256 encryption, manages helper access with scoped tokens, and maintains a complete audit trail.

## Features

- **AES-256 Encryption** - All credentials encrypted at rest
- **Scoped Access Tokens** - Helpers only see what they need
- **Audit Logging** - Every access logged (who, when, what)
- **Auto-Revoke** - Tokens expire after configured time
- **Admin Control** - Full credential management
- **Helper Access** - Limited, time-bound access for contractors

## Security Model

### Encryption
```
Plaintext → AES-256-GCM → Encrypted → Base64 → Database
Database → Base64 → Encrypted → AES-256-GCM → Plaintext
```

- Master encryption key (32 bytes) stored in environment
- PBKDF2 key derivation (100,000 iterations)
- Fernet symmetric encryption
- No credential values stored in plaintext

### Access Control
```
Admin:
✅ Create/update/delete credentials
✅ Grant helper access
✅ View audit logs
✅ Revoke tokens

Helper (with token):
✅ Read only assigned credentials
❌ Cannot create/update/delete
❌ Cannot see other credentials
❌ Cannot grant access
```

### Audit Trail
Every access logged:
- Credential accessed
- Who accessed (admin or helper name)
- When (timestamp)
- IP address
- Success/failure

## API Endpoints

### Authentication

**POST /auth/admin**
```bash
curl -X POST http://localhost:8025/auth/admin \
  -d "username=admin&password=your_password"

# Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Credential Management (Admin Only)

**POST /credentials** - Create credential
```bash
curl -X POST http://localhost:8025/credentials \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sendgrid_api_key",
    "type": "api_key",
    "value": "SG.abc123...",
    "service": "sendgrid",
    "metadata": {"environment": "production"}
  }'
```

**GET /credentials** - List all credentials
```bash
curl http://localhost:8025/credentials \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**GET /credentials/{id}** - Get credential with decrypted value
```bash
curl http://localhost:8025/credentials/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Response:
{
  "name": "sendgrid_api_key",
  "value": "SG.abc123...",  # Decrypted
  "service": "sendgrid",
  "type": "api_key"
}
```

**PUT /credentials/{id}** - Update credential
```bash
curl -X PUT http://localhost:8025/credentials/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "SG.new_key...", "is_active": true}'
```

**DELETE /credentials/{id}** - Delete credential
```bash
curl -X DELETE http://localhost:8025/credentials/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Helper Access Tokens (Admin Only)

**POST /tokens** - Create helper access token
```bash
curl -X POST http://localhost:8025/tokens \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "helper_name": "sendgrid_setup_contractor",
    "credential_ids": [1],
    "scope": "read_only",
    "expires_hours": 24
  }'

# Response:
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "helper_name": "sendgrid_setup_contractor",
  "credential_ids": [1],
  "scope": "read_only",
  "expires_at": "2025-01-15T10:00:00Z"
}
```

**DELETE /tokens/{id}** - Revoke token
```bash
curl -X DELETE http://localhost:8025/tokens/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Audit Logs (Admin Only)

**GET /audit** - View audit logs
```bash
curl http://localhost:8025/audit \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Response:
[
  {
    "id": 1,
    "credential_id": 1,
    "action": "access",
    "accessor": "sendgrid_setup_contractor",
    "ip_address": "192.168.1.100",
    "timestamp": "2025-01-14T10:30:00Z",
    "success": true,
    "details": {}
  }
]
```

## Setup

### 1. Install Dependencies
```bash
cd /Users/jamessunheart/Development/agents/services/credentials-manager
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env

# Generate encryption key (32 bytes hex)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate JWT secret
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate admin password hash
python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your_password'))"

# Edit .env with generated values
```

### 3. Setup Database
```bash
# Install PostgreSQL
brew install postgresql  # macOS
# or: apt install postgresql  # Linux

# Create database
createdb credentials

# Update DATABASE_URL in .env
DATABASE_URL=postgresql+asyncpg://username:password@localhost/credentials
```

### 4. Start Service
```bash
uvicorn app.main:app --port 8025 --reload

# Or for production:
uvicorn app.main:app --host 0.0.0.0 --port 8025
```

## Usage Examples

### Storing API Keys

**SendGrid API Key:**
```bash
# Admin stores SendGrid key
curl -X POST http://localhost:8025/credentials \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "sendgrid_production",
    "type": "api_key",
    "value": "SG.abc123...",
    "service": "sendgrid"
  }'
```

**OpenAI API Key:**
```bash
curl -X POST http://localhost:8025/credentials \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "openai_production",
    "type": "api_key",
    "value": "sk-abc123...",
    "service": "openai"
  }'
```

### Granting Helper Access

**Scenario: Hire contractor to setup SendGrid**

1. Store SendGrid billing details:
```bash
curl -X POST http://localhost:8025/credentials \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "sendgrid_billing",
    "type": "credit_card",
    "value": "{"number": "4111...", "cvv": "123", "exp": "12/25"}",
    "service": "sendgrid"
  }'

# Response: credential_id = 5
```

2. Create access token for helper:
```bash
curl -X POST http://localhost:8025/tokens \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "helper_name": "contractor_john",
    "credential_ids": [5],
    "scope": "read_only",
    "expires_hours": 24
  }'

# Response:
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_at": "2025-01-15T10:00:00Z"
}
```

3. Give token to contractor:
```
"Here's your access token. Use it to access SendGrid billing.
It expires in 24 hours.

Token: eyJ0eXAiOiJKV1QiLCJhbGc..."
```

4. Contractor accesses credential:
```bash
curl http://localhost:8025/credentials/5 \
  -H "Authorization: Bearer $HELPER_TOKEN"

# Response:
{
  "name": "sendgrid_billing",
  "value": "{"number": "4111...", "cvv": "123", "exp": "12/25"}",
  "service": "sendgrid"
}
```

5. After task complete, revoke access:
```bash
curl -X DELETE http://localhost:8025/tokens/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Integration with Business OS

### Outreach Service Integration
```python
# Outreach service needs SendGrid key
import httpx

async def get_sendgrid_key():
    response = await httpx.get(
        "http://localhost:8025/credentials/1",
        headers={"Authorization": f"Bearer {service_token}"}
    )
    credential = response.json()
    return credential["value"]
```

### Helper Management Integration
```python
# Helper management creates token for contractor
async def hire_contractor(task: str, credential_ids: List[int]):
    # Create access token
    response = await httpx.post(
        "http://localhost:8025/tokens",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "helper_name": f"contractor_{task}",
            "credential_ids": credential_ids,
            "scope": "read_only",
            "expires_hours": 24
        }
    )
    token_data = response.json()

    # Send token to contractor
    send_to_contractor(token_data["token"])
```

## Security Best Practices

1. **Never log credential values** - Only log credential IDs
2. **Rotate encryption keys** - Every 6-12 months
3. **Monitor audit logs** - Check for suspicious access
4. **Revoke unused tokens** - Don't leave active tokens open
5. **Use HTTPS in production** - Credentials in transit must be encrypted
6. **Backup database encrypted** - Use pgcrypto or disk encryption
7. **Limit token lifetime** - Default 24 hours, shorter for sensitive credentials

## Files

```
credentials-manager/
├── app/
│   ├── __init__.py       # Service metadata
│   ├── config.py         # Configuration
│   ├── models.py         # Data models
│   ├── database.py       # Database connection
│   ├── crypto.py         # Encryption utilities
│   ├── auth.py           # Authentication/authorization
│   └── main.py           # FastAPI application
├── requirements.txt      # Dependencies
├── .env.example          # Environment template
└── README.md             # This file
```

---

**Status:** Ready for deployment
**Version:** 1.0.0
**Droplet ID:** 25
**Port:** 8025

🔐 Secure Foundation for Business Operating System
