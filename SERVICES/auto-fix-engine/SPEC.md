# auto-fix-engine - SPECS

**Created:** 2025-11-15
**Status:** Production (Droplet #23)
**Port:** 8300

---

## Purpose

Automates Sacred Loop Step 5.5 by automatically fixing issues found by the Verifier. Analyzes verification reports, generates fixes using Claude API, applies them safely with backup/restore, and re-verifies until the service is APPROVED. Closes the Sacred Loop enabling true end-to-end autonomy.

---

## Requirements

### Functional Requirements
- [ ] Accept verification job ID and service path for auto-fixing
- [ ] Fetch verification reports from Verifier service
- [ ] Analyze issues and categorize by severity (critical, important, minor)
- [ ] Use Claude API to generate context-aware fixes for issues
- [ ] Backup files before modification
- [ ] Apply fixes (code changes, dependency updates, commands)
- [ ] Restore from backup if application fails
- [ ] Re-verify with Verifier after each fix iteration
- [ ] Iterate up to max attempts (default 3) until APPROVED
- [ ] Track all iterations with detailed logs
- [ ] Support fix types: startup failures, test failures, code quality
- [ ] Return final status (APPROVED, FIXES_REQUIRED, max iterations reached)

### Non-Functional Requirements
- [ ] Performance: Fix generation < 30 seconds, full iteration < 3 minutes
- [ ] Safety: Always backup before changes, automatic rollback on failure
- [ ] Reliability: Graceful handling of Claude API failures with retries
- [ ] Iterative: Max 3 iterations to prevent infinite loops
- [ ] Logging: Complete audit trail of all fixes attempted

---

## API Specs

### Endpoints

**POST /fix**
- **Purpose:** Submit service for auto-fixing
- **Input:** JSON with droplet_path, droplet_name, verification_job_id, max_iterations
- **Output:** fix_job_id, status, created_at
- **Success:** 201 Created
- **Errors:** 400 if invalid input, 500 if job creation fails

**GET /fix/{job_id}**
- **Purpose:** Get status and details of fix job
- **Input:** job_id
- **Output:** Fix job status, iterations, current progress, final decision
- **Success:** 200 OK
- **Errors:** 404 if job not found

**GET /fix/{job_id}/iterations**
- **Purpose:** Get detailed log of all fix iterations
- **Input:** job_id
- **Output:** Array of iteration details (issues found, fixes applied, results)
- **Success:** 200 OK
- **Errors:** 404 if job not found

**POST /fix/{job_id}/cancel**
- **Purpose:** Cancel an in-progress fix job
- **Input:** job_id
- **Output:** Confirmation of cancellation
- **Success:** 200 OK
- **Errors:** 404 if job not found, 409 if already completed

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "service": "auto-fix-engine", "claude_api": "connected"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

**GET /capabilities**
- **Purpose:** UDC capabilities endpoint
- **Input:** None
- **Output:** Supported fix types, max iterations, Claude model info
- **Success:** 200 OK
- **Errors:** 500 if unavailable

### Data Models

```python
class FixRequest:
    droplet_path: str
    droplet_name: str
    verification_job_id: str
    max_iterations: int = 3

class Issue:
    issue_id: str
    severity: str  # "critical", "important", "minor"
    category: str  # "startup_failure", "test_failure", "code_quality"
    description: str
    location: Optional[str]  # File path
    details: dict

class Fix:
    fix_id: str
    issue_id: str
    fix_type: str  # "code_change", "dependency_update", "command"
    file_path: Optional[str]
    old_content: Optional[str]
    new_content: Optional[str]
    command: Optional[str]
    reasoning: str

class FixIteration:
    iteration_number: int
    verification_job_id: str
    issues_found: List[Issue]
    fixes_generated: List[Fix]
    fixes_applied: List[Fix]
    fixes_failed: List[Fix]
    new_verification_job_id: str
    verification_decision: str
    duration_seconds: int
    timestamp: datetime

class FixJobStatus:
    fix_job_id: str
    droplet_name: str
    droplet_path: str
    status: str  # "pending", "running", "completed", "failed", "cancelled"
    current_iteration: int
    max_iterations: int
    iterations: List[FixIteration]
    final_decision: Optional[str]  # "APPROVED", "FIXES_REQUIRED", "FAILED"
    total_fixes_applied: int
    started_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str]
```

---

## Dependencies

### External Services
- Verifier (Port 8200): Fetches verification reports, submits re-verification
- Claude API (Anthropic): Generates intelligent fixes based on context

### APIs Required
- Anthropic Claude API: For fix generation
- Verifier API: GET /verify/{job_id}, POST /verify

### Data Sources
- Verification reports from Verifier
- Service source code files
- requirements.txt for dependency management

---

## Success Criteria

How do we know this service works?

- [ ] Successfully fetches verification reports from Verifier
- [ ] Claude API generates fixes for common issue types
- [ ] Backup/restore mechanism works correctly
- [ ] Fixes are applied without breaking service
- [ ] Re-verification is triggered automatically
- [ ] Iterates until APPROVED or max iterations reached
- [ ] All iterations logged with full details
- [ ] Health check returns 200 OK
- [ ] Handles Claude API failures gracefully
- [ ] At least 80% of auto-fixable issues resolved successfully

---

## Fix Types Supported

### 1. Startup Failures (Critical)
- Missing dependencies in requirements.txt
- Import errors (wrong module names, missing packages)
- Syntax errors in Python code
- Async/await issues
- Port conflicts

### 2. Test Failures (Important)
- Broken test cases
- Missing test dependencies
- Incorrect assertions
- Test timeout issues

### 3. Code Quality (Minor)
- Print statements (replace with logging)
- Bare except clauses (add exception types)
- TODO/FIXME comments
- Deprecated function usage
- Anti-patterns

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8300
- **Resource limits:**
  - Memory: 512MB max
  - CPU: 1 core
  - Storage: 1GB for backups and logs
- **Response time:** < 3 minutes per iteration, < 10 minutes total
- **Claude API:** Uses claude-3-sonnet-20240229, max 8000 tokens per request
- **Max iterations:** 3 (configurable, prevents infinite loops)
- **Timeout:** 10 minutes per fix job
- **Backup retention:** 24 hours

---

## Integration with Sacred Loop

### Before Auto-Fix Engine
```
Build → Verify → ❌ FIXES_REQUIRED → Manual debugging → Manual fixes → Manual re-verify
```
Time: 30-60 minutes of manual work

### After Auto-Fix Engine
```
Build → Verify → ❌ FIXES_REQUIRED → Auto-Fix (automated) → Re-verify → ✅ APPROVED
```
Time: 3-5 minutes, fully autonomous

### Flow
1. Verifier returns FIXES_REQUIRED with verification_job_id
2. Auto-Fix Engine fetches report and analyzes issues
3. Claude generates fixes for each issue
4. Fixes applied with backup
5. Verifier re-runs verification
6. If APPROVED: Success
7. If still issues: Iterate (max 3 times)
8. Return final decision

---

## Error Handling

- Claude API timeout: Retry up to 3 times with exponential backoff
- File write failure: Restore from backup, log error, continue to next fix
- NGINX test failure: Automatic rollback to backup config
- Verifier unavailable: Pause job, retry when available
- Max iterations reached: Return status with partial fixes applied

---

**Next Step:** Integrate with Deployer for complete autonomous Sacred Loop
