# BUILD ASSIGNMENT - SESSION C
**Component:** ARENA_MANAGER_v2 (Completion) + Integration
**Estimated Time:** 1 hour
**Priority:** HIGH (Integrates all components)

---

## 🎯 YOUR MISSION

Complete **Arena Manager v2** by adding event sourcing, then integrate all 3 components into a working system.

---

## 📋 SPECIFICATION REFERENCE

**Primary Spec:** `/Users/jamessunheart/Development/agents/services/treasury-arena/ARENA_MANAGER_v2_SPEC.md`

**Read Lines 260-378** for complete build instructions (PROMPT A - BUILDER)

---

## ✅ ALREADY COMPLETE

From previous session (bugs fixed):
- ✅ Capital allocation validation (lines 174-186 in arena_manager.py)
- ✅ Error isolation - safe_run_evolution() (lines 392-406)

---

## 🔧 WHAT TO BUILD

Add these enhancements to `/Users/jamessunheart/Development/agents/services/treasury-arena/`:

1. **src/events.py** - Event types and schemas (NEW)
   - Event classes (AgentSpawned, CapitalAllocated, etc.)
   - Event validation
   - Event serialization

2. **src/exceptions.py** - Custom exceptions (NEW)
   - AllocationError
   - CapitalConservationError
   - ValidationError

3. **src/arena_manager.py** - Add event sourcing (ENHANCE)
   - emit_event() method
   - verify_capital_conservation() method
   - replay_events() method
   - get_capital_allocation_breakdown() method
   - All state changes emit events

4. **tests/test_arena_v2.py** - Comprehensive tests (NEW)
   - Test allocation validation
   - Test event sourcing
   - Test capital conservation
   - Test error isolation
   - Test event replay

5. **migrations/002_add_events.sql** - Database migration (NEW)
   - Create events table
   - Create arena_state table
   - Create capital_ledger table

6. **docs/ARENA_V2_MIGRATION.md** - Migration guide (NEW)

---

## 📊 DATABASE SCHEMA

From ARENA_MANAGER_v2_SPEC.md lines 88-138:

Add 3 new tables to SQLite:
- events (event_id, event_type, agent_id, timestamp, data, caused_by)
- arena_state (derived from events)
- capital_ledger (validates conservation)

**See spec lines 88-138 for exact schema.**

---

## 🎯 EVENT SOURCING IMPLEMENTATION

From ARENA_MANAGER_v2_SPEC.md lines 307-323:

### **Core Event Emission:**
```python
def emit_event(self, event_type: str, agent_id: Optional[str], data: Dict) -> str:
    event_id = str(uuid.uuid4())

    # Write to database
    self.db.execute(
        "INSERT INTO events (event_id, event_type, agent_id, data) VALUES (?, ?, ?, ?)",
        (event_id, event_type, agent_id, json.dumps(data))
    )

    # Log
    logger.info(event_type, event_id=event_id, agent_id=agent_id, data=data)

    return event_id
```

### **Events to Emit:**
- spawn_agent() → AgentSpawned
- allocate_capital() → CapitalAllocated
- kill_underperformers() → AgentKilled
- graduate_to_arena() → AgentGraduated
- run_evolution_cycle() → EvolutionCycleComplete

---

## ⚠️ CRITICAL REQUIREMENTS

From ARENA_MANAGER_v2_SPEC.md lines 370-377:

- ✅ Thread-safe capital allocation (use threading.Lock)
- ✅ All state changes emit events
- ✅ Capital validation before allocation (ALREADY DONE)
- ✅ Event log persisted to SQLite
- ✅ Type hints on everything
- ✅ Comprehensive error handling

---

## ✅ SUCCESS CRITERIA

From ARENA_MANAGER_v2_SPEC.md lines 224-255:

**Functional:**
- [ ] Capital allocation validates total ≤ arena_capital (ALREADY DONE)
- [ ] All capital movements logged as events
- [ ] Can replay event history for audit
- [ ] Capital conservation verified (sum equals total)
- [ ] Evolution cycle errors don't crash system (ALREADY DONE)
- [ ] Event log persisted to SQLite

**Technical:**
- [ ] Thread-safe capital allocation
- [ ] Event sourcing implemented correctly
- [ ] Capital ledger balances
- [ ] Type hints on all methods
- [ ] Comprehensive error handling

**Testing:**
- [ ] Test allocation overflow rejected (ALREADY WORKS)
- [ ] Test capital conservation verified
- [ ] Test events persist correctly
- [ ] Test event replay accurate
- [ ] Integration test: Full evolution cycle with events
- [ ] Stress test: 1000 events written correctly

**Validation:**
- [ ] Total allocated capital never exceeds arena_capital
- [ ] Event log has no gaps (sequential)
- [ ] Capital ledger sum = 0 (conservation)
- [ ] Can reconstruct current state from events alone

---

## 🧪 VERIFICATION

After building, verify using **PROMPT B** from ARENA_MANAGER_v2_SPEC.md lines 381-494.

**Critical Checks:**
- [ ] Capital validation present (ALREADY DONE)
- [ ] Event sourcing implemented
- [ ] Error isolation added (ALREADY DONE)
- [ ] Capital conservation check
- [ ] Events persisted to database
- [ ] Thread-safe
- [ ] All tests pass

---

## 🔗 INTEGRATION TESTING

After completing Arena Manager v2, integrate with components from Sessions A & B:

### **Integration Test Sequence:**

1. **Verify All Components Built:**
   - [ ] SIMULATION_ENGINE complete (Session A)
   - [ ] TRADING_ENGINE complete (Session B)
   - [ ] ARENA_MANAGER_v2 complete (Session C)

2. **Create Integration Test:**
   - File: `tests/test_full_integration.py`
   - Test full workflow:
     ```python
     # 1. Spawn 10 agents in simulation
     # 2. Run 30-day backtest
     # 3. Graduate top performers
     # 4. Allocate capital (validate)
     # 5. Execute trades (simulation mode)
     # 6. Run evolution cycle
     # 7. Verify events logged
     # 8. Verify capital conservation
     ```

3. **Run Full System Test:**
   ```bash
   pytest tests/test_full_integration.py -v
   ```

4. **Create System Status Report:**
   - File: `SYSTEM_READY_REPORT.md`
   - List all components complete
   - Show all tests passing
   - Ready for Phase 1 deployment

---

## 📤 DELIVERABLES

**When Complete:**
1. Create file: `BUILD_COMPLETE_ARENA_MANAGER_v2.md`
2. Create file: `INTEGRATION_COMPLETE.md`
3. Create file: `SYSTEM_READY_REPORT.md`
4. List all files created
5. Paste verification results
6. Show all integration tests passing
7. Commit to git with message: "Treasury Arena: Full System Integration Complete - Ready for Phase 1"

---

## 🎯 COORDINATE WITH OTHER SESSIONS

**Wait for Sessions A & B to complete:**
- Session A: SIMULATION_ENGINE
- Session B: TRADING_ENGINE

**Then integrate all 3 components and verify full system works.**

---

## 🚀 FINAL VALIDATION

Before declaring system ready:

1. **All 4 components complete:**
   - ✅ TREASURY_AGENT_v2 (bugs fixed)
   - ✅ SIMULATION_ENGINE (Session A)
   - ✅ TRADING_ENGINE (Session B)
   - ✅ ARENA_MANAGER_v2 (Session C)

2. **All tests pass:**
   - Unit tests
   - Integration tests
   - Full system test

3. **Ready for Phase 1:**
   - Can spawn 50 agents
   - Can run 180-day backtest
   - Can execute trades (simulation mode)
   - Can run evolution cycles
   - All events logged
   - Capital conserved

---

**START IMMEDIATELY** - Use ARENA_MANAGER_v2_SPEC.md PROMPT A (lines 260-378) as your complete build guide.

⚡💎🏛️ **Complete event sourcing, integrate everything, ship Phase 1**
