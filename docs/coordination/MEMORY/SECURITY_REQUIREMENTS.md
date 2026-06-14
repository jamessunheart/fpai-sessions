# Security Requirements

**Security standards for all Full Potential AI services**

---

## Core Principles

1. **Defense in Depth** - Multiple layers of security
2. **Least Privilege** - Minimum necessary permissions
3. **Fail Secure** - Fail closed, not open
4. **Security by Default** - Secure out of the box
5. **Never Trust Input** - Validate everything

---

## Authentication & Authorization

### API Keys
- **NEVER hardcode** API keys in code
- **ALWAYS use** environment variables or credential vault
- **ROTATE** keys regularly (every 90 days)
- **REVOKE** immediately if compromised

### Credential Vault
```bash
# Get credentials from vault (NEVER ask user first!)
export API_KEY=$(./scripts/session-get-credential.sh anthropic_api_key)
```

**Available credentials:**
- anthropic_api_key
- openai_api_key
- server_admin_password
- stripe_api_key
- +more

### Password Requirements
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- No common passwords
- Hashed with bcrypt (cost factor 12+)
- Never stored in plain text

---

## Input Validation

### Always Validate
- **All user inputs** - forms, APIs, URLs
- **All file uploads** - size, type, content
- **All external data** - APIs, databases, files

### Use Pydantic Models
```python
from pydantic import BaseModel, EmailStr, validator

class UserInput(BaseModel):
    email: EmailStr
    age: int

    @validator('age')
    def age_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Age must be positive')
        return v
```

### Prevent Injection Attacks
- **SQL Injection**: Use parameterized queries
- **Command Injection**: Never pass user input to shell commands
- **XSS**: Escape all user-generated content
- **Path Traversal**: Validate file paths

---

## Data Protection

### Encryption
- **In Transit**: HTTPS/TLS 1.3 for all network communication
- **At Rest**: Encrypt sensitive data in database
- **API Keys**: Store in encrypted credential vault

### Sensitive Data
**NEVER log:**
- Passwords
- API keys
- Credit card numbers
- Personal identifying information (PII)

**Example:**
```python
# ❌ WRONG
logger.info(f"User logged in: {email} with password {password}")

# ✅ CORRECT
logger.info(f"User logged in: {email}")
```

### Data Retention
- Keep only what's necessary
- Delete when no longer needed
- Comply with privacy regulations (GDPR, CCPA)

---

## Network Security

### HTTPS Only
- Production MUST use HTTPS
- Redirect HTTP → HTTPS
- Use valid SSL certificates

### CORS
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fullpotential.com"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Rate Limiting
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/data")
@limiter.limit("10/minute")
async def get_data():
    return {"data": "value"}
```

---

## Server Security

### SSH Access
- **Key-based authentication only** (no passwords)
- **Disable root login** (use sudo)
- **Change default ports** if possible
- **Fail2ban** to prevent brute force

### Firewall
- Only open necessary ports
- Whitelist known IP addresses
- Block all other traffic

### Updates
- Keep system packages updated
- Apply security patches promptly
- Monitor security advisories

---

## Application Security

### Error Handling
```python
# ❌ WRONG - Exposes internal details
@app.get("/data")
async def get_data():
    return {"result": database.query("SELECT * FROM users")}

# ✅ CORRECT - Generic error messages
@app.get("/data")
async def get_data():
    try:
        result = database.query("SELECT * FROM users")
        return {"result": result}
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Dependency Security
```bash
# Check for vulnerabilities
pip install safety
safety check

# Keep dependencies updated
pip list --outdated
```

---

## Compliance Requirements

### Church Guidance Ministry
- **Educational ministry** (not legal service)
- **AI compliance support** (documentation aid, not legal advice)
- **Clear liability boundaries** in all user-facing content
- **Privacy policy** for user data
- **Terms of service** with disclaimers

### Payment Processing
- **PCI DSS compliance** when handling credit cards
- **Use Stripe** for payment processing (don't handle card data directly)
- **Secure webhooks** with signature verification

---

## Security Checklist

**Before deploying ANY service:**

- [ ] All secrets in environment variables or vault
- [ ] Input validation on all endpoints
- [ ] HTTPS enabled in production
- [ ] CORS configured properly
- [ ] Rate limiting implemented
- [ ] Error messages don't expose internals
- [ ] No sensitive data in logs
- [ ] Dependencies checked for vulnerabilities
- [ ] Authentication/authorization working
- [ ] Security headers configured

---

## Security Headers

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# Force HTTPS
app.add_middleware(HTTPSRedirectMiddleware)

# Trusted hosts only
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["fullpotential.com", "*.fullpotential.com"]
)

# Security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

## Incident Response

**If security breach occurs:**

1. **Contain** - Isolate affected systems
2. **Investigate** - Determine scope and impact
3. **Remediate** - Fix vulnerability
4. **Notify** - Inform affected users if PII exposed
5. **Learn** - Document and improve processes

---

## Resources

**Credential Vault:**
- URL: https://fullpotential.com/vault
- Docs: https://fullpotential.com/vault/docs
- Health: https://fullpotential.com/vault/health

**Security Tools:**
- `safety` - Python dependency vulnerability scanner
- `bandit` - Python security linter
- `semgrep` - Static analysis security scanner

---

**Security is everyone's responsibility. When in doubt, ask for review before deploying.**
