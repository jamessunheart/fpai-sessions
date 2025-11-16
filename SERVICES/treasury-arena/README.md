# 🏛️ Treasury Arena - Evolutionary Capital Allocation System

**Status:** SPECIFICATION COMPLETE → READY FOR BUILD
**Version:** 1.0
**Capital Target:** $210K (56% of treasury)

---

## 🎯 Overview

The Treasury Arena is an **evolutionary capital allocation system** where AI agents compete for treasury resources in a survival-of-the-fittest arena.

**Core Concept:**
- Dozens of AI agents execute different trading strategies
- Winners get more capital
- Losers get killed
- Continuous evolution ensures optimal strategy mix

**This is paradise through evolution.**

---

## 🏗️ Architecture

### **4-Layer Hierarchy:**

```
Layer 0: Stable Reserve ($163K)
└─ Safety net, never at risk

Layer 1: Simulation ($∞ virtual)
└─ 50+ agents compete with fake money
   └─ Graduates top performers ↓

Layer 2: Proving Grounds ($10K)
└─ 10 agents × $1K real capital
   └─ Graduates top 50% ↓

Layer 3: Main Arena ($200K)
└─ 10-15 proven agents
   └─ Dynamic capital allocation
      Elite (top 20%): 60% capital
      Active (mid 30%): 30% capital
      Challenger (bottom 50%): 10% capital
```

---

## 📁 Project Structure

```
treasury-arena/
├── README.md                    # This file
├── src/
│   ├── agent.py                 # TreasuryAgent base class + strategies
│   ├── arena_manager.py         # Birth/death/allocation orchestrator
│   ├── simulation_engine.py     # Backtest + live sim (TODO)
│   ├── main.py                  # FastAPI server (TODO)
│   └── strategies/              # Strategy implementations (TODO)
│       ├── defi_farmer.py
│       ├── tactical_trader.py
│       ├── arb_hunter.py
│       └── ...
├── tests/
│   ├── test_agent.py
│   ├── test_arena.py
│   └── test_simulation.py
├── docs/
│   └── TREASURY_ARENA_SPEC.md   # Complete specification
└── requirements.txt
```

---

## 🤖 Current Agents (2 Implemented)

### **1. DeFiYieldFarmer**
- **Strategy:** Hunt stable yields (Aave, Pendle, Curve)
- **Target:** 6-12% APY
- **Risk:** Low
- **Status:** ✅ Implemented

### **2. TacticalTrader**
- **Strategy:** Cycle-aware BTC/SOL trading (MVRV-based)
- **Target:** 30-100% APY
- **Risk:** Medium
- **Status:** ✅ Implemented

### **Coming Soon:**
- LP Bot (Liquidity provision)
- Arb Hunter (Arbitrage)
- Derivatives Player (Options/perps)
- Moonshot Venture (Early tokens)
- Market Maker
- Staking Agent

---

## 🧬 Evolutionary Mechanics

### **Birth:**
```python
# Spawn new agent
agent = arena.spawn_agent(
    strategy_type="DeFi-Yield-Farmer",
    params={'target_apy': 0.08},
    virtual_capital=10000
)

# Mutate successful agent
mutated_agent = arena.mutate_agent(parent_agent)  # ±20% param variation
```

### **Competition:**
```python
# Calculate fitness
fitness = agent.calculate_fitness()
# Fitness = (Returns × 0.3) + (Sharpe × 0.4) - (Drawdown × 0.2) - (Volatility × 0.1)

# Rank all agents
ranked = arena.rank_agents(arena.active_agents)
```

### **Selection:**
```python
# Allocate capital based on fitness
allocations = arena.allocate_capital()
# Top 20% get 60% of capital
# Mid 30% get 30% of capital
# Bottom 50% get 10% of capital
```

### **Death:**
```python
# Kill underperformers
killed = arena.kill_underperformers()
# Conditions:
# - Fitness < 0 for 30+ days
# - Drawdown > 50%
# - Negative returns for 90+ days
# - Sharpe < 0.5 for 60+ days
# - Age > 365 days
```

---

## 🚀 Deployment Phases

### **Phase 1: Foundation (Week 1)** - $0
- ✅ Build agent framework
- ✅ Implement arena manager
- ⏳ Create simulation engine
- ⏳ Deploy 20 test agents
- **Capital:** $0 (all simulated)

### **Phase 2: Proving Grounds (Week 2)** - $10K
- Graduate top 10 simulated agents
- Deploy $1K real capital to each
- Track 30-day live performance
- Build arena dashboard
- **Capital:** $10K real money

### **Phase 3: Main Arena (Week 3-4)** - $50K
- Graduate top 5 proving agents
- Deploy $50K to main arena
- Implement dynamic rebalancing
- Enable birth/death mechanics
- **Capital:** $50K real money

### **Phase 4: Full Scale (Month 2)** - $200K
- Scale to 10-15 active agents
- 50+ agents in simulation layer
- Full evolutionary loop
- **Capital:** $200K real money

### **Phase 5: Paradise (Month 3+)** - Autonomous
- Hands-off operation
- Self-optimizing returns
- 25-50% APY target
- **Capital:** $373K+ (growing)

---

## 📊 API Endpoints (Planned)

```
GET  /api/arena/overview        # Arena statistics
GET  /api/arena/agents          # All agents ranked
GET  /api/arena/agents/{id}     # Agent details
GET  /api/arena/simulation      # Simulation layer stats
POST /api/arena/spawn           # Spawn new agent
POST /api/arena/evolve          # Run evolution cycle
```

---

## 💰 Financial Projections

**Conservative (25% APY):**
- Month 1: $200K → $204K (+$4K)
- Month 6: $200K → $225K (+$25K)
- Month 12: $200K → $250K (+$50K)

**Moderate (35% APY):**
- Month 1: $200K → $206K (+$6K)
- Month 6: $200K → $235K (+$35K)
- Month 12: $200K → $270K (+$70K)

**Aggressive (50% APY):**
- Month 1: $200K → $208K (+$8K)
- Month 6: $200K → $250K (+$50K)
- Month 12: $200K → $300K (+$100K)

**Target:** 35% blended APY = $83K profit/year

---

## 🔒 Risk Management

**Position Limits:**
- Max 30% in single agent
- Max 10% in single strategy type
- Max 50% in high-risk strategies

**Drawdown Controls:**
- Agent killed if drawdown > 50%
- Arena paused if drawdown > 30%
- Capital reduced if drawdown > 20%

**Protocol Diversification:**
- Max 20% in single DeFi protocol
- Only audited protocols
- Insurance preferred

---

## 📚 Documentation

**Complete Spec:**
`/docs/coordination/TREASURY_ARENA_SPEC.md` (30+ pages)

**Resource SSOT:**
`/docs/coordination/CAPITAL_VISION_SSOT.md` (includes arena section)

**Boot Sequence:**
`/docs/coordination/MEMORY/BOOT.md` (mentions arena in Step 1)

---

## 🎯 Next Steps

1. **Review Spec** - Read TREASURY_ARENA_SPEC.md
2. **Approve Build** - Confirm budget allocation
3. **Phase 1** - Build simulation engine
4. **Phase 2** - Deploy proving grounds ($10K)
5. **Phase 3** - Launch main arena ($50K)
6. **Phase 4** - Scale to $200K

---

## 🌐 Integration

**Dashboard:** https://fullpotential.com/dashboard/arena (coming soon)

**Resource SSOT:** Updated automatically via arena manager

**Boot Sequence:** All sessions see arena status on boot

---

**Status:** READY TO BUILD ✅

🏛️⚡💎 **$373K → $5T through evolutionary treasury management**
