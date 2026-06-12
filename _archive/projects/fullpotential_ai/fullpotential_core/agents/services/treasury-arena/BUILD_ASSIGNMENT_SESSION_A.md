# BUILD ASSIGNMENT - SESSION A
**Component:** SIMULATION_ENGINE
**Estimated Time:** 1-2 hours
**Priority:** HIGH (Enables Phase 1 testing)

---

## 🎯 YOUR MISSION

Build the **Simulation Engine** that enables backtesting treasury agents with zero capital risk.

---

## 📋 SPECIFICATION REFERENCE

**Primary Spec:** `/Users/jamessunheart/Development/agents/services/treasury-arena/SIMULATION_ENGINE_SPEC.md`

**Read Lines 325-409** for complete build instructions (PROMPT A - BUILDER)

---

## 🔧 WHAT TO BUILD

Generate these 10 files in `/Users/jamessunheart/Development/agents/services/treasury-arena/`:

1. **src/simulation_engine.py** - Core simulation engine
   - SimulationEngine class
   - backtest() method with time progression
   - live_simulate() method
   - Market data fetching (async)
   - Data caching in SQLite
   - Evolution cycle execution at configurable speed

2. **src/data_sources.py** - External data connectors
   - CoinGeckoAPI class (historical prices)
   - DeFiLlamaAPI class (historical APYs)
   - Async fetching with aiohttp
   - Rate limiting
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

7. **requirements.txt** - Updated dependencies (append to existing)

8. **README_SIMULATION.md** - Usage guide

9. **migrations/001_create_simulation_tables.sql** - Database schema

10. **docs/SIMULATION_GUIDE.md** - Complete documentation

---

## ⚠️ CRITICAL REQUIREMENTS

From SIMULATION_ENGINE_SPEC.md lines 392-407:

- ✅ Full implementations (no TODO or placeholders)
- ✅ Async data fetching (aiohttp)
- ✅ SQLite for caching
- ✅ Type hints on all functions
- ✅ Comprehensive error handling
- ✅ Logging with structlog
- ✅ Unit tests with pytest
- ✅ CLI with click
- ✅ Time progression configurable (1x to 1000x speed)
- ✅ All market data cached (no redundant API calls)
- ✅ Agent execution isolated (one crash doesn't kill simulation)
- ✅ Results deterministic (same inputs = same outputs)

---

## 📊 DATABASE SCHEMA

From SIMULATION_ENGINE_SPEC.md lines 126-192:

Create 4 tables in SQLite:
- market_data
- protocol_data
- simulation_runs
- simulation_snapshots

**See spec lines 126-192 for exact schema.**

---

## 🔗 DEPENDENCIES

**Context Files to Reference:**
- `src/agent.py` - TreasuryAgent interface (already exists, bugs fixed)
- `src/arena_manager.py` - ArenaManager interface (already exists)
- `SIMULATION_ENGINE_SPEC.md` - Your complete specification

**External APIs:**
- CoinGecko API (free tier) - historical prices
- DeFi Llama API (free tier) - historical APYs

---

## ✅ SUCCESS CRITERIA

From SIMULATION_ENGINE_SPEC.md lines 289-320:

**Functional:**
- [ ] Can backtest 50 agents over 1 year in <10 minutes
- [ ] Market data cached locally
- [ ] Agent fitness scores calculated daily
- [ ] Evolution mechanics work at any speed
- [ ] Simulation results exportable to JSON
- [ ] Can replay any historical period deterministically

**Technical:**
- [ ] SQLite database created, schema matches spec
- [ ] All API calls async
- [ ] Error handling for missing data
- [ ] Memory efficient (handles 50+ agents)
- [ ] Unit tests pass
- [ ] Integration test: 30-day simulation completes

**Performance:**
- [ ] Fetch and cache 1 year data in <2 minutes
- [ ] Process 1 simulated day in <0.5 seconds (50 agents)
- [ ] 180-day backtest completes in <5 minutes

---

## 🧪 VERIFICATION

After building, verify using **PROMPT B** from SIMULATION_ENGINE_SPEC.md lines 411-493.

Run through the complete checklist and mark each item as:
- ✅ PASS
- ⚠️ PARTIAL
- ❌ FAIL

---

## 📤 DELIVERABLES

**When Complete:**
1. Create file: `BUILD_COMPLETE_SIMULATION_ENGINE.md`
2. List all files created
3. Paste verification results (PROMPT B checklist)
4. Commit to git with message: "Treasury Arena: Simulation Engine Complete"

---

## 🎯 COORDINATE WITH OTHER SESSIONS

**Session B** is building TRADING_ENGINE (parallel)
**Session C** is completing ARENA_MANAGER_v2 (parallel)

After all 3 complete, we'll integrate and run full system test.

---

**START IMMEDIATELY** - Use SIMULATION_ENGINE_SPEC.md PROMPT A (lines 325-409) as your complete build guide.

⚡💎 **Build fast, verify thoroughly**
