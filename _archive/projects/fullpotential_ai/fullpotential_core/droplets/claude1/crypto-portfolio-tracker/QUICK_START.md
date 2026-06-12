# 🚀 Quick Start - 5 Minutes to Live Dashboard

## Step 1: Install (2 min)

```bash
# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Your Positions (2 min)

```bash
# Copy example file
cp data/positions.example.json data/positions.json

# Edit with your real positions
nano data/positions.json  # or use your favorite editor
```

## Step 3: Run (1 min)

```bash
# Start the dashboard
python run.py
```

## Step 4: Open in Browser

Go to: **http://localhost:8002/dashboard/money**

That's it! 🎉

---

## What to Edit in positions.json

Replace the example data with your actual holdings:

```json
{
  "spot_positions": [
    {
      "asset": "BTC",           ← Your crypto
      "amount": 1.0,            ← How much you own
      "entry_price": 45000,     ← What you bought at
      "current_price": 50000,   ← Current market price
      "location": "Wallet 1"    ← Where it's stored
    }
  ],
  "leveraged_positions": [
    {
      "asset": "BTC",
      "amount": 0.5,
      "leverage": 2.0,          ← 2x, 3x, 5x, etc.
      "entry_price": 45000,
      "current_price": 50000,
      "liquidation_price": 30000,  ← CRITICAL!
      "margin_deployed": 11250,
      "exchange": "Binance"
    }
  ]
}
```

## Troubleshooting

**Port 8002 already in use?**
```bash
python run.py --port 8080
```

**Can't install dependencies?**
```bash
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

**Dashboard not loading?**
- Check that run.py started without errors
- Try http://127.0.0.1:8002/dashboard/money
- Check firewall settings

## Need Help?

- Check README.md for full documentation
- Email: [your support email]
- Open an issue on GitHub

---

**You're now tracking your portfolio like a pro!** 💰
