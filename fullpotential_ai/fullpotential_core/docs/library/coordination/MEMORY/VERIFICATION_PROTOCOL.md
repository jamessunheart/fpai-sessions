# Verification Protocol

**Quality checkpoints for all services - What senior devs check**

---

## Overview

Before any service goes to production, it must pass verification.

**Verification ensures:**
- Technical quality (code works correctly)
- Security standards (no vulnerabilities)
- Integration readiness (plays well with others)
- Documentation completeness (others can maintain it)

**Who verifies:** Any session can verify. Self-verification is encouraged.

---

## Verification Levels

### Level 1: Basic Functionality ⭐
**Time:** 10 minutes
**Goal:** Service works at all

**Checklist:**
- [ ] Service starts without errors
- [ ] /health endpoint returns 200
- [ ] Core endpoints return expected responses
- [ ] No crashes on basic inputs

**Test:**
```bash
# Start service
python3 src/main.py &
sleep 3

# Test health
curl http://localhost:8XXX/health

# Test core endpoint
curl http://localhost:8XXX/api/resource

# Kill service
pkill -f "python3 src/main.py"
```

**Status:** ✅ **PASS** if service responds correctly

---

### Level 2: UDC Compliance ⭐⭐
**Time:** 15 minutes
**Goal:** Service follows ecosystem standards

**Checklist:**
- [ ] All 6 UDC endpoints implemented
  - [ ] /health (returns status, service, version, timestamp)
  - [ ] /capabilities (returns version, features, dependencies, udc_version)
  - [ ] /state (returns uptime, requests, metrics)
  - [ ] /dependencies (returns required, optional, missing)
  - [ ] /message (receives messages)
  - [ ] /send (sends messages)
- [ ] Registered in SERVICE_REGISTRY.json
- [ ] Can discover other services via registry

**Test:**
```bash
cd /Users/jamessunheart/Development/SERVICES
python3 integrated-registry-system.py
```

**Look for:**
```
Service: my-service
  UDC Compliant: ✅ YES
  Missing Endpoints: []
```

**Status:** ✅ **PASS** if all 6 endpoints present and working

---

### Level 3: Test Coverage ⭐⭐⭐
**Time:** 20 minutes
**Goal:** Code is thoroughly tested

**Checklist:**
- [ ] Tests exist (tests/ directory)
- [ ] Tests pass (pytest exits 0)
- [ ] >80% code coverage
- [ ] Edge cases covered
- [ ] Error cases covered

**Test:**
```bash
cd BUILD
pytest tests/ -v --cov=src --cov-report=term-missing
```

**Look for:**
```
---------- coverage: platform darwin, python 3.x -----------
Name                Stmts   Miss  Cover   Missing
-------------------------------------------------
src/main.py           45      5    89%   12-14, 67
src/services.py       30      2    93%   45, 78
-------------------------------------------------
TOTAL                 75      7    91%
```

**Required:** >80% coverage

**Status:** ✅ **PASS** if coverage >80% and tests pass

---

### Level 4: Code Quality ⭐⭐⭐⭐
**Time:** 30 minutes
**Goal:** Code is maintainable

**Checklist:**
- [ ] Follows CODE_STANDARDS.md
  - [ ] Type hints on all functions
  - [ ] Docstrings on all public functions
  - [ ] Proper error handling
  - [ ] No code smells (long functions, deep nesting)
- [ ] No security vulnerabilities
- [ ] Dependencies are up to date
- [ ] No hardcoded secrets

**Test:**
```bash
# Check dependencies for vulnerabilities
pip install safety
safety check

# Lint code
pip install pylint
pylint src/

# Check formatting
pip install black
black --check src/
```

**Manual Review:**
```python
# ✅ GOOD
async def get_user(user_id: int) -> Optional[User]:
    """Get user by ID.

    Args:
        user_id: User's unique identifier

    Returns:
        User object if found, None otherwise
    """
    try:
        return await db.get_user(user_id)
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

# ❌ BAD
def get_user(user_id):
    return db.get_user(user_id)  # No error handling, no types, no docs
```

**Status:** ✅ **PASS** if no critical issues found

---

### Level 5: Security Audit ⭐⭐⭐⭐⭐
**Time:** 45 minutes
**Goal:** Service is secure

**Checklist:**
- [ ] All inputs validated (Pydantic models)
- [ ] No SQL injection vulnerabilities
- [ ] No command injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] HTTPS in production
- [ ] CORS configured properly
- [ ] Rate limiting implemented
- [ ] No secrets in code/logs
- [ ] Authentication/authorization working
- [ ] Security headers configured

**Test:**
```bash
# Check for common vulnerabilities
pip install bandit
bandit -r src/

# Check for exposed secrets
pip install detect-secrets
detect-secrets scan
```

**Manual Review:**
```python
# ❌ VULNERABLE
@app.get("/api/data")
async def get_data(query: str):
    # SQL injection risk!
    result = db.execute(f"SELECT * FROM users WHERE name = '{query}'")
    return result

# ✅ SECURE
@app.get("/api/data")
async def get_data(query: str):
    # Parameterized query - safe
    result = await db.execute("SELECT * FROM users WHERE name = %s", (query,))
    return result
```

**See:** `MEMORY/SECURITY_REQUIREMENTS.md` for full checklist

**Status:** ✅ **PASS** if no security issues found

---

### Level 6: Production Readiness ⭐⭐⭐⭐⭐⭐
**Time:** 1 hour
**Goal:** Service is ready for real users

**Checklist:**
- [ ] All previous levels passed
- [ ] Documentation complete
  - [ ] SPECS.md (technical specification)
  - [ ] README.md (usage guide)
  - [ ] API docs (auto-generated or manual)
- [ ] Deployment tested
  - [ ] Dockerfile works (if using Docker)
  - [ ] Deploy script works
  - [ ] Service starts on server
- [ ] Monitoring configured
  - [ ] Health checks working
  - [ ] Logging to proper location
  - [ ] Metrics exposed
- [ ] Integration tested
  - [ ] Can communicate with other services
  - [ ] Handles service failures gracefully
- [ ] Performance acceptable
  - [ ] Response times <500ms
  - [ ] Can handle expected load
  - [ ] No memory leaks
- [ ] Rollback plan exists

**Load Test:**
```bash
# Install Apache Bench
apt install apache2-utils

# Test performance
ab -n 1000 -c 10 http://localhost:8XXX/api/endpoint

# Look for:
# - Time per request <500ms
# - No failed requests
# - Consistent response times
```

**Deployment Test:**
```bash
# Deploy to staging first
./deploy.sh staging

# Verify deployment
curl http://staging.fullpotential.com/my-service/health

# Test functionality
curl http://staging.fullpotential.com/my-service/api/test

# Check logs
ssh root@staging 'journalctl -u my-service -n 50'

# If all good, deploy to production
./deploy.sh production
```

**Status:** ✅ **PASS** if service is production-ready

---

## Verification Workflow

### Self-Verification (Recommended)
```bash
# 1. Run all tests
pytest tests/ -v --cov=src --cov-report=html

# 2. Check UDC compliance
cd /Users/jamessunheart/Development/SERVICES
python3 integrated-registry-system.py

# 3. Run security checks
cd my-service
bandit -r src/
safety check

# 4. Test deployment
./deploy.sh staging

# 5. Update README with verification status
echo "✅ Verified: All checks passed" >> README.md
```

### Peer Review (Optional but recommended)
```bash
# Request review from another session
./docs/coordination/scripts/session-send-message.sh "broadcast" \
    "Code Review Request" \
    "Session #5: Completed email service. Requesting peer review before production." \
    "normal"

# Other session reviews:
# - Code quality
# - Test coverage
# - Security
# - Documentation
```

---

## Common Issues and Fixes

### Issue: "Tests failing"
**Fix:**
```bash
# Run with verbose output to see exact failure
pytest tests/ -v -s

# Fix failing tests
# Re-run until all pass
```

### Issue: "Coverage too low"
**Fix:**
```bash
# Identify uncovered lines
pytest tests/ --cov=src --cov-report=term-missing

# Write tests for uncovered lines
# Re-run until coverage >80%
```

### Issue: "Security vulnerability found"
**Fix:**
```bash
# Update vulnerable dependency
pip install --upgrade vulnerable-package

# Re-run security checks
bandit -r src/
safety check
```

### Issue: "Service won't deploy"
**Fix:**
```bash
# Check deployment logs
ssh root@198.54.123.234 'journalctl -u my-service -n 50'

# Common issues:
# - Missing dependencies (update requirements.txt)
# - Port conflict (change port)
# - Permission issues (check file permissions)
```

---

## Verification Badges

**Add to README.md:**
```markdown
## Verification Status

- ✅ Level 1: Basic Functionality (PASS)
- ✅ Level 2: UDC Compliance (PASS)
- ✅ Level 3: Test Coverage (91% coverage)
- ✅ Level 4: Code Quality (PASS)
- ✅ Level 5: Security Audit (PASS)
- ✅ Level 6: Production Ready (PASS)

**Verified By:** Session #5
**Date:** 2025-11-15
**Version:** 1.0.0
```

---

## Automated Verification

**Create verification script:**
```bash
#!/bin/bash
# verify.sh - Automated verification

set -e

echo "🔍 Running verification checks..."

echo "✓ Level 1: Testing basic functionality..."
python3 src/main.py &
PID=$!
sleep 3
curl -sf http://localhost:8XXX/health > /dev/null || { echo "❌ Health check failed"; exit 1; }
kill $PID

echo "✓ Level 2: Checking UDC compliance..."
cd /Users/jamessunheart/Development/SERVICES
python3 integrated-registry-system.py | grep -q "UDC Compliant: ✅" || { echo "❌ UDC check failed"; exit 1; }

echo "✓ Level 3: Running tests..."
cd BUILD
pytest tests/ -v --cov=src --cov-report=term | grep -q "PASSED" || { echo "❌ Tests failed"; exit 1; }

echo "✓ Level 4: Checking code quality..."
pylint src/ || echo "⚠️  Some linting issues (non-blocking)"

echo "✓ Level 5: Running security checks..."
safety check || { echo "❌ Security vulnerabilities found"; exit 1; }
bandit -r src/ -ll || { echo "❌ Security issues found"; exit 1; }

echo "✅ All verification checks passed!"
```

---

## Quality Gates

**Minimum standards for production:**

| Level | Required | Blocking |
|-------|----------|----------|
| Level 1: Basic Functionality | YES | YES |
| Level 2: UDC Compliance | YES | YES |
| Level 3: Test Coverage | YES | YES |
| Level 4: Code Quality | YES | NO (warnings OK) |
| Level 5: Security Audit | YES | YES |
| Level 6: Production Ready | YES | YES |

**Meaning:**
- **Required + Blocking:** Must pass to deploy
- **Required + Non-blocking:** Should pass, but warnings acceptable
- **Not required:** Nice to have

---

**Verify rigorously → Deploy confidently → Scale successfully**
