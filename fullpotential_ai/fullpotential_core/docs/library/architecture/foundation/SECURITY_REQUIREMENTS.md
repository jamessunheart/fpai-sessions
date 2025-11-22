# 🔒 SECURITY REQUIREMENTS - Security Standards for All Droplets

**Version:** 1.0
**Last Updated:** 2025-11-15
**Purpose:** Mandatory security requirements for all Full Potential AI droplets

---

## 1. SECURITY PHILOSOPHY

**Security is not optional. It's a requirement.**

Every droplet must:
- ✅ Protect user data
- ✅ Prevent unauthorized access
- ✅ Resist common attacks
- ✅ Maintain audit trails
- ✅ Fail securely

**Rule:** If it touches user data or the network, it must follow these requirements.

---

## 2. AUTHENTICATION & AUTHORIZATION

### 2.1 JWT Token Authentication

**Requirement:** All protected endpoints MUST validate JWT tokens from Registry.

**Implementation:**
```python
from fastapi import Depends, HTTPException, Header
from jose import JWTError, jwt
import httpx

# Get public key from Registry (cache this)
async def get_registry_public_key():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://registry:8000/auth/public-key")
        return response.json()["public_key"]

# Verify JWT token
def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")

        public_key = get_registry_public_key()  # Cache this!
        payload = jwt.decode(token, public_key, algorithms=["RS256"])

        # Verify expiration
        exp = payload.get("exp")
        if not exp or exp < time.time():
            raise HTTPException(status_code=401, detail="Token expired")

        return payload

    except (ValueError, JWTError) as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# Use in endpoints
@app.get("/protected")
def protected_endpoint(token_data: dict = Depends(verify_token)):
    service_id = token_data["service_id"]
    return {"message": f"Authenticated as service {service_id}"}
```

**Requirements:**
- ✅ Use RS256 (RSA signatures)
- ✅ Verify signature with Registry's public key
- ✅ Check expiration (`exp` claim)
- ✅ Cache public key (don't fetch every request)
- ❌ Never accept unsigned tokens
- ❌ Never use weak algorithms (HS256 with shared secret is acceptable only for internal services)

---

### 2.2 API Key Management

**Requirement:** Never hardcode API keys.

**Bad:**
```python
# ❌ NEVER DO THIS
ANTHROPIC_API_KEY = "sk-ant-api03-abc123..."
```

**Good:**
```python
# ✅ Always use environment variables
import os
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set")
```

**Best:**
```python
# ✅ Fetch from credentials manager
async def get_api_key(key_name: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://credentials-manager:8025/credentials/{key_name}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        return response.json()["value"]
```

---

## 3. INPUT VALIDATION

### 3.1 Always Validate Input

**Requirement:** Use Pydantic for ALL input validation.

**Bad:**
```python
# ❌ No validation - vulnerable to injection
@app.post("/user")
def create_user(name: str, email: str):
    db.execute(f"INSERT INTO users (name, email) VALUES ('{name}', '{email}')")
```

**Good:**
```python
# ✅ Pydantic validates automatically
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9 ]+$")
    email: EmailStr

@app.post("/user")
def create_user(user: UserCreate):
    # Input already validated by Pydantic
    db.execute(
        "INSERT INTO users (name, email) VALUES (:name, :email)",
        {"name": user.name, "email": user.email}
    )
```

**Requirements:**
- ✅ All string inputs: max length validation
- ✅ All numbers: min/max range validation
- ✅ All patterns: regex validation
- ✅ All emails: EmailStr type
- ✅ All URLs: HttpUrl type
- ❌ Never trust client input

---

### 3.2 SQL Injection Prevention

**Requirement:** ALWAYS use parameterized queries.

**Bad:**
```python
# ❌ SQL INJECTION VULNERABILITY
user_id = request.args.get("id")
query = f"SELECT * FROM users WHERE id = {user_id}"
result = db.execute(query)
```

**Good:**
```python
# ✅ Parameterized query
user_id = request.args.get("id")
query = "SELECT * FROM users WHERE id = :id"
result = db.execute(query, {"id": user_id})
```

**With SQLAlchemy:**
```python
# ✅ ORM protects against SQL injection
from sqlalchemy import select
stmt = select(User).where(User.id == user_id)
result = session.execute(stmt)
```

**Requirements:**
- ✅ Use parameterized queries (`:param` syntax)
- ✅ Use ORM when possible
- ❌ Never concatenate user input into SQL
- ❌ Never use f-strings with user input in SQL

---

### 3.3 Path Traversal Prevention

**Requirement:** Validate and sanitize file paths.

**Bad:**
```python
# ❌ Path traversal vulnerability
filename = request.args.get("file")
with open(f"/data/{filename}") as f:
    return f.read()
# Attacker could use: file=../../etc/passwd
```

**Good:**
```python
# ✅ Validate filename
import os
from pathlib import Path

def safe_open_file(filename: str):
    # Remove path components
    filename = os.path.basename(filename)

    # Validate against whitelist
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_")
    if not set(filename).issubset(allowed_chars):
        raise ValueError("Invalid filename")

    # Construct safe path
    base_dir = Path("/data")
    file_path = (base_dir / filename).resolve()

    # Verify it's still under base_dir
    if not str(file_path).startswith(str(base_dir)):
        raise ValueError("Path traversal detected")

    return file_path

file_path = safe_open_file(request.args.get("file"))
with open(file_path) as f:
    return f.read()
```

---

## 4. SECRETS MANAGEMENT

### 4.1 Never Commit Secrets

**Requirements:**
- ✅ Use .env files for local development (add to .gitignore)
- ✅ Use environment variables in production
- ✅ Use credentials-manager for shared secrets
- ❌ Never commit .env files
- ❌ Never commit API keys
- ❌ Never commit passwords
- ❌ Never commit private keys

**.gitignore:**
```
.env
.env.*
!.env.example
*.key
*.pem
credentials.json
secrets/
```

---

### 4.2 Encryption at Rest

**Requirement:** Encrypt sensitive data in database.

**Example:**
```python
from cryptography.fernet import Fernet

class EncryptedField:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()

# In models
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]  # Not sensitive
    api_key_encrypted: Mapped[str]  # Encrypted

    @property
    def api_key(self) -> str:
        return encryptor.decrypt(self.api_key_encrypted)

    @api_key.setter
    def api_key(self, value: str):
        self.api_key_encrypted = encryptor.encrypt(value)
```

**What to encrypt:**
- API keys
- Access tokens
- Private keys
- Social Security Numbers
- Credit card numbers
- Personal health information

**What NOT to encrypt:**
- Public identifiers
- Non-sensitive metadata
- Log data (encrypt logs separately if needed)

---

## 5. SECURE COMMUNICATION

### 5.1 HTTPS Only

**Requirement:** All external communication must use HTTPS.

**Internal services (within Docker network):** HTTP acceptable
**External APIs:** HTTPS required

```python
# ✅ Always use HTTPS for external APIs
async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.anthropic.com/v1/messages",  # HTTPS
        headers={"x-api-key": api_key},
        timeout=30.0
    )
```

---

### 5.2 TLS Verification

**Requirement:** Always verify TLS certificates.

**Bad:**
```python
# ❌ Disables certificate verification - MITM VULNERABLE
response = requests.get("https://api.example.com", verify=False)
```

**Good:**
```python
# ✅ Verify certificates (default behavior)
response = requests.get("https://api.example.com")
```

---

### 5.3 Timeout All Requests

**Requirement:** Always set timeouts on external requests.

**Bad:**
```python
# ❌ No timeout - can hang forever
response = httpx.get("https://api.example.com")
```

**Good:**
```python
# ✅ Set reasonable timeout
response = httpx.get(
    "https://api.example.com",
    timeout=10.0  # 10 seconds
)
```

---

## 6. SECURITY HEADERS

### 6.1 Required HTTP Headers

**Requirement:** Include security headers in all responses.

```python
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# CORS (if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard.fullpotential.ai"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Headers explained:**
- `X-Content-Type-Options: nosniff` - Prevent MIME-type sniffing
- `X-Frame-Options: DENY` - Prevent clickjacking
- `X-XSS-Protection: 1; mode=block` - Enable XSS filtering
- `Strict-Transport-Security` - Force HTTPS (when using HTTPS)

---

## 7. ERROR HANDLING

### 7.1 Don't Leak Information

**Bad:**
```python
# ❌ Exposes internal details
@app.get("/user/{id}")
def get_user(id: int):
    try:
        result = db.execute(f"SELECT * FROM users WHERE id = {id}")
        return result
    except Exception as e:
        return {"error": str(e)}  # Might expose: "Table 'users' doesn't exist"
```

**Good:**
```python
# ✅ Generic error messages
@app.get("/user/{id}")
def get_user(id: int):
    try:
        result = db.execute("SELECT * FROM users WHERE id = :id", {"id": id})
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        return result
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")  # Log detailed error
        raise HTTPException(status_code=500, detail="Internal server error")  # Generic message
```

**Requirements:**
- ✅ Log detailed errors for debugging
- ✅ Return generic errors to clients
- ❌ Never expose stack traces
- ❌ Never expose database errors
- ❌ Never expose file paths

---

## 8. RATE LIMITING

### 8.1 Implement Rate Limiting

**Requirement:** Protect against abuse with rate limiting.

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints
@app.get("/api/resource")
@limiter.limit("10/minute")  # 10 requests per minute
def get_resource(request: Request):
    return {"data": "value"}
```

**Limits:**
- Public endpoints: 10-100 requests/minute
- Authenticated endpoints: 100-1000 requests/minute
- Heavy operations: 1-10 requests/minute

---

## 9. LOGGING & MONITORING

### 9.1 Security Event Logging

**Requirement:** Log all security-relevant events.

```python
import logging
import json

logger = logging.getLogger(__name__)

# Log authentication attempts
def log_auth_attempt(success: bool, service_id: str, ip: str):
    logger.info(json.dumps({
        "event": "authentication_attempt",
        "success": success,
        "service_id": service_id,
        "ip": ip,
        "timestamp": datetime.utcnow().isoformat()
    }))

# Log authorization failures
def log_authz_failure(service_id: str, resource: str, action: str):
    logger.warning(json.dumps({
        "event": "authorization_failure",
        "service_id": service_id,
        "resource": resource,
        "action": action,
        "timestamp": datetime.utcnow().isoformat()
    }))
```

**What to log:**
- ✅ Authentication attempts (success/failure)
- ✅ Authorization failures
- ✅ Suspicious activity (repeated failures, unusual patterns)
- ✅ Data access (who accessed what)
- ✅ Configuration changes
- ❌ Don't log passwords
- ❌ Don't log API keys
- ❌ Don't log personal data (unless required for audit)

---

## 10. DEPENDENCY SECURITY

### 10.1 Keep Dependencies Updated

**Requirement:** Regularly update dependencies for security patches.

```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies
pip list --outdated
pip install --upgrade package-name
```

**Process:**
1. Run `safety check` weekly
2. Update security patches immediately
3. Test after updates
4. Update requirements.txt

---

### 10.2 Pin Dependencies

**Requirement:** Pin exact versions in requirements.txt.

**Good:**
```
fastapi==0.104.0
uvicorn==0.24.0
sqlalchemy==2.0.23
```

**Bad:**
```
fastapi>=0.104.0  # Unpredictable updates
uvicorn  # No version specified
```

---

## 11. SECURITY CHECKLIST

Before deploying ANY droplet:

- [ ] All endpoints validate JWT (except /health)
- [ ] All input validated with Pydantic
- [ ] All database queries parameterized
- [ ] No secrets in code or git
- [ ] All external requests use HTTPS
- [ ] All external requests have timeouts
- [ ] Security headers included
- [ ] Error messages don't leak information
- [ ] Rate limiting implemented
- [ ] Security events logged
- [ ] Dependencies scanned for vulnerabilities
- [ ] .gitignore includes .env, *.key, *.pem

---

## 12. SECURITY TESTING

### 12.1 Required Tests

```python
# Test authentication
def test_protected_endpoint_without_auth():
    response = client.get("/protected")
    assert response.status_code == 401

def test_protected_endpoint_with_invalid_token():
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

# Test input validation
def test_sql_injection_attempt():
    response = client.post(
        "/user",
        json={"name": "'; DROP TABLE users; --"}
    )
    assert response.status_code in [400, 422]  # Validation error

# Test rate limiting
def test_rate_limiting():
    for i in range(15):
        response = client.get("/api/resource")
    assert response.status_code == 429  # Too many requests
```

---

## 13. INCIDENT RESPONSE

**If you discover a security vulnerability:**

1. **Don't panic**
2. **Don't disclose publicly**
3. **Document the issue** (what, where, impact)
4. **Notify the architect immediately**
5. **Fix ASAP** (security patches skip normal review)
6. **Update this document** if it reveals a gap

---

**Security is everyone's responsibility.**

**When in doubt, ask. Don't guess about security.**

🔒⚡💎
