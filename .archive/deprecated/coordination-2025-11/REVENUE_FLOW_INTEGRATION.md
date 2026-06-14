# Revenue Flow Integration to Commons Reserve

**Version:** 1.0.0  
**Status:** SPEC - Ready for Implementation  
**Canonical Reference:** `docs/protocols/TOKENS_STRATEGY.md`

---

## Overview

This document specifies how revenue flows from various sources into the Commons Reserve Fund. Every economic activity in the ecosystem contributes a portion to the commons.

---

## Revenue Sources and Allocations

| Source | Service | Allocation to Commons | Implementation |
|--------|---------|----------------------|----------------|
| **UC Protocol Fees** | fp-credits-gateway | 30% | Modify credits gateway |
| **$FI Transaction Fees** | FI-Art | 30% | Extend $FI policy |
| **LLC Profits** | All LLCs via Trust | 30% | Contractual |
| **Member Contributions** | fp-credits-gateway | 80% | Donation processing |
| **Treasury Arena Yields** | treasury-arena | 30% of surplus | Wire to reserve |
| **Service Margins** | Various | 20% | Per-service wiring |

---

## Implementation Details

### 1. UC Protocol Fees (fp-credits-gateway)

**Current:** Fees collected but not routed to commons

**Change:** Add commons allocation on every transaction

```python
# In fp-credits-gateway debit handler
async def process_debit(user_id: str, amount: float, service: str):
    # Existing logic
    await debit_user(user_id, amount)
    
    # NEW: Calculate commons allocation
    fee = amount * PROTOCOL_FEE_RATE  # e.g., 2.9%
    commons_share = fee * 0.30  # 30% of fee to commons
    
    # NEW: Route to commons reserve
    await commons_reserve.credit(
        amount=commons_share,
        source="uc_protocol_fee",
        transaction_id=transaction_id
    )
    
    # Log for transparency
    await log_commons_flow(
        source="uc_protocol_fee",
        amount=commons_share,
        transaction_id=transaction_id
    )
```

**Endpoint to Add:**
```
POST /api/commons/credit
{
  "amount": 0.87,
  "source": "uc_protocol_fee",
  "transaction_id": "tx_123"
}
```

---

### 2. $FI Transaction Fees (FI-Art)

**Current:** Transaction fees go to FI-Art Treasury

**Change:** Split fees between FI-Art and Commons

```python
# In FI-Art transaction handler
async def process_fi_transaction(transaction):
    fee = transaction.amount * FI_FEE_RATE  # e.g., 5%
    
    # Split fee
    fi_art_share = fee * 0.70  # 70% stays with FI-Art
    commons_share = fee * 0.30  # 30% to commons
    
    await fi_art_treasury.credit(fi_art_share)
    await commons_reserve.credit(
        amount=commons_share,
        source="fi_transaction_fee",
        transaction_id=transaction.id
    )
```

**Sacred Circulation Policy Update:**
Add to `SACRED_CIRCULATION_POLICY.md`:
```
### Commons Contribution
30% of all $FI transaction fees flow to the Commons Reserve Fund,
supporting the broader mission of meeting members' needs.
```

---

### 3. LLC Profits (via Sunheart Trust)

**Current:** Profits flow to Trust, then Church

**Change:** Allocate portion to Commons Reserve Fund before Church distribution

This is a **trust-level** decision, not a code change. The Trustee should:

1. Update Trust distribution policy
2. Designate 30% of LLC profits to Commons Reserve Fund
3. Remaining 70% continues to Church as beneficiary

**Trust Policy Addition:**
```
Before distributing to beneficiary, Trustee shall allocate
30% of net LLC profits to the Commons Reserve Fund for
needs-meeting purposes.
```

---

### 4. Member Contributions/Donations (fp-credits-gateway)

**Current:** Donations credited to user as UC

**Change:** Route majority to Commons Reserve

```python
# In donation handler
async def process_donation(user_id: str, amount: float, purpose: str):
    if purpose == "commons" or purpose == "general":
        # 80% to commons reserve
        commons_share = amount * 0.80
        donor_credit = amount * 0.20  # Thank-you UC
        
        await commons_reserve.credit(
            amount=commons_share,
            source="member_donation",
            donor_id=user_id
        )
        
        # Give donor some UC as thank-you
        await credit_user(user_id, donor_credit, reason="donation_thanks")
        
        # Issue TRUST for contribution
        await contribution_tracker.log({
            "member_id": user_id,
            "type": "financial",
            "amount": amount,
            "trust_earned": int(amount)  # 1 TRUST per UC
        })
```

---

### 5. Treasury Arena Yields (treasury-arena)

**Current:** Yields managed by arena system

**Change:** Route portion of surplus to Commons

```python
# In treasury-arena daily optimizer
async def distribute_yields():
    surplus = calculate_surplus()
    
    if surplus > 0:
        # 30% of surplus to commons
        commons_share = surplus * 0.30
        reinvest = surplus * 0.50
        operations = surplus * 0.20
        
        await commons_reserve.credit(
            amount=commons_share,
            source="treasury_arena_yield",
            period=current_period
        )
        
        await arena_treasury.reinvest(reinvest)
        await operations_fund.credit(operations)
```

---

### 6. Service Margins (Various Services)

**Current:** Service revenue covers costs

**Change:** Route margin to commons after costs

```python
# Generic service margin routing
async def process_service_revenue(service: str, revenue: float, cost: float):
    margin = revenue - cost
    
    if margin > 0:
        commons_share = margin * 0.20  # 20% of margin
        service_retain = margin * 0.80
        
        await commons_reserve.credit(
            amount=commons_share,
            source=f"service_margin_{service}",
            period=current_period
        )
```

**Applicable Services:**
- AI Brain (inference margin)
- Voice Phone (call margin)
- Content Studio (generation margin)
- I-Match (commission margin)

---

## Commons Reserve API

A new endpoint in fp-credits-gateway (or new service) to receive commons contributions:

### POST /api/commons/credit
```json
{
  "amount": 100.00,
  "source": "uc_protocol_fee",
  "transaction_id": "tx_123",
  "metadata": {}
}
```

### GET /api/commons/balance
```json
{
  "balance_uc": 50000,
  "period_inflow": 5000,
  "period": "2025-12",
  "sources": {
    "uc_protocol_fee": 1500,
    "fi_transaction_fee": 800,
    "llc_profits": 1200,
    "member_donation": 500,
    "treasury_yield": 700,
    "service_margin": 300
  }
}
```

### GET /api/commons/flow-report
```json
{
  "period": "2025-12",
  "inflows": [
    {"source": "uc_protocol_fee", "amount": 1500, "count": 3500},
    {"source": "fi_transaction_fee", "amount": 800, "count": 150}
  ],
  "outflows": [
    {"category": "survival", "amount": 2000, "recipients": 15},
    {"category": "stability", "amount": 1200, "recipients": 8}
  ],
  "net": 3100,
  "reserve_ratio": 1.45
}
```

---

## Implementation Checklist

### Phase 1: Core Wiring
- [ ] Add Commons Reserve ledger to fp-credits-gateway
- [ ] Create `/api/commons/*` endpoints
- [ ] Wire UC protocol fees (30%)
- [ ] Wire member donations (80%)

### Phase 2: Domain Integration
- [ ] Wire $FI transaction fees (30%)
- [ ] Update Sacred Circulation Policy
- [ ] Wire Treasury Arena yields (30% of surplus)

### Phase 3: Service Integration
- [ ] Wire AI Brain margins (20%)
- [ ] Wire Voice Phone margins (20%)
- [ ] Wire Content Studio margins (20%)
- [ ] Wire I-Match margins (20%)

### Phase 4: Trust-Level
- [ ] Update Sunheart Trust distribution policy
- [ ] Formalize LLC → Trust → Commons flow

---

## Monitoring

Add to God Mode dashboard:

### Commons Flow Widget
```
┌─────────────────────────────────────────┐
│  Commons Reserve                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Balance: $52,340                       │
│  Reserve Ratio: 1.45x                   │
│                                         │
│  This Month:                            │
│  ├─ Inflows:  +$5,234                  │
│  ├─ Outflows: -$2,100 (needs)          │
│  └─ Net:      +$3,134                  │
│                                         │
│  Sources (This Month):                  │
│  ▓▓▓▓▓▓░░░░ UC Fees    $1,500 (29%)   │
│  ▓▓▓▓░░░░░░ $FI Fees   $800  (15%)    │
│  ▓▓▓▓▓░░░░░ LLC Prof   $1,200 (23%)   │
│  ▓▓░░░░░░░░ Donations  $500  (10%)    │
│  ▓▓▓░░░░░░░ Treasury   $700  (13%)    │
│  ▓░░░░░░░░░ Services   $300  (6%)     │
└─────────────────────────────────────────┘
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-11 | Initial specification |

---

**END OF SPEC**










