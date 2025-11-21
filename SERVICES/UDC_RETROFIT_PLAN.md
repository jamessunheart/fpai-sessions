# UDC Retrofit Plan
**Created by:** Session #2 (Coordination & Infrastructure)
**Date:** 2025-11-15
**Based on:** Bulk compliance check of 18 registered services

---

## 📊 Current State Summary

**Total Services Registered:** 18
**Services Running:** 3 locally detected + 2 on alternate ports = 5 total
**UDC Compliance:**
- ✅ Fully compliant: 1 (i-match: 5/5 endpoints)
- ⚠️ Partially compliant: 4 (fpai-hub, master-dashboard, ai-automation, i-proactive: 1/5 endpoints)
- ❌ Non-compliant: 0 running services without any endpoints
- ⚪ Not running: 13 services

**Compliance Rate:** 20% (1/5 running services fully compliant)
**Target:** 100% compliance for all active services

---

## 🎯 Retrofit Priority Matrix

### Priority 1: IMMEDIATE (Running Services - Missing 4 Endpoints)

#### 1.1 fpai-hub (port 8010)
- **Current:** 1/5 endpoints (/health only)
- **Missing:** /capabilities, /state, /dependencies, /message
- **Status:** 🟢 Running
- **Impact:** HIGH - Core hub service
- **Effort:** 1-2 hours
- **Action:** Add 4 UDC endpoints following ai-automation pattern

#### 1.2 master-dashboard (port 8026)
- **Current:** 1/5 endpoints (/health only)
- **Missing:** /capabilities, /state, /dependencies, /message
- **Status:** 🟢 Running
- **Impact:** HIGH - Dashboard service
- **Effort:** 1-2 hours
- **Action:** Add 4 UDC endpoints

#### 1.3 ai-automation (port 8700) [DONE ✅]
- **Current:** 5/5 endpoints
- **Status:** ✅ FULLY COMPLIANT
- **Action:** None - use as reference template

#### 1.4 i-proactive (port 8400)
- **Current:** 1/5 endpoints (has custom /health)
- **Missing:** /capabilities, /state, /dependencies, /message
- **Status:** 🟢 Running on server
- **Impact:** HIGH - Proactive task execution
- **Effort:** 1-2 hours
- **Action:** Add 4 UDC endpoints
- **Note:** Port mismatch - registry says 8106, actually on 8400

### Priority 2: HIGH (Production/Active Services Not Running)

#### 2.1 i-match (port 8401)
- **Current:** 5/5 endpoints
- **Status:** ✅ FULLY COMPLIANT
- **Running:** Only when tested
- **Action:** None needed for compliance, ensure stable deployment

#### 2.2 unified-chat (port 8100)
- **Current:** Not tested (not running locally)
- **Expected:** Needs all 5 UDC endpoints
- **Impact:** MEDIUM - Chat service
- **Action:** Start service, test compliance, retrofit if needed

#### 2.3 registry (port 8000)
- **Current:** Not running locally
- **Expected:** Core registry service
- **Impact:** HIGH
- **Action:** Start service, verify/add UDC endpoints

#### 2.4 jobs (port 8008)
- **Current:** Not running locally
- **Port detected:** 8008 found in code
- **Impact:** MEDIUM
- **Action:** Start service, verify/add UDC endpoints

### Priority 3: MEDIUM (Development Services)

All other services with status="discovered" need:
1. Service description updated in registry
2. Port verification (actual vs assigned)
3. Startup and testing
4. UDC compliance check
5. Retrofitting if needed

**Services in this category:**
- dashboard (8103)
- orchestrator (8109)
- deployer (8104)
- credentials-manager (8102)
- autonomous-executor (8101)
- helper-management (8105)
- landing-page (8107)
- membership (8108)
- proxy-manager (8110)
- verifier (8111)
- auto-fix-engine (8112)

---

## 🛠️ Retrofit Implementation Guide

### Standard UDC Endpoint Template

Use ai-automation/main.py as reference. All services need these 5 endpoints:

```python
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

# 1. Health Check
@app.get("/health")
async def health():
    """UDC Endpoint 1: Health check"""
    return {
        "status": "active",
        "service": "SERVICE_NAME",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# 2. Capabilities
@app.get("/capabilities")
async def capabilities():
    """UDC Endpoint 2: Service capabilities"""
    return {
        "version": "1.0.0",
        "features": ["list", "of", "features"],
        "dependencies": ["list", "of", "dependencies"],
        "udc_version": "1.0",
        "metadata": {}
    }

# 3. State/Metrics
@app.get("/state")
async def state():
    """UDC Endpoint 3: Resource usage"""
    return {
        "uptime_seconds": 0,
        "requests_total": 0,
        "requests_per_minute": 0.0,
        "errors_last_hour": 0,
        "last_restart": datetime.utcnow().isoformat() + "Z"
    }

# 4. Dependencies
@app.get("/dependencies")
async def dependencies():
    """UDC Endpoint 4: Service dependencies"""
    return {
        "required": [],
        "optional": [],
        "missing": []
    }

# 5. Inter-Service Messaging
@app.post("/message")
async def message(payload: dict):
    """UDC Endpoint 5: Inter-service communication"""
    return {
        "status": "received",
        "message_id": f"msg-{datetime.utcnow().timestamp()}",
        "processed_at": datetime.utcnow().isoformat() + "Z"
    }
```

### Retrofit Process (Per Service)

1. **Locate main file**
   - Check: `src/main.py`, `app/main.py`, `app.py`, or `main.py`
   - Verify it's a FastAPI app

2. **Add missing endpoints**
   - Copy template above
   - Customize with service-specific data
   - Keep existing endpoints intact

3. **Test locally**
   - Start service
   - Test all 5 endpoints:
     ```bash
     curl http://localhost:PORT/health
     curl http://localhost:PORT/capabilities
     curl http://localhost:PORT/state
     curl http://localhost:PORT/dependencies
     curl -X POST http://localhost:PORT/message -d '{}'
     ```

4. **Verify compliance**
   ```bash
   cd /Users/jamessunheart/Development/docs/coordination/scripts
   ./enforce-udc-compliance.sh SERVICE_NAME
   ```

5. **Deploy**
   ```bash
   ./sync-service.sh SERVICE_NAME
   ```

---

## 📅 Recommended Execution Timeline

### Week 1: Priority 1 (Running Services)
**Day 1-2:**
- ✅ ai-automation (COMPLETE)
- Retrofit fpai-hub
- Retrofit master-dashboard

**Day 3:**
- Retrofit i-proactive
- Verify all P1 services are 5/5 compliant

### Week 2: Priority 2 (Production Services)
**Day 1:**
- Start and test unified-chat, registry, jobs
- Identify compliance gaps

**Day 2-3:**
- Retrofit any P2 services needing UDC compliance
- Deploy to production

### Week 3-4: Priority 3 (Development Services)
**Ongoing:**
- As services are activated, retrofit to UDC
- Use `new-service.sh` for new services (auto-compliant)
- Update service descriptions in registry

---

## 🎯 Success Metrics

**Target Metrics:**
- 100% of running services UDC compliant
- 100% of production services UDC compliant
- 80%+ of all registered services UDC compliant

**Current Progress:**
- Running services: 20% compliant (1/5)
- All services: 5.5% compliant (1/18)

**After P1 Completion:**
- Running services: 100% compliant (5/5)
- All services: 27.7% compliant (5/18)

**After P2 Completion:**
- Running services: 100% compliant
- Production services: 100% compliant
- All services: ~44% compliant (8/18)

---

## 🔧 Automation Opportunities

### Bulk Retrofit Script (Future Enhancement)
Create `bulk-udc-retrofit.sh` to:
1. Scan service for missing endpoints
2. Generate boilerplate UDC code
3. Insert into main file
4. Test compliance
5. Auto-commit if tests pass

### Continuous Compliance Monitoring
- Run `enforce-udc-compliance.sh` daily
- Alert if compliance drops
- Auto-create retrofit tickets

---

## 📋 Port Registry Cleanup

**Issue Identified:** Assigned ports don't match actual running ports

**Services with port mismatches:**
- i-proactive: Registry says 8106, actually on 8400
- ai-automation: Not in initial registry, actually on 8700

**Action Required:**
1. Survey all running services for actual ports
2. Update SERVICE_REGISTRY.json with correct ports
3. Standardize port assignment strategy:
   - 8000-8099: Core infrastructure
   - 8100-8199: User-facing services
   - 8200-8299: Backend services
   - 8300-8399: Integration services
   - 8400-8499: AI/automation services
   - 8500+: Experimental/development

---

## 🚀 Quick Win Strategy

**Fastest path to 100% running service compliance:**

1. **Start here (30 minutes):**
   - Copy ai-automation UDC endpoints
   - Paste into fpai-hub/app.py
   - Customize service name and features
   - Test: `curl http://localhost:8010/capabilities`
   - Deploy: `./sync-service.sh fpai-hub`

2. **Repeat for master-dashboard (30 minutes):**
   - Same process for port 8026

3. **Handle i-proactive (45 minutes):**
   - Fix port in registry (8106 → 8400)
   - Add UDC endpoints to server deployment
   - Test on server
   - Update registry status to "production"

**Total time to 100% compliance for running services: ~2 hours**

---

## 📞 For Other Claude Sessions

**If you're retrofitting a service:**

1. Find the main file (usually `app/main.py` or `app.py`)
2. Copy UDC endpoints from `/Users/jamessunheart/Development/SERVICES/ai-automation/main.py` (lines 33-103)
3. Paste after existing `@app.get("/health")` or at the top of your endpoints
4. Customize the returned data with your service info
5. Test: `./enforce-udc-compliance.sh YOUR_SERVICE`
6. Deploy: `./sync-service.sh YOUR_SERVICE`

**Template location:**
`/Users/jamessunheart/Development/SERVICES/ai-automation/main.py`

**Documentation:**
`/Users/jamessunheart/Development/SERVICES/UDC_COMPLIANCE_REPORT.md`

---

## ✅ Next Actions

**Immediate (This Session):**
- [ ] Test new-service.sh with sample service
- [ ] Document all findings
- [ ] Broadcast retrofit plan to collective

**Next Session:**
- [ ] Retrofit fpai-hub (P1.1)
- [ ] Retrofit master-dashboard (P1.2)
- [ ] Retrofit i-proactive (P1.4)
- [ ] Achieve 100% compliance for running services

**Future Sessions:**
- [ ] Clean up port assignments
- [ ] Start P2 services and verify compliance
- [ ] Create bulk retrofit automation
- [ ] Continuous compliance monitoring

---

**Created:** 2025-11-15 16:25 PST
**Session:** #2 (Coordination & Infrastructure)
**Status:** Ready for execution
**Est. Time to 100% running service compliance:** 2-3 hours
