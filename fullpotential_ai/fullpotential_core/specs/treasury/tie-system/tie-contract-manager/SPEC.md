# tie-contract-manager - SPEC

**Service:** TIE NFT Contract Issuance & Management
**Port:** 8921
**Status:** BUILD Phase
**Created:** 2025-11-16

---

## Purpose

**Issues and manages TIE contract NFTs representing 2x value of deposited SOL.**

When a user deposits SOL to treasury, this service mints an NFT contract that:
- Represents 2x the deposited SOL value
- Tracks held vs redeemed status
- Determines voting weight (2x held, 1x redeemed)
- Is tradeable on secondary markets
- Contains all covenant metadata

---

## Requirements

### Functional Requirements
- [x] Mint TIE contract NFT when deposit confirmed
- [x] Set contract value to 2x deposited SOL
- [x] Track contract status (held vs redeemed)
- [x] Update voting weight when status changes
- [x] Enable secondary market trading
- [x] Query user's contracts (held and redeemed)
- [x] Update contract on redemption
- [x] Integration with sol-treasury-core (trigger on deposit)
- [x] Integration with voting-weight-tracker (update votes)
- [x] Metaplex NFT standard compliance

### Non-Functional Requirements
- [x] Performance: Mint NFT < 30 seconds
- [x] Reliability: 99.9% minting success rate
- [x] Scalability: Handle 1000+ mints per day
- [x] Security: Owner-only updates
- [x] Standards: Metaplex NFT metadata standard

---

## API Specs

### Endpoints

**POST /contracts/mint**
- Description: Mint new TIE contract NFT (called by sol-treasury-core)
- Body: `{"deposit_tx": "string", "wallet": "string", "sol_deposited": float}`
- Returns: `{"contract_id": "string", "nft_mint": "string", "contract_value": float, "voting_weight": 2}`
- Status: 201 Created

**GET /contracts/{wallet}**
- Description: Get all contracts for a wallet
- Returns: `{"held": [...], "redeemed": [...], "total_voting_power": int}`
- Status: 200 OK

**GET /contracts/nft/{mint_address}**
- Description: Get contract details by NFT mint address
- Returns: `{"contract_id": "string", "owner": "string", "sol_deposited": float, "contract_value": float, "status": "held|redeemed", "voting_weight": int}`
- Status: 200 OK

**POST /contracts/redeem**
- Description: Mark contract as redeemed (called by redemption-algorithm)
- Body: `{"nft_mint": "string", "redeemer": "string", "authorization": "string"}`
- Returns: `{"redeemed": true, "voting_weight_updated": 1}`
- Status: 200 OK

**GET /health**
- Description: Health check
- Returns: `{"status": "ok", "service": "tie-contract-manager"}`
- Status: 200 OK

---

## NFT Metadata Structure

### Metaplex Standard:

```json
{
  "name": "TIE Contract #1234",
  "symbol": "TIE",
  "description": "Token Insurance Equity - 2x Abundance Covenant Contract",
  "image": "https://tie.fullpotential.com/nft/1234.png",
  "external_url": "https://tie.fullpotential.com/contract/1234",
  "attributes": [
    {
      "trait_type": "SOL Deposited",
      "value": "10.5"
    },
    {
      "trait_type": "Contract Value",
      "value": "21.0"
    },
    {
      "trait_type": "Issue Date",
      "value": "2025-11-16"
    },
    {
      "trait_type": "Status",
      "value": "HELD"
    },
    {
      "trait_type": "Voting Weight",
      "value": "2"
    },
    {
      "trait_type": "Covenant Type",
      "value": "Abundance Demonstration"
    },
    {
      "trait_type": "Treasury Deposit TX",
      "value": "5J7Yx..."
    }
  ],
  "properties": {
    "category": "image",
    "files": [
      {
        "uri": "https://tie.fullpotential.com/nft/1234.png",
        "type": "image/png"
      }
    ],
    "creators": [
      {
        "address": "TiE...",
        "share": 100
      }
    ]
  }
}
```

---

## Data Models

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class ContractStatus(str, Enum):
    HELD = "held"
    REDEEMED = "redeemed"

class TIEContract(BaseModel):
    contract_id: str
    nft_mint: str  # Solana NFT mint address
    owner: str  # Current owner wallet

    sol_deposited: float
    contract_value: float  # Always 2x deposited

    status: ContractStatus
    voting_weight: int  # 2 if held, 1 if redeemed

    deposit_tx: str  # Original treasury deposit transaction
    issue_date: datetime
    redeemed_date: Optional[datetime] = None

    metadata_uri: str

class MintContractRequest(BaseModel):
    deposit_tx: str
    wallet: str
    sol_deposited: float

class RedeemContractRequest(BaseModel):
    nft_mint: str
    redeemer: str
    authorization: str  # From redemption-algorithm

class UserContracts(BaseModel):
    wallet: str
    held_contracts: List[TIEContract]
    redeemed_contracts: List[TIEContract]
    total_held: int
    total_redeemed: int
    total_voting_power: int
```

---

## Integration Flow

### Deposit → Mint Flow:

```
1. User deposits 10 SOL to treasury
   ↓
2. sol-treasury-core confirms deposit
   ↓
3. sol-treasury-core calls POST /contracts/mint
   {
     "deposit_tx": "5J7Yx...",
     "wallet": "7xKXtg...",
     "sol_deposited": 10.0
   }
   ↓
4. tie-contract-manager mints NFT:
   - Creates Metaplex NFT on Solana
   - Sets metadata (2x value = 20 SOL)
   - Sets status = HELD
   - Sets voting_weight = 2
   ↓
5. tie-contract-manager calls voting-weight-tracker:
   POST /voting/add
   {
     "wallet": "7xKXtg...",
     "votes": 2,
     "contract_id": "TIE-1234"
   }
   ↓
6. Return to sol-treasury-core:
   {
     "contract_id": "TIE-1234",
     "nft_mint": "NFT...",
     "contract_value": 20.0,
     "voting_weight": 2
   }
   ↓
7. User sees new TIE NFT in wallet
```

### Redemption → Update Flow:

```
1. redemption-algorithm approves redemption
   ↓
2. Calls POST /contracts/redeem
   {
     "nft_mint": "NFT...",
     "redeemer": "7xKXtg...",
     "authorization": "sig..."
   }
   ↓
3. tie-contract-manager updates NFT:
   - Update metadata: status = REDEEMED
   - Set voting_weight = 1
   - Record redeemed_date
   ↓
4. Call voting-weight-tracker:
   POST /voting/update
   {
     "wallet": "7xKXtg...",
     "contract_id": "TIE-1234",
     "old_weight": 2,
     "new_weight": 1
   }
   ↓
5. Return confirmation
```

---

## Success Criteria

**Phase 1: SPEC → BUILD**
- [x] All sections complete
- [x] NFT metadata structure defined
- [x] Integration flows mapped
- [x] API endpoints specified

**Phase 2: BUILD → TEST**
- [ ] Service starts without errors
- [ ] Can mint NFT on devnet
- [ ] Metadata correctly formatted
- [ ] Integration with sol-treasury-core works
- [ ] Can update contract status
- [ ] Voting weight updates correctly

**Phase 3: TEST → PRODUCTION**
- [ ] All tests pass
- [ ] NFTs visible in Phantom wallet
- [ ] Secondary market trading works
- [ ] 1000+ mints stress test passes
- [ ] Deployed to mainnet

---

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **NFT Standard:** Metaplex
- **Blockchain:** Solana
- **Database:** PostgreSQL (contract records)
- **Port:** 8921

---

**SPEC Status:** ✅ COMPLETE - Ready for BUILD
**Estimated Build Time:** 3 hours
**Priority:** CRITICAL (needed for deposits to work)
