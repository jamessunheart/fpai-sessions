# ZEND + TON Wallet Integration Specification

**Version:** 1.0.0  
**Status:** CANONICAL  
**Effective:** 2025-12-14  
**Authority:** Church of Consciousness / Cora Nation PMA  
**Maintainer:** Commons Ministry

---

## Quick Lookup

| Question | Answer |
|----------|--------|
| **What is this?** | TON blockchain integration for real money (USDT) alongside UC credits |
| **Settlement currency?** | USDT on TON (native Telegram wallet) |
| **Do we custody funds?** | No. All USDT moves wallet-to-wallet |
| **P2P Exchange?** | Yes. Marketplace at port 8584 |
| **Entity support?** | Yes. Trusts, churches, LLCs can be liquidity providers |

---

## Part 1: Architecture

### 1.1 Service Map

| Service | Port | Purpose |
|---------|------|---------|
| `zend-wallet` | 8580 | UC balance, entity distribution, unified view |
| `zend-ton` | 8583 | TON Connect, USDT balance, transfer links |
| `zend-marketplace` | 8584 | P2P order book, matching, settlement |

### 1.2 Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      TELEGRAM ECOSYSTEM                              │
│                                                                     │
│   ┌─────────────────────┐         ┌─────────────────────┐          │
│   │   ARIA BOT          │◄───────▶│   TON WALLET        │          │
│   │   (Commands)        │         │   (Native)          │          │
│   └─────────────────────┘         └─────────────────────┘          │
│            │                               │                        │
│            ▼                               ▼                        │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │                    ZEND SERVICES                         │      │
│   │                                                         │      │
│   │   zend-wallet ──► zend-marketplace ◄── zend-ton        │      │
│   │       │                  │                 │            │      │
│   │       ▼                  ▼                 ▼            │      │
│   │   Credits           Escrow UC         TON RPC          │      │
│   │   Gateway           for P2P           (toncenter)      │      │
│   └─────────────────────────────────────────────────────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: TON Integration (zend-ton)

### 2.1 Wallet Connection

```python
# API: POST /api/ton/connect
# Initiates TON Connect flow

# API: POST /api/ton/connection/save
# Saves wallet address after connection
{
    "member_id": "james",
    "ton_address": "UQBx...7Kd"
}
```

### 2.2 Balance Query

```python
# API: GET /api/ton/wallet/{member_id}
# Returns:
{
    "member_id": "james",
    "ton_address": "UQBx...7Kd",
    "connected": true,
    "balances": {"USDT": 1250.00, "TON": 45.3},
    "usdt_balance": 1250.00,
    "ton_balance": 45.3,
    "usdt_yield_apy": 2.86
}
```

### 2.3 Transfer Generation

```python
# API: POST /api/ton/transfer
# Generates deep link for USDT transfer (user signs in wallet)
{
    "from_member_id": "james",
    "to_address": "UQAb...3Cd",
    "amount_usdt": 50.0,
    "comment": "Coffee payment"
}
# Returns:
{
    "transfer_id": "tt_abc123",
    "deep_link": "ton://transfer/UQAb...?jetton=...&amount=50000000",
    "qr_data": "ton://...",
    "expires_at": "2025-12-15T00:00:00Z"
}
```

### 2.4 Transaction Verification

```python
# API: GET /api/ton/verify/{tx_hash}
{
    "verified": true,
    "amount_usdt": 50.0,
    "from_address": "UQBx...",
    "to_address": "UQAb...",
    "confirmed_at": "2025-12-14T12:00:00Z"
}
```

---

## Part 3: Entity Accounts

### 3.1 Entity Types

| Type | Daily Buy Limit | Daily Distribute | Can Provide Liquidity |
|------|-----------------|------------------|----------------------|
| Individual | 1,000 UC | 1,000 UC | No |
| Trust | 50,000 UC | 25,000 UC | Yes |
| LLC | 25,000 UC | 10,000 UC | Yes |
| Church | 100,000 UC | 50,000 UC | Yes |
| Family Office | 500,000 UC | 250,000 UC | Yes |

### 3.2 Entity Registration

```python
# API: POST /api/zend/entities
{
    "entity_type": "trust",
    "legal_name": "Sunheart Family Trust",
    "ein_or_tin": "XX-XXXXXXX",
    "admin_member_id": "james",
    "ton_wallet_address": "UQBx...7Kd"
}
```

### 3.3 Distribution

```python
# API: POST /api/zend/entities/{entity_id}/distribute
{
    "distributions": [
        {"member_id": "maria", "amount_uc": 100, "note": "Volunteer appreciation"},
        {"member_id": "carlos", "amount_uc": 100},
        {"member_id": "bob@email.com", "amount_uc": 50}  # Creates invite
    ],
    "note": "December volunteer distribution"
}
```

---

## Part 4: P2P Marketplace

### 4.1 Order Types

- **sell_uc**: User wants to convert UC → USDT
- **buy_uc**: User/entity wants to convert USDT → UC

### 4.2 Trade Flow

```
1. Seller lists: "Sell 100 UC"
   → UC escrowed in system:marketplace_escrow

2. Buyer matches (or LP auto-matches)
   → Trade created, status: pending_payment

3. Buyer sends USDT to seller's TON wallet
   → Direct wallet-to-wallet transfer

4. Seller confirms receipt
   → UC released from escrow to buyer
   → Trade complete
```

### 4.3 Liquidity Providers

Entities can register as LPs with auto-buy settings:

```python
# API: POST /api/marketplace/liquidity/register
{
    "entity_id": "entity:trust:abc123",
    "max_buy_uc": 1000,
    "daily_limit_uc": 5000,
    "auto_buy_enabled": true,
    "min_amount_uc": 10,
    "max_amount_uc": 500,
    "ton_wallet_address": "UQBx...7Kd"
}
```

When a sell order matches LP criteria:
- Instant match
- LP sends USDT automatically
- Seller confirms → UC to LP

---

## Part 5: Aria Commands

### 5.1 Balance Commands

| Command | Action |
|---------|--------|
| "my balance" | Personal UC balance |
| "all balances" | Unified view (UC + entities + TON) |
| "trust balance" | Entity balance |

### 5.2 Send Commands

| Command | Action |
|---------|--------|
| "zend 50 UC to @bob" | UC transfer |
| "send $50 to @sarah" | USDT transfer (via TON) |
| "distribute 500 from church..." | Entity distribution |

### 5.3 Cash Out

| Command | Action |
|---------|--------|
| "cash out 100 UC" | Create sell order in marketplace |

---

## Part 6: Security Model

### 6.1 Non-Custodial Principle

- **UC Escrow**: Only during P2P trades (in Credits Gateway)
- **USDT**: Never held. Direct wallet-to-wallet transfers.
- **TON**: User's own wallet. We generate links, they sign.

### 6.2 Authorization

- Entity operations require admin role
- Beneficiaries can only receive, not send
- All transfers logged to Credits Gateway

### 6.3 Limits

| Limit | Value |
|-------|-------|
| Min trade | 10 UC |
| Max trade | 10,000 UC |
| Order expiry | 24 hours |
| Trade timeout | 1 hour |

---

## Part 7: Database Schema

### 7.1 TON Connections (zend-ton)

```sql
CREATE TABLE ton_connections (
    member_id TEXT PRIMARY KEY,
    ton_address TEXT NOT NULL,
    connected_at TEXT NOT NULL,
    last_verified TEXT
);
```

### 7.2 Entities (zend-wallet)

```sql
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    legal_name TEXT NOT NULL,
    ein_or_tin TEXT,
    uc_account_id TEXT NOT NULL,
    ton_wallet_address TEXT,
    daily_buy_limit_uc REAL,
    daily_distribute_limit_uc REAL,
    is_liquidity_provider BOOLEAN
);
```

### 7.3 Marketplace (zend-marketplace)

```sql
CREATE TABLE market_orders (
    order_id TEXT PRIMARY KEY,
    order_type TEXT NOT NULL,  -- sell_uc | buy_uc
    member_id TEXT NOT NULL,
    entity_id TEXT,
    amount_uc REAL NOT NULL,
    status TEXT NOT NULL,      -- open | matched | completed | cancelled
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE trades (
    trade_id TEXT PRIMARY KEY,
    sell_order_id TEXT NOT NULL,
    buy_order_id TEXT NOT NULL,
    amount_uc REAL NOT NULL,
    amount_usdt REAL NOT NULL,
    seller_confirmed BOOLEAN,
    status TEXT NOT NULL       -- pending_payment | completed | disputed
);

CREATE TABLE liquidity_providers (
    entity_id TEXT PRIMARY KEY,
    max_buy_uc REAL NOT NULL,
    daily_limit_uc REAL NOT NULL,
    daily_used_uc REAL DEFAULT 0,
    auto_buy_enabled BOOLEAN,
    ton_wallet_address TEXT NOT NULL
);
```

---

## Part 8: Environment Variables

```bash
# zend-ton
TON_NETWORK=mainnet
TON_API_KEY=<toncenter_api_key>
USDT_JETTON_MASTER=EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs

# zend-marketplace
ZEND_WALLET_URL=http://localhost:8580
ZEND_TON_URL=http://localhost:8583
CREDITS_GATEWAY_URL=http://localhost:8765
MARKETPLACE_ESCROW_ACCOUNT=system:marketplace_escrow

# Aria
ZEND_WALLET_URL=http://198.54.123.234:8580
ZEND_TON_URL=http://198.54.123.234:8583
ZEND_MARKETPLACE_URL=http://198.54.123.234:8584
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-14 | Initial TON + marketplace + entity integration |

---

## For AI Agents

```python
# Service endpoints
ZEND_TON = "http://198.54.123.234:8583"
ZEND_MARKETPLACE = "http://198.54.123.234:8584"
ZEND_WALLET = "http://198.54.123.234:8580"

# Quick reference
USDT_CONTRACT = "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"
UC_RATE = 1.0  # 1 UC = $1 USD (fixed)
```

---

**END OF SPECIFICATION**

*"Money moves outside. Ease lives inside. Entities provide liquidity."*




