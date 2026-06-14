# PARALLEL BUILD COORDINATOR
**Treasury Arena v2.0 - Multi-Session Build**
**Total Build Time:** 1-2 hours (vs 36-42 hours human time)
**Sessions Required:** 3 Claude Code sessions

---

## 🎯 MISSION

Build the complete Treasury Arena system in **1-2 hours** using 3 parallel Claude Code sessions.

---

## 🚀 HOW TO LAUNCH

### **Step 1: Open 3 Claude Code Sessions**

Open 3 terminal windows and start 3 Claude Code sessions:

```bash
# Terminal 1 - Session A
cd /Users/jamessunheart/Development/agents/services/treasury-arena
claude

# Terminal 2 - Session B
cd /Users/jamessunheart/Development/agents/services/treasury-arena
claude

# Terminal 3 - Session C
cd /Users/jamessunheart/Development/agents/services/treasury-arena
claude
```

---

### **Step 2: Give Each Session Their Assignment**

**In Session A:**
```
Read BUILD_ASSIGNMENT_SESSION_A.md and execute it.

Build the SIMULATION_ENGINE per the specification.
You have 1-2 hours. Start immediately.
```

**In Session B:**
```
Read BUILD_ASSIGNMENT_SESSION_B.md and execute it.

Build the TRADING_ENGINE per the specification.
You have 1-2 hours. Start immediately.
```

**In Session C:**
```
Read BUILD_ASSIGNMENT_SESSION_C.md and execute it.

Complete ARENA_MANAGER_v2 event sourcing, then integrate all components.
You have 1 hour. Start after Sessions A & B complete.
```

---

## 📋 BUILD ASSIGNMENTS

### **Session A: SIMULATION_ENGINE**
**File:** `BUILD_ASSIGNMENT_SESSION_A.md`
**Time:** 1-2 hours
**Deliverable:** Complete simulation engine for backtesting

**What They Build:**
- src/simulation_engine.py
- src/data_sources.py
- src/simulation_results.py
- src/cli.py
- tests/test_simulation.py
- Database schema
- Documentation

**Specification:** SIMULATION_ENGINE_SPEC.md (lines 325-409)

---

### **Session B: TRADING_ENGINE**
**File:** `BUILD_ASSIGNMENT_SESSION_B.md`
**Time:** 1-2 hours
**Deliverable:** Complete trading engine with safety controls

**What They Build:**
- src/trading_engine.py
- src/protocols/base.py
- src/protocols/aave.py
- src/protocols/uniswap.py
- src/protocols/simulation.py
- src/validators.py
- tests/test_trading_engine.py
- tests/test_protocols.py
- Configuration files

**Specification:** TRADING_ENGINE_SPEC.md (lines 343-437)

---

### **Session C: ARENA_MANAGER_v2 + Integration**
**File:** `BUILD_ASSIGNMENT_SESSION_C.md`
**Time:** 1 hour
**Deliverable:** Event sourcing + full system integration

**What They Build:**
- src/events.py
- src/exceptions.py
- Enhanced arena_manager.py (event sourcing)
- tests/test_arena_v2.py
- Integration tests
- System status report

**Specification:** ARENA_MANAGER_v2_SPEC.md (lines 260-378)

---

## ⏱️ TIMELINE

**Parallel Execution (Sessions A & B):**
```
0:00 - Session A & B start building simultaneously
1:00 - Session A: SIMULATION_ENGINE ~50% complete
1:00 - Session B: TRADING_ENGINE ~50% complete
2:00 - Session A: SIMULATION_ENGINE complete ✅
2:00 - Session B: TRADING_ENGINE complete ✅
```

**Sequential Execution (Session C waits for A & B):**
```
2:00 - Session C starts ARENA_MANAGER_v2 event sourcing
2:30 - Session C: Event sourcing complete
2:30 - Session C: Integration testing starts
3:00 - Session C: Full system integration complete ✅
```

**Total Time: ~3 hours** (vs 36-42 hours with human developers)

---

## ✅ SUCCESS CRITERIA

**After All 3 Sessions Complete:**

1. **All Components Built:**
   - ✅ TREASURY_AGENT_v2 (bugs already fixed)
   - ✅ SIMULATION_ENGINE (Session A)
   - ✅ TRADING_ENGINE (Session B)
   - ✅ ARENA_MANAGER_v2 (Session C)

2. **All Tests Passing:**
   - Unit tests for each component
   - Integration tests
   - Full system test

3. **Deliverables Created:**
   - BUILD_COMPLETE_SIMULATION_ENGINE.md
   - BUILD_COMPLETE_TRADING_ENGINE.md
   - BUILD_COMPLETE_ARENA_MANAGER_v2.md
   - INTEGRATION_COMPLETE.md
   - SYSTEM_READY_REPORT.md

4. **Git Commits:**
   - Session A: "Treasury Arena: Simulation Engine Complete"
   - Session B: "Treasury Arena: Trading Engine Complete (Safety Verified)"
   - Session C: "Treasury Arena: Full System Integration Complete - Ready for Phase 1"

5. **Ready for Phase 1:**
   - Can spawn 50 agents in simulation
   - Can run 180-day backtest in <10 minutes
   - Can execute trades (simulation mode)
   - Can run evolution cycles
   - All events logged
   - Capital conserved

---

## 📊 MONITORING PROGRESS

**Check Session Status:**

```bash
# Session A status
ls -la src/simulation_engine.py src/data_sources.py

# Session B status
ls -la src/trading_engine.py src/protocols/

# Session C status
ls -la src/events.py src/exceptions.py

# All deliverables
ls -la BUILD_COMPLETE_*.md INTEGRATION_COMPLETE.md
```

**Run Tests:**
```bash
# After each session completes
pytest tests/test_simulation.py -v      # Session A
pytest tests/test_trading_engine.py -v  # Session B
pytest tests/test_arena_v2.py -v        # Session C
pytest tests/test_full_integration.py -v # Final integration
```

---

## 🔄 COORDINATION PROTOCOL

### **When Session A Completes:**
1. Create `BUILD_COMPLETE_SIMULATION_ENGINE.md`
2. Commit code to git
3. Signal completion (file marker or message)

### **When Session B Completes:**
1. Create `BUILD_COMPLETE_TRADING_ENGINE.md`
2. Commit code to git
3. Signal completion

### **When Sessions A & B Both Complete:**
1. Session C starts integration
2. Verifies both components work
3. Adds event sourcing
4. Runs full integration test

### **When Session C Completes:**
1. Create all completion documents
2. Final git commit
3. Announce: **SYSTEM READY FOR PHASE 1**

---

## 🚨 IF SOMETHING FAILS

**If Session A (Simulation) Fails:**
- Session B can continue (independent)
- Session A debugs and fixes
- Session C waits for both

**If Session B (Trading) Fails:**
- Session A can continue (independent)
- Session B debugs and fixes
- Session C waits for both

**If Session C (Integration) Fails:**
- Sessions A & B are still complete
- Session C debugs integration issues
- May need to iterate with A & B

**Coordination Rule:**
Each session can work independently. Session C only needs A & B outputs to integrate.

---

## 📄 REFERENCE FILES

**For All Sessions:**
- TREASURY_ARENA_BUILD_PLAN.md - Master plan
- TREASURY_ARENA_ANALYSIS.md - Complete analysis
- README.md - Project overview

**Session-Specific:**
- Session A: SIMULATION_ENGINE_SPEC.md
- Session B: TRADING_ENGINE_SPEC.md
- Session C: ARENA_MANAGER_v2_SPEC.md

**Existing Code:**
- src/agent.py - TreasuryAgent (bugs fixed)
- src/arena_manager.py - ArenaManager (validation added)

---

## 🎯 FINAL VALIDATION

**Before declaring READY FOR PHASE 1:**

Run this complete validation:

```bash
# 1. All files exist
ls -la src/simulation_engine.py
ls -la src/trading_engine.py
ls -la src/events.py

# 2. All tests pass
pytest tests/ -v

# 3. Can spawn agents
python -c "from src.arena_manager import ArenaManager; arena = ArenaManager(); print('✅ Arena spawns')"

# 4. Can run simulation
python -m src.simulation_engine --help

# 5. Git history clean
git log --oneline -5

# 6. Deliverables present
ls -la BUILD_COMPLETE_*.md SYSTEM_READY_REPORT.md
```

If all ✅, system is **READY FOR PHASE 1 DEPLOYMENT**.

---

## 🚀 LAUNCH COMMAND

**To Start All 3 Sessions:**

```bash
# Quick launch (paste in terminal)
echo "Session A: Build SIMULATION_ENGINE"
echo "Session B: Build TRADING_ENGINE"
echo "Session C: Complete ARENA_MANAGER_v2 + Integrate"
echo ""
echo "Give each session their BUILD_ASSIGNMENT_SESSION_X.md file"
echo "Estimated completion: 3 hours"
echo ""
echo "GO! ⚡💎🏛️"
```

---

**STATUS: READY TO LAUNCH** ✅

All assignment files created. All specifications complete. All coordination protocols defined.

**Launch 3 Claude Code sessions and build in parallel!**

⚡💎🏛️ **$373K → $5T through parallel AI construction**
