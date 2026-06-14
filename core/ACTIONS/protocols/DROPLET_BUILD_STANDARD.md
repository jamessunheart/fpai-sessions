# 🏗️ Droplet Build Standard - Assembly Line Protocol

**Last Updated:** 2025-11-15
**Status:** ACTIVE - ALL builds must follow this structure

---

## 🎯 Purpose

**Every droplet follows the same path:**
1. SPECS first (blueprint/requirements)
2. BUILD (implementation)
3. README (documentation/progress tracking)
4. PRODUCTION (deployment)

**Why:** So ANY session can pick up where the last one left off and see progress instantly.

---

## 📁 Standard Droplet Structure

```
SERVICES/[droplet-name]/
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

## 🔄 Build Phases (Assembly Line)

### Phase 1: SPECS (Blueprint)
**Time:** 10-30 minutes
**Output:** `SPECS.md`

**Questions to Answer:**
1. What does this droplet DO? (Purpose)
2. Who uses it? (Consumers)
3. What does it expose? (API/Endpoints)
4. What does it need? (Dependencies)
5. How do we know it works? (Success criteria)

**Template:**
```markdown
# [Droplet Name] - SPECS

## Purpose
[1-2 sentence description]

## Requirements
- [ ] Functional requirement 1
- [ ] Functional requirement 2
- [ ] Non-functional requirement 1

## API Specs
### Endpoints
- GET /endpoint1 - Description
- POST /endpoint2 - Description

### Data Models
[Schema definitions]

## Dependencies
- External services needed
- APIs required
- Data sources

## Success Criteria
- [ ] Criterion 1 (testable)
- [ ] Criterion 2 (testable)

## Compliance Notes
[Legal/regulatory considerations]
```

**Status:** ✅ SPECS COMPLETE when all questions answered

---

### Phase 2: BUILD (Implementation)
**Time:** Varies by complexity
**Output:** Working code in `BUILD/`

**Steps:**
1. Create BUILD/ directory structure
2. Implement src/ code following SPECS
3. Write tests/ covering success criteria
4. Update README.md with build progress
5. Test locally until all success criteria pass

**README Progress Tracking:**
```markdown
## Build Status

### Complete
- [x] Core functionality implemented
- [x] Tests written (85% coverage)

### In Progress
- [ ] Integration with dependency X
- [ ] Error handling refinement

### Pending
- [ ] Performance optimization
- [ ] Security audit
```

**Status:** ✅ BUILD COMPLETE when all tests pass + success criteria met

---

### Phase 3: README (Documentation)
**Time:** 10-20 minutes
**Output:** Complete `README.md`

**Must Include:**
1. **Current Status** - Where is this droplet in lifecycle?
2. **Quick Start** - How to run locally
3. **Testing** - How to run tests
4. **API Documentation** - Endpoints/usage
5. **Deployment** - How to deploy to production
6. **Progress Tracking** - What's done/pending

**Template:**
```markdown
# [Droplet Name]

**Status:** [Planning/Building/Testing/Production]
**Progress:** [X%]
**Last Updated:** [Date]

## Quick Start
\`\`\`bash
# Commands to run locally
\`\`\`

## Testing
\`\`\`bash
# Commands to run tests
\`\`\`

## API
[Endpoint documentation]

## Progress
### Complete ✅
- Item 1
- Item 2

### In Progress 🚧
- Item 3

### Pending ⏳
- Item 4
```

**Status:** ✅ README COMPLETE when any session can understand & continue

---

### Phase 4: PRODUCTION (Deployment)
**Time:** 15-60 minutes
**Output:** Live service + `PRODUCTION/` artifacts

**Steps:**
1. Create PRODUCTION/ directory
2. Deploy to server/platform
3. Log deployment details
4. Set up health checks
5. Update README status to "Production"

**Deployment Checklist:**
- [ ] Environment variables configured
- [ ] Service running on designated port
- [ ] Health check endpoint responding
- [ ] Monitoring/logs accessible
- [ ] Integration with other services tested

**Status:** ✅ PRODUCTION when service is live & monitored

---

## 🚦 Assembly Line Rules

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

## 📊 Progress Visibility

**Any session should be able to run:**
```bash
# See all droplets and their status
ls -1 SERVICES/

# Check specific droplet progress
cat SERVICES/[droplet-name]/README.md

# See what's needed
cat SERVICES/[droplet-name]/SPECS.md

# Check if production-ready
ls SERVICES/[droplet-name]/PRODUCTION/
```

**Result:** Instant context, zero ambiguity

---

## 🎯 Example: Church Guidance Ministry Droplet

```
SERVICES/church-guidance-ministry/
│
├── SPECS.md
│   Purpose: Educational ministry providing church formation guidance
│   Requirements: AI compliance support, educational content, liability clarity
│   API: Landing page, intake form, document generation
│   Success: User completes intake, receives guidance documents
│
├── README.md
│   Status: Building
│   Progress: 30%
│   Complete: SPECS, landing page mockup
│   Pending: Stripe integration, AI compliance module
│
├── BUILD/
│   ├── src/
│   │   ├── app.py
│   │   ├── compliance_module.py
│   │   └── templates/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
└── PRODUCTION/
    (Empty - not deployed yet)
```

---

## ✅ Checklist for New Droplets

**Before starting ANY build:**
- [ ] Create SERVICES/[droplet-name]/ directory
- [ ] Write SPECS.md (blueprint first!)
- [ ] Create README.md with status tracking
- [ ] Create BUILD/ directory structure
- [ ] Create PRODUCTION/ directory (empty initially)
- [ ] Document compliance considerations
- [ ] Define success criteria (testable)

**Then follow the assembly line:**
1. SPECS → 2. BUILD → 3. README → 4. PRODUCTION

---

## 🔄 Updating the Assembly Line

**This protocol itself can evolve:**
- If pattern emerges → Add to protocol
- If step is redundant → Remove from protocol
- If structure doesn't work → Update structure

**But changes require:**
1. Update this document first
2. Apply to new builds going forward
3. Optionally migrate existing droplets

---

## 💡 Why This Works

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

**Status:** ACTIVE
**Applies to:** ALL droplet builds (existing + future)
**Next:** Apply to Church Guidance Ministry as first example

🏗️⚡✅
