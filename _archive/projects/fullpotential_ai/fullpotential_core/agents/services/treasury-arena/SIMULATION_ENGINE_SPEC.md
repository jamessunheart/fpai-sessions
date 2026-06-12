# SIMULATION_ENGINE_SPEC.md
**Treasury Arena - Simulation Engine**
**Version:** 2.0
**Created:** November 15, 2025
**Priority:** TIER 1 - Enables Phase 1 (Zero Capital Risk Testing)

---

## 1. 🎯 PURPOSE

The Simulation Engine enables backtesting and live simulation of treasury agents using historical market data and virtual capital, proving evolutionary mechanics before risking real money.

**TIER 1 IMPACT:**
Removes $200K capital risk by validating all agents in simulation before deployment. Enables Phase 1 launch with zero real capital exposure.

**Problem Solved:**
Currently no way to test agents without real money. This creates a backtest environment that validates:
- Agent strategies work
- Fitness calculations are accurate
- Evolution mechanics function correctly
- Capital allocation logic is sound

---

## 2. 📋 CORE REQUIREMENTS

**As a System Architect, I must be able to:**
1. Run backtests on historical data (2020-2025) to validate agent performance
2. Simulate live market conditions with virtual capital
3. Fast-forward time to test 6-month scenarios in minutes
4. Compare agent performance across multiple market conditions (bull, bear, sideways)

**As an Arena Manager, I must be able to:**
5. Spawn 50+ agents in simulation without capital constraints
6. Graduate top performers from simulation to proving grounds based on real metrics
7. Test evolution cycles (birth/death/mutation) at 100x speed
8. Validate fitness calculations match expected outcomes

**As a Developer, I must be able to:**
9. Add new market data sources without changing core engine
10. Replay specific historical periods for debugging
11. Export simulation results for analysis
12. Run simulations in parallel for faster iteration

---

## 3. 🎨 USER INTERFACE

**No UI required - API only**

CLI interface for running backtests:
```bash
$ python -m src.simulation_engine backtest \
    --agents 50 \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --speed 100x

Simulation Running:
Progress: ████████░░░░░░░░░░ 42% (152/365 days)
Agents Active: 47 | Dead: 15 | Avg Fitness: 2.34
Elapsed: 3.2 minutes | Est. Remaining: 4.1 minutes
```

---

## 4. 🔌 INTEGRATIONS

**Internal Integrations:**
- Arena Manager: Provides agents for simulation
- Agent Base Class: All agents run in simulation mode
- Trading Engine: Executes virtual trades
- Dashboard (future): Displays simulation results

**External Integrations:**
- CoinGecko API: Historical price data (free tier)
- DeFi Llama API: Historical APY data (free)
- Local SQLite: Cache historical data to avoid re-fetching

**Data Sources:**
```python
PRICE_SOURCES = {
    'BTC': 'coingecko',
    'ETH': 'coingecko',
    'SOL': 'coingecko'
}

APY_SOURCES = {
    'aave': 'defillama',
    'pendle': 'defillama',
    'curve': 'defillama'
}
```

---

## 5. 🔧 TECHNICAL STACK

**Default Stack:**
- Backend: Python 3.11+
- Data: pandas, numpy (time series manipulation)
- Database: SQLite (historical data cache)
- Testing: pytest
- No Docker needed (simulation runs locally)

**Additional Requirements:**
- aiohttp: Async API calls for market data
- joblib: Parallel simulation execution
- matplotlib: Optional visualization

**Libraries:**
```python
# requirements.txt additions
pandas==2.1.0
numpy==1.24.0
aiohttp==3.9.0
joblib==1.3.0
matplotlib==3.8.0  # Optional
python-dateutil==2.8.2
```

---

## 6. 📊 DATABASE SCHEMA

**SQLite Schema (Historical Data Cache):**

```sql
-- Table: market_data
CREATE TABLE market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset TEXT NOT NULL,
    date DATE NOT NULL,
    price_usd REAL NOT NULL,
    volume_24h REAL,
    market_cap REAL,
    mvrv REAL,  -- For BTC
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset, date)
);

CREATE INDEX idx_market_data_asset_date ON market_data(asset, date);

-- Table: protocol_data
CREATE TABLE protocol_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol TEXT NOT NULL,
    date DATE NOT NULL,
    apy REAL NOT NULL,
    tvl REAL,
    volume_24h REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(protocol, date)
);

CREATE INDEX idx_protocol_data_protocol_date ON protocol_data(protocol, date);

-- Table: simulation_runs
CREATE TABLE simulation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_agents INTEGER NOT NULL,
    final_agents INTEGER NOT NULL,
    total_spawned INTEGER NOT NULL,
    total_killed INTEGER NOT NULL,
    final_capital REAL NOT NULL,
    total_return REAL NOT NULL,
    sharpe_ratio REAL,
    max_drawdown REAL,
    config JSON,  -- Simulation parameters
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Table: simulation_snapshots
CREATE TABLE simulation_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    date DATE NOT NULL,
    agent_id TEXT NOT NULL,
    virtual_capital REAL NOT NULL,
    fitness_score REAL,
    sharpe_ratio REAL,
    status TEXT,
    tier TEXT,
    FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id)
);

CREATE INDEX idx_snapshots_run_date ON simulation_snapshots(run_id, date);
```

---

## 7. 🎯 API ENDPOINTS

**Core Simulation API:**

```python
# Internal API (no HTTP, called by arena manager)

class SimulationEngine:
    
    def backtest(
        self,
        agents: List[TreasuryAgent],
        start_date: datetime,
        end_date: datetime,
        speed_multiplier: int = 1
    ) -> SimulationResults
    """
    Run backtest on historical data.
    
    Args:
        agents: List of agents to simulate
        start_date: Start of backtest period
        end_date: End of backtest period
        speed_multiplier: 1 = real-time, 100 = 100x speed
        
    Returns:
        SimulationResults with performance metrics
    """
    
    def live_simulate(
        self,
        agents: List[TreasuryAgent],
        duration_days: int = 30
    ) -> SimulationResults
    """
    Simulate with live market data but virtual capital.
    
    Args:
        agents: Agents to simulate
        duration_days: How long to run simulation
        
    Returns:
        SimulationResults
    """
    
    def get_market_data(
        self,
        date: datetime,
        assets: List[str]
    ) -> Dict[str, Dict]
    """
    Fetch market data for specific date (cached).
    
    Returns:
        {'BTC': {'price': 45000, 'volume': 1.2e9, 'mvrv': 2.3}}
    """
    
    def get_protocol_data(
        self,
        date: datetime,
        protocols: List[str]
    ) -> Dict[str, Dict]
    """
    Fetch protocol APY data for date (cached).
    
    Returns:
        {'aave': {'apy': 0.08, 'tvl': 5.2e9}}
    """
```

**CLI Interface:**

```bash
# Run backtest
python -m src.simulation_engine backtest \
    --config simulation_config.json \
    --output results.json

# Fast-forward simulation
python -m src.simulation_engine fastforward \
    --agents 50 \
    --days 180 \
    --speed 100x

# Replay specific period
python -m src.simulation_engine replay \
    --start 2024-05-01 \
    --end 2024-08-01 \
    --agents-file agents.json
```

---

## 8. ✅ SUCCESS CRITERIA

**Functional Requirements:**
- [ ] Can backtest 50 agents over 1 year period in <10 minutes
- [ ] Market data cached locally (no re-fetching on subsequent runs)
- [ ] Agent fitness scores calculated daily during simulation
- [ ] Evolution mechanics (birth/death/mutation) work at any speed
- [ ] Simulation results exportable to JSON for analysis
- [ ] Can replay any historical period deterministically
- [ ] Parallel execution of multiple simulation runs

**Technical Requirements:**
- [ ] SQLite database created and schema matches spec
- [ ] All historical data API calls async (aiohttp)
- [ ] Error handling for missing data (interpolate or skip day)
- [ ] Simulation state serializable (can pause/resume)
- [ ] Memory efficient (handles 50+ agents without issues)
- [ ] Unit tests for: data fetching, time progression, agent execution
- [ ] Integration test: Full 30-day simulation completes successfully

**Performance Requirements:**
- [ ] Fetch and cache 1 year of data in <2 minutes
- [ ] Process 1 simulated day in <0.5 seconds (50 agents)
- [ ] 180-day backtest completes in <5 minutes
- [ ] Parallel runs: 4 simultaneous backtests on 8-core machine

**Validation Requirements:**
- [ ] Agent performance matches expected ranges (DeFi: 6-12% APY)
- [ ] Fitness calculations identical between simulation and live
- [ ] Capital allocation totals equal initial capital (no leaks)
- [ ] Evolution produces improving average fitness over time

---

## 9. 🚀 APPRENTICE EXECUTION PROMPTS

### PROMPT A - BUILDER (For Claude)

```
I need to build the Simulation Engine for the Treasury Arena system.

SPECIFICATION:
[Upload: SIMULATION_ENGINE_SPEC.md]

CONTEXT FILES:
[Upload: UDC_COMPLIANCE.md]
[Upload: TECH_STACK.md]
[Upload: SECURITY_REQUIREMENTS.md]
[Upload: CODE_STANDARDS.md]
[Upload: INTEGRATION_GUIDE.md]

REFERENCE IMPLEMENTATIONS:
[Upload: agent.py - shows TreasuryAgent interface]
[Upload: arena_manager.py - shows how agents are managed]

Please generate complete production-ready code for:

1. **src/simulation_engine.py** - Core simulation engine
   - SimulationEngine class
   - backtest() method with time progression
   - live_simulate() method
   - Market data fetching (async)
   - Data caching in SQLite
   - Evolution cycle execution at configurable speed
   - Error handling for missing data

2. **src/data_sources.py** - External data connectors
   - CoinGeckoAPI class (historical prices)
   - DeFiLlamaAPI class (historical APYs)
   - Async fetching with aiohttp
   - Rate limiting (respect free tier limits)
   - Error handling and retries

3. **src/simulation_results.py** - Results container
   - SimulationResults class
   - Performance metrics aggregation
   - Export to JSON
   - Comparison utilities

4. **src/cli.py** - Command-line interface
   - Click-based CLI
   - backtest, fastforward, replay commands
   - Progress bars (tqdm)
   - Config file loading

5. **tests/test_simulation.py** - Test suite
   - Test data fetching
   - Test time progression
   - Test agent execution in simulation
   - Integration test: 30-day backtest

6. **simulation_config.json** - Example config
   - Backtest parameters
   - Agent spawn rules
   - Evolution settings

7. **requirements.txt** - Updated dependencies

8. **README_SIMULATION.md** - Usage guide
   - How to run backtests
   - Config file format
   - Interpreting results

REQUIREMENTS:
- Full implementations (no TODO or placeholders)
- Async data fetching (aiohttp)
- SQLite for caching
- Type hints on all functions
- Comprehensive error handling
- Logging with structlog
- Unit tests with pytest
- CLI with click

IMPORTANT:
- Time progression must be configurable (1x to 1000x speed)
- All market data must be cached (no redundant API calls)
- Agent execution must be isolated (one agent crash doesn't kill simulation)
- Results must be deterministic (same inputs = same outputs)

Generate all files with complete code.
```

### PROMPT B - VERIFIER (For Gemini)

```
Verify the Simulation Engine implementation against the specification.

ORIGINAL SPECIFICATION:
[Upload: SIMULATION_ENGINE_SPEC.md]

GENERATED CODE:
[Upload: Complete simulation_engine code package]

VERIFY CHECKLIST:

**Functionality:**
- [ ] Can fetch historical market data from CoinGecko
- [ ] Can fetch historical APY data from DeFi Llama
- [ ] Data is cached in SQLite (no redundant API calls)
- [ ] Backtest progresses through time correctly
- [ ] Agents execute strategies each simulated day
- [ ] Fitness scores calculated correctly
- [ ] Evolution mechanics (spawn/kill/mutate) work
- [ ] Can run at different speeds (1x, 10x, 100x)
- [ ] CLI commands work (backtest, fastforward, replay)
- [ ] Results exportable to JSON

**Code Quality:**
- [ ] All functions have type hints
- [ ] Async/await used for API calls
- [ ] Error handling for missing data
- [ ] Logging present (structlog)
- [ ] No print() statements
- [ ] No bare except clauses
- [ ] No hardcoded values (use config)

**Testing:**
- [ ] Unit tests for data fetching
- [ ] Unit tests for time progression
- [ ] Integration test runs 30-day simulation
- [ ] Tests pass with pytest
- [ ] Mock API calls in tests (don't hit real APIs)

**Performance:**
- [ ] Can cache 1 year of data in <2 minutes
- [ ] 180-day backtest completes in <10 minutes
- [ ] Memory usage reasonable (50 agents)

**Data Integrity:**
- [ ] SQLite schema matches spec exactly
- [ ] Data cached correctly (check timestamps)
- [ ] Missing data handled gracefully
- [ ] No data leaks between simulation runs

**Integration:**
- [ ] Works with existing TreasuryAgent class
- [ ] Works with existing ArenaManager
- [ ] Results format matches expected structure

**Critical Issues:**
Look for:
- Race conditions in async code
- SQL injection vulnerabilities
- API rate limit violations
- Memory leaks in long backtests
- Non-deterministic behavior

OUTPUT FORMAT:
For each checklist item:
✅ PASS - [Evidence: file, line number]
⚠️ PARTIAL - [What works, what's missing]
❌ FAIL - [Specific issue, how to fix]

SEVERITY RATINGS:
- CRITICAL: Breaks simulation, data corruption, security
- MAJOR: Performance issues, missing features
- MINOR: Code style, documentation

FINAL VERDICT:
[ ] PASS - Ready for Phase 1 deployment
[ ] PARTIAL - Fix issues listed below
[ ] FAIL - Major rework needed

List all issues with severity and fix recommendations.
```

---

## METADATA

**Complexity Assessment:**
- Sprint Size: 2 (8-12 hours)
- Difficulty: Medium
- Reasoning: Async data fetching + time simulation logic + caching

**Dependencies:**
- Required: agent.py, arena_manager.py (already exist)
- Optional: Dashboard (for visualization)
- External: CoinGecko API, DeFi Llama API

**Blockers:**
- None (APIs are free tier, no auth needed)

**Recommended Developer Level:**
- Level: Intermediate
- Reasoning: Requires async Python, pandas, data caching

**Estimated Timeline:**
- Build: 8-12 hours
- Verification: 2-3 hours
- Total: 10-15 hours

**Capital Required:**
- Phase 1: $0 (all virtual)
- APIs: Free tier (rate limited but sufficient)

---

**END SIMULATION_ENGINE_SPEC.md**

*Enables Phase 1 - Zero capital risk validation of all arena mechanics*
