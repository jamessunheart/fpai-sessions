# SPEC: Verifier Droplet

**Version:** 1.0
**Author:** Architect (James) + Claude (Sonnet 4.5)
**Status:** Ready for Assembly
**Depends on:**
- VERIFICATION_PROTOCOL.md (the checklist to automate)
- Python 3.11+
- Target droplet codebase (to verify)

---

## 1. Intent (Purpose)

The Verifier Droplet automates the VERIFICATION_PROTOCOL.md - the human Senior Developer's 2-3 hour verification checklist.

It removes manual verification work by exposing an HTTP API that:
- Accepts a droplet codebase (path or archive)
- Runs all 6 verification phases automatically
- Generates a structured verification report
- Makes APPROVE / APPROVE_WITH_NOTES / FIXES_REQUIRED decision
- Returns actionable feedback for developers

**This turns verification into a programmable service that:**
- Coordinator can call before deployment
- CI/CD pipelines can integrate
- Developers can run locally before submission
- Reduces Senior Developer time from 2-3 hours to 5 minutes (review report)

---

## 2. Scope & Non-Scope

### In Scope

**Phase 1: Structure Scan**
- Check file/directory structure
- Verify required files exist (main.py, models.py, tests/, .env.example)
- Validate folder organization (app/, tests/ structure)

**Phase 2: UDC Compliance**
- Start the droplet in test mode
- Test required endpoints: `/health`, `/capabilities`, `/state`, `/dependencies`
- Validate response schemas match UDC spec
- Verify status enum values are correct

**Phase 3: Security Checks**
- Scan for hardcoded secrets (patterns: password=, api_key=, sk-)
- Verify environment variable usage (pydantic-settings)
- Check input validation (Pydantic models)
- Detect SQL injection patterns (if database code present)
- Verify JWT authentication implementation (if applicable)

**Phase 4: Functionality**
- Run pytest test suite
- Calculate coverage
- Parse test results
- Identify failing tests

**Phase 5: Code Quality**
- Check for anti-patterns (print statements, bare except, requests library)
- Detect TODO/FIXME in production code
- Check for type hints
- Check for synchronous I/O in async code

**Phase 6: Decision & Report**
- Aggregate all findings
- Apply decision logic (critical issues → FIXES_REQUIRED)
- Generate structured verification report
- Return actionable feedback

**API Features:**
- `POST /verify` - Submit droplet for verification
- `GET /verify/{job_id}` - Get verification status/results
- `GET /verify/{job_id}/report` - Get detailed report
- `GET /health` - UDC health endpoint

### Out of Scope (v1)

- Actually fixing code (just reports issues)
- Running droplets in production mode (test mode only)
- Multi-language support (Python only for v1)
- Integration with GitHub (just local/uploaded code)
- Rewriting code (just verification)
- Teaching mode (just pass/fail + notes)

---

## 3. Success Criteria

### Functional:
1. Given a valid Python droplet codebase at `/path/to/droplet`, calling `POST /verify`:
   - Runs all 6 verification phases
   - Returns job_id immediately (async processing)
   - Completes verification in <5 minutes
   - Returns structured report with APPROVE or FIXES_REQUIRED

2. Given a droplet with hardcoded secrets, verification report:
   - Marks as FIXES_REQUIRED
   - Lists exact files and line numbers
   - Provides clear explanation of issue

3. Given a droplet with all tests passing and UDC compliant:
   - Marks as APPROVED
   - Highlights strengths
   - Suggests minor improvements (if any)

### Operational:
4. Verification is reproducible:
   - Same codebase → same decision
   - Deterministic results

5. All operations logged:
   - `job_id`, `droplet_name`, `phase`, `result`, `duration`

6. Verifier health endpoint:
   - Returns healthy if can run verifications
   - Returns degraded if slow or issues

---

## 4. API Design

**Base path:** `http://<verifier-host>:<port>/`

All responses JSON, UDC-style errors.

### 4.1 Routes

#### 4.1.1 Submit Verification Job
`POST /verify`

**Request Body:**
```json
{
  "droplet_path": "/path/to/droplet",
  "droplet_name": "proxy-manager",
  "quick_mode": false
}
```

**Or upload archive:**
```bash
curl -X POST http://localhost:8200/verify \
  -F "file=@droplet.tar.gz" \
  -F "droplet_name=proxy-manager"
```

**Response (202 Accepted):**
```json
{
  "job_id": "ver-1234-abcd",
  "status": "queued",
  "droplet_name": "proxy-manager",
  "created_at": "2024-11-14T00:00:00Z",
  "estimated_duration_seconds": 180
}
```

#### 4.1.2 Get Verification Status
`GET /verify/{job_id}`

**Response:**
```json
{
  "job_id": "ver-1234-abcd",
  "status": "running|completed|failed",
  "droplet_name": "proxy-manager",
  "current_phase": "Phase 3: Security",
  "progress_percent": 45,
  "started_at": "2024-11-14T00:00:00Z",
  "completed_at": null,
  "decision": null
}
```

**When completed:**
```json
{
  "job_id": "ver-1234-abcd",
  "status": "completed",
  "droplet_name": "proxy-manager",
  "decision": "APPROVED|APPROVED_WITH_NOTES|FIXES_REQUIRED",
  "summary": {
    "critical_issues": 0,
    "important_issues": 2,
    "minor_issues": 5,
    "tests_passing": "20/20",
    "coverage_percent": 58
  },
  "completed_at": "2024-11-14T00:03:00Z",
  "duration_seconds": 180
}
```

#### 4.1.3 Get Detailed Report
`GET /verify/{job_id}/report`

**Response:**
```json
{
  "job_id": "ver-1234-abcd",
  "droplet_name": "proxy-manager",
  "decision": "APPROVED_WITH_NOTES",
  "phases": [
    {
      "phase": "Structure Scan",
      "status": "PASS",
      "duration_seconds": 5,
      "checks": [
        {"name": "Required files present", "status": "PASS"},
        {"name": "Directory structure correct", "status": "PASS"}
      ]
    },
    {
      "phase": "UDC Compliance",
      "status": "PASS",
      "duration_seconds": 30,
      "checks": [
        {"name": "/health endpoint", "status": "PASS", "response": {...}},
        {"name": "/capabilities endpoint", "status": "PASS"},
        {"name": "Status enum correct", "status": "PASS"}
      ]
    },
    {
      "phase": "Security",
      "status": "PASS",
      "duration_seconds": 15,
      "checks": [
        {"name": "No hardcoded secrets", "status": "PASS"},
        {"name": "Environment variables", "status": "PASS"},
        {"name": "Input validation", "status": "PASS"}
      ]
    },
    {
      "phase": "Functionality",
      "status": "PASS",
      "duration_seconds": 60,
      "checks": [
        {"name": "Tests passing", "status": "PASS", "details": "20/20 tests passed"},
        {"name": "Coverage", "status": "PASS", "details": "58% coverage"}
      ]
    },
    {
      "phase": "Code Quality",
      "status": "MINOR_ISSUES",
      "duration_seconds": 10,
      "checks": [
        {"name": "No print statements", "status": "PASS"},
        {"name": "Async patterns", "status": "MINOR_ISSUE", "details": "Some datetime.utcnow() deprecation warnings"}
      ]
    }
  ],
  "critical_issues": [],
  "important_issues": [],
  "minor_issues": [
    {
      "severity": "minor",
      "category": "deprecation",
      "file": "app/main.py",
      "line": 122,
      "message": "Using deprecated datetime.utcnow()",
      "suggestion": "Use datetime.now(datetime.UTC) instead"
    }
  ],
  "strengths": [
    "All 20 tests passing",
    "Good test coverage (58%)",
    "Clean UDC compliance",
    "No security issues found"
  ],
  "recommendations": [
    "Fix deprecation warnings for Python 3.13+ compatibility",
    "Consider adding more edge case tests"
  ]
}
```

#### 4.1.4 List Recent Verifications
`GET /verify/recent?limit=10`

**Response:**
```json
{
  "verifications": [
    {
      "job_id": "ver-1234-abcd",
      "droplet_name": "proxy-manager",
      "decision": "APPROVED",
      "completed_at": "2024-11-14T00:00:00Z"
    }
  ]
}
```

#### 4.1.5 Health
`GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "verifier",
  "version": "1.0.0",
  "checks": {
    "can_run_pytest": true,
    "can_scan_files": true,
    "queue_size": 0
  }
}
```

---

## 5. Data & Configuration

### 5.1 Environment Variables
- `VERIFIER_PORT` (default 8200)
- `WORK_DIR` (default `/tmp/verifier-jobs`)
- `MAX_CONCURRENT_JOBS` (default 3)
- `JOB_TIMEOUT_SECONDS` (default 600 - 10 minutes)
- `QUICK_MODE_ENABLED` (default true - skip some checks for speed)

### 5.2 Internal Models

**VerificationJob**
- `job_id`: str
- `droplet_name`: str
- `droplet_path`: str
- `status`: Enum[queued, running, completed, failed]
- `decision`: Optional[Enum[APPROVED, APPROVED_WITH_NOTES, FIXES_REQUIRED]]
- `current_phase`: Optional[str]
- `started_at`: datetime
- `completed_at`: Optional[datetime]

**VerificationPhase**
- `phase_name`: str
- `status`: Enum[PASS, FAIL, MINOR_ISSUES]
- `checks`: List[Check]
- `duration_seconds`: int

**Issue**
- `severity`: Enum[critical, important, minor]
- `category`: str (e.g., "security", "udc", "quality")
- `file`: Optional[str]
- `line`: Optional[int]
- `message`: str
- `suggestion`: Optional[str]

---

## 6. Non-Functional Requirements

- **Language:** Python 3.11
- **Framework:** FastAPI
- **Performance:**
  - Standard verification: <5 minutes
  - Quick mode: <2 minutes
  - Can handle 3 concurrent jobs
- **Security:**
  - Sandboxed execution (jobs in isolated directories)
  - No execution of arbitrary droplet code in main process
  - Subprocess timeout protection
- **Resilience:**
  - Job timeout handling
  - Graceful failure on errors
  - Jobs can be retried
- **Logging:**
  - Structured logs: `job_id`, `phase`, `action`, `result`, `duration`

---

## 7. Integration Points

### 7.1 Coordinator (Future)
Coordinator will call:
- `POST /verify` when apprentice submits code
- `GET /verify/{job_id}` to check status
- `GET /verify/{job_id}/report` to review results
- Make deployment decision based on `decision` field

### 7.2 CI/CD (Future)
GitHub Actions can call:
- `POST /verify` on pull request
- Add verification report as PR comment
- Block merge if FIXES_REQUIRED

### 7.3 Local Development
Developers can run:
```bash
curl -X POST http://localhost:8200/verify \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_path": "/path/to/my-droplet",
    "droplet_name": "my-droplet"
  }'
```

---

## 8. Testing Strategy

### 8.1 Unit Tests
- Each verification phase as separate testable function
- Mock subprocess calls (pytest, grep, etc.)
- Test decision logic with various issue combinations
- Test report generation

### 8.2 Integration Tests
- Full verification of a known-good droplet (expect APPROVED)
- Full verification of droplet with critical issues (expect FIXES_REQUIRED)
- Test job queue and status updates
- Test timeout handling

### 8.3 Manual Acceptance
- Verify the Proxy Manager we just built
- Verify a droplet with security issues
- Verify a droplet with failing tests
- Confirm reports are actionable

---

## 9. Verification Phases Implementation

### Phase 1: Structure Scan
```python
def verify_structure(droplet_path: Path) -> PhaseResult:
    checks = [
        check_file_exists("app/main.py"),
        check_file_exists("app/models.py"),
        check_file_exists("tests/"),
        check_file_exists("requirements.txt"),
        check_file_exists(".env.example"),
    ]
    # Return PASS/FAIL with details
```

### Phase 2: UDC Compliance
```python
async def verify_udc(droplet_path: Path) -> PhaseResult:
    # Start droplet in subprocess
    process = start_droplet_test_mode(droplet_path)

    # Test endpoints
    health = await test_endpoint("/health")
    capabilities = await test_endpoint("/capabilities")
    state = await test_endpoint("/state")

    # Validate schemas
    validate_health_schema(health)
    validate_status_enum(health["status"])

    # Stop droplet
    process.terminate()
```

### Phase 3: Security
```python
def verify_security(droplet_path: Path) -> PhaseResult:
    issues = []

    # Check for hardcoded secrets
    issues += scan_for_secrets(droplet_path)

    # Check environment variables
    issues += check_env_usage(droplet_path)

    # Check input validation
    issues += check_pydantic_usage(droplet_path)

    # Check SQL injection
    issues += check_sql_patterns(droplet_path)

    return PhaseResult(issues)
```

### Phase 4: Functionality
```python
def verify_functionality(droplet_path: Path) -> PhaseResult:
    # Run pytest
    result = run_pytest(droplet_path)

    # Parse results
    tests_passed = parse_test_count(result)
    coverage = parse_coverage(result)

    return PhaseResult(
        tests_passed=tests_passed,
        coverage=coverage
    )
```

### Phase 5: Code Quality
```python
def verify_code_quality(droplet_path: Path) -> PhaseResult:
    issues = []

    # Anti-patterns
    issues += grep_for_pattern("print(", "Using print statements")
    issues += grep_for_pattern("except:", "Bare except clause")
    issues += grep_for_pattern("TODO|FIXME", "TODO in production")

    return PhaseResult(issues)
```

### Phase 6: Decision Logic
```python
def make_decision(all_phases: List[PhaseResult]) -> Decision:
    critical = count_critical_issues(all_phases)
    important = count_important_issues(all_phases)

    if critical > 0:
        return Decision.FIXES_REQUIRED
    elif important > 2:
        return Decision.FIXES_REQUIRED
    elif has_minor_issues(all_phases):
        return Decision.APPROVED_WITH_NOTES
    else:
        return Decision.APPROVED
```

---

## 10. Deliverables

**Repo:** `~/Development/verifier/`

**Files:**
- `app/main.py` - FastAPI app, routes
- `app/models.py` - Pydantic models
- `app/config.py` - Settings
- `app/phases/` - Verification phase implementations
  - `structure.py`
  - `udc.py`
  - `security.py`
  - `functionality.py`
  - `quality.py`
  - `decision.py`
- `app/job_manager.py` - Job queue and status tracking
- `app/report_generator.py` - Report formatting
- `tests/` - Unit + integration tests
- `Dockerfile` - Container for deployment
- `SPEC_Verifier_Droplet_v1.md` - This file

**CI:**
- pytest green
- Can verify itself (meta!)

---

## 11. Example Usage Flow

```bash
# 1. Submit verification
curl -X POST http://localhost:8200/verify \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_path": "/Users/james/Development/proxy-manager",
    "droplet_name": "proxy-manager"
  }'

# Response: {"job_id": "ver-1234", "status": "queued"}

# 2. Check status
curl http://localhost:8200/verify/ver-1234

# Response: {"status": "running", "current_phase": "Phase 2: UDC Compliance", "progress_percent": 40}

# 3. Wait for completion...

# 4. Get report
curl http://localhost:8200/verify/ver-1234/report

# Response: Full verification report with decision
```

---

## 12. Critical Implementation Notes

**Sandboxing:**
- Each verification job runs in isolated directory
- Droplet code never imported directly into Verifier
- All droplet execution via subprocess with timeout

**Timeouts:**
- Each phase has timeout (e.g., pytest max 2 minutes)
- Total job timeout (10 minutes default)
- Graceful failure if timeout exceeded

**Concurrency:**
- Max 3 concurrent jobs (configurable)
- Queue system for overflow
- Job status tracked in-memory (v1) or Redis (v2)

**Error Handling:**
- If phase crashes, mark as FAIL but continue
- Collect all issues before making decision
- Never crash Verifier due to bad droplet code

---

**END OF SPEC**

**Next:** Build the Verifier Droplet implementation!
