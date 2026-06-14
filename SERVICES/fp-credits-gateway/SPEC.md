# SPEC - FP Credits Gateway

**Version:** 1.0.0  
**Created:** 2025-11-28  
**Port:** 8760  
**Status:** Development → Ready for Deployment

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The FP Credits Gateway is the **unified credits API** for the entire Full Potential ecosystem. It consolidates credit operations from multiple services into a single, secure, and easily integrable system.

### 1.2 Position in Ecosystem
- **Upstream:** All services that need to charge or reward users
- **Downstream:** User accounts, transaction ledger
- **Role:** The Central Bank of the FP ecosystem

### 1.3 Problem Solved
Previously, credits were fragmented across:
- WhiteRock API (member/provider credits)
- Autonomy Optimizer (contributor rewards)
- Various ad-hoc implementations

This gateway unifies them all with:
- Single API endpoint
- Consistent authentication
- Multi-currency support
- Easy SDK integration

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **Balance Management** - Track FP Credits, Cora Credits, and USD
2. **Credit/Debit Operations** - Add or remove credits with full audit trail
3. **Transfers** - Move credits between accounts
4. **Currency Exchange** - Convert between credit types
5. **API Key Management** - Secure access for external services
6. **Real-time Updates** - WebSocket for live balance changes

### 2.2 Supported Credit Types
| Type | Symbol | Exchange Rate | Purpose |
|------|--------|---------------|---------|
| FP Credits | FPC | 1 FPC = $1 USD | Primary ecosystem currency |
| Cora Credits | CC | 10 CC = 1 FPC | Costa Rica experiences |
| USD | $ | 1 USD = 1 FPC | External settlements |

---

## 3. API SPECIFICATION

### 3.1 UDC Endpoints (Required)

#### Health Check
```
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "service": "fp-credits-gateway",
  "version": "1.0.0",
  "accounts": 150,
  "transactions_total": 5420
}
```

### 3.2 Authentication

All API endpoints (except `/health` and `/`) require authentication via:
- Header: `X-API-Key: fps_your_key_here`
- Or: `Authorization: Bearer fps_your_key_here`

### 3.3 Core Endpoints

#### Get Balance
```
GET /api/balance/{account_id}
```

#### Credit Account
```
POST /api/credit
{
  "account_id": "user:123",
  "amount": 10.0,
  "credit_type": "fp_credits",
  "reason": "Welcome bonus",
  "reference_id": "optional-ref"
}
```

#### Debit Account
```
POST /api/debit
{
  "account_id": "user:123",
  "amount": 5.0,
  "credit_type": "fp_credits",
  "reason": "Service usage"
}
```

#### Transfer
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

#### Exchange
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

### 3.4 WebSocket

```
ws://host:8760/ws/{account_id}
```

Receives real-time balance updates:
```json
{
  "type": "balance_update",
  "account_id": "user:123",
  "balances": {
    "fp_credits": 150.0,
    "cora_credits": 500.0,
    "usd": 0.0
  }
}
```

---

## 4. INTEGRATION GUIDE

### 4.1 Python SDK

```python
from fp_credits import FPCredits

# Initialize
credits = FPCredits(api_key="fps_your_key")

# Check balance
balance = credits.get_balance("user:123")

# Charge for service
credits.charge("user:123", 10.0, "AI Chat Session")

# Award credits
credits.credit("user:123", 5.0, "Referral bonus")
```

### 4.2 HTTP/cURL

```bash
# Check balance
curl http://198.54.123.234:8760/api/balance/user:123 \
  -H "X-API-Key: fps_your_key"

# Debit
curl -X POST http://198.54.123.234:8760/api/debit \
  -H "X-API-Key: fps_your_key" \
  -H "Content-Type: application/json" \
  -d '{"account_id":"user:123","amount":10,"reason":"Test"}'
```

### 4.3 JavaScript

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
    reason: 'Premium feature'
  })
});
```

---

## 5. PERMISSIONS

API keys have granular permissions:

| Permission | Description |
|------------|-------------|
| `read` | View balances and transactions |
| `credit` | Add credits to accounts |
| `debit` | Deduct credits from accounts |
| `transfer` | Transfer between accounts |
| `exchange` | Exchange credit types |
| `admin` | Full access including key management |

---

## 6. DEPLOYMENT

### 6.1 Local Development
```bash
cd SERVICES/fp-credits-gateway
pip install -r requirements.txt
python app/main.py
```

### 6.2 Production
```bash
# Deploy to server
scp -r SERVICES/fp-credits-gateway root@198.54.123.234:/opt/fpai/

# Create systemd service
# See README.md for full instructions
```

### 6.3 Nginx Configuration
```nginx
location /services/credits {
    proxy_pass http://127.0.0.1:8760/;
}

location /api/credits {
    proxy_pass http://127.0.0.1:8760/api/;
}
```

---

## 7. SECURITY

- **API Key Hashing** - Keys stored as SHA-256 hashes
- **Rate Limiting** - Per-key limits (default 100/min)
- **Audit Logging** - Every transaction recorded
- **Permission Scoping** - Granular access control
- **HTTPS Required** - In production

---

## 8. FUTURE ENHANCEMENTS

- [ ] PostgreSQL backend (replace in-memory)
- [ ] Redis caching for balances
- [ ] Stripe integration for USD deposits
- [ ] Batch operations API
- [ ] Webhook notifications
- [ ] Credit expiration policies
- [ ] Multi-tenant support

---

Built with ⚡ by Full Potential AI


