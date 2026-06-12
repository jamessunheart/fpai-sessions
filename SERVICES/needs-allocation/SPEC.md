# Needs Allocation Engine Specification

**Service:** needs-allocation  
**Port:** 8565  
**Version:** 1.0.0  
**Status:** SPEC - Ready for Build  
**Canonical Reference:** `docs/protocols/TOKENS_STRATEGY.md`

---

## Overview

The Needs Allocation Engine manages the distribution of ministry benefits from the Commons Reserve Fund to eligible members. It processes needs-support requests, enforces fairness rules, and ensures benefits flow to genuine needs.

---

## Purpose

1. **Process needs-support requests** from PMA members
2. **Verify eligibility** (TRUST holding + Proof of Contribution)
3. **Allocate resources** across benefit categories
4. **Enforce fairness limits** and hard guardrails
5. **Track and report** all allocations

---

## Needs Categories

| Category | Allocation | Description |
|----------|------------|-------------|
| **Survival** | 40% | Food, shelter, health emergencies |
| **Stability** | 25% | Debt relief, emergency fund, insurance |
| **Growth** | 20% | Education, tools, creation grants |
| **Contribution** | 10% | Contributor recognition and support |
| **Infrastructure** | 5% | Commons infrastructure, public goods |

---

## Request Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Member    │────▶│ Personal AI │────▶│  Global AI  │────▶│  Approval   │
│   Request   │     │   Steward   │     │   Policy    │     │  & Fulfill  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                          │                    │
                          ▼                    ▼
                    Check eligibility    Check budget
                    Check need type      Check fairness
                    Check history        Check guardrails
```

### Step 1: Member Request
Member submits needs-support request via platform:
- Category (survival, stability, growth, etc.)
- Description of need
- Amount requested (in UC equivalent)
- Supporting documentation (optional)

### Step 2: Personal AI Assessment
Personal AI steward checks:
- TRUST holding (minimum required)
- Proof of Contribution score (100+ quarterly)
- Recent request history
- Category appropriateness

### Step 3: Global Policy Check
Needs Allocation Engine checks:
- Commons Reserve health (Trust Index)
- Category budget availability
- Fairness limits (max 5% of monthly to one member)
- Hard guardrails

### Step 4: Approval & Fulfillment
If approved:
- Benefit provided in-kind (services, support)
- Logged in allocation history
- Member notified

If denied:
- Reason provided
- Appeal path offered

---

## API Endpoints

### POST /api/needs/request
Submit a needs-support request.

**Request:**
```json
{
  "member_id": "mem_abc123",
  "category": "survival",
  "subcategory": "housing",
  "description": "Emergency rent assistance for unexpected job loss",
  "amount_uc": 500,
  "urgency": "high",
  "supporting_docs": ["doc_xyz"]
}
```

**Response:**
```json
{
  "request_id": "req_123",
  "status": "pending_review",
  "estimated_decision": "2025-12-11T20:00:00Z",
  "eligibility": {
    "trust_held": 250,
    "contribution_score": 145,
    "eligible": true
  }
}
```

### GET /api/needs/request/{request_id}
Get request status.

### GET /api/needs/budget
Get current budget allocation.

**Response:**
```json
{
  "trust_index": 0.72,
  "posture": "generous",
  "monthly_budget_uc": 10000,
  "categories": {
    "survival": {"budget": 4000, "used": 2500, "available": 1500},
    "stability": {"budget": 2500, "used": 1000, "available": 1500},
    "growth": {"budget": 2000, "used": 800, "available": 1200},
    "contribution": {"budget": 1000, "used": 400, "available": 600},
    "infrastructure": {"budget": 500, "used": 100, "available": 400}
  },
  "period": "2025-12",
  "resets": "2026-01-01T00:00:00Z"
}
```

### GET /api/needs/eligibility/{member_id}
Check member eligibility.

**Response:**
```json
{
  "member_id": "mem_abc123",
  "eligible": true,
  "trust_held": 250,
  "contribution_score": 145,
  "contribution_tier": "active",
  "recent_allocations": 2,
  "recent_total_uc": 300,
  "fairness_limit_remaining": 200,
  "eligible_categories": ["survival", "stability", "growth"]
}
```

### GET /api/needs/committed
Get total committed needs (for Trust Index calculation).

**Response:**
```json
{
  "total_committed_uc": 25000,
  "pending_requests_uc": 5000,
  "approved_pending_fulfillment_uc": 3000,
  "monthly_projection_uc": 12000
}
```

### POST /api/needs/fulfill/{request_id}
Mark request as fulfilled.

### POST /api/needs/appeal/{request_id}
Submit appeal for denied request.

---

## Eligibility Rules

### TRUST Holding
- Minimum: 50 TRUST to request survival benefits
- Minimum: 100 TRUST to request stability benefits
- Minimum: 150 TRUST to request growth benefits

### Proof of Contribution

| Tier | Quarterly Score | Eligibility |
|------|-----------------|-------------|
| Active | 100+ | All categories |
| Engaged | 50-99 | Survival only, 50% max |
| Inactive | <50 | Not eligible |

### Fairness Limits
- Maximum 5% of monthly budget per member
- Maximum 3 requests per month per member
- 30-day cooldown after large allocation (>$200)

---

## Budget Calculation

```python
def calculate_monthly_budget(trust_index: float, commons_reserve: float) -> float:
    """Calculate monthly budget based on Trust Index and reserve."""
    
    # Base rate: 5% of reserve when generous, 1% when conservative
    if trust_index > 0.7:
        base_rate = 0.05  # Generous
    elif trust_index > 0.3:
        base_rate = 0.03  # Balanced
    else:
        base_rate = 0.01  # Conservative
    
    # Apply safety buffer
    safety_reserve = commons_reserve * 0.20  # Always keep 20%
    available = commons_reserve - safety_reserve
    
    # Calculate budget
    monthly_budget = available * base_rate
    
    return monthly_budget
```

---

## Hard Guardrails

```python
GUARDRAILS = {
    "min_reserve_ratio": 1.20,  # Stop distributions if below
    "max_single_allocation_percent": 0.05,  # 5% of monthly
    "max_single_allocation_absolute": 1000,  # UC max per request
    "max_requests_per_month": 3,
    "cooldown_days_large_allocation": 30,
    "emergency_freeze_trust_index": 0.20
}
```

---

## Benefit Fulfillment

Benefits are provided in-kind, NEVER as cash:

| Need Type | Fulfillment Method |
|-----------|-------------------|
| Housing | Direct payment to landlord/service |
| Health | Payment to provider or UC credits for health services |
| Education | Course access, UC credits for educational services |
| Tools | Direct provision or UC credits for equipment |
| Emergency | Immediate service access, expedited processing |

---

## Integration

### With Trust Index Service
```python
# Get Trust Index for policy decisions
trust_index = await trust_index_service.get_current()
policy = get_policy(trust_index)
```

### With PMA Membership
```python
# Verify member eligibility
member = await pma_service.get_member(member_id)
contribution_score = await contribution_service.get_score(member_id)
```

### With Credits Gateway
```python
# Issue service credits for fulfillment
await credits_gateway.credit(
    user_id=member_id,
    amount=approved_amount,
    reason="needs_allocation",
    category=category
)
```

---

## Events / Webhooks

| Event | Trigger | Payload |
|-------|---------|---------|
| `needs.request_submitted` | New request | Request data |
| `needs.request_approved` | Approval | Request + allocation |
| `needs.request_denied` | Denial | Request + reason |
| `needs.request_fulfilled` | Fulfillment | Request + fulfillment |
| `needs.budget_low` | Category < 20% | Category + remaining |
| `needs.guardrail_triggered` | Limit hit | Guardrail + context |

---

## Tech Stack

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **Queue:** Redis + Celery (for async processing)
- **Cache:** Redis

---

## File Structure

```
SERVICES/needs-allocation/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── models.py            # Pydantic models
│   ├── db_models.py         # SQLAlchemy models
│   ├── eligibility.py       # Eligibility checking
│   ├── budget.py            # Budget calculation
│   ├── allocation.py        # Allocation logic
│   ├── fulfillment.py       # Fulfillment handling
│   ├── guardrails.py        # Guardrail enforcement
│   └── routers/
│       ├── requests.py      # Request endpoints
│       ├── budget.py        # Budget endpoints
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










