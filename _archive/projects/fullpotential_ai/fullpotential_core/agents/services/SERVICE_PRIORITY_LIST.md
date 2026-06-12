# Service Priority List
**Updated:** 2025-11-15
**Session:** #2 (Coordination & Infrastructure)

---

## 🟢 CURRENTLY RUNNING (Production/Active)

### Fully Operational & UDC Compliant
1. **i-match** (port 8401)
   - Status: ✅ Production
   - UDC: 5/5 endpoints
   - Action: None needed

2. **ai-automation** (port 8700)
   - Status: ✅ Production
   - UDC: 5/5 endpoints (retrofitted this session)
   - Action: None needed

### Running but Needs UDC Retrofit
3. **fpai-hub** (port 8010)
   - Status: 🟢 Running
   - UDC: 1/5 endpoints ⚠️
   - Missing: /capabilities, /state, /dependencies, /message
   - Action: Add 4 endpoints (30 min)

4. **master-dashboard** (port 8026)
   - Status: 🟢 Running
   - UDC: 1/5 endpoints ⚠️
   - Missing: /capabilities, /state, /dependencies, /message
   - Action: Add 4 endpoints (30 min)

5. **i-proactive** (port 8400 - on server)
   - Status: 🟢 Running on server
   - UDC: 1/5 endpoints ⚠️
   - Missing: /capabilities, /state, /dependencies, /message
   - Note: Port mismatch in registry (says 8106, actually 8400)
   - Action: Fix registry port + add 4 endpoints (45 min)

### Also Running (Ports Detected)
6. **unified-chat** (port 8100)
   - Status: 🟢 Running
   - UDC: Not tested
   - Action: Test compliance, retrofit if needed

7. **registry** (port 8000)
   - Status: 🟢 Running
   - UDC: Not tested
   - Action: Test compliance, retrofit if needed

8. **jobs** (port 8008)
   - Status: 🟢 Running
   - UDC: Not tested
   - Action: Test compliance, retrofit if needed

9. **Unknown services on ports:**
   - 8030, 8031, 8035, 8500, 8765, 8888, 8889, 8890, 9000
   - Action: Identify and register

---

## 📋 PRIORITY QUEUE (Not Running - Ordered by Priority)

### PRIORITY 1: HIGH - Core Infrastructure (Start These Next)

#### P1.1 - registry (port 8000)
- **Purpose:** Service registry/discovery
- **Impact:** HIGH - Core coordination
- **Status:** Discovered, not running locally
- **Action:** Start service, test UDC compliance, retrofit if needed
- **Est. Time:** 1 hour
- **Depends on:** Nothing
- **Blocks:** Service discovery features

#### P1.2 - orchestrator (port 8109)
- **Purpose:** Service orchestration
- **Impact:** HIGH - Coordinates multiple services
- **Status:** Discovered, has main.py + requirements
- **Action:** Review purpose, start, test UDC, deploy
- **Est. Time:** 1-2 hours
- **Depends on:** registry (optional)
- **Blocks:** Multi-service workflows

#### P1.3 - deployer (port 8104)
- **Purpose:** Automated deployment
- **Impact:** HIGH - Infrastructure automation
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, integrate with automation suite
- **Est. Time:** 1-2 hours
- **Depends on:** Nothing
- **Blocks:** Automated deployments

### PRIORITY 2: MEDIUM - User-Facing Services

#### P2.1 - dashboard (port 8103)
- **Purpose:** Main dashboard
- **Impact:** MEDIUM - User interface
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, deploy
- **Est. Time:** 1 hour
- **Depends on:** Backend services
- **Blocks:** User visibility

#### P2.2 - landing-page (port 8107)
- **Purpose:** Public landing page
- **Impact:** MEDIUM - First impression
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, deploy
- **Est. Time:** 45 min
- **Depends on:** Nothing
- **Blocks:** Public access

#### P2.3 - membership (port 8108)
- **Purpose:** Membership management
- **Impact:** MEDIUM - User management
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, deploy
- **Est. Time:** 1 hour
- **Depends on:** Nothing
- **Blocks:** User onboarding

### PRIORITY 3: MEDIUM - Backend Services

#### P3.1 - credentials-manager (port 8102)
- **Purpose:** Credential/secret management
- **Impact:** MEDIUM - Security
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, integrate with vault
- **Est. Time:** 1-2 hours
- **Depends on:** Nothing
- **Blocks:** Secure credential access

#### P3.2 - proxy-manager (port 8110)
- **Purpose:** Proxy/routing management
- **Impact:** MEDIUM - Infrastructure
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, deploy
- **Est. Time:** 1 hour
- **Depends on:** Nothing
- **Blocks:** Proxy features

#### P3.3 - helper-management (port 8105)
- **Purpose:** Helper/assistant management
- **Impact:** MEDIUM - AI coordination
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, deploy
- **Est. Time:** 1 hour
- **Depends on:** Nothing
- **Blocks:** Helper features

### PRIORITY 4: LOW - Support Services

#### P4.1 - verifier (port 8111)
- **Purpose:** Verification service
- **Impact:** LOW-MEDIUM - Quality assurance
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, deploy
- **Est. Time:** 45 min
- **Depends on:** Services to verify
- **Blocks:** Verification features

#### P4.2 - autonomous-executor (port 8101)
- **Purpose:** Autonomous task execution
- **Impact:** LOW-MEDIUM - Automation
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, deploy
- **Est. Time:** 1 hour
- **Depends on:** Nothing
- **Blocks:** Autonomous features

#### P4.3 - auto-fix-engine (port 8112)
- **Purpose:** Automated fixes
- **Impact:** LOW - Nice to have
- **Status:** Discovered, has main.py + requirements
- **Action:** Start, test UDC, deploy
- **Est. Time:** 1 hour
- **Depends on:** Services to fix
- **Blocks:** Auto-fix features

---

## 🔧 DEVELOPMENT QUEUE (Incomplete - Need Work Before Starting)

### Needs Development
1. **treasury-manager** - Has SPEC, no main.py yet
2. **autonomous-agents** - Has SPEC, no main.py yet
3. **content-generation-engine** - Has SPEC, no main.py yet
4. **email-automation-system** - Has SPEC, no main.py yet
5. **reddit-auto-responder** - Has SPEC, no main.py yet
6. **seo-landing-generator** - Has SPEC, no main.py yet
7. **social-auto-poster** - Has SPEC, no main.py yet
8. **legal-verification-agent** - Has SPEC, no main.py yet
9. **api-hub** - Has SPEC, no main.py yet
10. **ops** - Has SPEC, no main.py yet
11. **orchestrator-unified** - Has SPEC, no main.py yet
12. **hub** - Has main.py + SPEC, needs review
13. **collective-mind** - Has main.py, needs review
14. **coranation** - Has main.py, needs review

**Action for these:** Use `new-service.sh` to scaffold properly, or develop from SPEC

---

## 🎯 RECOMMENDED EXECUTION ORDER

### Phase 1: Achieve 100% UDC Compliance for Running Services (2-3 hours)
1. Retrofit fpai-hub (30 min)
2. Retrofit master-dashboard (30 min)
3. Retrofit i-proactive on server (45 min)
4. Test unified-chat, registry, jobs compliance (30 min)
5. Retrofit any that need it (30-60 min)

**Milestone:** All running services 5/5 UDC compliant

### Phase 2: Start Core Infrastructure (3-4 hours)
1. Start registry service (if not already)
2. Start orchestrator
3. Start deployer
4. Test all three for UDC compliance
5. Integrate with existing services

**Milestone:** Core infrastructure operational

### Phase 3: User-Facing Services (2-3 hours)
1. Start dashboard
2. Start landing-page
3. Start membership
4. Test UDC compliance
5. Deploy to production

**Milestone:** User services accessible

### Phase 4: Backend Services (3-4 hours)
1. Start credentials-manager
2. Start proxy-manager
3. Start helper-management
4. Test UDC compliance
5. Integrate with existing services

**Milestone:** Backend services complete

### Phase 5: Support Services (2-3 hours)
1. Start verifier
2. Start autonomous-executor
3. Start auto-fix-engine
4. Test UDC compliance

**Milestone:** Support services operational

### Phase 6: Development Services (Ongoing)
- Develop services from SPECs as needed
- Use `new-service.sh` for guaranteed UDC compliance

**Total estimated time to all services running:** 12-17 hours

---

## 📊 Current Statistics

**Total Services:** 18 active + 16 development = 34 total
**Running:** 5-9 services (some on unregistered ports)
**UDC Compliant:** 2/5 tested (40%)
**Registered:** 18/18 active services (100%)
**Ready to start:** 13 services with code
**Need development:** 16 services with SPECs only

---

## 🚀 Quick Start Guide

**To work on next priority service:**

```bash
cd /Users/jamessunheart/Development/agents/services/[service-name]

# If service exists:
./start.sh  # or python3 main.py or python3 app/main.py

# Test compliance:
cd ~/Development/docs/coordination/scripts
./enforce-udc-compliance.sh [service-name]

# If not compliant, add UDC endpoints from:
# /Users/jamessunheart/Development/agents/services/ai-automation/main.py

# Deploy:
./sync-service.sh [service-name]
```

**To create new service from SPEC:**

```bash
cd ~/Development/docs/coordination/scripts
./new-service.sh [service-name] "Description from SPEC" [port]
# Auto-creates with all 5 UDC endpoints!
```

---

**Priority list maintained by:** Session #2 (Coordination & Infrastructure)
**Updated:** 2025-11-15
**Status:** Ready for execution
