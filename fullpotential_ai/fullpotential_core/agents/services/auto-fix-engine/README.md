# Auto-Fix Engine - Droplet #23

**Sacred Loop Step 5.5 - Automatic Issue Resolution**

## Overview

The Auto-Fix Engine closes the Sacred Loop by automatically fixing issues found by the Verifier (Droplet #8). Instead of requiring manual intervention, it analyzes verification reports, generates fixes using Claude API, applies them automatically, and re-verifies until the service is APPROVED.

## Sacred Loop Integration

```
1. Intent → 2. SPEC → 3. Package → 4. Build → 5. VERIFY
                                                  ↓
                                              APPROVED? → 6. Deploy
                                                  ↓ NO
                                              5.5 AUTO-FIX
                                                  ↓
                                            Re-verify (Step 5)
```

Without Auto-Fix: Verifier → Manual fix → Manual re-verify → Repeat
**With Auto-Fix: Verifier → Auto-analyze → Auto-fix → Auto-re-verify → APPROVED**

## Capabilities

- **Issue Analysis**: Parses Verifier reports and categorizes issues by severity
- **Intelligent Fixing**: Uses Claude API to generate context-aware fixes
- **Safe Application**: Backs up files before modifying, restores on failure
- **Iterative Loop**: Re-verifies after each fix until APPROVED (max 3 iterations)
- **Complete Autonomy**: Zero manual intervention required

## Fix Types Supported

1. **Startup Failures** (Critical)
   - Missing dependencies
   - Import errors
   - Syntax errors
   - Async/await issues

2. **Test Failures** (Important)
   - Broken test cases
   - Missing test dependencies

3. **Code Quality** (Minor)
   - Print statements → logging
   - Bare except clauses
   - Anti-patterns

## Architecture

```
FixRequest
    ↓
AutoFixLoop (orchestrator)
    ├─ IssueAnalyzer: Parse Verifier report → List[Issue]
    ├─ FixGenerator: Claude API → List[Fix]
    ├─ FixApplier: Apply changes (with backup/restore)
    └─ Re-verify → Repeat until APPROVED
```

## API Endpoints

### POST /fix
Submit a service for auto-fixing

**Request:**
```json
{
  "droplet_path": "/path/to/service",
  "droplet_name": "i-proactive",
  "verification_job_id": "ver-abc123",
  "max_iterations": 3
}
```

**Response:**
```json
{
  "fix_job_id": "fix-def456",
  "droplet_name": "i-proactive",
  "status": "pending",
  "max_iterations": 3,
  "created_at": "2025-01-14T10:00:00Z"
}
```

### GET /fix/{job_id}
Get status of a fix job

**Response:**
```json
{
  "fix_job_id": "fix-def456",
  "droplet_name": "i-proactive",
  "status": "verified",
  "current_iteration": 2,
  "max_iterations": 3,
  "final_decision": "APPROVED",
  "total_fixes_applied": 3,
  "iterations": [...]
}
```

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Start Service
```bash
uvicorn app.main:app --port 8300
```

## Configuration

Edit `.env`:

```bash
# Required
ANTHROPIC_API_KEY=your_key_here

# Optional
SERVICE_PORT=8300
CLAUDE_MODEL=claude-3-sonnet-20240229
MAX_TOKENS=8000
MAX_FIX_ITERATIONS=3
VERIFIER_URL=http://localhost:8200
```

## Usage Example

```bash
# Start Auto-Fix Engine
uvicorn app.main:app --port 8300

# Submit service for auto-fixing
curl -X POST http://localhost:8300/fix \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_path": "/Users/jamessunheart/Development/agents/services/i-proactive",
    "droplet_name": "i-proactive",
    "verification_job_id": "ver-781d5018",
    "max_iterations": 3
  }'

# Check status
curl http://localhost:8300/fix/{job_id}
```

## How It Works

### Iteration Flow

For each iteration (max 3):

1. **Fetch Verification Report**
   - Get report from Verifier using job_id
   - Check decision (APPROVED / FIXES_REQUIRED / FAILED)

2. **Analyze Issues**
   - Extract issues from report
   - Prioritize by severity: critical → important → minor
   - Filter for auto-fixable issues

3. **Generate Fixes**
   - For startup failures: Analyze code with Claude API
   - Claude suggests: updated requirements.txt, code changes
   - Build Fix objects with file changes and commands

4. **Apply Fixes**
   - Backup all files before modifying
   - Write new content to files
   - Run commands (pip install, etc.)
   - Restore from backup if failure

5. **Re-Verify**
   - Submit service to Verifier
   - Wait for completion (timeout 180s)
   - Use new verification_job_id for next iteration

6. **Check Decision**
   - If APPROVED: Complete with success
   - If FIXES_REQUIRED: Continue to next iteration
   - If max iterations reached: Return final status

## Files

```
auto-fix-engine/
├── app/
│   ├── __init__.py           # Service metadata
│   ├── config.py             # Pydantic settings
│   ├── models.py             # Data models (Issue, Fix, FixJobStatus)
│   ├── issue_analyzer.py     # Parses Verifier reports
│   ├── fix_generator.py      # Claude API integration
│   ├── fix_applier.py        # Applies fixes with backup/restore
│   ├── auto_fix_loop.py      # Main orchestration loop
│   └── main.py               # FastAPI application
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

## Benefits

### For Individual Services
- Fixes startup failures automatically
- Corrects code quality issues
- Re-verifies until passing

### For the System
- **Completes Sacred Loop**: True autonomy from Intent → APPROVED
- **Foundational Optimization**: Every future service benefits
- **Zero Manual Work**: Architect declares intent only
- **Self-Healing**: System fixes itself

## Future Enhancements

- Support for more issue types (security, performance)
- Multi-file context for complex fixes
- Learning from past fixes
- Parallel fix generation
- Integration with Deployer (Step 6)

## Status

**Version:** 1.0.0
**Droplet ID:** 23
**Sacred Loop Step:** 5.5
**Port:** 8300

---

**This is the foundational optimization.** It transforms the Sacred Loop from semi-autonomous (manual fixes required) to fully autonomous (self-healing).
