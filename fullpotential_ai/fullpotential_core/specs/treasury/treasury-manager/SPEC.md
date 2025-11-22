# treasury-manager - SPECS

**Created:** 2025-11-15
**Status:** Phase 1 Complete (Market Intelligence), Phase 2 In Progress

---

## Purpose

Intelligent DeFi portfolio management system autonomously managing $400K treasury across Base Yield (60%) and Tactical (40%) allocations. Uses AI-driven decision making via Claude API, real-time market intelligence, and automated rebalancing to achieve 25-50% APY target.

---

## Requirements

### Functional Requirements
- [ ] Real-time market data fetching (BTC/ETH prices, MVRV, funding rates, Fear & Greed)
- [ ] Market phase detection (Accumulation, Euphoria, Top, Bear)
- [ ] Allocation signal generation based on market intelligence
- [ ] AI-powered allocation decisions using Claude
- [ ] Portfolio state tracking (positions, balances, allocations)
- [ ] DeFi protocol integration (Aave, Pendle, Curve)
- [ ] Automated rebalancing based on MVRV thresholds
- [ ] Position execution with slippage protection
- [ ] Gas optimization for transactions
- [ ] Risk management and safety checks
- [ ] Performance tracking and analytics
- [ ] Dashboard for real-time monitoring
- [ ] Decision logging and learning system

### Non-Functional Requirements
- [ ] Performance: Market data fetch < 5 seconds, decision cycle < 30 seconds
- [ ] Safety: All large moves (>$50K) require human approval, position limits enforced
- [ ] Security: Private keys encrypted, transaction simulation before execution
- [ ] Reliability: Graceful handling of API failures, retry logic for all operations
- [ ] Data caching: 5-minute cache for market data to reduce API calls
- [ ] Logging: Complete audit trail of all decisions and transactions

---

## API Specs

### Endpoints

**GET /market/data**
- **Purpose:** Get current market intelligence
- **Input:** None
- **Output:** BTC/ETH prices, MVRV, funding rates, Fear & Greed, market phase
- **Success:** 200 OK
- **Errors:** 500 if data fetch fails

**GET /market/signal**
- **Purpose:** Get current allocation signal
- **Input:** None
- **Output:** Recommended allocations, confidence, reasoning
- **Success:** 200 OK
- **Errors:** 500 if signal generation fails

**GET /portfolio/status**
- **Purpose:** Get current portfolio state
- **Input:** None
- **Output:** Total value, positions, allocations, performance
- **Success:** 200 OK
- **Errors:** 500 if state unavailable

**POST /portfolio/rebalance**
- **Purpose:** Execute rebalancing based on current signal
- **Input:** Optional: force (bool), max_slippage (float)
- **Output:** Rebalancing plan, transactions, status
- **Success:** 202 Accepted
- **Errors:** 400 if invalid params, 403 if requires approval

**GET /decisions/pending**
- **Purpose:** List decisions awaiting human approval
- **Input:** None
- **Output:** Array of pending decisions
- **Success:** 200 OK
- **Errors:** 500 if unavailable

**POST /decisions/{id}/approve**
- **Purpose:** Approve or reject pending decision
- **Input:** decision_id, approved (bool), notes
- **Output:** Decision result
- **Success:** 200 OK
- **Errors:** 404 if not found

**GET /performance/metrics**
- **Purpose:** Get performance analytics
- **Input:** Optional: time_range
- **Output:** Returns, APY, Sharpe ratio, drawdown, trade history
- **Success:** 200 OK
- **Errors:** 500 if unavailable

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "ai_status": "connected", "protocols_status": {...}}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

### Data Models

```python
class MarketData:
    btc_price: float
    eth_price: float
    mvrv_z_score: float
    funding_rate: float
    fear_greed_index: int  # 0-100
    market_phase: MarketPhase  # Enum
    timestamp: datetime

class MarketPhase(Enum):
    ACCUMULATION = "accumulation"
    EUPHORIA = "euphoria"
    TOP = "top"
    BEAR = "bear"

class AllocationSignal:
    mode: str  # "conservative", "tactical", "aggressive", "hedge"
    target_allocations: dict  # {"base_yield": 0.6, "tactical": 0.4}
    confidence: float  # 0-1
    reasoning: str
    trigger: str  # What triggered this signal
    recommended_actions: List[str]
    risk_level: str  # "low", "medium", "high"

class Position:
    protocol: str  # "aave", "pendle", "curve"
    asset: str  # "USDC", "ETH", etc.
    amount: float
    value_usd: float
    apy: float
    entered_at: datetime
    current_return: float

class PortfolioState:
    total_value_usd: float
    positions: List[Position]
    cash_balance: float
    allocations: dict  # Current vs target
    last_rebalance: datetime
    performance_24h: float
    performance_7d: float
    performance_30d: float

class RebalancingPlan:
    plan_id: str
    current_allocations: dict
    target_allocations: dict
    required_transactions: List[Transaction]
    estimated_gas_cost: float
    estimated_slippage: float
    requires_approval: bool
    risk_level: str

class Transaction:
    tx_type: str  # "deposit", "withdraw", "swap"
    protocol: str
    from_asset: str
    to_asset: str
    amount: float
    estimated_gas: float
    slippage_tolerance: float
```

---

## Dependencies

### External Services
- CoinGecko: BTC/ETH prices (50 calls/min free)
- Glassnode: MVRV Z-Score ($500/month or manual fallback)
- Coinglass: Funding rates (free API)
- Alternative.me: Fear & Greed Index (free, no key)
- Claude API (Anthropic): AI decision making
- Aave: Yield protocol
- Pendle: PT strategies
- Curve: LP positions
- 1inch: Token swaps
- Ethereum RPC: Transaction execution
- Arbitrum RPC: Alternative chain

### APIs Required
- Anthropic Claude API: Allocation decisions
- DeFi protocol APIs: Position management
- Web3 RPC: Transaction execution
- Market data APIs: Real-time intelligence

### Data Sources
- PostgreSQL: State, decisions, performance history
- State files: Live portfolio state (JSON)
- Blockchain: On-chain position data

---

## Success Criteria

How do we know this works?

- [ ] Market intelligence fetches data from all 5 sources
- [ ] Market phase detected correctly
- [ ] Allocation signals generated with reasoning
- [ ] AI makes allocation decisions via Claude
- [ ] Portfolio state tracked accurately
- [ ] Rebalancing triggered at correct MVRV thresholds
- [ ] At least 1 successful position execution
- [ ] Gas optimization working
- [ ] Safety bounds enforced (max position size, etc.)
- [ ] Performance metrics calculated correctly
- [ ] Dashboard displays real-time data
- [ ] System runs autonomously for 7+ days

---

## Strategy Overview

### Base Yield (60% - $240K)
**Goal:** Stable 6.5% APY
**Protocols:**
- Aave: USDC lending
- Pendle: PT positions
- Curve: Stablecoin LPs

**Characteristics:**
- Low risk
- Predictable returns
- Minimal management

### Tactical (40% - $160K)
**Goal:** 50-100% returns via market timing
**Approach:** Dynamic allocation based on MVRV

**MVRV Thresholds:**
- MVRV < 0: Accumulation → 100% in BTC/ETH
- MVRV 0-3: Euphoria → 60% in BTC/ETH
- MVRV > 3.5: Top forming → Start selling (25% of tactical)
- MVRV > 5: Sell 50% of tactical
- MVRV > 7: Sell 67% of tactical
- MVRV > 9: Exit 100% → Stablecoins

---

## Market Intelligence System

**Data Sources:**
1. **CoinGecko:** BTC/ETH prices
2. **MVRV Z-Score:** Cycle indicator (manual or Glassnode)
3. **Coinglass:** Funding rates
4. **Alternative.me:** Fear & Greed Index
5. **Deribit:** Options data (future)

**Intelligence Output:**
- Market phase (Accumulation/Euphoria/Top/Bear)
- Allocation mode (Conservative/Tactical/Aggressive/Hedge)
- Target allocations
- Rebalancing triggers
- Confidence scores
- Reasoning

**Caching:**
- 5-minute cache for all market data
- Reduces API calls
- Ensures consistency during decision cycle

---

## AI Decision Making

**Claude evaluates:**
```python
decision = await claude_client.analyze(
    market_data=current_market_data,
    portfolio_state=current_portfolio,
    signal=allocation_signal,
    safety_bounds=safety_limits
)
```

**Output:**
```python
{
    "decision": "rebalance",
    "target_allocations": {"base": 0.6, "tactical": 0.3, "cash": 0.1},
    "reasoning": "MVRV at 6.2 indicates late euphoria. Reduce tactical exposure by 25%...",
    "risk_assessment": "medium",
    "requires_approval": True  # If position > $50K
}
```

---

## Safety System

**Position Limits:**
- Max 40% in volatile assets (hard limit)
- Max 25% in single position
- Min protocol TVL: $10M
- Max risk score: 5/10

**Transaction Limits:**
- Max $50K without approval
- Max 10 trades per day
- Gas price limit: 100 gwei

**Emergency Procedures:**
- Emergency stop button
- Automatic position exit on black swan
- Human approval for large moves

---

## Performance Targets

**Conservative (6 months):**
- Base yield: $15,600 (6.5% APY × $240K)
- Tactical: +50% = $80,000
- **Total: $95,600 (24% return)**

**Optimistic (6 months):**
- Base yield: $15,600
- Tactical: +100% = $160,000
- **Total: $175,600 (44% return)**

**Comparison:**
- Static 6.5% yield: $13,000
- Buy & hold BTC: ~$80,000 (if +50%)
- **Dynamic strategy: 2-3x better**

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8600 (planned)
- **Database:** PostgreSQL
- **Resource limits:**
  - Memory: 1GB max
  - CPU: 1 core
  - Storage: 2GB for database and state
- **Response time:** Decision cycle < 30 seconds, data fetch < 5 seconds
- **Private keys:** Encrypted, never logged
- **Transaction simulation:** Always before execution

---

## Development Phases

**Phase 1: Market Intelligence** ✅ COMPLETE
- Real-time data fetching
- Market phase detection
- Allocation signal generation
- Data caching

**Phase 2: Portfolio Manager** 🚧 IN PROGRESS
- State tracking
- Position management
- Allocation calculator

**Phase 3: Protocol Integration** 📋 NEXT
- Aave adapter
- Pendle adapter
- Curve adapter
- 1inch adapter

**Phase 4: AI Decision Layer**
- Claude integration
- Daily analysis
- Approval logic

**Phase 5: Rebalancing Engine**
- Transaction planner
- Safe execution
- Gas optimization

**Phase 6: Dashboard & Analytics**
- Real-time monitoring
- Performance tracking
- Decision logging

---

**Next Step:** Complete Portfolio Manager, integrate DeFi protocols, deploy with $400K
