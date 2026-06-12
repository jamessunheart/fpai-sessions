# Coracle Data Source Integration Guide

This guide explains how to integrate additional data sources for on-chain metrics and options data.

## Current Data Sources (Working)

### WhaleTrack API (Primary)
- **URL**: `http://localhost:8600/api/coracle/signals/{symbol}`
- **Signals**: Funding Rate, CVD, Liquidations, Open Interest, Long/Short Ratio, Fear & Greed
- **No additional setup required** - uses existing WhaleTrack service

### Hyperliquid (Direct)
- **URL**: `https://api.hyperliquid.xyz/info`
- **Signals**: Real-time prices, L2 orderbook (for BAI/OBS), Recent trades (for WADI)
- **No API key required** - public endpoints

### Alternative.me
- **URL**: `https://api.alternative.me/fng/`
- **Signals**: Fear & Greed Index
- **No API key required** - public endpoint

---

## Optional Data Sources

### 1. Glassnode (On-Chain Metrics)

**What it provides:**
- SOPR (Spent Output Profit Ratio)
- MVRV (Market Value to Realized Value)
- NUPL (Net Unrealized Profit/Loss)
- Difficulty Ribbon, Realized Cap, etc.

**Setup:**
1. Sign up at https://glassnode.com
2. Choose plan:
   - **Standard** (~$29/month): Basic metrics, hourly resolution
   - **Advanced** (~$79/month): More metrics, real-time
   - **Professional**: Full suite

3. Generate API key in dashboard

4. Add to environment:
```bash
export GLASSNODE_API_KEY=your_api_key_here
```

**Signal usage in Sacred Gate:**
- SOPR informs holder behavior (profit taking vs capitulation)
- MVRV indicates market valuation (overvalued/undervalued zones)
- NUPL shows aggregate profit/loss state

**API Example:**
```python
import httpx

async def fetch_sopr():
    url = "https://api.glassnode.com/v1/metrics/indicators/sopr"
    params = {
        "a": "BTC",
        "api_key": "your_key"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        return data[-1]["v"]  # Latest value
```

---

### 2. Deribit (Options Data - FREE)

**What it provides:**
- Options open interest (for PCR calculation)
- Strike distribution (for Max Pain)
- Estimated GEX (from OI and strike data)

**Setup:**
No API key required - uses public endpoints.

**Endpoints:**
```
GET https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=option
GET https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd
```

**Signal usage in Sacred Gate:**
- GEX < 0 = Gamma Key passes (volatility expansion regime)
- PCR is contrarian indicator (extreme values signal reversals)

---

### 3. Laevitas (Premium Options Data)

**What it provides:**
- Pre-calculated GEX (more accurate than Deribit estimate)
- Options flow (smart money tracking)
- IV surfaces
- Historical data

**Setup:**
1. Sign up at https://laevitas.ch
2. Choose plan (pricing varies)
3. Get API key

4. Add to environment:
```bash
export LAEVITAS_API_KEY=your_key_here
```

**When to use Laevitas vs Deribit:**
- Deribit (free): Good enough for basic GEX estimation
- Laevitas (paid): Better accuracy, more features

---

### 4. CryptoQuant (Alternative to Glassnode)

**What it provides:**
- Similar on-chain metrics to Glassnode
- Exchange flow data
- Miner metrics

**Setup:**
1. Sign up at https://cryptoquant.com
2. Get API key

```bash
export CRYPTOQUANT_API_KEY=your_key_here
```

---

## Integration Architecture

```
                    ┌─────────────────────┐
                    │   Coracle Engine    │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  WhaleTrack   │    │  Hyperliquid  │    │ External APIs │
│  (Primary)    │    │   (Direct)    │    │  (Optional)   │
└───────────────┘    └───────────────┘    └───────────────┘
        │                      │                      │
        │                      │           ┌─────────┼─────────┐
        │                      │           │         │         │
        ▼                      ▼           ▼         ▼         ▼
   ┌─────────┐            ┌─────────┐  ┌──────┐ ┌───────┐ ┌─────────┐
   │Coinglass│            │ L2 Book │  │Glass-│ │Deribit│ │Laevitas │
   │via WT   │            │ Trades  │  │ node │ │(free) │ │ (paid)  │
   └─────────┘            └─────────┘  └──────┘ └───────┘ └─────────┘
```

## Priority Order for Additional Data

1. **Deribit** (FREE) - Add first for GEX signal
   - Improves Sacred Gate gamma key accuracy
   - No cost, easy integration

2. **Glassnode Standard** (~$29/month) - Add second
   - Enables SOPR, MVRV, NUPL
   - Good value for on-chain insights

3. **Laevitas** (variable) - Add if needed
   - Only if free Deribit GEX is insufficient
   - More accurate gamma calculations

---

## Testing Data Sources

After adding API keys, test with:

```bash
# Check health to see data source status
curl http://localhost:8650/health

# Get signals to verify data
curl http://localhost:8650/api/signals/BTC

# Full analysis with all sources
curl -X POST http://localhost:8650/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker": "BTC"}'
```

The response will show which signals are available and their sources.

---

## Cost Summary

| Source | Monthly Cost | Signals Enabled |
|--------|-------------|-----------------|
| WhaleTrack | FREE (existing) | FR, CVD, OI, L/S, FGI |
| Hyperliquid | FREE | BAI, OBS, WADI, Price |
| Deribit | FREE | PCR, Max Pain, Est. GEX |
| Glassnode Standard | $29 | SOPR, MVRV, NUPL |
| Laevitas | ~$50+ | Accurate GEX, Flows |

**Recommended minimum setup**: WhaleTrack + Hyperliquid + Deribit = **$0/month**

**Full professional setup**: Add Glassnode = **$29/month**


