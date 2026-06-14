# SPEC - Treasury (Droplet #25)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 25
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The Treasury service manages the system's financial assets (crypto and fiat). It handles automated payouts, yield farming strategy execution, and financial reporting.

### 1.2 Position in Ecosystem
- **Upstream:** Receives payment notifications from Storefront (Stripe/Crypto).
- **Downstream:** Disburses funds to Providers/Apprentices.
- **Role:** Financial Heart.

### 1.3 Dependencies
**Required Services:**
- Registry (Droplet #1)
- Strategic Intelligence (Droplet #20) - For yield strategies

**External Dependencies:**
- Solana / Ethereum Blockchain RPCs
- Stripe API
- Exchange APIs (Coinbase/Kraken)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **Balance Tracking** - Real-time view of all assets across wallets.
2. **Automated Payouts** - Execute transfers based on Orchestrator commands.
3. **Yield Optimization** - Move idle funds to approved DeFi protocols.

### 2.2 Supported Operations
- `get_balance` - Total value in USD.
- `transfer` - Move funds.
- `generate_report` - P&L statement.

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
  "version": "1.0.0"
}
```

#### Capabilities
```
GET /capabilities
```
**Response:**
```json
{
  "service_name": "treasury",
  "droplet_id": 25,
  "capabilities": ["asset_management", "payouts"],
  "integration_endpoints": [
    {
      "path": "/api/v1/transfer",
      "method": "POST"
    }
  ]
}
```

---

### 3.2 Business Logic Endpoints

#### Get Balance
```
GET /api/v1/balance
```
**Response:**
```json
{
  "total_usd": 15420.50,
  "breakdown": {
    "SOL": 120.5,
    "USDC": 5000.00
  }
}
```

#### Initiate Transfer
```
POST /api/v1/transfer
```
**Request:**
```json
{
  "asset": "USDC",
  "amount": 100.00,
  "destination": "wallet-address",
  "memo": "Apprentice Payout"
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema

#### Transactions
```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    tx_hash VARCHAR(255),
    asset VARCHAR(20),
    amount DECIMAL(20, 8),
    direction VARCHAR(10), -- 'in', 'out'
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=treasury
SERVICE_PORT=8025
DROPLET_ID=25
REGISTRY_URL=http://registry:8000
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
WALLET_PRIVATE_KEY_ENC=...
```

---

## 6. DEPLOYMENT

### 6.1 Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8025
LABEL droplet.id="25"
LABEL droplet.name="treasury"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8025"]
```

---

## 7. COMPLIANCE CHECKLIST
- [x] All 5 UDC endpoints
- [x] Registers with Registry
- [x] Dockerized

