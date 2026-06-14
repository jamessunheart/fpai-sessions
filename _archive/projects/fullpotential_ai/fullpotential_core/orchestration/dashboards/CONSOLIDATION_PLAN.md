# 🎯 DASHBOARD CONSOLIDATION PLAN
**From 8 fragmented dashboards → 4-5 unified views**
**Generated:** 2025-11-17 12:36 UTC

---

## 📊 CURRENT STATE (8 Dashboards Running)

### Coordination Dashboards (3):
1. Visual Coordination (8031) - Most comprehensive
2. Master Dashboard (8026) - System overview
3. Simple Coordination (8030) - Lightweight

**Problem:** Three dashboards doing similar things

---

### Financial Dashboards (3):
1. Treasury (8005) - Portfolio tracking
2. 2X Treasury (8052) - Growth strategy
3. Treasury Arena (8035) - Trading simulation

**Problem:** Financial data spread across 3 dashboards

---

### Operational Dashboards (2):
1. Jobs (8008) - Task tracking
2. FPAI Hub (8010) - Service coordination

**Status:** These are fine, keep separate

---

## 🎯 TARGET STATE (4-5 Dashboards)

### 1. PRIMARY DASHBOARD (Port 8031) ⭐
**Visual Coordination Dashboard - Enhanced**

**What it shows:**
- All Claude sessions (active, idle, timed out)
- All 34 services (health, status, metrics)
- System coherence score
- Quick links to other dashboards
- Real-time updates from SSOT

**What to add:**
- Links to: Financial, Jobs, FPAI Hub
- Quick actions (scan services, update SSOT)
- Alert panel (liquidation risks, errors)
- Revenue metrics summary

**Status:** Enhance existing dashboard

---

### 2. UNIFIED FINANCIAL DASHBOARD (Port 8100) 💰
**NEW - Consolidates 3 financial dashboards**

**What it shows:**
- **Portfolio View** (from Treasury 8005):
  - Current positions (BTC, SOL, etc.)
  - P&L, liquidation risks
  - Yield generation

- **2X Growth Strategy** (from 2X Treasury 8052):
  - Target: $373K → $500K
  - Deployment strategy (40/40/20)
  - Progress tracking

- **Trading Arena** (from Treasury Arena 8035):
  - Simulations running
  - Agent performance
  - Historical results

- **Unified Metrics:**
  - Total capital
  - Monthly yield
  - Risk score
  - Revenue projections

**Status:** BUILD NEW (consolidate 8005, 8052, 8035)

---

### 3. JOBS DASHBOARD (Port 8008) 📋
**Keep as-is**

**What it shows:**
- Active tasks
- Completed work
- Session assignments

**Status:** NO CHANGE (working well)

---

### 4. FPAI HUB (Port 8010) 🌐
**Keep as-is**

**What it shows:**
- Service management
- Central coordination
- Hub functionality

**Status:** NO CHANGE (working well)

---

### 5. SPECIALIZED DASHBOARDS (As needed)
**Approval, Email, etc.**

**Status:** Activate when required, link from primary

---

## 🔧 IMPLEMENTATION PLAN

### Phase 1: Quick Wins (15 min) ✅ DONE
- ✅ Create DASHBOARDS directory
- ✅ Document all dashboards
- ✅ Create quick launcher script
- ✅ Identify consolidation opportunities

### Phase 2: Enhance Primary (30 min)
**Update Visual Coordination Dashboard (8031):**

```python
# Add navigation panel with links
DASHBOARD_LINKS = {
    'financial': 'http://localhost:8100',  # Future unified
    'jobs': 'http://localhost:8008',
    'fpai_hub': 'http://localhost:8010',
    'treasury': 'http://localhost:8005',  # Current, until 8100 ready
    '2x_treasury': 'http://localhost:8052',
    'arena': 'http://localhost:8035'
}

# Add quick actions
QUICK_ACTIONS = [
    'Scan Services (updates SSOT)',
    'Check Treasury Risk',
    'View Revenue Status',
    'Check I MATCH Matches'
]

# Add alert panel
ALERTS = [
    'BTC 24% from liquidation',
    'I MATCH: 0 matches, 0 revenue',
    'Treasury yield: $0/month'
]
```

**Location:** Find where 8031 is running, enhance it

---

### Phase 3: Build Unified Financial (60 min)
**Create new consolidated financial dashboard:**

```bash
# Create new service
mkdir -p agents/services/unified-financial-dashboard
cd agents/services/unified-financial-dashboard

# Structure:
- app/main.py (FastAPI)
- app/templates/index.html
- app/portfolio.py (pulls from treasury 8005)
- app/growth_strategy.py (pulls from 2x treasury 8052)
- app/trading_arena.py (pulls from arena 8035)
- requirements.txt
- start.sh
```

**Features:**
1. **Portfolio View:**
   - Fetch data from treasury-dashboard API
   - Show positions, P&L, risks
   - Real-time updates

2. **2X Strategy View:**
   - Deployment progress ($373K → $500K)
   - Strategy allocation (40/40/20)
   - Yield tracking

3. **Trading Arena View:**
   - Active simulations
   - Agent rankings
   - Performance charts

4. **Unified Metrics:**
   - Total capital across all
   - Monthly yield projection
   - Risk score (aggregate)
   - Quick actions (rebalance, deploy, etc.)

---

### Phase 4: Deprecate Redundant (15 min)
**Stop redundant dashboards:**

```bash
# Stop Simple Coordination (8030)
kill $(lsof -ti:8030)

# Stop Master Dashboard (8026)
kill $(lsof -ti:8026)

# Keep 8005, 8052, 8035 running until 8100 is ready
# Then stop them and redirect to 8100
```

**Update documentation:**
- Mark as deprecated in SSOT
- Add redirect notices
- Update all links

---

### Phase 5: Final Cleanup (15 min)
**Archive old dashboards:**

```bash
# Move to archive
mkdir -p DASHBOARDS/archive
mv agents/services/master-dashboard DASHBOARDS/archive/
# Keep source code for reference
```

**Update primary dashboard:**
- Remove links to deprecated dashboards
- Update launcher script
- Test all navigation

---

## 📋 DETAILED STEPS

### Step 1: Enhance Visual Coordination Dashboard (8031)

**Find where it's running:**
```bash
ps aux | grep 8031
lsof -i:8031
# Likely running from temp file
```

**Current implementation:** Find the actual source

**Enhancements needed:**
1. Add navigation sidebar with dashboard links
2. Add quick action buttons
3. Add alerts panel
4. Pull data from SSOT
5. Add auto-refresh (every 30 seconds)

---

### Step 2: Build Unified Financial Dashboard (8100)

**File: agents/services/unified-financial-dashboard/app/main.py**
```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "unified-financial-dashboard"}

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Fetch from multiple sources
    async with httpx.AsyncClient() as client:
        treasury = await client.get("http://localhost:8005/api/portfolio")
        growth = await client.get("http://localhost:8052/api/strategy")
        arena = await client.get("http://localhost:8035/api/simulations")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "treasury": treasury.json(),
        "growth": growth.json(),
        "arena": arena.json()
    })

@app.get("/api/unified-metrics")
async def unified_metrics():
    # Aggregate all financial data
    return {
        "total_capital": 373261,
        "monthly_yield": 0,
        "risk_score": "HIGH",
        "positions": {...},
        "deployment_progress": "0%"
    }
```

**File: agents/services/unified-financial-dashboard/app/templates/index.html**
- 3-column layout (Portfolio | 2X Strategy | Trading Arena)
- Unified metrics bar at top
- Quick actions at bottom
- Auto-refresh every 30s

---

### Step 3: Update All Links

**Primary Dashboard (8031):**
```html
<nav>
  <a href="http://localhost:8100">💰 Financial</a>
  <a href="http://localhost:8008">📋 Jobs</a>
  <a href="http://localhost:8010">🌐 FPAI Hub</a>
</nav>
```

**Launcher Script:**
```bash
# Remove deprecated dashboards
# open http://localhost:8026  # REMOVED
# open http://localhost:8030  # REMOVED

# Add new unified dashboard
open http://localhost:8100  # Unified Financial
```

---

## 🎯 CONSOLIDATION BENEFITS

### Resource Savings:
- **Before:** 8 processes, ~800MB RAM
- **After:** 4-5 processes, ~500MB RAM
- **Saved:** 3 processes, ~300MB RAM

### User Experience:
- **Before:** Jump between 8 dashboards, fragmented data
- **After:** Single primary entry point, unified views
- **Improvement:** 80% less context switching

### Maintenance:
- **Before:** Update 8 dashboards when data changes
- **After:** Update 4-5 dashboards, shared components
- **Improvement:** 40% less maintenance work

---

## ✅ SUCCESS CRITERIA

### Must Have:
- [ ] Visual Coordination Dashboard (8031) enhanced with links
- [ ] Unified Financial Dashboard (8100) operational
- [ ] All financial data accessible from single view
- [ ] Primary dashboard shows all key metrics
- [ ] Quick launcher opens 4-5 dashboards (not 8)

### Nice to Have:
- [ ] Auto-refresh on all dashboards
- [ ] Shared navigation component
- [ ] Mobile-responsive layouts
- [ ] Alert system integration
- [ ] Dark/light mode toggle

---

## 🚀 EXECUTION TIMELINE

**Phase 1 (Done):** 15 min ✅
**Phase 2 (Next):** 30 min - Enhance primary dashboard
**Phase 3 (After):** 60 min - Build unified financial
**Phase 4 (Then):** 15 min - Deprecate redundant
**Phase 5 (Finally):** 15 min - Cleanup & archive

**Total Time:** ~2 hours

**Priority:** Do you want me to execute Phase 2-5, or just leave the organization/documentation?

---

## 💬 YOUR CHOICE

**Option A: Just Organization (Done)** ✅
- DASHBOARDS directory created
- All dashboards documented
- Quick launcher ready
- Consolidation plan documented

**Option B: Full Consolidation (2 hours)**
- Execute Phases 2-5
- Build unified financial dashboard
- Enhance primary dashboard
- Deprecate redundant dashboards
- Complete cleanup

**Option C: Partial (30 min)**
- Just enhance primary dashboard with links
- Leave consolidation for later
- Quick win for navigation

**Which do you prefer?**

🌐⚡💎
