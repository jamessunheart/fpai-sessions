# SPEC - Treasury Manager (Droplet #25)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 25
**Status:** Phase 2 (In Progress)

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
Intelligent DeFi portfolio management system autonomously managing $400K treasury across Base Yield (60%) and Tactical (40%) allocations. Uses AI-driven decision making via Claude API, real-time market intelligence, and automated rebalancing to achieve 25-50% APY target.

### 1.2 Position in Ecosystem
This service sits in the **Revenue Layer**, managing the system's capital. It interacts with external DeFi protocols and market data providers, reporting performance to the Dashboard.

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery
- Orchestrator (droplet #10) - Task scheduling
- Credentials Manager (droplet #20) - Secure key management

**External Dependencies:**
- CoinGecko / Glassnode (Market Data)
- Anthropic Claude API (Strategy)
- DeFi Protocols (Aave, Pendle, Curve, 1inch)
- Web3 RPC Providers (Infura/Alchemy)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Market Intelligence]** - Real-time analysis of MVRV, funding rates, and sentiment.
2. **[Portfolio Management]** - Automated rebalancing between Base Yield and Tactical buckets.
3. **[Safe Execution]** - Transaction simulation, gas optimization, and slippage protection.

### 2.2 Supported Operations
- `get_market_signal` - Returns current market phase and allocation advice.
- `get_portfolio_status` - Returns current positions and performance.
- `execute_rebalance` - Triggers portfolio adjustment (requires approval for large moves).

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
  "version": "1.0.0",
  "timestamp": "2025-11-23T12:00:00Z"
}
```

#### Capabilities
```
GET /capabilities
```
**Response:**
```json
{
  "service_name": "treasury-manager",
  "droplet_id": 25,
  "capabilities": ["market_intel", "portfolio_mgmt", "defi_execution"],
  "supported_operations": ["get_signal", "rebalance", "view_portfolio"],
  "integration_endpoints": [
    { "path": "/api/v1/portfolio", "method": "GET" }
  ]
}
```

#### State
```
GET /state
```
**Response:**
```json
{
  "status": "active",
  "tvl_usd": 400000,
  "apy_current": 0.125,
  "market_phase": "accumulation"
}
```

#### Dependencies
```
GET /dependencies
```
**Response:**
```json
{
  "required_services": [
    { "name": "registry", "status": "connected" }
  ],
  "external_apis": [
    { "name": "coingecko", "status": "connected" },
    { "name": "ethereum_rpc", "status": "connected" }
  ]
}
```

#### Message
```
POST /message
```
**Response:**
```json
{
  "received": true,
  "status": "processing"
}
```

---

### 3.2 Business Logic Endpoints

#### Get Market Signal
```
GET /api/v1/market/signal
```
**Response:**
```json
{
  "phase": "euphoria",
  "mvrv_z_score": 2.1,
  "recommendation": "hold_tactical",
  "confidence": 0.85
}
```

#### Get Portfolio
```
GET /api/v1/portfolio
```
**Response:**
```json
{
  "total_value": 405200.00,
  "allocations": {
    "base_yield": 0.60,
    "tactical": 0.40
  },
  "positions": [
    { "asset": "USDC", "protocol": "Aave", "amount": 240000 }
  ]
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema (Conceptual)

#### `positions`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary Key |
| asset | String | Token symbol |
| protocol | String | DeFi protocol |
| amount | Float | Token amount |
| value_usd | Float | USD value |
| updated_at | Timestamp | Last check |

#### `signals`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary Key |
| indicator | String | Signal type |
| value | Float | Raw value |
| created_at | Timestamp | Signal time |

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=treasury-manager
SERVICE_PORT=8600
DROPLET_ID=25
REGISTRY_URL=http://registry:8000
WEB3_RPC_URL=https://mainnet.infura.io/v3/...
ANTHROPIC_API_KEY=sk-...
PRIVATE_KEY_PATH=/secure/keys/treasury.key
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Registers with Registry
- [x] Secure key handling (Vault/Encrypted)
- [ ] Protocol adapters fully implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎
