# ARENA_MANAGER_v2_SPEC.md
**Treasury Arena - Arena Manager (Enhanced)**
**Version:** 2.0
**Created:** November 15, 2025
**Priority:** TIER 1 - Adds Critical Validation & Event Sourcing

---

## 1. 🎯 PURPOSE

The Arena Manager orchestrates agent competition with **validated capital allocation**, **event sourcing for audit trail**, and **error isolation** to prevent cascading failures.

**TIER 1 IMPACT:**
Prevents capital loss through:
1. Validation that allocated capital never exceeds total capital
2. Event sourcing for complete audit trail (regulatory compliance)
3. Error isolation preventing one agent from crashing the system

**Problem Solved:**
Current arena_manager.py allocates capital without checking totals. Could allocate $250K when only $200K available. This v2 adds validation and auditability.

---

## 2. 📋 CORE REQUIREMENTS

**As an Arena Coordinator, I must be able to:**
1. Allocate capital to agents with validation (total ≤ arena_capital)
2. Track all capital movements through event sourcing
3. Recover from agent errors without stopping arena
4. Audit complete history of births, deaths, allocations

**As a Financial Auditor, I must be able to:**
5. Replay all capital movements from event log
6. Verify capital conservation (no money created/destroyed)
7. See who allocated what capital when and why
8. Detect anomalies in allocation patterns

**As a System Monitor, I must be able to:**
9. See real-time capital allocation status
10. Track allocation overflow attempts
11. Monitor agent health across all pools
12. Review evolution cycle outcomes

---

## 3. 🎨 USER INTERFACE

**No UI required - Python class library**

Event log viewable via CLI:
```bash
$ python -m src.arena_manager events --tail 20

2025-11-15 10:23:45 | AgentSpawned | agent-abc123 | DeFi-Yield-Farmer | virtual=$10,000
2025-11-15 10:24:12 | CapitalAllocated | agent-abc123 | $1,000 | tier=proving
2025-11-15 10:25:03 | AgentGraduated | agent-abc123 | proving→active
2025-11-15 10:26:30 | CapitalAllocated | agent-abc123 | $15,000 | tier=elite
```

---

## 4. 🔌 INTEGRATIONS

**Internal Integrations:**
- Treasury Agent v2: Manages agent instances
- Simulation Engine: Runs agents in backtest
- Trading Engine: Executes real trades
- Dashboard (future): Displays arena status

**No External Integrations**

---

## 5. 🔧 TECHNICAL STACK

**Default Stack:**
- Python 3.11+ (type hints)
- SQLite (event log storage)
- structlog (logging)

**Additional Requirements:**
- threading.Lock (thread-safe capital allocation)

---

## 6. 📊 DATABASE SCHEMA

**Event Sourcing Schema:**

```sql
-- Table: events
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,  -- UUID
    event_type TEXT NOT NULL,  -- AgentSpawned, CapitalAllocated, etc.
    agent_id TEXT,  -- Null for system events
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSON NOT NULL,  -- Event-specific data
    caused_by TEXT,  -- Previous event_id that triggered this
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_agent ON events(agent_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);

-- Table: arena_state (derived from events)
CREATE TABLE arena_state (
    id INTEGER PRIMARY KEY,  -- Only 1 row
    total_capital REAL NOT NULL,
    stable_reserve REAL NOT NULL,
    arena_capital REAL NOT NULL,
    allocated_capital REAL NOT NULL,  -- Sum of all agent allocations
    available_capital REAL NOT NULL,  -- arena_capital - allocated_capital
    agents_active INTEGER NOT NULL,
    agents_proving INTEGER NOT NULL,
    agents_simulating INTEGER NOT NULL,
    agents_dead INTEGER NOT NULL,
    last_evolution_cycle TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: capital_ledger (validates conservation)
CREATE TABLE capital_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    agent_id TEXT,
    old_capital REAL NOT NULL,
    new_capital REAL NOT NULL,
    delta REAL NOT NULL,  -- new - old
    reason TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(event_id)
);

CREATE INDEX idx_ledger_agent ON capital_ledger(agent_id);
CREATE INDEX idx_ledger_timestamp ON capital_ledger(timestamp);
```

---

## 7. 🎯 API ENDPOINTS

**No HTTP endpoints** - Python class interface only.

**Enhanced Methods:**

```python
class ArenaManagerV2:
    
    def allocate_capital_validated(
        self
    ) -> Dict[str, float]:
        """
        Allocate capital with validation and event logging.
        
        Returns:
            Dict mapping agent_id to capital amount
            
        Raises:
            AllocationError: If total allocation > arena_capital
        """
    
    def emit_event(
        self,
        event_type: str,
        agent_id: Optional[str],
        data: Dict
    ) -> str:
        """
        Emit event to event log.
        
        Returns:
            event_id (UUID)
        """
    
    def verify_capital_conservation(self) -> bool:
        """
        Verify total capital unchanged.
        
        Returns:
            True if sum(allocations) == total_capital
        """
    
    def safe_run_evolution(self) -> Tuple[bool, Optional[Exception]]:
        """
        Run evolution cycle with error isolation.
        
        Returns:
            (success, error)
        """
    
    def replay_events(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        Replay events for audit.
        
        Returns:
            List of events
        """
    
    def get_capital_allocation_breakdown(self) -> Dict:
        """
        Get detailed breakdown of capital allocation.
        
        Returns:
            {
                'total': 373261,
                'stable_reserve': 163261,
                'arena_capital': 200000,
                'allocated': 185000,
                'available': 15000,
                'by_tier': {'elite': 111000, 'active': 55500, 'challenger': 18500},
                'by_agent': {'agent-123': 15000, ...}
            }
        """
```

---

## 8. ✅ SUCCESS CRITERIA

**Functional Requirements:**
- [ ] Capital allocation validates total ≤ arena_capital
- [ ] All capital movements logged as events
- [ ] Can replay event history for audit
- [ ] Capital conservation verified (sum equals total)
- [ ] Evolution cycle errors don't crash system
- [ ] Event log persisted to SQLite

**Technical Requirements:**
- [ ] Thread-safe capital allocation (using locks)
- [ ] Event sourcing implemented correctly
- [ ] Capital ledger balances
- [ ] Type hints on all methods
- [ ] Comprehensive error handling
- [ ] Logging with structlog

**Testing Requirements:**
- [ ] Unit test: Allocation overflow rejected
- [ ] Unit test: Capital conservation verified
- [ ] Unit test: Events persist correctly
- [ ] Unit test: Event replay accurate
- [ ] Integration test: Full evolution cycle with events
- [ ] Stress test: 1000 events written correctly

**Validation Requirements:**
- [ ] Total allocated capital never exceeds arena_capital
- [ ] Event log has no gaps (sequential)
- [ ] Capital ledger sum = 0 (conservation)
- [ ] Can reconstruct current state from events alone

---

## 9. 🚀 APPRENTICE EXECUTION PROMPTS

### PROMPT A - BUILDER (For Claude)

```
I need to build Arena Manager v2 - adding capital validation and event sourcing.

SPECIFICATION:
[Upload: ARENA_MANAGER_v2_SPEC.md]

CURRENT IMPLEMENTATION:
[Upload: arena_manager.py - current version]

CONTEXT FILES:
[Upload: TREASURY_AGENT_v2_SPEC.md - fixed agent]
[Upload: CODE_STANDARDS.md]
[Upload: SECURITY_REQUIREMENTS.md]

ENHANCEMENTS TO ADD:

**Enhancement 1: Capital Validation**
Current code (arena_manager.py line 245):
```python
for agent in elite:
    agent.real_capital = elite_capital_per_agent  # No validation!
    allocations[agent.id] = elite_capital_per_agent
```

Fix: Validate BEFORE allocating:
```python
# Calculate total allocation first
total_allocated = (
    len(elite) * elite_capital_per_agent +
    len(active) * active_capital_per_agent +
    len(challengers) * challenger_capital_per_agent
)

# Validate
if total_allocated > self.arena_capital:
    raise AllocationError(
        f"Allocation overflow: ${total_allocated:,.0f} > ${self.arena_capital:,.0f}"
    )

# Then allocate
for agent in elite:
    agent.real_capital = elite_capital_per_agent
    allocations[agent.id] = elite_capital_per_agent
```

**Enhancement 2: Event Sourcing**
Add event emission for all state changes:
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

**Enhancement 3: Error Isolation**
Wrap evolution cycle:
```python
def safe_run_evolution(self) -> Tuple[bool, Optional[Exception]]:
    try:
        self.run_evolution_cycle()
        return True, None
    except Exception as e:
        logger.error("Evolution cycle failed", error=str(e), stack=traceback.format_exc())
        return False, e
```

Please generate:

1. **src/arena_manager_v2.py** - Enhanced arena manager
   - Add capital validation
   - Add event sourcing (all state changes)
   - Add error isolation
   - Add capital conservation check
   - All existing functionality preserved

2. **src/events.py** - Event types and schemas
   - Event classes (AgentSpawned, CapitalAllocated, etc.)
   - Event validation
   - Event serialization

3. **src/exceptions.py** - Custom exceptions
   - AllocationError
   - CapitalConservationError
   - ValidationError

4. **tests/test_arena_v2.py** - Comprehensive tests
   - Test allocation validation
   - Test event sourcing
   - Test capital conservation
   - Test error isolation
   - Test event replay

5. **migrations/001_add_events.sql** - Database migration
   - Create events table
   - Create arena_state table
   - Create capital_ledger table

6. **docs/ARENA_V2_MIGRATION.md** - Migration guide

REQUIREMENTS:
- Thread-safe capital allocation (use threading.Lock)
- All state changes emit events
- Capital validation before allocation
- Event log persisted to SQLite
- Type hints on everything
- Comprehensive error handling

Generate complete code with no TODOs.
```

### PROMPT B - VERIFIER (For Gemini)

```
Verify that Arena Manager v2 adds all critical enhancements.

SPECIFICATION:
[Upload: ARENA_MANAGER_v2_SPEC.md]

ORIGINAL CODE:
[Upload: arena_manager.py - v1]

NEW CODE:
[Upload: arena_manager_v2.py]

CRITICAL ENHANCEMENT VERIFICATION:

**Enhancement 1: Capital Validation**
❌ OLD (No validation):
```python
for agent in elite:
    agent.real_capital = elite_capital_per_agent
```

✅ MUST HAVE:
```python
total_allocated = sum_of_all_allocations()
if total_allocated > self.arena_capital:
    raise AllocationError("Overflow")

# Then allocate
for agent in elite:
    agent.real_capital = elite_capital_per_agent
```

**Verification:**
1. Find allocate_capital method
2. Verify total calculated before allocation
3. Verify overflow raises AllocationError
4. Verify test proves overflow rejected

**Enhancement 2: Event Sourcing**
✅ MUST HAVE:
- emit_event() method
- Events written to SQLite
- All state changes emit events:
  * spawn_agent() → AgentSpawned
  * allocate_capital() → CapitalAllocated
  * kill_underperformers() → AgentKilled
  * graduate_to_arena() → AgentGraduated

**Verification:**
1. Find emit_event() method
2. Verify writes to events table
3. Verify all state changes call emit_event()
4. Check event_id is UUID
5. Verify test proves events persist

**Enhancement 3: Error Isolation**
✅ MUST HAVE:
```python
def safe_run_evolution():
    try:
        self.run_evolution_cycle()
        return True, None
    except Exception as e:
        logger.error("Evolution failed", error=e)
        return False, e
```

**Verification:**
1. Find safe_run_evolution() method
2. Verify try/except wraps evolution
3. Verify returns (success, error) tuple
4. Verify test proves error doesn't crash

**CHECKLIST:**

**Enhancements:**
- [ ] Capital validation present: ✅/❌
- [ ] Event sourcing implemented: ✅/❌
- [ ] Error isolation added: ✅/❌
- [ ] Capital conservation check: ✅/❌

**Database:**
- [ ] events table created
- [ ] arena_state table created
- [ ] capital_ledger table created
- [ ] Indexes present

**Code Quality:**
- [ ] Thread-safe (Lock used)
- [ ] Type hints present
- [ ] Logging comprehensive
- [ ] Error messages clear

**Testing:**
- [ ] Test allocation validation
- [ ] Test event persistence
- [ ] Test capital conservation
- [ ] Test error isolation
- [ ] All tests pass

**Critical Issues:**
- [ ] Can allocate more than available: CRITICAL
- [ ] Events not persisted: MAJOR
- [ ] Not thread-safe: MAJOR
- [ ] Errors crash system: CRITICAL

OUTPUT:
✅ PASS - All enhancements working
❌ FAIL - [List issues with severity]

This is financial infrastructure - be thorough.
```

---

## METADATA

**Complexity Assessment:**
- Sprint Size: 2 (8-12 hours)
- Difficulty: Medium
- Reasoning: Event sourcing + validation logic + threading

**Dependencies:**
- Required: Treasury Agent v2 (fixed version)
- Blocks: Phase 2 deployment (need validation before $10K)

**Blockers:**
- None

**Recommended Developer Level:**
- Level: Intermediate
- Reasoning: Event sourcing pattern + thread safety

**Estimated Timeline:**
- Build: 8-10 hours
- Verification: 2-3 hours
- Total: 10-13 hours

**Risk if Not Fixed:**
- CRITICAL: Could allocate $250K when only $200K exists
- MAJOR: No audit trail (regulatory problem)
- MAJOR: One agent error kills entire system

---

**END ARENA_MANAGER_v2_SPEC.md**

*Must have before Phase 2 - Financial integrity depends on validation*
