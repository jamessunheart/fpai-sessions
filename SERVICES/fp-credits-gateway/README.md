# FP Credits Gateway

**The unified credits API for the Full Potential ecosystem.**

Port: `8765`  
Production URL: `https://fullpotential.ai/services/credits`

---

## 🎯 Purpose

The FP Credits Gateway consolidates all credit operations into a single, secure API that any service (on-server or external) can easily integrate with.

### Features

- **Unified API** - One endpoint for all credit operations
- **Multi-currency** - FP Credits, Cora Credits, USD
- **API Key Auth** - Secure access for external services
- **Real-time Updates** - WebSocket for balance changes
- **Rate Limiting** - Prevent abuse
- **Audit Trail** - Complete transaction history
- **Database Persistence** - SQLite (dev) / PostgreSQL (production)
- **Batch Operations** - Bulk credit/debit for efficiency
- **Admin Dashboard** - Visual management at `/admin`
- **Integration Adapters** - Drop-in replacements for WhiteRock & Autonomy
- **Python SDK** - `from fp_credits import FPCredits`
- **JavaScript SDK** - `import { FPCredits } from './fp-credits.js'`

---

## 🚀 Quick Start

### 1. Install SDK

```bash
pip install requests
# Copy sdk/fp_credits.py to your project
```

### 2. Get API Key

Contact admin or use the admin API to create a key:

```bash
curl -X POST http://198.54.123.234:8760/api/keys \
  -H "X-API-Key: YOUR_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "my-service",
    "description": "My awesome service",
    "permissions": ["read", "debit"]
  }'
```

### 3. Use in Your Service

```python
from fp_credits import FPCredits

# Initialize
credits = FPCredits(api_key="fps_your_key_here")

# Check balance
balance = credits.get_balance("user:123")
print(f"FP Credits: {balance.fp_credits}")

# Charge for service usage
credits.charge("user:123", 10.0, "AI Chat Session")

# Award credits
credits.credit("user:123", 5.0, "Referral bonus")
```

---

## 📚 API Reference

### Authentication

All endpoints require an API key via header:
- `X-API-Key: fps_your_key_here`
- Or: `Authorization: Bearer fps_your_key_here`

### Endpoints

#### Health Check
```
GET /health
```
No auth required. Returns service status.

#### Get Balance
```
GET /api/balance/{account_id}
```
Returns current balance for all credit types.

#### Credit Account
```
POST /api/credit
{
  "account_id": "user:123",
  "amount": 10.0,
  "credit_type": "fp_credits",
  "reason": "Welcome bonus",
  "reference_id": "optional-ref",
  "metadata": {}
}
```

#### Debit Account
```
POST /api/debit
{
  "account_id": "user:123",
  "amount": 5.0,
  "credit_type": "fp_credits",
  "reason": "Service usage",
  "reference_id": "session-123"
}
```

#### Transfer Credits
```
POST /api/transfer
{
  "from_account": "user:123",
  "to_account": "user:456",
  "amount": 25.0,
  "credit_type": "fp_credits",
  "reason": "Gift"
}
```

#### Exchange Credits
```
POST /api/exchange
{
  "account_id": "user:123",
  "from_type": "fp_credits",
  "to_type": "cora_credits",
  "amount": 10.0
}
```

#### Transaction History
```
GET /api/transactions/{account_id}?limit=50
```

### WebSocket

Connect for real-time balance updates:
```javascript
const ws = new WebSocket('ws://198.54.123.234:8760/ws/user:123');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Balance update:', data.balances);
};
```

---

## 💎 Credit Types

| Type | Symbol | Exchange Rate |
|------|--------|---------------|
| FP Credits | FPC | 1 FPC = $1 USD |
| Cora Credits | CC | 10 CC = 1 FPC |
| USD | $ | 1 USD = 1 FPC |

---

## 🔐 Permissions

API keys can have these permissions:
- `read` - View balances and transactions
- `credit` - Add credits to accounts
- `debit` - Deduct credits from accounts
- `transfer` - Transfer between accounts
- `exchange` - Exchange credit types
- `admin` - Full access including key management

---

## 🏗️ Integration Examples

### Python Service

```python
from fp_credits import FPCredits, require_credits

credits = FPCredits(api_key=os.environ["FP_CREDITS_API_KEY"])

@app.post("/ai/chat")
async def chat(user_id: str, message: str):
    # Check and charge
    if not credits.has_sufficient_balance(user_id, 10.0):
        raise HTTPException(402, "Insufficient credits")
    
    credits.charge(user_id, 10.0, "AI Chat", message[:50])
    
    # Do the work...
    return {"response": "..."}
```

### JavaScript/Node.js

```javascript
const response = await fetch('http://198.54.123.234:8760/api/debit', {
  method: 'POST',
  headers: {
    'X-API-Key': process.env.FP_CREDITS_API_KEY,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    account_id: `user:${userId}`,
    amount: 10.0,
    credit_type: 'fp_credits',
    reason: 'Premium feature access'
  })
});
```

### cURL

```bash
# Check balance
curl http://198.54.123.234:8760/api/balance/user:123 \
  -H "X-API-Key: fps_your_key"

# Debit credits
curl -X POST http://198.54.123.234:8760/api/debit \
  -H "X-API-Key: fps_your_key" \
  -H "Content-Type: application/json" \
  -d '{"account_id":"user:123","amount":10,"reason":"Test"}'
```

---

## 🌐 External Service Integration

For services outside the FPAI server:

1. **Request API Key** - Contact admin with your service name
2. **Whitelist IP** (optional) - For enhanced security
3. **Use Production URL** - `https://fullpotential.ai/api/credits`
4. **Handle Errors** - Especially 402 (insufficient funds) and 429 (rate limit)

---

## 📊 Deployment

### Local Development

```bash
cd SERVICES/fp-credits-gateway
pip install -r requirements.txt
python app/main.py
```

### Production (Server)

```bash
# Deploy
scp -r SERVICES/fp-credits-gateway root@198.54.123.234:/opt/fpai/

# Create service
ssh root@198.54.123.234 << 'EOF'
cat > /etc/systemd/system/fpai-credits-gateway.service << 'SERVICE'
[Unit]
Description=FP Credits Gateway
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/fp-credits-gateway
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8760
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable fpai-credits-gateway
systemctl start fpai-credits-gateway
EOF
```

### Nginx Configuration

Add to `/etc/nginx/sites-available/fullpotential.ai`:

```nginx
location /services/credits {
    proxy_pass http://127.0.0.1:8760/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

location /api/credits {
    proxy_pass http://127.0.0.1:8760/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## 🔗 Related Services

- **WhiteRock API** (8750) - Member/Provider management
- **Cora Credits Bridge** (8755) - Costa Rica experiences
- **Contribution Bridge** (8053) - Developer rewards

---

## 🔌 Integration Adapters

### WhiteRock API Migration

Drop-in replacement for the existing WhiteRock CreditsService:

```python
# In your WhiteRock API code, replace:
# from services.credits import CreditsService

# With:
from fp_credits_gateway.integrations import WhiteRockCreditsAdapter

# Same interface, now uses the gateway
credits = WhiteRockCreditsAdapter()
await credits.credit_member(member_id, 10.0, "welcome_bonus", "Welcome!")
await credits.transfer_member_to_provider(member_id, provider_id, 50.0)
```

### Autonomy Optimizer Migration

Drop-in replacement for the contributor credits ledger:

```python
# In your Autonomy Optimizer code, replace:
# from credits import credit_ledger

# With:
from fp_credits_gateway.integrations import ContributorCreditsAdapter

credits = ContributorCreditsAdapter()
await credits.award_credits("contributor_123", 100, "API key used")
await credits.record_api_usage("contributor_123", "key_abc", calls=5)
```

---

## 📁 Project Structure

```
fp-credits-gateway/
├── app/
│   ├── main.py          # FastAPI application
│   ├── database.py      # SQLAlchemy models & repos
│   ├── services.py      # Business logic
│   └── static/
│       ├── index.html   # Public dashboard
│       └── admin.html   # Admin dashboard
├── sdk/
│   ├── fp_credits.py    # Python SDK
│   ├── fp-credits.js    # JavaScript SDK
│   └── fp-credits.d.ts  # TypeScript types
├── integrations/
│   ├── whiterock_adapter.py   # WhiteRock drop-in
│   └── autonomy_adapter.py    # Autonomy drop-in
├── README.md
├── SPEC.md
└── requirements.txt
```

---

## 🌐 URLs

| Endpoint | Description |
|----------|-------------|
| `/` | Public credits dashboard |
| `/admin` | Admin management dashboard |
| `/docs` | Swagger API documentation |
| `/health` | Health check endpoint |
| `/api/*` | REST API endpoints |
| `/ws/{account_id}` | WebSocket for real-time updates |

---

Built with ⚡ by Full Potential AI

