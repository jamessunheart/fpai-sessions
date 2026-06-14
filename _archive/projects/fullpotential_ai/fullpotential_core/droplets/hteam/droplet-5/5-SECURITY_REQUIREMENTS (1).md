# SECURITY_REQUIREMENTS.md
**Full Potential AI - Security Best Practices**
**Version:** 1.0
**Last Updated:** November 2025

---

## 🎯 SECURITY PHILOSOPHY

**Zero Trust Architecture:** Never trust, always verify
**Defense in Depth:** Multiple layers of protection
**Least Privilege:** Minimum permissions necessary
**Fail Secure:** Default to denying access when uncertain

---

## 🔐 AUTHENTICATION & AUTHORIZATION

### JWT Token Management

**Required Implementation:**

```python
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, Header

# JWT Configuration
JWT_ALGORITHM = "RS256"  # MUST use asymmetric encryption
JWT_ISSUER = "registry.fullpotential.ai"
JWT_AUDIENCE = "fullpotential.droplets"
TOKEN_EXPIRY_HOURS = 24

# Token Verification (Required on ALL endpoints except /health)
async def verify_jwt_token(authorization: str = Header(None)) -> dict:
    """
    Verify JWT token from Authorization header.
    
    Security Requirements:
    1. Token must be present
    2. Must be properly formatted ("Bearer <token>")
    3. Signature must be valid (verified with Registry's public key)
    4. Token must not be expired
    5. Issuer must match expected value
    6. Audience must match expected value
    """
    
    # Check header presence
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check Bearer format
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract token
    token = authorization.replace("Bearer ", "")
    
    try:
        # Verify signature and claims
        payload = jwt.decode(
            token,
            REGISTRY_PUBLIC_KEY,  # Get from secure config
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True
            }
        )
        
        # Additional validation
        if "droplet_id" not in payload:
            raise HTTPException(401, "Token missing droplet_id claim")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.JWTClaimsError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token claims: {e}"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {e}"
        )

# Apply to protected endpoints
@app.post("/message")
async def receive_message(
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    # Token verified, droplet_id in token_data
    source_droplet = token_data["droplet_id"]
    # Process message...
```

### Public Key Management

**CRITICAL: Never hardcode keys in code**

```python
# BAD - Never do this
PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"""

# GOOD - Load from secure location
from pathlib import Path

def load_registry_public_key() -> str:
    """Load Registry's public key from secure file"""
    key_path = Path("/etc/droplet/registry_public_key.pem")
    
    if not key_path.exists():
        raise RuntimeError("Registry public key not found")
    
    return key_path.read_text()

REGISTRY_PUBLIC_KEY = load_registry_public_key()
```

---

## 🔒 SECRET MANAGEMENT

### Environment Variables (Required)

**Never commit secrets to git:**

```bash
# .gitignore (MUST include)
.env
.env.local
.env.production
*.pem
*.key
secrets/
```

**Use pydantic-settings for validation:**

```python
from pydantic_settings import BaseSettings
from pydantic import SecretStr, validator

class Settings(BaseSettings):
    # Database
    database_url: SecretStr
    
    # Authentication
    jwt_secret: SecretStr
    registry_public_key: str
    
    # API Keys
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    
    # Environment
    environment: str = "development"
    
    @validator("environment")
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("Invalid environment")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Load settings
settings = Settings()

# Use secrets safely
db_url = settings.database_url.get_secret_value()  # Only when needed
```

### .env.example Template

**Required in every repository:**

```bash
# .env.example
# Copy this to .env and fill in actual values
# NEVER commit .env to git

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Authentication
JWT_SECRET=your-secret-key-here
REGISTRY_URL=https://registry.fullpotential.ai

# Droplet Configuration
DROPLET_ID=14
DROPLET_NAME=Visibility Deck
DROPLET_STEWARD=Your Name
DROPLET_URL=https://your-droplet.fullpotential.ai

# API Keys (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

---

## 🛡️ INPUT VALIDATION

### Pydantic Models (Required)

**ALWAYS validate inputs with Pydantic:**

```python
from pydantic import BaseModel, Field, validator
from typing import Literal

class UDCMessage(BaseModel):
    """Validated UDC message format"""
    
    trace_id: str = Field(..., min_length=36, max_length=36)
    source: int = Field(..., ge=1, le=999)
    target: int = Field(..., ge=1, le=999)
    message_type: Literal["status", "event", "command", "query"]
    payload: dict
    timestamp: str
    
    @validator("trace_id")
    def validate_trace_id_format(cls, v):
        """Ensure trace_id is valid UUID"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("trace_id must be valid UUID")
        return v
    
    @validator("timestamp")
    def validate_timestamp_format(cls, v):
        """Ensure timestamp is valid ISO 8601"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("timestamp must be ISO 8601 format")
        return v
    
    @validator("payload")
    def validate_payload_size(cls, v):
        """Prevent payload bombs"""
        import json
        payload_size = len(json.dumps(v))
        if payload_size > 1_000_000:  # 1MB limit
            raise ValueError("Payload too large (max 1MB)")
        return v

# Use in endpoints
@app.post("/message")
async def receive_message(message: UDCMessage):
    # Pydantic has validated everything automatically
    # Safe to use message.trace_id, message.source, etc.
    pass
```

### SQL Injection Prevention

**Use parameterized queries ALWAYS:**

```python
# GOOD - Parameterized (safe)
async def get_user(user_id: int):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )

# GOOD - ORM (safe)
user = await User.get(id=user_id)

# BAD - String formatting (NEVER DO THIS)
async def get_user(user_id: int):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return await conn.fetchrow(query)
    # Vulnerable to SQL injection!
```

### Path Traversal Prevention

```python
from pathlib import Path

def safe_file_access(filename: str, base_dir: str) -> Path:
    """Prevent path traversal attacks"""
    
    # Resolve to absolute path
    base_path = Path(base_dir).resolve()
    file_path = (base_path / filename).resolve()
    
    # Ensure file is within allowed directory
    if not file_path.is_relative_to(base_path):
        raise ValueError("Invalid file path")
    
    return file_path

# Usage
try:
    safe_path = safe_file_access(user_input, "/var/droplet/data")
    content = safe_path.read_text()
except ValueError:
    # Path traversal attempt blocked
    raise HTTPException(403, "Access denied")
```

---

## 🌐 NETWORK SECURITY

### HTTPS Only (Production)

**Required in production environment:**

```python
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

@app.middleware("http")
async def enforce_https(request: Request, call_next):
    """Enforce HTTPS in production"""
    
    if settings.environment == "production":
        if request.url.scheme != "https":
            raise HTTPException(
                status_code=403,
                detail="HTTPS required in production"
            )
    
    return await call_next(request)
```

### CORS Configuration

**Restrictive by default:**

```python
from fastapi.middleware.cors import CORSMiddleware

# GOOD - Specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dashboard.fullpotential.ai",
        "https://fullpotential.ai"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# BAD - Permissive (only for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Never in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting

**Prevent abuse:**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints
@app.post("/message")
@limiter.limit("100/minute")  # Max 100 requests per minute
async def receive_message(request: Request, message: UDCMessage):
    pass

# More restrictive for expensive operations
@app.post("/process")
@limiter.limit("10/minute")
async def process_task(request: Request, task: TaskModel):
    pass
```

---

## 📝 SECURE LOGGING

### Never Log Sensitive Data

```python
import structlog

log = structlog.get_logger()

# GOOD - Log without sensitive data
log.info(
    "user_login",
    user_id=user.id,
    ip_address=request.client.host,
    success=True
)

# BAD - Logs password
log.info(
    "user_login",
    username=username,
    password=password,  # NEVER LOG PASSWORDS!
    success=True
)

# BAD - Logs full JWT
log.info(
    "request_authenticated",
    token=token  # Contains sensitive claims!
)

# GOOD - Log token metadata only
log.info(
    "request_authenticated",
    droplet_id=token_data["droplet_id"],
    token_expires_at=token_data["exp"]
)
```

### Sanitize Error Messages

```python
# GOOD - Generic error to user, detailed log
try:
    sensitive_operation()
except Exception as e:
    log.error(
        "operation_failed",
        error=str(e),
        stack_trace=traceback.format_exc()
    )
    raise HTTPException(
        status_code=500,
        detail="An error occurred"  # Generic
    )

# BAD - Exposes internal details
try:
    sensitive_operation()
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Database error: {e}"  # Reveals DB structure!
    )
```

---

## 🔍 SECURITY HEADERS

**Required for all responses:**

```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

## 🐳 DOCKER SECURITY

### Secure Dockerfile

```dockerfile
# GOOD - Security best practices
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 droplet && \
    chown -R droplet:droplet /app

# Set working directory
WORKDIR /app

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=droplet:droplet . .

# Switch to non-root user
USER droplet

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# BAD - Running as root
FROM python:3.11-slim
COPY . .
CMD ["python", "app.py"]  # Runs as root!
```

### Docker Secrets

```yaml
# docker-compose.yml
services:
  droplet:
    image: droplet-14:latest
    secrets:
      - db_password
      - jwt_secret
    environment:
      - DATABASE_URL=postgresql://user:file:///run/secrets/db_password@db:5432/droplet

secrets:
  db_password:
    file: ./secrets/db_password.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
```

---

## 🔄 DEPENDENCY SECURITY

### Regular Updates

```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
pip install --upgrade -r requirements.txt

# For npm
npm audit
npm audit fix
```

### Dependency Pinning

```txt
# requirements.txt
# Pin exact versions for production
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# Not just >=0.104.0 which could break
```

---

## ✅ SECURITY CHECKLIST

**Before deploying to production:**

### Authentication
- [ ] JWT verification on all protected endpoints
- [ ] Using RS256 (asymmetric) algorithm
- [ ] Token expiration verified
- [ ] Public key loaded from secure location
- [ ] No hardcoded secrets

### Input Validation
- [ ] All inputs validated with Pydantic
- [ ] SQL queries parameterized
- [ ] File paths sanitized
- [ ] Payload size limits enforced

### Network
- [ ] HTTPS enforced in production
- [ ] CORS configured restrictively
- [ ] Rate limiting implemented
- [ ] Security headers added

### Logging
- [ ] No passwords logged
- [ ] No tokens logged
- [ ] Error messages sanitized
- [ ] Structured logging implemented

### Docker
- [ ] Running as non-root user
- [ ] Secrets not in image
- [ ] Minimal base image
- [ ] Dependencies scanned for vulnerabilities

### Environment
- [ ] .env in .gitignore
- [ ] .env.example provided
- [ ] Production secrets in secure storage
- [ ] Different secrets for dev/staging/prod

---

## 🚨 INCIDENT RESPONSE

### If Security Issue Discovered:

1. **Immediate:** Take affected system offline if critical
2. **Document:** Record what happened, when, how discovered
3. **Notify:** Contact James (system architect) immediately
4. **Patch:** Fix vulnerability
5. **Test:** Verify fix works
6. **Deploy:** Roll out patch
7. **Monitor:** Watch for similar issues
8. **Learn:** Document lesson, update this guide

---

## 📞 SECURITY CONTACTS

**Report security issues to:**
- **Primary:** James (System Architect)
- **Registry:** Liban (Authentication issues)
- **Never:** Public channels (Slack, GitHub issues)

---

**END SECURITY_REQUIREMENTS.md**
