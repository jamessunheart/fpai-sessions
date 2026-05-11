# Quick Start Guide

## What You Have

✅ **Complete Magnet Trading System** built and ready to deploy

## Next Steps

### 1. Configure Environment (2 minutes)

```bash
cd magnet-trading-system/backend
cp .env.example .env
# Edit .env and add:
# - DATABASE_URL (or use default)
# - EXCHANGE_API_KEY (Binance testnet)
# - EXCHANGE_API_SECRET (Binance testnet)
# - SECRET_KEY (generate random string)
```

### 2. Deploy Backend (5 minutes)

**Option A: Docker (Recommended)**
```bash
cd ../deployment
chmod +x deploy.sh
./deploy.sh
```

**Option B: Local Development**
```bash
cd ../backend
pip install -r requirements.txt
python3 main.py
```

### 3. Start Frontend (3 minutes)

```bash
cd ../frontend/investor-dashboard
npm install
npm run dev
```

### 4. Verify (1 minute)

```bash
# Test backend health
curl http://localhost:8000/health

# Test leverage calculation
curl -X POST http://localhost:8000/api/leverage/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "primary_magnet_price": 44000.0,
    "current_price": 43200.0,
    "magnet_strength": 70.0,
    "conflict_index": 0.3,
    "volatility_pressure": 1.0,
    "atr": 450.0
  }'

# Visit frontend
open http://localhost:3000
```

## What to Configure Next

1. **Binance API** - Get testnet credentials from https://testnet.binance.vision/
2. **Database** - Configure PostgreSQL (or use Docker default)
3. **Integration** - Connect to Registry/Orchestrator if available

## Key Files

- `README.md` - Full documentation
- `DEPLOYMENT_REPORT.md` - Complete build report
- `backend/config.yaml` - System configuration
- `deployment/deploy.sh` - One-command deployment

## Need Help?

See `DEPLOYMENT_REPORT.md` for comprehensive documentation.

**The fund must survive.** 💎
