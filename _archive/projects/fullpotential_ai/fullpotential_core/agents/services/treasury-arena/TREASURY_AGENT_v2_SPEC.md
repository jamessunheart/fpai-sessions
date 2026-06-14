# TREASURY_AGENT_v2_SPEC.md
**Treasury Arena - Agent System (Fixed)**
**Version:** 2.0
**Created:** November 15, 2025
**Priority:** TIER 1 - Fixes Critical Bugs in Current Implementation

---

## 1. 🎯 PURPOSE

The Treasury Agent system provides the base class for all trading strategies competing in the arena, with **fixed fitness calculation** and **validated capital tracking**.

**TIER 1 IMPACT:**
Fixes 3 critical bugs that would cause capital loss in production:
1. Fitness calculated AFTER being recorded (circular reference)
2. Capital updates without validation (potential overspending)
3. No error isolation (one crash kills all agents)

**Problem Solved:**
Current agent.py has fitness bug that makes metrics unreliable. This v2 fixes all issues before Phase 2 ($10K real capital deployment).

---

## 2. 📋 CORE REQUIREMENTS

**As a Trading Strategy, I must be able to:**
1. Calculate fitness score accurately (BEFORE recording in history)
2. Validate capital changes (prevent overspending or negative balances)
3. Execute strategies safely (errors don't crash other agents)
4. Track performance metrics reliably (Sharpe, drawdown, win rate)

**As an Arena Manager, I must be able to:**
5. Trust that agent fitness scores are correct
6. Know that capital allocations are validated
7. Recover from agent crashes without system failure
8. Audit all capital movements

**As a System Monitor, I must be able to:**
9. See real-time capital validation errors
10. Track agent health status
11. Review trade execution history
12. Verify capital conservation (total capital unchanged)

---

## 3. 🎨 USER INTERFACE

**No UI required - Python class library**

---

## 4. 🔌 INTEGRATIONS

**Internal Integrations:**
- Arena Manager: Manages agent lifecycle
- Simulation Engine: Runs agents in backtest mode
- Trading Engine: Executes actual trades
- Dashboard (future): Displays agent metrics

**No External Integrations**

---

## 5. 🔧 TECHNICAL STACK

**Default Stack:**
- Python 3.11+ (type hints)
- numpy (calculations)
- No database needed (in-memory)
- structlog (logging)

---

## 6. 📊 DATABASE SCHEMA

**No database** - Agent state is in-memory only.

Capital persistence handled by Arena Manager's database.

---

## 7. 🎯 API ENDPOINTS

**No HTTP endpoints** - Python class interface only.

**Core Methods:**

```python
class TreasuryAgent:
    
    def execute_strategy(
        self,
        market_data: Dict
    ) -> List[Dict]:
        """Execute trading strategy safely (with error handling)"""
    
    def calculate_fitness(self) -> float:
        """Calculate multi-factor fitness score"""
    
    def validate_capital_change(
        self,
        old_capital: float,
        new_capital: float
    ) -> bool:
        """Validate capital change is legal"""
    
    def record_performance(
        self,
        capital: float,
        pnl: float,
        trades: List[Dict]
    ):
        """Record performance AFTER calculating fitness"""
    
    def safe_execute(
        self,
        market_data: Dict
    ) -> Tuple[List[Dict], Optional[Exception]]:
        """Execute strategy with error isolation"""
```

---

## 8. ✅ SUCCESS CRITERIA

**Functional Requirements:**
- [ ] Fitness calculated BEFORE being added to performance_history
- [ ] Capital changes validated (no negative, no overspending)
- [ ] Agent errors isolated (try/except in safe_execute)
- [ ] All performance metrics accurate (Sharpe, drawdown, win rate)
- [ ] Capital conservation verified (sum of changes = 0)

**Technical Requirements:**
- [ ] Type hints on all methods
- [ ] Comprehensive error handling
- [ ] Logging with structlog
- [ ] No circular dependencies in calculations
- [ ] Thread-safe capital updates (using locks if needed)

**Testing Requirements:**
- [ ] Unit test: Fitness calculation order
- [ ] Unit test: Capital validation rejects negative
- [ ] Unit test: Capital validation rejects overspending
- [ ] Unit test: Agent crash doesn't propagate
- [ ] Integration test: Full strategy execution cycle

**Validation Requirements:**
- [ ] Fitness score never uses self.fitness_score before calculation
- [ ] Capital never goes negative
- [ ] Sum of all agent capital equals total allocated capital
- [ ] Exception in execute_strategy() returns error, doesn't crash

---

## 9. 🚀 APPRENTICE EXECUTION PROMPTS

### PROMPT A - BUILDER (For Claude)

```
I need to build Treasury Agent v2 - fixing critical bugs in the current implementation.

SPECIFICATION:
[Upload: TREASURY_AGENT_v2_SPEC.md]

CURRENT IMPLEMENTATION (BUGGY):
[Upload: agent.py - current version with bugs]

CONTEXT FILES:
[Upload: CODE_STANDARDS.md]
[Upload: SECURITY_REQUIREMENTS.md]

CRITICAL BUGS TO FIX:

**Bug 1: Fitness Calculation Order**
Current code (agent.py line 130):
```python
self.performance_history.append({
    'fitness': self.fitness_score  # Uses OLD fitness!
})
```

Fix: Calculate fitness FIRST, then record it:
```python
new_fitness = self.calculate_fitness()
self.performance_history.append({
    'fitness': new_fitness  # Uses NEW fitness
})
```

**Bug 2: No Capital Validation**
Current code just sets capital without validation:
```python
self.real_capital = elite_capital_per_agent
```

Fix: Add validation method:
```python
def validate_capital_change(self, old: float, new: float) -> bool:
    if new < 0:
        raise ValueError("Capital cannot be negative")
    if new > old * 10:  # Sanity check
        raise ValueError("Capital increase too large")
    return True
```

**Bug 3: No Error Isolation**
Current code:
```python
trades = agent.execute_strategy(market_data)  # Can crash!
```

Fix: Wrap in safe execution:
```python
def safe_execute(self, market_data: Dict) -> Tuple[List[Dict], Optional[Exception]]:
    try:
        trades = self.execute_strategy(market_data)
        return trades, None
    except Exception as e:
        logger.error(f"Agent {self.id} crashed", error=str(e))
        return [], e
```

Please generate:

1. **src/agent_v2.py** - Fixed TreasuryAgent class
   - Fix fitness calculation order
   - Add capital validation
   - Add error isolation (safe_execute)
   - Add capital audit logging
   - All existing functionality preserved

2. **src/strategies_v2.py** - Updated strategy implementations
   - DeFiYieldFarmer (updated)
   - TacticalTrader (updated)
   - Both use safe_execute pattern

3. **tests/test_agent_v2.py** - Comprehensive tests
   - Test fitness calculation order (verify bug is fixed)
   - Test capital validation (negative rejected)
   - Test capital validation (overspending rejected)
   - Test error isolation (exception doesn't propagate)
   - Test capital conservation
   - Test all performance metrics

4. **docs/AGENT_V2_MIGRATION.md** - Migration guide
   - Breaking changes from v1
   - How to update existing code
   - Verification checklist

REQUIREMENTS:
- All bugs fixed with unit tests proving they're fixed
- Backward compatible where possible
- Type hints on everything
- Comprehensive logging
- Error messages that explain what went wrong

Generate complete code with no TODOs.
```

### PROMPT B - VERIFIER (For Gemini)

```
Verify that Treasury Agent v2 fixes all critical bugs.

SPECIFICATION:
[Upload: TREASURY_AGENT_v2_SPEC.md]

ORIGINAL BUGGY CODE:
[Upload: agent.py - v1 with bugs]

NEW FIXED CODE:
[Upload: agent_v2.py - supposedly fixed]

CRITICAL BUG VERIFICATION:

**Bug 1: Fitness Calculation Order**
❌ OLD BUG:
```python
self.performance_history.append({
    'fitness': self.fitness_score  # Wrong!
})
# Then calculate_fitness() called
```

✅ MUST BE FIXED TO:
```python
new_fitness = self.calculate_fitness()  # Calculate FIRST
self.performance_history.append({
    'fitness': new_fitness  # Then record
})
```

**Verification Steps:**
1. Find record_performance() method
2. Verify calculate_fitness() called BEFORE append
3. Verify fitness stored is the newly calculated value
4. Check test proves this with assertion

**Bug 2: Capital Validation**
❌ OLD BUG:
```python
agent.real_capital = new_value  # No validation!
```

✅ MUST BE FIXED WITH:
```python
def validate_capital_change(self, old, new):
    if new < 0:
        raise ValueError("Negative capital")
    if new > old * 10:
        raise ValueError("Suspiciously large increase")
    return True

# Usage:
self.validate_capital_change(self.real_capital, new_capital)
self.real_capital = new_capital
```

**Verification Steps:**
1. Find validate_capital_change() method
2. Verify it raises ValueError for negative
3. Verify it raises ValueError for >10x increase
4. Verify it's called before all capital updates
5. Check tests prove validation works

**Bug 3: Error Isolation**
❌ OLD BUG:
```python
trades = agent.execute_strategy(data)  # Crashes propagate
```

✅ MUST BE FIXED WITH:
```python
def safe_execute(self, market_data):
    try:
        return self.execute_strategy(market_data), None
    except Exception as e:
        logger.error("Agent crashed", error=e)
        return [], e
```

**Verification Steps:**
1. Find safe_execute() method
2. Verify it has try/except
3. Verify it returns (trades, error) tuple
4. Verify it logs errors
5. Check test proves crash doesn't propagate

**CHECKLIST:**

**Bug Fixes:**
- [ ] Fitness calculation BEFORE recording: ✅/❌
- [ ] Capital validation present: ✅/❌
- [ ] Error isolation implemented: ✅/❌

**Code Quality:**
- [ ] Type hints on all methods
- [ ] Logging with structlog
- [ ] No circular dependencies
- [ ] Thread-safe if needed

**Testing:**
- [ ] Test proves fitness bug is fixed
- [ ] Test proves capital validation works
- [ ] Test proves error isolation works
- [ ] All tests pass

**Critical Issues:**
- [ ] Fitness still calculated wrong: CRITICAL
- [ ] Capital can go negative: CRITICAL
- [ ] Errors can crash system: CRITICAL

OUTPUT:
✅ PASS - All bugs fixed, tests prove it
❌ FAIL - [List unfixed bugs with line numbers]

Be extremely thorough - these bugs could lose $200K.
```

---

## METADATA

**Complexity Assessment:**
- Sprint Size: 1 (4-6 hours)
- Difficulty: Simple
- Reasoning: Fixing existing code, not building from scratch

**Dependencies:**
- Required: None (standalone fixes)
- Blocks: Phase 2 deployment (can't risk $10K with bugs)

**Blockers:**
- None

**Recommended Developer Level:**
- Level: Intermediate
- Reasoning: Need to understand fitness calculations and validation logic

**Estimated Timeline:**
- Build: 4 hours
- Verification: 2 hours
- Total: 6 hours

**Risk if Not Fixed:**
- CRITICAL: Fitness scores unreliable → bad agents survive
- CRITICAL: Capital can go negative → system bankruptcy
- CRITICAL: Agent crash kills arena → total system failure

---

**END TREASURY_AGENT_v2_SPEC.md**

*Must fix before Phase 2 - These bugs would lose money*
