# Verifier Droplet

**Version:** 1.0.0
**Status:** Production Ready
**Port:** 8200

Automates the VERIFICATION_PROTOCOL.md - turning a 2-3 hour manual verification into a 3-5 minute automated process with structured reports.

## Purpose

The Verifier Droplet automates droplet verification by running through all 6 phases of the verification protocol:
1. **Structure Scan** - File organization and required files
2. **UDC Compliance** - Test all Universal Droplet Contract endpoints
3. **Security** - Scan for hardcoded secrets, SQL injection, etc.
4. **Functionality** - Run pytest suite and check coverage
5. **Code Quality** - Check for anti-patterns and best practices
6. **Decision** - Make APPROVED/FIXES_REQUIRED decision

## Quick Start

### Prerequisites

- Python 3.11+
- Target droplet codebase to verify

### Installation

```bash
# Clone or navigate to verifier
cd ~/Development/verifier

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running

```bash
# Development
uvicorn app.main:app --reload --port 8200

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8200
```

## API Endpoints

### Submit Verification

```bash
POST /verify
```

**Request:**
```json
{
  "droplet_path": "/Users/james/Development/proxy-manager",
  "droplet_name": "proxy-manager",
  "quick_mode": false
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "ver-abc123",
  "status": "queued",
  "droplet_name": "proxy-manager",
  "created_at": "2024-11-14T00:00:00Z",
  "estimated_duration_seconds": 180
}
```

### Get Job Status

```bash
GET /verify/{job_id}
```

**Response:**
```json
{
  "job_id": "ver-abc123",
  "status": "running",
  "droplet_name": "proxy-manager",
  "current_phase": "Phase 3: Security",
  "progress_percent": 50,
  "started_at": "2024-11-14T00:00:00Z"
}
```

### Get Full Report

```bash
GET /verify/{job_id}/report
```

**Response:**
```json
{
  "job_id": "ver-abc123",
  "droplet_name": "proxy-manager",
  "decision": "APPROVED_WITH_NOTES",
  "phases": [...],
  "critical_issues": [],
  "important_issues": [],
  "minor_issues": [...],
  "strengths": [
    "All 20 tests passing",
    "Clean UDC compliance"
  ],
  "recommendations": [
    "Fix deprecation warnings"
  ],
  "summary": {
    "critical_issues": 0,
    "important_issues": 0,
    "minor_issues": 5,
    "tests_passing": "20/20 tests passed (100%)",
    "coverage_percent": 58
  }
}
```

### Health Check

```bash
GET /health
```

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

## Usage Example

```bash
# 1. Start the Verifier
uvicorn app.main:app --port 8200

# 2. Submit a droplet for verification
curl -X POST http://localhost:8200/verify \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_path": "/Users/james/Development/proxy-manager",
    "droplet_name": "proxy-manager"
  }'

# Response: {"job_id": "ver-abc123", ...}

# 3. Check status
curl http://localhost:8200/verify/ver-abc123

# 4. Get full report when completed
curl http://localhost:8200/verify/ver-abc123/report
```

## Verification Phases

### Phase 1: Structure Scan (1 sec)
- ✅ Required files exist (main.py, models.py, tests/)
- ✅ Directory structure correct
- ✅ Optional files present (Dockerfile, README, etc.)

### Phase 2: UDC Compliance (30 sec)
- ✅ Starts droplet in test mode
- ✅ Tests /health endpoint
- ✅ Tests /capabilities and /state (if present)
- ✅ Validates response schemas
- ✅ Checks status enum values

### Phase 3: Security (15 sec)
- ✅ Scans for hardcoded secrets (passwords, API keys)
- ✅ Verifies environment variable usage
- ✅ Checks input validation (Pydantic models)
- ✅ Detects SQL injection patterns

### Phase 4: Functionality (60 sec)
- ✅ Runs pytest test suite
- ✅ Calculates test coverage
- ✅ Parses pass/fail counts
- ✅ Identifies failing tests

### Phase 5: Code Quality (10 sec)
- ✅ Checks for print statements
- ✅ Detects bare except clauses
- ✅ Finds TODO/FIXME comments
- ✅ Checks for synchronous I/O in async code

### Phase 6: Decision (5 sec)
- ✅ Aggregates all findings
- ✅ Applies decision logic
- ✅ Identifies strengths
- ✅ Generates recommendations

## Decision Logic

**FIXES_REQUIRED if:**
- Any critical issues (hardcoded secrets, SQL injection)
- UDC compliance fails
- Security vulnerabilities found
- More than 2 important issues
- Tests <80% passing

**APPROVED_WITH_NOTES if:**
- All critical checks pass
- Minor issues present (deprecations, print statements)
- Recommendations for improvement

**APPROVED if:**
- All checks pass
- No issues found
- Clean, production-ready code

## Architecture

```
verifier/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── models.py            # Pydantic models
│   ├── job_manager.py       # Job queue and execution
│   ├── phases/
│   │   ├── structure.py     # Phase 1
│   │   ├── udc.py           # Phase 2
│   │   ├── security.py      # Phase 3
│   │   ├── functionality.py # Phase 4
│   │   ├── quality.py       # Phase 5
│   │   └── decision.py      # Phase 6
├── Dockerfile
├── requirements.txt
├── SPEC_Verifier_Droplet_v1.md
└── README.md
```

## Configuration

Environment variables:

```bash
VERIFIER_PORT=8200
WORK_DIR=/tmp/verifier-jobs
MAX_CONCURRENT_JOBS=3
JOB_TIMEOUT_SECONDS=600
QUICK_MODE_ENABLED=true
TEST_TIMEOUT_SECONDS=120
STARTUP_TIMEOUT_SECONDS=30
```

## Integration

### With Coordinator (Future)
```python
# Coordinator calls Verifier before deployment
response = await http.post(
    "http://verifier:8200/verify",
    json={
        "droplet_path": "/path/to/droplet",
        "droplet_name": "new-droplet"
    }
)
job_id = response.json()["job_id"]

# Wait for completion
while True:
    status = await http.get(f"http://verifier:8200/verify/{job_id}")
    if status.json()["status"] == "completed":
        break

# Check decision
report = await http.get(f"http://verifier:8200/verify/{job_id}/report")
if report.json()["decision"] == "APPROVED":
    deploy(droplet)
```

### With CI/CD
```yaml
# .github/workflows/verify.yml
- name: Verify Droplet
  run: |
    curl -X POST http://verifier:8200/verify \
      -d '{"droplet_path": ".", "droplet_name": "${{ github.event.repository.name }}"}'
```

## Example Verification Report

```json
{
  "decision": "APPROVED_WITH_NOTES",
  "strengths": [
    "All 20 tests passing",
    "Good test coverage (58%)",
    "Clean UDC compliance",
    "No security issues found"
  ],
  "recommendations": [
    "Fix deprecation warnings for Python 3.13+ compatibility",
    "Consider adding more edge case tests"
  ],
  "critical_issues": 0,
  "important_issues": 0,
  "minor_issues": 5
}
```

## Troubleshooting

### Droplet won't start
- Check that virtual environment exists: `.venv/`
- Verify dependencies installed: `pip install -r requirements.txt`
- Check port isn't already in use

### Tests timeout
- Increase `TEST_TIMEOUT_SECONDS` in config
- Check for infinite loops or blocking I/O in tests

### UDC checks fail
- Ensure droplet has `/health` endpoint
- Verify droplet starts successfully locally
- Check endpoint response schemas

## Development

```bash
# Run verifier
uvicorn app.main:app --reload --port 8200

# Test with proxy-manager
curl -X POST http://localhost:8200/verify \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_path": "/Users/james/Development/proxy-manager",
    "droplet_name": "proxy-manager"
  }'
```

## Docker

```bash
# Build
docker build -t verifier:latest .

# Run
docker run -d \
  --name verifier \
  -p 8200:8200 \
  -v /path/to/droplets:/droplets \
  verifier:latest
```

---

**Built with ❤️ by Full Potential AI**
🔍 Automating Verification · Building the Future

