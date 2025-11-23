# Simulation Engine - Complete Guide

## Overview

The Simulation Engine enables risk-free backtesting of treasury agent strategies using historical market data.

## Key Features

✅ **Time Travel** - Replay any historical period at 1x to 1000x speed
✅ **Zero Risk** - All capital is virtual, no real funds at stake
✅ **Data Caching** - Historical data cached locally (no redundant API calls)
✅ **Evolution Cycles** - Automatic spawning/killing of agents
✅ **Performance Metrics** - Sharpe ratio, max drawdown, total return
✅ **Deterministic** - Same inputs = same outputs (reproducible results)

## How It Works

1. **Data Fetching**
   - CoinGecko API: Historical prices for BTC, SOL, ETH
   - DeFi Llama API: Historical APYs for Aave, Pendle, Curve
   - All data cached in SQLite

2. **Time Progression**
   - Start at `start_date`, progress day-by-day to `end_date`
   - Each day: fetch market data, execute agents, take snapshots
   - Configurable speed: 1x (real-time) to 1000x (fast-forward)

3. **Agent Execution**
   - Each agent's `execute_strategy()` called with market data
   - Trades executed in simulation (virtual capital updated)
   - Errors isolated (one crash doesn't kill simulation)

4. **Evolution Cycles**
   - Every N days: kill bottom performers, spawn new mutants
   - Survival of the fittest drives strategy improvement

## CLI Commands

### Backtest
```bash
python3 -m src.cli backtest --days 180 --agents 50 --speed 100
```

Options:
- `--days`: Number of days to simulate
- `--agents`: Initial agent count
- `--speed`: Time multiplier (1-1000x)

### Compare Runs
```bash
python3 -m src.cli compare run-id-1 run-id-2 run-id-3
```

Shows side-by-side comparison of performance metrics.

### List All Runs
```bash
python3 -m src.cli list
```

Displays all completed simulations with summary stats.

## Database Schema

### Tables
1. **market_data** - Cached price/volume data
2. **protocol_data** - Cached APY data
3. **simulation_runs** - Run metadata & results
4. **simulation_snapshots** - Daily agent states

See `migrations/001_create_simulation_tables.sql` for complete schema.

## Performance Benchmarks

| Simulation | Agents | Days | Time (10x) | Data Points |
|-----------|--------|------|------------|-------------|
| Quick Test | 10 | 30 | ~1 min | 120 |
| Standard | 50 | 180 | ~5 min | 9,000 |
| Full Year | 50 | 365 | ~10 min | 18,250 |

## API Rate Limits

- **CoinGecko (free):** 10-50 calls/minute
- **DeFi Llama:** No official limit (we use 1s delay)
- **Caching:** First run fetches data, subsequent runs use cache

## Interpreting Results

### Total Return
```
(Final Capital - Initial Capital) / Initial Capital * 100%
```

### Sharpe Ratio
```
(Average Daily Return / Std Dev of Returns) * sqrt(365)
```
- < 1.0: Poor risk-adjusted returns
- 1.0-2.0: Good
- > 2.0: Excellent

### Max Drawdown
```
Maximum peak-to-trough decline during simulation
```
- < 10%: Very stable
- 10-20%: Moderate volatility
- > 20%: High risk

## Troubleshooting

**"No market data available"**
→ Run with internet connection on first run to fetch data

**"Agent execution failed"**
→ Check agent strategy implementation for bugs

**"Simulation too slow"**
→ Increase `--speed` parameter (up to 1000x)

## Next Steps

After successful backtest:
1. Identify top-performing agents
2. Deploy to Proving Grounds (paper trading)
3. Graduate to Active Arena (real capital)

See main README.md for full system architecture.
