# BUILD ASSIGNMENT - SESSION B
**Component:** TRADING_ENGINE
**Estimated Time:** 1-2 hours
**Priority:** HIGH (Enables Phase 2 real trading)

---

## 🎯 YOUR MISSION

Build the **Trading Engine** that executes real trades on DeFi protocols with comprehensive safety controls.

---

## 📋 SPECIFICATION REFERENCE

**Primary Spec:** `/Users/jamessunheart/Development/SERVICES/treasury-arena/TRADING_ENGINE_SPEC.md`

**Read Lines 343-437** for complete build instructions (PROMPT A - BUILDER)

---

## 🔧 WHAT TO BUILD

Generate these 10 files in `/Users/jamessunheart/Development/SERVICES/treasury-arena/`:

1. **src/trading_engine.py** - Core trading engine
   - TradingEngine class
   - submit_trade() method
   - execute_trade() method with retries
   - validate_trade() method (position limits, slippage, capital)
   - emergency_stop() / emergency_resume()
   - Async execution

2. **src/protocols/base.py** - Protocol interface
   - ProtocolAdapter base class
   - Standard methods: deposit, withdraw, swap, stake
   - Error handling

3. **src/protocols/aave.py** - Aave integration
   - AaveAdapter(ProtocolAdapter)
   - deposit() - deposit assets to Aave
   - withdraw() - withdraw from Aave
   - get_apy() - fetch current APY
   - Uses web3.py

4. **src/protocols/uniswap.py** - Uniswap integration
   - UniswapAdapter(ProtocolAdapter)
   - swap() - execute token swap
   - estimate_output() - calculate expected output
   - calculate_slippage()
   - Uses web3.py

5. **src/protocols/simulation.py** - Simulation protocol
   - SimulationAdapter(ProtocolAdapter)
   - Executes virtual trades (no blockchain)
   - Returns mock results
   - For testing and Phase 1

6. **src/validators.py** - Trade validation
   - PositionLimitValidator
   - SlippageValidator
   - CapitalValidator
   - CompositeValidator

7. **tests/test_trading_engine.py** - Comprehensive tests
   - Test trade submission
   - Test trade validation
   - Test execution (mocked)
   - Test capital updates
   - Test emergency stop

8. **tests/test_protocols.py** - Protocol tests
   - Test Aave adapter (mocked)
   - Test Uniswap adapter (mocked)
   - Test simulation adapter

9. **configs/protocols.json** - Protocol config
   - Contract addresses
   - Gas limits
   - Slippage tolerances

10. **docs/TRADING_ENGINE_GUIDE.md** - Usage guide

---

## ⚠️ CRITICAL REQUIREMENTS

From TRADING_ENGINE_SPEC.md lines 419-434:

- ✅ All blockchain interactions async (web3.py AsyncWeb3)
- ✅ Retry logic for transient failures (tenacity)
- ✅ All external calls mocked in tests
- ✅ Simulation mode works without blockchain
- ✅ Type hints on everything
- ✅ Comprehensive error handling
- ✅ Position limits enforced
- ✅ **Private keys NEVER in code (environment only)**

**IMPORTANT:**
- Phase 1: Only simulation mode needed
- Phase 2: Aave + Uniswap needed
- Phase 3: Add CEX integrations

Start with simulation mode working, then add real protocols.

---

## 📊 DATABASE SCHEMA

From TRADING_ENGINE_SPEC.md lines 122-188:

Create 4 tables in SQLite:
- trades
- protocol_config
- position_limits
- execution_log

**See spec lines 122-188 for exact schema.**

---

## 🔗 DEPENDENCIES

**Context Files to Reference:**
- `src/agent.py` - TreasuryAgent interface (shows agent structure)
- `src/arena_manager.py` - ArenaManager interface (shows how trades are submitted)
- `TRADING_ENGINE_SPEC.md` - Your complete specification

**External Libraries Needed:**
```python
# requirements.txt additions
web3==6.11.0
aiohttp==3.9.0
tenacity==8.2.3
eth-account==0.10.0
```

---

## ✅ SUCCESS CRITERIA

From TRADING_ENGINE_SPEC.md lines 300-340:

**Functional:**
- [ ] Can execute DeFi operations (Aave deposit/withdraw)
- [ ] Can execute DEX swaps (Uniswap)
- [ ] Validates trades before execution
- [ ] Updates agent capital accurately
- [ ] Logs all executions to database
- [ ] Emergency stop works instantly

**Technical:**
- [ ] Async execution (multiple trades in parallel)
- [ ] Type hints on all methods
- [ ] Comprehensive error handling
- [ ] Retry logic for transient failures
- [ ] Gas estimation before execution
- [ ] Transaction confirmation tracking

**Testing:**
- [ ] Unit test: Trade validation logic
- [ ] Unit test: Capital update calculations
- [ ] Integration test: Mock Aave deposit
- [ ] Integration test: Mock Uniswap swap
- [ ] Simulation mode works without real blockchain
- [ ] All external calls mocked in tests

**Safety (CRITICAL):**
- [ ] Position limits enforced
- [ ] Slippage limits enforced
- [ ] Gas limits enforced
- [ ] Emergency stop tested
- [ ] **No private keys in code (use environment)**

**Performance:**
- [ ] Can execute 100 trades/minute
- [ ] Trade validation <100ms
- [ ] Handles failed transactions gracefully

---

## 🔒 SAFETY REQUIREMENTS

**This controls real money - be extremely thorough:**

From TRADING_ENGINE_SPEC.md lines 443-558:

### **Critical Verification Points:**

**1. Trade Execution Safety:**
```python
async def execute_trade(trade_id):
    # Validate BEFORE execution
    valid, error = await self.validate_trade(trade)
    if not valid:
        return False, error

    # Execute with retry logic
    @retry(stop=stop_after_attempt(3))
    async def _execute():
        return await self.protocol.execute(trade)

    # Update capital ONLY on success
    agent.real_capital += result['pnl']
```

**2. Position Limits:**
```python
def validate_trade(agent, trade):
    # Check position limit
    current_position = self.get_position(agent, trade['asset'])
    if current_position + trade['amount'] > agent.max_position:
        return False, "Position limit exceeded"
```

**3. Emergency Stop:**
```python
def emergency_stop(self):
    self.trading_enabled = False
    logger.critical("EMERGENCY STOP activated")

async def execute_trade(trade_id):
    if not self.trading_enabled:
        return False, "Trading disabled"
```

---

## 🧪 VERIFICATION

After building, verify using **PROMPT B** from TRADING_ENGINE_SPEC.md lines 439-558.

**Critical Issues to Check:**
- [ ] Executes without validation: CRITICAL
- [ ] No position limits: CRITICAL
- [ ] Private keys in code: CRITICAL
- [ ] Capital updated before success: CRITICAL
- [ ] No emergency stop: MAJOR

---

## 📤 DELIVERABLES

**When Complete:**
1. Create file: `BUILD_COMPLETE_TRADING_ENGINE.md`
2. List all files created
3. Paste verification results (PROMPT B checklist)
4. **Run all safety tests and prove they pass**
5. Commit to git with message: "Treasury Arena: Trading Engine Complete (Safety Verified)"

---

## 🎯 COORDINATE WITH OTHER SESSIONS

**Session A** is building SIMULATION_ENGINE (parallel)
**Session C** is completing ARENA_MANAGER_v2 (parallel)

After all 3 complete, we'll integrate and run full system test.

---

## ⚠️ CRITICAL WARNING

This component controls real capital. Every line of code must be:
- Thoroughly tested
- Properly validated
- Error-isolated
- Safety-first

**DO NOT skip any safety checks. DO NOT skip any tests.**

---

**START IMMEDIATELY** - Use TRADING_ENGINE_SPEC.md PROMPT A (lines 343-437) as your complete build guide.

⚡💎🔒 **Build fast, verify thoroughly, prioritize safety**
