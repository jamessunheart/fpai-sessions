# TRADING_ENGINE_SPEC.md
**Treasury Arena - Trading Engine**
**Version:** 1.0
**Created:** November 15, 2025
**Priority:** TIER 1 - Required for Phase 2 (Real Capital Execution)

---

## 1. 🎯 PURPOSE

The Trading Engine executes trades on behalf of agents, interfacing with real DeFi protocols and exchanges while maintaining safety controls and execution logs.

**TIER 1 IMPACT:**
Enables Phase 2 by providing the bridge between agent strategies and real capital deployment. Without this, agents can't actually trade.

**Problem Solved:**
Currently agents return trade objects but nothing executes them. This engine:
- Executes DeFi operations (deposit to Aave, buy BTC, etc.)
- Validates trades before execution
- Logs all execution results
- Updates agent capital accurately

---

## 2. 📋 CORE REQUIREMENTS

**As a Treasury Agent, I must be able to:**
1. Submit trades for execution
2. Have trades validated before execution
3. Receive execution results (success/failure)
4. Have my capital updated accurately after trades

**As a Risk Manager, I must be able to:**
5. Review all pending trades before execution
6. Set position limits per agent
7. Emergency stop all trading
8. Audit complete trade history

**As a System Monitor, I must be able to:**
9. See real-time execution status
10. Track execution success/failure rates
11. Monitor gas costs and slippage
12. Detect anomalous trading patterns

**As a Developer, I must be able to:**
13. Add new protocols without changing core engine
14. Test executions in simulation mode
15. Replay failed trades with different parameters
16. Mock external APIs for testing

---

## 3. 🎨 USER INTERFACE

**No UI required - Python class library**

CLI for monitoring:
```bash
$ python -m src.trading_engine status

Trading Engine Status:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mode: SIMULATION
Pending Trades: 3
Executed Today: 47
Success Rate: 95.7%
Total Gas Spent: $12.34

Recent Executions:
[10:23:45] ✅ agent-abc123 | Deposit $1000 to Aave | APY: 8.2%
[10:24:12] ✅ agent-def456 | Buy 0.05 BTC @ $45,000
[10:25:03] ❌ agent-ghi789 | Swap failed | Slippage too high
```

---

## 4. 🔌 INTEGRATIONS

**Internal Integrations:**
- Treasury Agent v2: Receives trades from agents
- Arena Manager v2: Reports execution results
- Simulation Engine: Executes virtual trades
- Event Sourcing: Logs all executions

**External Integrations (Phase 2+):**
- Aave: Lending/borrowing
- Uniswap: DEX swaps
- Pendle: Yield trading
- Coinbase/Binance: CEX trading (optional)

**Safety Rails:**
- All executions require multi-sig approval in production
- Test mode available for dry-run
- Emergency stop switch

---

## 5. 🔧 TECHNICAL STACK

**Default Stack:**
- Python 3.11+ (async)
- web3.py (Ethereum interactions)
- SQLite (execution log)
- structlog (logging)

**Additional Requirements:**
- aiohttp (async HTTP for CEX APIs)
- tenacity (retry logic)
- web3.py (DeFi interactions)

**Libraries:**
```python
# requirements.txt additions
web3==6.11.0
aiohttp==3.9.0
tenacity==8.2.3
eth-account==0.10.0  # Wallet management
```

---

## 6. 📊 DATABASE SCHEMA

```sql
-- Table: trades
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT UNIQUE NOT NULL,  -- UUID
    agent_id TEXT NOT NULL,
    trade_type TEXT NOT NULL,  -- swap, deposit, withdraw, buy, sell
    status TEXT NOT NULL,  -- pending, executing, success, failed
    protocol TEXT,  -- aave, uniswap, etc.
    input_asset TEXT,
    input_amount REAL,
    output_asset TEXT,
    output_amount REAL,
    expected_return REAL,
    actual_return REAL,
    gas_cost_usd REAL,
    slippage REAL,
    execution_price REAL,
    tx_hash TEXT,  -- Blockchain transaction hash
    error_message TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP,
    failed_at TIMESTAMP
);

CREATE INDEX idx_trades_agent ON trades(agent_id);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_submitted ON trades(submitted_at);

-- Table: protocol_config
CREATE TABLE protocol_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol TEXT UNIQUE NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    contract_address TEXT,
    chain TEXT DEFAULT 'ethereum',
    max_slippage REAL DEFAULT 0.01,  -- 1%
    gas_limit INTEGER,
    config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: position_limits
CREATE TABLE position_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    asset TEXT,  -- Null = applies to all
    max_position_usd REAL NOT NULL,
    max_trade_size_usd REAL NOT NULL,
    max_daily_trades INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, asset)
);

-- Table: execution_log
CREATE TABLE execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,  -- info, warning, error
    message TEXT NOT NULL,
    data JSON,
    FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
);
```

---

## 7. 🎯 API ENDPOINTS

**No HTTP endpoints** - Python class interface only.

**Core Methods:**

```python
class TradingEngine:
    
    def __init__(self, mode: str = "simulation"):
        """
        Initialize trading engine.
        
        Args:
            mode: "simulation" or "production"
        """
    
    async def submit_trade(
        self,
        agent: TreasuryAgent,
        trade: Dict
    ) -> str:
        """
        Submit trade for execution.
        
        Args:
            agent: Agent submitting trade
            trade: Trade details
            
        Returns:
            trade_id (UUID)
        """
    
    async def execute_trade(
        self,
        trade_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute a pending trade.
        
        Returns:
            (success, error_message)
        """
    
    async def validate_trade(
        self,
        agent: TreasuryAgent,
        trade: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate trade before execution.
        
        Checks:
        - Agent has sufficient capital
        - Position limits not exceeded
        - Slippage within tolerance
        - Protocol enabled
        
        Returns:
            (valid, error_message)
        """
    
    async def execute_defi_operation(
        self,
        protocol: str,
        operation: str,
        params: Dict
    ) -> Dict:
        """
        Execute DeFi operation.
        
        Args:
            protocol: "aave", "uniswap", etc.
            operation: "deposit", "swap", etc.
            params: Operation-specific parameters
            
        Returns:
            Execution result with tx_hash
        """
    
    def get_execution_stats(
        self,
        agent_id: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict:
        """
        Get execution statistics.
        
        Returns:
            {
                'total_trades': 100,
                'successful': 95,
                'failed': 5,
                'success_rate': 0.95,
                'total_gas_usd': 234.56,
                'avg_slippage': 0.003
            }
        """
    
    def emergency_stop(self):
        """Stop all trading immediately"""
    
    def emergency_resume(self):
        """Resume trading after stop"""
```

---

## 8. ✅ SUCCESS CRITERIA

**Functional Requirements:**
- [ ] Can execute DeFi operations (Aave deposit/withdraw)
- [ ] Can execute DEX swaps (Uniswap)
- [ ] Can execute CEX trades (Coinbase API)
- [ ] Validates trades before execution
- [ ] Updates agent capital accurately
- [ ] Logs all executions to database
- [ ] Emergency stop works instantly

**Technical Requirements:**
- [ ] Async execution (multiple trades in parallel)
- [ ] Type hints on all methods
- [ ] Comprehensive error handling
- [ ] Retry logic for transient failures
- [ ] Gas estimation before execution
- [ ] Transaction confirmation tracking

**Testing Requirements:**
- [ ] Unit test: Trade validation logic
- [ ] Unit test: Capital update calculations
- [ ] Integration test: Mock Aave deposit
- [ ] Integration test: Mock Uniswap swap
- [ ] Simulation mode works without real blockchain
- [ ] All external calls mocked in tests

**Safety Requirements:**
- [ ] Position limits enforced
- [ ] Slippage limits enforced
- [ ] Gas limits enforced
- [ ] Emergency stop tested
- [ ] Multi-sig required for production (Phase 3)
- [ ] No private keys in code (use environment)

**Performance Requirements:**
- [ ] Can execute 100 trades/minute
- [ ] Trade validation <100ms
- [ ] Transaction confirmation tracking
- [ ] Handles failed transactions gracefully

---

## 9. 🚀 APPRENTICE EXECUTION PROMPTS

### PROMPT A - BUILDER (For Claude)

```
I need to build the Trading Engine for the Treasury Arena.

SPECIFICATION:
[Upload: TRADING_ENGINE_SPEC.md]

CONTEXT FILES:
[Upload: TREASURY_AGENT_v2_SPEC.md - shows agent interface]
[Upload: ARENA_MANAGER_v2_SPEC.md - shows how trades are submitted]
[Upload: CODE_STANDARDS.md]
[Upload: SECURITY_REQUIREMENTS.md]

Please generate:

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

REQUIREMENTS:
- All blockchain interactions async (web3.py AsyncWeb3)
- Retry logic for transient failures (tenacity)
- All external calls mocked in tests
- Simulation mode works without blockchain
- Type hints on everything
- Comprehensive error handling
- Position limits enforced
- Private keys NEVER in code (environment only)

IMPORTANT:
- Phase 1: Only simulation mode needed
- Phase 2: Aave + Uniswap needed
- Phase 3: Add CEX integrations

Start with simulation mode working, then add real protocols.

Generate complete code with no TODOs.
```

### PROMPT B - VERIFIER (For Gemini)

```
Verify Trading Engine implementation against spec.

SPECIFICATION:
[Upload: TRADING_ENGINE_SPEC.md]

GENERATED CODE:
[Upload: Complete trading_engine package]

CRITICAL VERIFICATION:

**1. Trade Execution Safety**
✅ MUST HAVE:
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
    
    # Update capital after success
    agent.real_capital += result['pnl']
```

**Verification:**
1. Find execute_trade() method
2. Verify validation happens first
3. Verify retry logic present
4. Verify capital updated ONLY on success
5. Check test proves this

**2. Position Limits**
✅ MUST HAVE:
```python
def validate_trade(agent, trade):
    # Check position limit
    current_position = self.get_position(agent, trade['asset'])
    if current_position + trade['amount'] > agent.max_position:
        return False, "Position limit exceeded"
    
    # Check trade size limit
    if trade['amount_usd'] > agent.max_trade_size:
        return False, "Trade too large"
```

**Verification:**
1. Find validate_trade() method
2. Verify position limits checked
3. Verify trade size limits checked
4. Verify limits enforced (test proves)

**3. Emergency Stop**
✅ MUST HAVE:
```python
def emergency_stop(self):
    self.trading_enabled = False
    logger.critical("EMERGENCY STOP activated")
    # Cancel all pending trades
    
async def execute_trade(trade_id):
    if not self.trading_enabled:
        return False, "Trading disabled (emergency stop)"
```

**Verification:**
1. Find emergency_stop() method
2. Verify sets trading_enabled = False
3. Verify execute_trade() checks flag
4. Verify test proves trades blocked

**CHECKLIST:**

**Core Functionality:**
- [ ] Can submit trades
- [ ] Validates before execution
- [ ] Executes DeFi operations
- [ ] Updates agent capital
- [ ] Logs all executions

**Safety:**
- [ ] Position limits enforced
- [ ] Slippage limits enforced
- [ ] Emergency stop works
- [ ] No private keys in code
- [ ] Capital validation

**Protocols:**
- [ ] Simulation adapter works
- [ ] Aave adapter (if Phase 2)
- [ ] Uniswap adapter (if Phase 2)
- [ ] All use ProtocolAdapter interface

**Testing:**
- [ ] All external calls mocked
- [ ] Simulation mode tested
- [ ] Validation logic tested
- [ ] Capital update tested
- [ ] Emergency stop tested

**Critical Issues:**
- [ ] Executes without validation: CRITICAL
- [ ] No position limits: CRITICAL
- [ ] Private keys in code: CRITICAL
- [ ] Capital updated before success: CRITICAL
- [ ] No emergency stop: MAJOR

OUTPUT:
✅ PASS - Ready for Phase 1
⚠️ PARTIAL - [Issues to fix]
❌ FAIL - [Critical problems]

This controls real money - be extremely thorough.
```

---

## METADATA

**Complexity Assessment:**
- Sprint Size: 2 (8-12 hours)
- Difficulty: Medium-Hard
- Reasoning: Web3 integration + async + safety critical

**Dependencies:**
- Required: Treasury Agent v2, Arena Manager v2
- Blocks: Phase 2 deployment (can't trade without this)

**Blockers:**
- None for Phase 1 (simulation only)
- Need Ethereum RPC for Phase 2 (Infura/Alchemy)
- Need private key management for Phase 2 (AWS Secrets Manager)

**Recommended Developer Level:**
- Level: Skilled
- Reasoning: DeFi knowledge + web3.py + safety critical

**Estimated Timeline:**
- Build: 10-12 hours
- Verification: 3-4 hours
- Total: 13-16 hours

**Phased Deployment:**
- Phase 1: Simulation mode only (safe)
- Phase 2: Add Aave + Uniswap ($10K testing)
- Phase 3: Add CEX + multi-sig ($200K production)

---

**END TRADING_ENGINE_SPEC.md**

*Critical for Phase 2 - This is how agents actually trade*
