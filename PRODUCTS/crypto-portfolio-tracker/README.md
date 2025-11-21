# 💰 Crypto Portfolio Tracker - Professional Dashboard

Track your crypto portfolio like a $354K+ professional trader.

## ✨ Features

- **Real-time Position Tracking** - Spot + Leveraged positions across all wallets
- **Liquidation Risk Monitoring** - Know exactly when you're at risk
- **Automatic P&L Calculations** - Track gains/losses in real-time
- **Multi-Wallet Support** - Consolidate all your holdings in one view
- **Beautiful Web Dashboard** - Responsive, modern interface
- **JSON API** - Integrate with other tools and bots

## 🚀 Quick Start (15 minutes)

### Prerequisites
- Python 3.9+
- pip
- 5 minutes of your time

### Installation

```bash
# 1. Clone/download this repository
cd crypto-portfolio-tracker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your positions
cp data/positions.example.json data/positions.json
# Edit data/positions.json with your actual holdings

# 4. Run the dashboard
python run.py

# 5. Open in browser
# http://localhost:8002/dashboard/money
```

That's it! You're tracking your portfolio like a pro.

## 📊 Screenshots

[Dashboard showing real-time positions, P&L, and liquidation risks]

## 🛠️ Tech Stack

- **Backend:** Python 3.9+, FastAPI
- **Frontend:** HTML5, CSS3, vanilla JavaScript
- **Database:** JSON file (easily upgradable to PostgreSQL)
- **API:** RESTful JSON endpoints

## 📖 Documentation

### Adding Positions

Edit `data/positions.json`:

```json
{
  "spot_positions": [
    {
      "asset": "BTC",
      "amount": 1.0,
      "entry_price": 45000,
      "current_price": 50000,
      "location": "Wallet 1"
    }
  ],
  "leveraged_positions": [
    {
      "asset": "BTC",
      "amount": 0.5,
      "leverage": 2.0,
      "entry_price": 45000,
      "current_price": 50000,
      "liquidation_price": 30000,
      "margin_deployed": 11250,
      "exchange": "Binance"
    }
  ]
}
```

### API Endpoints

- `GET /api/treasury/positions` - Get all positions with P&L
- `GET /api/treasury/summary` - Get portfolio summary
- `GET /dashboard/money` - Web dashboard UI

### Customization

**Change port:**
```bash
python run.py --port 8080
```

**Add live price feeds:**
See `docs/LIVE_PRICES.md` for integration with CoinGecko, Binance APIs

**Multi-user setup:**
See `docs/MULTI_USER.md` for authentication and user management

## 🎯 Perfect For

- Crypto traders managing $10K+ portfolios
- Anyone with leveraged positions
- Developers wanting portfolio tracking
- Teams needing portfolio transparency
- Anyone tired of spreadsheets

## 💡 Use Cases

1. **Risk Management** - Monitor liquidation distances in real-time
2. **Performance Tracking** - See exactly how each position is performing
3. **Portfolio Optimization** - Identify winners and losers quickly
4. **Team Transparency** - Share dashboard with co-investors
5. **Tax Preparation** - Export all positions for accounting

## 📁 Project Structure

```
crypto-portfolio-tracker/
├── app/
│   ├── main.py              # FastAPI application
│   ├── routers/
│   │   └── money.py         # Treasury endpoints
│   └── templates/
│       └── money.html       # Dashboard UI
├── data/
│   ├── positions.json       # Your positions (you create this)
│   └── positions.example.json  # Example structure
├── docs/
│   ├── LIVE_PRICES.md       # Add live price feeds
│   ├── MULTI_USER.md        # Multi-user setup
│   └── DEPLOYMENT.md        # Deploy to production
├── requirements.txt         # Python dependencies
├── run.py                   # Start script
└── README.md               # This file
```

## 🔒 Security

- **Never commit positions.json** - Contains your real holdings
- **Use environment variables** for API keys
- **Enable authentication** for production deployments
- See `docs/SECURITY.md` for best practices

## 🚢 Deployment

### Local Development
```bash
python run.py
```

### Production (with Nginx)
See `docs/DEPLOYMENT.md` for full production setup with:
- Nginx reverse proxy
- SSL/TLS certificates
- Process management (systemd/supervisor)
- Automated backups

## 📈 Advanced Features

### Live Price Integration
```bash
# Add your API keys
export COINGECKO_API_KEY="your_key"
export BINANCE_API_KEY="your_key"

# Enable live prices
python run.py --live-prices
```

### Liquidation Alerts
```bash
# Set up email/SMS alerts
python scripts/setup_alerts.py
```

### Historical Tracking
```bash
# Enable position history
python scripts/enable_history.py
```

## 🤝 Support

- **Documentation:** See `docs/` folder
- **Issues:** Open an issue in this repository
- **Email:** support@example.com
- **Discord:** Join our community [link]

## 📄 License

MIT License - Use commercially, modify, distribute freely.

## ✅ Satisfaction Guarantee

If you can't get this running in 15 minutes, contact us for a full refund.

---

**Built by a crypto trader, for crypto traders.**

Managing $354K+ portfolio with this exact system.

Start tracking your portfolio professionally in the next 15 minutes 🚀
