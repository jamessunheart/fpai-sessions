# Coracle Prediction Engine

High-frequency quantitative engine that processes multi-timeframe signals to generate probability-weighted trading contracts with adaptive risk management.

## Features

- **60+ Signals** across 4 assets (BTC, ETH, XRP, SOL)
- **Sacred Three-Key Gate** mandatory validation before contract generation
- **Non-linear Confluence Engine** with tier-weighted signal aggregation
- **Dynamic Stop-Loss** with ATR adjustment and liquidation buffer
- **Multi-Target Take Profit** (3 levels with probability decay)
- **Snowball Compounding** strategy with preservation mode
- **Real-time WebSocket** streaming for fast signals

## Quick Start

### Local Development

```bash
# Clone and navigate
cd SERVICES/coracle-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Start service
uvicorn app.main:app --reload --port 8650
```

### Docker

```bash
# Start all services (Coracle + PostgreSQL + Redis)
docker-compose up -d

# Check logs
docker-compose logs -f coracle-engine
```

### Production Deployment

```bash
# Deploy to server
./infra/scripts/deploy-coracle-engine.sh
```

## API Endpoints

### Analysis

```bash
# Generate trading contract
curl -X POST http://localhost:8650/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker": "BTC", "direction": "LONG"}'

# Get signal snapshot
curl http://localhost:8650/api/signals/BTC

# Check sacred gate
curl "http://localhost:8650/api/gate-check/BTC?direction=LONG"
```

### Contracts

```bash
# List contracts
curl http://localhost:8650/api/contracts

# Get contract stats
curl http://localhost:8650/api/contracts/stats/summary

# Resolve contract
curl -X POST http://localhost:8650/api/contracts/{id}/resolve \
  -H "Content-Type: application/json" \
  -d '{"outcome": "WIN", "exit_price": 105000}'
```

### WebSocket

```javascript
// Connect to signal stream
const ws = new WebSocket('ws://localhost:8650/ws/stream');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};

// Subscribe to specific symbols
ws.send(JSON.stringify({
  type: 'subscribe',
  symbols: ['BTC', 'ETH']
}));
```

## Signal Tiers

| Tier | Weight | Signals | Update Frequency |
|------|--------|---------|------------------|
| LIQUIDITY | 35% | BAI, SDS, BAR, OBS, LV, LCP | 100ms-1min |
| WHALE | 25% | WADI, WC, SD, ENF, SFR | 1-5min |
| DERIVATIVES | 20% | GEX, OID, PCR, CVD, MP | 15min-1h |
| FUNDING | 15% | FR, FRM, CEFS, FW | 1-8h |
| ON_CHAIN | 10% | SOPR, MVRV, NUPL, DF | 1-24h |
| TECHNICAL | 10% | MS, BOS, VRC, HHL | 1-60min |
| SENTIMENT | 5% | FGI, BTCD | 1-24h |

## Sacred Three-Key Gate

All three conditions must pass before contract generation:

1. **Whale Key**: WADI alignment with direction
   - LONG: WADI > 0.4 (whales accumulating)
   - SHORT: WADI < -0.4 (whales distributing)

2. **Liquidity Key**: LCP < 2.5 (no cascade risk)

3. **Gamma Key**: GEX < 0 (volatility expansion)

## Adding External Data Sources

### On-Chain (Glassnode)

```bash
# Get API key from https://glassnode.com (~$29/month)
export GLASSNODE_API_KEY=your_key_here
```

Enables: SOPR, MVRV, NUPL signals

### Options (Deribit/Laevitas)

```bash
# Deribit is free (no key needed)
# For Laevitas (paid): https://laevitas.ch
export LAEVITAS_API_KEY=your_key_here
```

Enables: GEX, PCR, Max Pain signals

## Architecture

```
SERVICES/coracle-engine/
├── app/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration
│   ├── models.py         # Pydantic models
│   └── routers/          # API endpoints
├── engine/
│   ├── ingestor.py       # Signal collection
│   ├── processor.py      # Signal computation
│   ├── sacred_gate.py    # Gate validation
│   ├── confluence.py     # Score calculation
│   ├── contract_generator.py  # Contract creation
│   └── compounding.py    # Capital management
├── signals/
│   ├── onchain.py        # Glassnode integration
│   └── options.py        # Deribit/Laevitas
└── data/
    ├── database.py       # PostgreSQL
    └── cache.py          # Redis
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Grade A Win Rate | >65% |
| Brier Score | <0.25 |
| Signal Latency (P95) | <100ms |
| Contract Generation | <500ms |
| System Uptime | >99.9% |

## License

Internal use only - Full Potential AI


