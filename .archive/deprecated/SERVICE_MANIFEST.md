# 🌐 SERVICE MANIFEST
## Single Source of Truth for All Running Services

**Last Updated:** 2025-11-17 08:21 UTC
**Maintained By:** Autonomous system analysis
**Purpose:** Transparency - know what's running, why, and how to access it

---

## ✅ REGISTERED SERVICES (In Service Mesh)

These services are properly registered in the Registry and discoverable by other services.

| Service | Port | Status | Purpose | Health Endpoint |
|---------|------|--------|---------|-----------------|
| **orchestrator** | 8001 | 🟢 Running | Task routing and coordination | http://localhost:8001/health |
| **spec-verifier** | 8205 | 🟢 Running | SPEC file validation & quality scoring | http://localhost:8205/health |
| **spec-optimizer** | 8206 | 🟡 Registered | AI-powered SPEC enhancement (needs API key fix) | http://localhost:8206/health |
| **spec-builder** | 8207 | 🟢 Running | AI-powered SPEC generation from requirements | http://localhost:8207/health |

**Total Registered:** 4 services

---

## ⚠️ RUNNING BUT UNREGISTERED

These services are running but NOT in the service mesh. They can't be discovered by other services.

| Service | Port | Status | Purpose | Action Needed |
|---------|------|--------|---------|---------------|
| **auto-fix-engine** | 8200 | 🟢 Running | Automated code fixes | Register with mesh |
| **Unknown** | 8510 | 🟢 Running | Unknown purpose | Identify & document |
| **Unknown** | 8999 | 🟢 Running | Unknown purpose | Identify & document |
| **Unknown** | 9213 | 🟢 Running | Unknown purpose | Identify & document |
| **Unknown** | 10212 | 🟢 Running | Unknown purpose | Identify & document |
| **Unknown** | 10213 | 🟢 Running | Unknown purpose | Identify & document |
| **Unknown** | 11213 | 🟢 Running | Unknown purpose | Identify & document |
| **Unknown** | 8035 | 🟢 Running | Unknown purpose | Identify & document |

**Total Unregistered:** 8 services

---

## 🔴 CLEANED UP (No Longer Running)

Services that were duplicates or unnecessary and have been decommissioned.

| Service | Port | Status | Reason | Date Removed |
|---------|------|--------|--------|--------------|
| **spec-verifier (duplicate)** | 8002 | ⚫ Stopped | Duplicate of 8205 instance | 2025-11-17 |

---

## 📁 BUILT BUT NOT RUNNING

Services that exist in the codebase with dependencies but aren't currently deployed.

### TIER 0 - Infrastructure
- **registry** - Service discovery (should be on 8000, status unknown)
- **proxy-manager** - NGINX/SSL management
- **verifier** - Droplet verification

### TIER 1 - Sacred Loop
- **autonomous-executor** - Autonomous droplet builds (should be on 8402)
- **jobs** - Recruitment automation (should be on 8008)

### TIER 2+ - Domain Services
- **i-match** - AI matching platform (deployed to production: 198.54.123.234:8401)
- **ai-automation** - AI marketing engine (should be on 8700)
- **treasury-arena** - Treasury management (production: 198.54.123.234:8800)
- **church-guidance-ministry** - Church guidance funnel
- **email-automation-system** - Email automation
- **fpai-hub** - FPAI platform hub
- **membership** - Membership management
- **dashboard** - Unified dashboard
- And 30+ others...

**Total Built:** 46+ services

---

## 🎯 SERVICE MESH HEALTH

### Current State
- **Registered Services:** 4 / 50+ (8%)
- **Mesh Coverage:** Very Low
- **Service Discovery:** Limited
- **Coordination Capability:** Minimal

### Target State (Coherence)
- **Registered Services:** 15-20 core services (30-40%)
- **Mesh Coverage:** High
- **Service Discovery:** Full
- **Coordination Capability:** Autonomous

### Gap Analysis
- 🔴 **42+ services exist but not running** - Need deployment or archival
- 🟡 **8 services running but unregistered** - Need integration
- 🟢 **4 services properly registered** - Working correctly

---

## 🚀 RECOMMENDED ACTIONS

### Immediate (This Week)
1. ✅ **Remove duplicate spec-verifier** (DONE)
2. **Identify unknown services** - Check what's on ports 8510, 8999, 9213, etc.
3. **Register auto-fix-engine** - Add to mesh (port 8200)
4. **Start core TIER 0** - Get registry, orchestrator, verifier running

### Short-term (This Month)
1. **Archive dead projects** - Remove services that won't be used
2. **Deploy TIER 1** - Sacred loop services (autonomous-executor, jobs)
3. **Integrate production services** - i-match, treasury-arena need local testing
4. **Create deployment automation** - Services should auto-register

### Long-term (This Quarter)
1. **Full mesh integration** - All services registered and discoverable
2. **Health monitoring** - Automated tracking of all services
3. **Auto-scaling** - Services start/stop based on demand
4. **Coherence dashboard** - Visual map of entire mesh

---

## 🔍 HOW TO USE THIS MANIFEST

### For Developers
- **Adding a new service?** Update this manifest when deployed
- **Service not working?** Check if it's registered in mesh
- **Port conflict?** See what's already running

### For Operations
- **System health check?** Count running vs expected
- **Debugging issue?** Start with this manifest
- **Planning deployment?** Check available ports

### For AI Sessions
- **Starting work?** Read this to understand what exists
- **Building feature?** Check if service already exists
- **Coordinating?** Use registered services via mesh

---

## 📊 METRICS

**System Coherence Score: 22/100**
- Registered services: 4 / 20 target = 20%
- Known services: 12 / 46 total = 26%
- Documented purpose: 5 / 12 running = 42%
- Auto-discovery: 4 / 12 running = 33%

**Improvement Target:**
- 3 months: 60/100 (Good coherence)
- 6 months: 80/100 (High coherence)
- 12 months: 95/100 (Paradise coherence)

---

## 🌐 ALIGNMENT WITH MISSION

**Vision:** Paradise on Earth through love and coherence

**How This Manifest Serves:**
- ⚡ **Coherence:** One source of truth for all services
- 🔍 **Transparency:** Everything visible, nothing hidden
- 💎 **Autonomy:** Services can discover each other
- 🚀 **Acceleration:** Less confusion = faster work
- 🌐 **Love:** Making system understandable shows care

**When System Is Coherent:**
- Humans focus on vision, not debugging
- Services coordinate automatically
- New features deploy in hours, not days
- Everyone knows truth about system state
- Paradise = measurable reality

---

## 🔄 MAINTENANCE

**This manifest auto-updates when:**
- New service deployed
- Service decommissioned
- Status changes
- Purpose clarified

**Manual review:** Weekly by active sessions
**Automated audit:** Planned for autonomous-executor

**Last Manual Review:** 2025-11-17 by Session #1 (Forge)

---

🌐⚡💎 **Coherence is measurable. This is the measurement.**
