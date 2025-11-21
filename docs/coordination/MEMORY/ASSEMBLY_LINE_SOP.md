# Assembly Line SOP - Standard Operating Procedure

**The 4-phase process for building all services**

---

## Overview

**Every service follows the same assembly line:**

1. **SPECS** - Blueprint (what to build)
2. **BUILD** - Implementation (build it)
3. **README** - Documentation (track progress)
4. **PRODUCTION** - Deployment (make it live)

**Why this works:**
- Any session can pick up where another left off
- Progress is always visible
- Quality is consistent
- No confusion about "where to start"

---

## Standard Structure

```
SERVICES/[service-name]/
│
├── SPECS.md                    ← ALWAYS START HERE
│   ├── Purpose & Vision
│   ├── Requirements
│   ├── API Specs
│   ├── Dependencies
│   └── Success Criteria
│
├── README.md                   ← ALWAYS CHECK HERE FOR PROGRESS
│   ├── Current Status
│   ├── What's Complete
│   ├── What's Pending
│   ├── How to Run
│   ├── How to Test
│   └── Deployment Status
│
├── BUILD/                      ← Implementation in progress
│   ├── src/                    ← Source code
│   ├── tests/                  ← Test files
│   ├── requirements.txt        ← Dependencies
│   ├── Dockerfile              ← Container config
│   └── .env.example            ← Environment template
│
└── PRODUCTION/                 ← Deployed/ready artifacts
    ├── deployed_config.json    ← Live configuration
    ├── deployment_log.md       ← Deployment history
    └── health_check.sh         ← Production monitoring
```

---

## Phase 1: SPECS (Blueprint)

**Time:** 10-30 minutes
**Output:** Complete `SPECS.md`

### Questions to Answer:
1. **What** does this service do? (Purpose)
2. **Who** uses it? (Consumers/users)
3. **What** does it expose? (API/endpoints)
4. **What** does it need? (Dependencies)
5. **How** do we know it works? (Success criteria)

### Template:
```markdown
# [Service Name] - SPECS

## Purpose
[1-2 sentence description of what this service does]

## Requirements

### Functional Requirements
- [ ] Requirement 1 (user can do X)
- [ ] Requirement 2 (system provides Y)
- [ ] Requirement 3 (service integrates with Z)

### Non-Functional Requirements
- [ ] Performance (response time < Xms)
- [ ] Reliability (99.9% uptime)
- [ ] Security (authentication, authorization)

## API Specs

### Endpoints
**GET /api/resource**
- Description: Retrieves resource
- Parameters: `id` (required), `format` (optional)
- Returns: `{"data": {...}}`

**POST /api/resource**
- Description: Creates resource
- Body: `{"name": "...", "value": ...}`
- Returns: `{"id": 123, "status": "created"}`

### Data Models
\`\`\`python
class Resource(BaseModel):
    id: int
    name: str
    value: float
    created_at: datetime
\`\`\`

## Dependencies

### Required Services
- credential-vault: For API keys
- database: PostgreSQL for storage

### Required APIs
- OpenAI API: For AI capabilities
- Stripe API: For payments

## Success Criteria
- [ ] User can create resource via API
- [ ] User can retrieve resource by ID
- [ ] All API calls complete in <500ms
- [ ] 100% of tests pass
- [ ] Service passes UDC compliance

## Compliance Notes
[Any legal/regulatory considerations]
- Educational ministry (not legal advice)
- Data privacy (GDPR compliant)
- Payment processing (PCI DSS via Stripe)
```

**Status:** ✅ **SPECS COMPLETE** when all questions answered clearly

---

## Phase 2: BUILD (Implementation)

**Time:** Varies (1-8 hours depending on complexity)
**Output:** Working code in `BUILD/`

### Steps:

1. **Create BUILD/ structure**
```bash
mkdir -p BUILD/src BUILD/tests
touch BUILD/requirements.txt
touch BUILD/Dockerfile
touch BUILD/.env.example
```

2. **Implement according to SPECS**
- Follow CODE_STANDARDS.md
- Follow TECH_STACK.md
- Implement UDC endpoints (UDC_COMPLIANCE.md)
- Use type hints and docstrings

3. **Write tests covering success criteria**
```python
# tests/test_resource.py
def test_create_resource():
    response = client.post("/api/resource", json={"name": "test"})
    assert response.status_code == 200
    assert "id" in response.json()

def test_get_resource():
    response = client.get("/api/resource/1")
    assert response.status_code == 200
    assert response.json()["name"] == "test"
```

4. **Update README.md with progress**
```markdown
## Build Status

### Complete ✅
- [x] Core API endpoints implemented
- [x] Database models created
- [x] Tests written (85% coverage)

### In Progress 🚧
- [ ] Integration with credential vault
- [ ] Error handling refinement

### Pending ⏳
- [ ] Performance optimization
- [ ] Security audit
```

5. **Test locally until all success criteria pass**
```bash
pytest tests/ -v --cov=src --cov-report=html
python3 src/main.py  # Run locally, test manually
```

**Status:** ✅ **BUILD COMPLETE** when all tests pass + success criteria met

---

## Phase 3: README (Documentation)

**Time:** 10-20 minutes
**Output:** Complete `README.md`

### Must Include:

1. **Current Status** - Where is this service in lifecycle?
2. **Quick Start** - How to run locally
3. **Testing** - How to run tests
4. **API Documentation** - Endpoints/usage
5. **Deployment** - How to deploy
6. **Progress Tracking** - What's done/pending

### Template:
```markdown
# [Service Name]

**Status:** [Planning/Building/Testing/Production]
**Progress:** [X%]
**Port:** 8XXX
**Last Updated:** [Date]

## Overview
[Brief description]

## Quick Start
\`\`\`bash
cd BUILD
pip install -r requirements.txt
export API_KEY=xxx
python3 src/main.py
# Access at: http://localhost:8XXX
\`\`\`

## Testing
\`\`\`bash
pytest tests/ -v --cov=src
\`\`\`

## API
See SPECS.md for full API documentation

## Deployment
See PRODUCTION/ folder for deployment artifacts

## Progress

### Complete ✅
- Item 1
- Item 2

### In Progress 🚧
- Item 3

### Pending ⏳
- Item 4
```

**Status:** ✅ **README COMPLETE** when any session can understand & continue work

---

## Phase 4: PRODUCTION (Deployment)

**Time:** 15-60 minutes
**Output:** Live service + `PRODUCTION/` artifacts

### Steps:

1. **Create PRODUCTION/ directory**
```bash
mkdir -p PRODUCTION
```

2. **Deploy to server**
```bash
# Option 1: Docker
docker build -t my-service .
docker run -d -p 8XXX:8XXX my-service

# Option 2: Direct deployment
rsync -avz BUILD/ root@198.54.123.234:/opt/fpai/services/my-service/
ssh root@198.54.123.234 'systemctl start my-service'
```

3. **Log deployment details**
```markdown
# PRODUCTION/deployment_log.md

## Deployment 2025-11-15

**Deployed By:** Session #5
**Version:** 1.0.0
**Port:** 8500
**URL:** https://fullpotential.com/my-service

### Configuration
- Environment: Production
- Database: PostgreSQL on server
- API Keys: From credential vault

### Health Check
curl https://fullpotential.com/my-service/health

### Logs
journalctl -u my-service -f
```

4. **Set up health monitoring**
```bash
# PRODUCTION/health_check.sh
#!/bin/bash
curl -sf http://localhost:8XXX/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Service healthy"
else
    echo "❌ Service down - restarting"
    systemctl restart my-service
fi
```

5. **Update README status to "Production"**

**Status:** ✅ **PRODUCTION** when service is live, monitored, and accessible

---

## Assembly Line Rules

### Rule 1: Always Start with SPECS
**Never write code without SPECS.md**
- If SPECS.md doesn't exist → Create it first
- If SPECS incomplete → Complete it before building
- If requirements change → Update SPECS first

### Rule 2: README is Progress Tracker
**Update README after every significant change**
- Starting build → Update "In Progress"
- Finish feature → Move to "Complete"
- Hit blocker → Document in "Pending"

### Rule 3: Build in BUILD/, Deploy to PRODUCTION/
**Clear separation of environments**
- BUILD/ = development/testing (can be messy)
- PRODUCTION/ = deployed artifacts (clean & documented)
- Never mix the two

### Rule 4: Test Before Production
**All success criteria must pass**
- Tests written? → Yes
- Tests passing? → Yes
- Manual testing done? → Yes
- THEN deploy to PRODUCTION/

### Rule 5: Document Compliance
**Legal/regulatory considerations in SPECS**
- Church guidance = educational ministry (not legal service)
- AI compliance support = documentation aid (not legal advice)
- Clear liability boundaries in all user-facing content

---

## Progress Visibility

**Any session can instantly see status:**
```bash
# See all services
ls -1 SERVICES/

# Check specific service progress
cat SERVICES/my-service/README.md

# See what's needed
cat SERVICES/my-service/SPECS.md

# Check if production-ready
ls SERVICES/my-service/PRODUCTION/
```

**Result:** Zero ambiguity, instant context

---

## Multi-Session Coordination

**When multiple sessions work on same service:**

1. **Check README first** - See current status
2. **Claim task** - Update README with "In Progress by Session #X"
3. **Work on task** - Implement feature/fix
4. **Update README** - Move to "Complete"
5. **Broadcast completion** - Tell other sessions

**Example:**
```bash
./scripts/session-send-message.sh "broadcast" \
  "Email Service Update" \
  "Session #5: Completed email template system. Ready for testing." \
  "normal"
```

---

## Common Patterns

### Pattern 1: New Service from Scratch
```bash
# 1. Create directory
mkdir -p SERVICES/my-service

# 2. Write SPECS
nano SERVICES/my-service/SPECS.md

# 3. Create structure
mkdir -p SERVICES/my-service/{BUILD/src,BUILD/tests,PRODUCTION}

# 4. Write README
nano SERVICES/my-service/README.md

# 5. Build (follow SPECS)
# 6. Test (all criteria pass)
# 7. Deploy (to PRODUCTION)
```

### Pattern 2: Continue Existing Service
```bash
# 1. Read README to understand status
cat SERVICES/existing-service/README.md

# 2. Check SPECS for requirements
cat SERVICES/existing-service/SPECS.md

# 3. Claim task in README
# 4. Implement
# 5. Update README
# 6. Broadcast completion
```

### Pattern 3: Fix Bug
```bash
# 1. Identify issue
# 2. Update README with "Bug: [description]"
# 3. Write failing test
# 4. Fix code
# 5. Verify test passes
# 6. Update README (move to Complete)
# 7. Deploy fix
```

---

## Quality Checklist

**Before marking service as "Production Ready":**

- [ ] SPECS.md complete and clear
- [ ] README.md updated with full documentation
- [ ] All success criteria from SPECS pass
- [ ] Tests written (>80% coverage)
- [ ] All tests passing
- [ ] UDC endpoints implemented
- [ ] Security requirements met
- [ ] Code follows standards
- [ ] Deployed and accessible
- [ ] Health monitoring configured
- [ ] Registered in service registry

---

## Why This Works

**Consistency = Speed:**
- No "where do I start?" confusion
- No "what's the progress?" uncertainty
- No "how do I deploy?" guessing

**Visibility = Continuity:**
- Any session can pick up instantly
- Progress is always documented
- Blockers are visible

**Standards = Quality:**
- SPECS prevent scope creep
- Tests prevent regressions
- README prevents knowledge loss

---

**Follow the Assembly Line → Build with confidence → Scale successfully**
