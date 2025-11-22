# Treasury Arena - Data Sources Explained

## 🎯 Current Status

### What's Currently Running:
**SIMULATED DATA** with **REAL STRATEGIES**

- ✅ Agent personalities: REAL (10 unique characters)
- ✅ Agent strategies: REAL (actual DeFi/Trading logic)
- ⚠️ Market data: SIMULATED (random but realistic)
- ⚠️ Trading: SIMULATED (no real capital at risk)

### Current Stats You're Seeing:
- Fitness scores (4.33 to -3.08): Based on simulated trades
- Capital amounts: Simulated performance over 14 days
- Win rates: From simulated market conditions

---

## 📊 Available Data Sources

### 1. **LIVE REAL DATA** (Just Built!)

**What It Is:**
- Real BTC price: **$95,675** (from CoinGecko API)
- Real DeFi APYs: **Aave 8%**, Compound, Pendle (from DeFi Llama)
- Updated every 5 minutes
- FREE public APIs

**Example:**
```python
from src.live_data import get_live_market_data

data = get_live_market_data()
# {
#   'prices': {'BTC': 95675.00},
#   'protocol_apys': {'aave': 0.08, 'compound': 0.06},
#   'data_source': 'LIVE (CoinGecko + DeFi Llama)'
# }
```

### 2. **HISTORICAL REAL DATA**

**What It Is:**
- Last 90 days of real BTC prices
- Real DeFi protocol yields over time
- Can backtest strategies on actual market conditions

**Scripts Available:**
- `run_real_data.py` - Run agents on last 14 days of real data
- `src/data_sources.py` - Full historical data engine (Session A)

---

## 🎮 Three Options for You

### Option 1: Keep Current (Simulated) ✅
**Status Quo**
- Fast iteration
- No API rate limits
- Controlled testing
- Current dashboard works perfectly

### Option 2: Switch to Live Real Data 🔴 LIVE
**What Changes:**
- Agents trade based on REAL current BTC price
- Use REAL current DeFi yields
- Performance reflects actual market conditions
- Updates every 5 minutes

**How to Deploy:**
I can update web/app.py to use `src/live_data.py` instead of random data

### Option 3: Backtest on Historical Real Data 📊
**What Changes:**
- Re-run agents on LAST 30 DAYS of real market data
- See how they would have performed in recent BTC crash
- Real market conditions, no future data leakage

**How to Run:**
```bash
python3 run_real_data.py 30  # Run on last 30 days
```

---

## 📈 Real Data Examples

### BTC Price (Last 7 Days - REAL):
```
2025-11-10: $105,909.07
2025-11-11: $102,960.78
2025-11-12: $101,521.71
2025-11-13: $99,730.45
2025-11-14: $94,456.39
2025-11-15: $95,508.31
2025-11-15: $95,674.94

Change: -8.6% (real market downturn)
```

### DeFi APYs (Current - REAL):
```
Aave USDC:     8.00% APY
Compound DAI:  6.00% APY
Pendle PT-sUSDe: 10.00% APY
```

---

## 💡 Recommendation

**For Entertainment/Demo:** Keep simulated (current)
**For Serious Backtesting:** Use Option 3 (historical real data)
**For Live Trading Simulation:** Use Option 2 (live real data)

The infrastructure is built. Just tell me which option you want!

---

## 🚀 Quick Deploy Commands

### Switch to Live Real Data:
```bash
# I'll update web/app.py to import from src/live_data
./deploy.sh  # Deploy to production
```

### Run Historical Backtest:
```bash
python3 run_real_data.py 30  # 30 days of real data
```

### Check Current Real Data:
```bash
python3 src/live_data.py
# Shows: BTC $95,675, Aave 8% APY (LIVE)
```

---

**Want me to switch it to real data? Just say which option!**
