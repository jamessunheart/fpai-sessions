# tie-contract-manager

**TIE NFT Contract Issuance & Management**

**Port:** 8921
**Status:** BUILD Complete ✅
**Version:** 1.0.0

---

## Purpose

**Mints and manages TIE contract NFTs representing 2x value of deposited SOL.**

When users deposit SOL:
- This service mints an NFT contract
- Contract value = 2x deposited SOL
- Initially: HELD status, 2 votes
- After redemption: REDEEMED status, 1 vote

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"

# Start service
uvicorn app.main:app --reload --port 8921
```

---

## API Endpoints

### Mint Contract (Called by sol-treasury-core)
```bash
POST /contracts/mint
{
  "deposit_tx": "5J7Yx...",
  "wallet": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
  "sol_deposited": 10.5
}

Returns:
{
  "contract_id": "TIE-000001",
  "nft_mint": "NFT_...",
  "contract_value": 21.0,
  "voting_weight": 2
}
```

### Get User Contracts
```bash
GET /contracts/7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU

Returns:
{
  "wallet": "7xKXtg...",
  "held_contracts": [...],
  "redeemed_contracts": [...],
  "total_held": 5,
  "total_redeemed": 2,
  "total_voting_power": 12  # (5×2) + (2×1)
}
```

### Redeem Contract (Called by redemption-algorithm)
```bash
POST /contracts/redeem
{
  "nft_mint": "NFT_...",
  "redeemer": "7xKXtg...",
  "authorization": "sig_from_redemption_algorithm"
}

Returns:
{
  "redeemed": true,
  "voting_weight_updated": 1
}
```

---

## Integration Flow

### Deposit → Mint:
```
sol-treasury-core (deposit confirmed)
  ↓
POST /contracts/mint
  ↓
Mint NFT on Solana (Metaplex)
  ↓
Call voting-weight-tracker (+2 votes)
  ↓
Return contract details
```

### Redeem → Update:
```
redemption-algorithm (approval)
  ↓
POST /contracts/redeem
  ↓
Update NFT metadata (status=REDEEMED)
  ↓
Call voting-weight-tracker (2→1 votes)
  ↓
Return confirmation
```

---

## NFT Metadata

TIE contracts are Metaplex NFTs with:
- **Name:** "TIE Contract #000001"
- **Symbol:** TIE
- **Attributes:**
  - SOL Deposited: 10.5
  - Contract Value: 21.0 (2x)
  - Status: HELD or REDEEMED
  - Voting Weight: 2 or 1
  - Treasury Deposit TX: Solana transaction

---

## Testing

```bash
pytest tests/ -v
```

---

## Next Steps

After tie-contract-manager:
1. Build voting-weight-tracker (receives notifications from this service)
2. Integration testing (treasury → contract → voting)
3. Deploy to production

---

**Status:** ✅ **BUILD COMPLETE** - Ready for Integration Testing

**Session #12 - Autonomous Build** 🏗️⚡💎
