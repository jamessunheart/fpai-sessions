# Contribution Tracker Service Specification

**Service:** contribution-tracker  
**Port:** 8570  
**Version:** 1.0.0  
**Status:** SPEC - Ready for Build  
**Canonical Reference:** `docs/protocols/TOKENS_STRATEGY.md`

---

## Overview

The Contribution Tracker Service tracks member contributions to the commons, calculates Proof of Contribution scores, and manages TRUST token earning. It is the backbone of the "earn, don't buy" token model.

---

## Purpose

1. **Track contributions** from all sources (service, governance, art, referrals, donations)
2. **Calculate contribution scores** for Proof of Contribution
3. **Issue TRUST tokens** based on verified contributions
4. **Determine eligibility tiers** for ministry benefits
5. **Provide transparency** to members on their contribution status

---

## Contribution Types

| Type | TRUST Earned | Verification |
|------|-------------|--------------|
| **Service** | 10 per verified hour | Recipient confirmation |
| **Governance** | 5 per vote cast | Automatic |
| **Art/Content** | Variable (1-100) | FI-Art platform |
| **Referral** | 50 per new member | Member activation |
| **Financial** | 1 per UC contributed | Payment confirmation |
| **Community** | Variable (1-50) | Council recognition |

---

## Contribution Score

The contribution score determines benefit eligibility:

```python
def calculate_quarterly_score(member_id: str, quarter: str) -> int:
    """Calculate quarterly contribution score."""
    contributions = get_contributions(member_id, quarter)
    
    total_score = 0
    for contribution in contributions:
        if contribution.verified:
            total_score += contribution.trust_earned
    
    return total_score
```

### Eligibility Tiers

| Tier | Quarterly Score | Benefit Eligibility | Voting Multiplier |
|------|-----------------|---------------------|-------------------|
| **Active** | 100+ | Full | 1.0x |
| **Engaged** | 50-99 | Reduced (survival only) | 0.5x |
| **Inactive** | <50 | None | 0x |
| **Founder** | Any + early contributor | Full + priority | 1.5x |

---

## API Endpoints

### POST /api/contributions/log
Log a new contribution.

**Request:**
```json
{
  "member_id": "mem_abc123",
  "type": "service",
  "description": "Helped new member with onboarding",
  "hours": 2,
  "recipient_id": "mem_xyz789",
  "evidence": ["link_to_chat", "screenshot"]
}
```

**Response:**
```json
{
  "contribution_id": "contrib_123",
  "member_id": "mem_abc123",
  "type": "service",
  "status": "pending_verification",
  "trust_potential": 20,
  "verification_method": "recipient_confirmation",
  "verification_deadline": "2025-12-14T18:00:00Z"
}
```

### POST /api/contributions/verify/{contribution_id}
Verify a contribution (by recipient or council).

**Request:**
```json
{
  "verifier_id": "mem_xyz789",
  "verified": true,
  "notes": "Excellent help, very patient"
}
```

### GET /api/contributions/member/{member_id}
Get member's contribution history.

**Query Parameters:**
- `period`: `quarter`, `year`, `all` (default: `quarter`)
- `type`: filter by contribution type

**Response:**
```json
{
  "member_id": "mem_abc123",
  "period": "2025-Q4",
  "total_score": 145,
  "tier": "active",
  "trust_earned": 145,
  "contributions": [
    {
      "id": "contrib_123",
      "type": "service",
      "trust_earned": 20,
      "verified": true,
      "date": "2025-12-10"
    }
  ],
  "by_type": {
    "service": 60,
    "governance": 25,
    "referral": 50,
    "financial": 10
  }
}
```

### GET /api/contributions/score/{member_id}
Get current contribution score.

**Response:**
```json
{
  "member_id": "mem_abc123",
  "current_quarter": "2025-Q4",
  "quarterly_score": 145,
  "tier": "active",
  "next_tier": null,
  "points_to_next_tier": 0,
  "voting_multiplier": 1.0,
  "benefit_eligible": true,
  "eligible_categories": ["survival", "stability", "growth"]
}
```

### GET /api/contributions/leaderboard
Get top contributors.

**Query Parameters:**
- `period`: `week`, `month`, `quarter`, `year`
- `limit`: number of results (default: 10)

### GET /api/contributions/aggregate
Get aggregate contribution metrics (for Trust Index).

**Response:**
```json
{
  "period": "2025-Q4",
  "total_members": 500,
  "active_contributors": 275,
  "active_ratio": 0.55,
  "avg_quarterly_score": 87,
  "total_trust_issued": 43500,
  "by_type": {
    "service": 15000,
    "governance": 8000,
    "art": 5000,
    "referral": 10000,
    "financial": 5500
  }
}
```

---

## TRUST Issuance

When contributions are verified, TRUST is issued:

```python
async def issue_trust(contribution: Contribution):
    """Issue TRUST tokens for verified contribution."""
    
    if not contribution.verified:
        raise ValueError("Cannot issue TRUST for unverified contribution")
    
    # Calculate TRUST amount
    trust_amount = calculate_trust_amount(contribution)
    
    # Issue to member
    await trust_ledger.credit(
        member_id=contribution.member_id,
        amount=trust_amount,
        reason=f"contribution_{contribution.type}",
        contribution_id=contribution.id
    )
    
    # Update contribution record
    contribution.trust_issued = trust_amount
    contribution.issued_at = datetime.utcnow()
    
    # Emit event
    await events.emit("trust.issued", {
        "member_id": contribution.member_id,
        "amount": trust_amount,
        "contribution_id": contribution.id
    })
```

---

## Verification Methods

| Contribution Type | Verification Method | Timeout |
|-------------------|---------------------|---------|
| Service | Recipient confirmation | 7 days |
| Governance | Automatic (vote recorded) | Immediate |
| Art/Content | FI-Art platform metrics | Automatic |
| Referral | New member activation | 30 days |
| Financial | Payment confirmation | Automatic |
| Community | Council recognition | 14 days |

### Verification Timeout
If verification times out:
- Service: Escalate to council review
- Referral: Extend if member active
- Community: Default to deny

---

## Founding Contributor Program

Early contributors earn enhanced TRUST:

```python
FOUNDING_MULTIPLIER = 1.5  # 50% bonus during bootstrap phase

def is_founding_period() -> bool:
    # Founding period: until Commons Reserve reaches $100K
    return commons_reserve < 100000

def calculate_trust_amount(contribution: Contribution) -> int:
    base = TRUST_RATES[contribution.type]
    
    if is_founding_period():
        return int(base * FOUNDING_MULTIPLIER)
    return base
```

Founding contributors also receive:
- **Founder** tier designation (permanent)
- Priority benefit eligibility
- Enhanced voting multiplier (1.5x)

---

## Integration

### With Needs Allocation
```python
# Check eligibility before processing request
score = await contribution_tracker.get_score(member_id)
if score.tier == "inactive":
    deny_request("Proof of Contribution not met")
```

### With Trust Index
```python
# Provide aggregate metrics for participation component
aggregate = await contribution_tracker.get_aggregate()
participation_score = calculate_participation(aggregate)
```

### With FI-Art
```python
# Receive art contribution events
@events.on("fi_art.creation_minted")
async def handle_art_contribution(event):
    await contribution_tracker.log({
        "member_id": event.creator_id,
        "type": "art",
        "trust_amount": event.trust_value,
        "verified": True  # Auto-verified by platform
    })
```

### With Governance
```python
# Receive vote events
@events.on("governance.vote_cast")
async def handle_vote(event):
    await contribution_tracker.log({
        "member_id": event.voter_id,
        "type": "governance",
        "trust_amount": 5,
        "verified": True  # Auto-verified
    })
```

---

## Events / Webhooks

| Event | Trigger | Payload |
|-------|---------|---------|
| `contribution.logged` | New contribution | Contribution data |
| `contribution.verified` | Verification complete | Contribution + verifier |
| `contribution.denied` | Verification failed | Contribution + reason |
| `trust.issued` | TRUST issued | Member + amount + contribution |
| `tier.changed` | Member tier change | Member + old/new tier |

---

## Tech Stack

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **Queue:** Redis + Celery
- **Cache:** Redis

---

## File Structure

```
SERVICES/contribution-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── models.py            # Pydantic models
│   ├── db_models.py         # SQLAlchemy models
│   ├── scoring.py           # Score calculation
│   ├── verification.py      # Verification logic
│   ├── issuance.py          # TRUST issuance
│   ├── tiers.py             # Tier determination
│   └── routers/
│       ├── contributions.py # Main endpoints
│       ├── scores.py        # Score endpoints
│       └── admin.py         # Admin endpoints
├── tests/
├── Dockerfile
├── requirements.txt
└── SPEC.md
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-11 | Initial specification |

---

**END OF SPEC**










