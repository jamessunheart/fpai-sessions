# verifier - SPECS

**Created:** 2025-11-15
**Status:** Production Ready (Droplet #8)
**Port:** 8200

---

## Purpose

Automates VERIFICATION_PROTOCOL.md turning 2-3 hour manual verification into 3-5 minute automated process. Runs through all 6 phases: Structure Scan, UDC Compliance, Security, Functionality, Code Quality, and Decision. Provides structured reports with APPROVED/FIXES_REQUIRED decision.

---

## Requirements

### Functional Requirements
- [ ] Accept droplet path and name for verification
- [ ] Phase 1: Structure scan (required files, directory organization)
- [ ] Phase 2: UDC compliance testing (health, capabilities, state endpoints)
- [ ] Phase 3: Security scanning (hardcoded secrets, SQL injection, input validation)
- [ ] Phase 4: Functionality testing (pytest suite, coverage calculation)
- [ ] Phase 5: Code quality checks (print statements, bare excepts, TODOs)
- [ ] Phase 6: Decision making (aggregate findings, apply logic, generate report)
- [ ] Quick mode option for faster verification (skip some checks)
- [ ] Structured JSON reports with all findings
- [ ] Issue categorization by severity (critical, important, minor)
- [ ] Strengths identification
- [ ] Recommendations generation
- [ ] Job queue for multiple concurrent verifications

### Non-Functional Requirements
- [ ] Performance: Full verification < 3 minutes, quick mode < 1 minute
- [ ] Reliability: Graceful failure handling, cleanup after verification
- [ ] Isolation: Each verification in separate process
- [ ] Timeout: Max 10 minutes per verification job
- [ ] Logging: Complete verification audit trail

---

## API Specs

### Endpoints

**POST /verify**
- **Purpose:** Submit droplet for verification
- **Input:** droplet_path, droplet_name, quick_mode (optional)
- **Output:** job_id, status, estimated_duration_seconds
- **Success:** 202 Accepted
- **Errors:** 400 if invalid input, 500 if job creation fails

**GET /verify/{job_id}**
- **Purpose:** Get verification job status
- **Input:** job_id
- **Output:** Job status, current_phase, progress_percent
- **Success:** 200 OK
- **Errors:** 404 if job not found

**GET /verify/{job_id}/report**
- **Purpose:** Get full verification report
- **Input:** job_id
- **Output:** Complete report with decision, phases, issues, recommendations
- **Success:** 200 OK
- **Errors:** 404 if job not found, 409 if not completed

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "service": "verifier", "can_run_pytest": true}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

**GET /capabilities**
- **Purpose:** UDC capabilities endpoint
- **Input:** None
- **Output:** Verification phases, supported file types, features
- **Success:** 200 OK
- **Errors:** 500 if unavailable

### Data Models

```python
class VerificationRequest:
    droplet_path: str
    droplet_name: str
    quick_mode: bool = False

class VerificationJob:
    job_id: str
    droplet_name: str
    droplet_path: str
    status: str  # "queued", "running", "completed", "failed"
    current_phase: str
    progress_percent: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    quick_mode: bool

class VerificationPhase:
    phase_name: str
    status: str  # "pending", "running", "completed", "failed", "skipped"
    duration_seconds: Optional[int]
    findings: List[Finding]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class Finding:
    severity: str  # "critical", "important", "minor"
    category: str  # Specific to each phase
    description: str
    location: Optional[str]  # File path or line number
    suggestion: Optional[str]

class VerificationReport:
    job_id: str
    droplet_name: str
    decision: str  # "APPROVED", "APPROVED_WITH_NOTES", "FIXES_REQUIRED"
    phases: List[VerificationPhase]
    critical_issues: List[Finding]
    important_issues: List[Finding]
    minor_issues: List[Finding]
    strengths: List[str]
    recommendations: List[str]
    summary: dict
    completed_at: datetime
    duration_seconds: int
```

---

## Dependencies

### External Services
- None (standalone)

### Tools Required
- pytest: Test execution
- Python 3.11+: Target environment
- uvicorn: For starting services in test mode

### Data Sources
- Service source code
- Test suite
- Configuration files

---

## Success Criteria

How do we know this works?

- [ ] All 6 phases execute correctly
- [ ] Structure scan identifies missing files
- [ ] UDC compliance tests all required endpoints
- [ ] Security scan catches hardcoded secrets
- [ ] Tests run and coverage calculated
- [ ] Code quality issues detected
- [ ] Decision logic applied correctly
- [ ] Reports generated with all findings
- [ ] Verification completes in < 3 minutes
- [ ] At least 1 service verified with APPROVED decision

---

## Verification Phases

### Phase 1: Structure Scan (1 second)
**Checks:**
- Required files exist (main.py, models.py, tests/)
- Directory structure correct
- Optional files present (Dockerfile, README, requirements.txt)

**Findings:**
- Missing required files (critical)
- Missing optional files (minor)

### Phase 2: UDC Compliance (30 seconds)
**Checks:**
- Start service in test mode
- Test /health endpoint (required)
- Test /capabilities endpoint (optional)
- Test /state endpoint (optional)
- Validate response schemas
- Check status enum values

**Findings:**
- Missing /health endpoint (critical)
- Invalid response format (important)
- Missing optional endpoints (minor)

### Phase 3: Security (15 seconds)
**Checks:**
- Scan for hardcoded secrets (API keys, passwords)
- Verify environment variable usage
- Check input validation (Pydantic models)
- Detect SQL injection patterns
- Check for insecure dependencies

**Findings:**
- Hardcoded secrets (critical)
- Missing input validation (important)
- Insecure patterns (important)

### Phase 4: Functionality (60 seconds)
**Checks:**
- Run pytest test suite
- Calculate test coverage
- Parse pass/fail counts
- Identify failing tests

**Findings:**
- Tests failing (critical if >20%)
- Low coverage (important if <50%)
- No tests present (critical)

### Phase 5: Code Quality (10 seconds)
**Checks:**
- Print statements (should use logging)
- Bare except clauses
- TODO/FIXME comments
- Synchronous I/O in async code
- Deprecated function usage

**Findings:**
- Print statements (minor)
- Bare excepts (important)
- TODOs (minor)

### Phase 6: Decision (5 seconds)
**Logic:**
- Aggregate all findings
- Apply decision rules
- Identify strengths
- Generate recommendations

**Decision Rules:**
- FIXES_REQUIRED if: Any critical issues, UDC fails, security vulnerabilities, >2 important issues, tests <80% passing
- APPROVED_WITH_NOTES if: All critical pass, minor issues present
- APPROVED if: All checks pass, no issues

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8200
- **Resource limits:**
  - Memory: 512MB max
  - CPU: 1 core
  - Storage: 1GB for work directory
- **Response time:** Full verification < 3 minutes, quick mode < 1 minute
- **Concurrency:** Max 3 concurrent jobs
- **Timeout:** 10 minutes per job
- **Cleanup:** Delete work directory after completion

---

## Integration

### With Auto-Fix Engine
Verifier provides job_id to Auto-Fix Engine:
```python
# Auto-Fix fetches report
report = httpx.get(f"http://verifier:8200/verify/{job_id}/report")

# Analyzes issues and generates fixes
for issue in report["critical_issues"]:
    fix = await generate_fix(issue)
    apply_fix(fix)

# Re-verify
new_job = httpx.post("http://verifier:8200/verify", json={...})
```

### With Deployer
Deployer checks verification before deployment:
```python
# Submit for verification
verify_response = httpx.post("http://verifier:8200/verify", json={...})
job_id = verify_response.json()["job_id"]

# Wait for completion
while True:
    status = httpx.get(f"http://verifier:8200/verify/{job_id}")
    if status.json()["status"] == "completed":
        break

# Check decision
report = httpx.get(f"http://verifier:8200/verify/{job_id}/report")
if report.json()["decision"] == "APPROVED":
    deploy(service)
```

---

## Quick Mode

**Skips:**
- Optional UDC endpoints
- Code quality checks (except critical)
- Coverage calculation
- Some security scans

**Use when:**
- Rapid iteration during development
- Pre-verification before full check
- Time-sensitive deployments

**Duration:** < 1 minute vs 3 minutes

---

**Next Step:** Integrate with Auto-Fix Engine and Deployer for complete Sacred Loop
