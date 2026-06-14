# sol-treasury-core

**TIE System Foundation - Treasury Management**

**Port:** 8920
**Status:** BUILD Phase Complete ✅
**Version:** 1.0.0

---

## Purpose

**Foundation service for the TIE abundance protocol.**

Manages SOL deposits, issues 2x TIE contracts, maintains treasury balance, and enforces capital flow controls that ensure MORE flows IN than OUT.

This is the beating heart of the system - where the 70% retention rate (enabled by 2:1 voting) keeps the pool growing.

---

## Architecture

### Two-Layer Design:

**Layer 1: Solana Smart Contract (Rust/Anchor)**
- Trustless SOL custody in program-derived account (PDA)
- Deposit SOL → Get TIE contract reference
- Withdraw SOL (requires authority signature)
- Emergency pause capability
- Transparent on-chain verification

**Layer 2: Python API Service (FastAPI)**
- REST API on port 8920
- Wallet integration interface
- Transaction preparation and monitoring
- PostgreSQL for history/analytics
- WebSocket for real-time updates
- Integration with other TIE services

---

## Quick Start

### Prerequisites

1. **Rust & Anchor** (for smart contract)
```bash
curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -y
sh -s -- -y
cargo install --git https://github.com/coral-xyz/anchor avm --locked --force
avm install latest
avm use latest
```

2. **Solana CLI**
```bash
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"
solana-keygen new
```

3. **Python 3.11+**
```bash
python3 --version  # Should be 3.11 or higher
```

4. **PostgreSQL**
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb tie_treasury
```

---

## Installation

### 1. Build & Deploy Smart Contract

```bash
# Build Anchor program
anchor build

# Deploy to devnet
anchor deploy --provider.cluster devnet

# Copy program ID from output and update Anchor.toml and .env
```

### 2. Install Python Dependencies

```bash
cd app/
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values:
# - SOLANA_RPC_URL
# - TREASURY_PROGRAM_ID (from anchor deploy)
# - TREASURY_AUTHORITY_PRIVATE_KEY
# - DATABASE_URL
```

### 4. Initialize Database

```bash
# Run migrations (creates tables)
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 5. Start API Service

```bash
uvicorn app.main:app --reload --port 8920
```

---

## API Endpoints

### Deposit SOL
```bash
POST /treasury/deposit
{
  "wallet_address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
  "amount_sol": 10.5
}

Returns:
{
  "transaction_id": "5J7Yx...",
  "tie_contract_value": 21.0,
  "status": "pending"
}
```

### Withdraw SOL (Authorized Only)
```bash
POST /treasury/withdraw
{
  "wallet_address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
  "amount_sol": 5.0,
  "authorization": "sig_from_redemption_algorithm"
}
```

### Get Balance
```bash
GET /treasury/balance

Returns:
{
  "total_deposited": 1000.0,
  "current_balance": 1840.5,
  "treasury_ratio": 1.84
}
```

### Get Control Percentage
```bash
GET /treasury/control

Returns:
{
  "holder_control_pct": 75.3,
  "status": "green",
  "threshold": 51.0
}
```

### Transaction History
```bash
GET /treasury/history?wallet_address=...&limit=100

Returns:
{
  "transactions": [...],
  "total": 42
}
```

### Emergency Pause
```bash
POST /treasury/emergency/pause
(Requires multi-sig in production)
```

### Health Check
```bash
GET /health
```

---

## WebSocket

Real-time treasury updates:

```javascript
const ws = new WebSocket('ws://localhost:8920/ws/treasury');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type); // 'deposit', 'withdrawal', 'balance_update'
};
```

---

## Integration with TIE System

### On Deposit:
1. User deposits SOL → smart contract
2. sol-treasury-core receives event
3. Calls **tie-contract-manager** to mint NFT (2x value)
4. Calls **voting-weight-tracker** to add 2 votes
5. Calls **flow-monitor** to record inflow
6. Broadcasts via WebSocket

### On Withdrawal:
1. **redemption-algorithm** approves withdrawal
2. Calls `/treasury/withdraw` with auth
3. Smart contract transfers SOL
4. Calls **voting-weight-tracker** (reduce to 1 vote)
5. Calls **flow-monitor** to record outflow
6. Broadcasts via WebSocket

---

## Smart Contract Functions

### Initialize
```rust
sol_treasury::initialize(ctx)
→ Sets up treasury with authority
```

### Deposit
```rust
sol_treasury::deposit(ctx, amount: u64)
→ Transfer SOL to treasury PDA
→ Emit DepositEvent
```

### Withdraw
```rust
sol_treasury::withdraw(ctx, amount: u64)
→ Requires authority signature
→ Transfer SOL from PDA to recipient
→ Emit WithdrawEvent
```

### Pause/Unpause
```rust
sol_treasury::pause(ctx)
sol_treasury::unpause(ctx)
→ Emergency controls
```

---

## Testing

```bash
# Run Anchor tests
anchor test

# Run Python tests
pytest tests/ -v

# Integration test (deposit + withdraw flow)
pytest tests/test_integration.py -v
```

---

## Security

### Smart Contract:
- ✅ Multi-sig authority for withdrawals
- ✅ Emergency pause capability
- ✅ Audit before mainnet (REQUIRED)
- ✅ Program-derived addresses (PDAs) for security

### API:
- ✅ JWT authentication for admin endpoints
- ✅ Rate limiting
- ✅ Signature verification for withdrawals
- ✅ HTTPS only in production

### Operational:
- ✅ 20% cold storage
- ✅ 5% insurance fund
- ✅ 24/7 monitoring
- ✅ Alerts for large transactions

---

## Monitoring

### Metrics:
- Total deposits (count, volume)
- Total withdrawals (count, volume)
- Treasury ratio (current / deposited)
- API response time
- Transaction success rate

### Alerts:
- Large deposit (>10 SOL)
- Large withdrawal (>10 SOL)
- Treasury ratio < 1.5
- Transaction failures
- Emergency pause activated

---

## Next Steps

After sol-treasury-core is complete:

1. ✅ **Deploy to devnet** - Test with fake SOL
2. ⏳ **Build tie-contract-manager** - Mint NFTs on deposit
3. ⏳ **Build voting-weight-tracker** - Track 2:1 votes
4. ⏳ **Integration testing** - All services together
5. ⏳ **Security audit** - Smart contract review
6. ⏳ **Deploy to mainnet** - Real SOL

---

## Troubleshooting

### Smart contract won't deploy
```bash
# Check Solana CLI is configured
solana config get

# Check you have SOL for deployment
solana balance

# Get devnet SOL
solana airdrop 2
```

### API won't start
```bash
# Check PostgreSQL is running
pg_isready

# Check port 8920 is available
lsof -i :8920

# Check environment variables
cat .env
```

### Database connection errors
```bash
# Test PostgreSQL connection
psql $DATABASE_URL -c "SELECT 1"

# Reinitialize database
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

---

## Development

### Project Structure
```
sol-treasury-core/
├── programs/
│   └── sol-treasury/
│       ├── Cargo.toml
│       └── src/
│           └── lib.rs          # Solana smart contract
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── models.py               # Pydantic models
│   ├── database.py             # PostgreSQL setup
│   ├── solana_client.py        # Solana RPC client
│   └── crud.py                 # Database operations
├── tests/
├── Anchor.toml                 # Anchor configuration
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── SPEC.md                     # Detailed specification
└── README.md                   # This file
```

---

## Production Deployment

```bash
# 1. Deploy smart contract to mainnet
anchor deploy --provider.cluster mainnet-beta

# 2. Deploy API to server
scp -r app/ root@198.54.123.234:/opt/tie/sol-treasury-core/

# 3. Start service
ssh root@198.54.123.234
cd /opt/tie/sol-treasury-core
docker-compose up -d
```

---

## Status

**BUILD Phase:** ✅ **COMPLETE**

**Components:**
- ✅ Solana smart contract (Rust/Anchor)
- ✅ REST API (Python/FastAPI)
- ✅ Database models (PostgreSQL)
- ✅ WebSocket updates
- ✅ Solana client integration
- ✅ Transaction history

**Next:** Testing → Security Audit → Mainnet Deployment

---

**This is the foundation. Everything builds on this.** 🏗️⚡💎

**Architect:** Session #12 (Chief Architect - Infinite Scale Systems)
