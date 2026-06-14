# Trust Index Service Specification

**Service:** trust-index  
**Port:** 8560  
**Version:** 1.0.0  
**Status:** SPEC - Ready for Build  
**Canonical Reference:** `docs/protocols/TOKENS_STRATEGY.md`

---

## Overview

The Trust Index Service calculates and publishes the Trust Index, a composite metric (0-1) that guides Commons Ministry policy. It extends the existing Treasury Health Score (THS) with additional dimensions.

---

## Purpose

1. **Calculate Trust Index** from multiple data sources
2. **Publish metrics** for AI stewardship and governance
3. **Trigger policy adjustments** based on index thresholds
4. **Provide transparency** to members and systems

---

## Trust Index Formula

```
Trust Index = (
    Solvency Score × 0.40 +
    Commons Health Score × 0.30 +
    Participation Score × 0.30
)
```

### Component Calculations

#### 1. Solvency Score (40% weight)
Source: Treasury Health Score from `fp-credits-gateway`

```python
solvency_score = min(1.0, treasury_health_score / 1.5)

# Where THS = Treasury Assets / UC Outstanding
# THS of 1.5+ = 1.0 score
# THS of 1.0 = 0.67 score
# THS of 0.5 = 0.33 score
```

#### 2. Commons Health Score (30% weight)
Source: Commons Reserve Fund metrics

```python
reserve_ratio = commons_reserve / committed_needs
liquidity_ratio = liquid_assets / total_reserve
stability = 1 - (volatility_30d / max_acceptable_volatility)

commons_health = (
    min(1.0, reserve_ratio / 2.0) * 0.50 +
    liquidity_ratio * 0.30 +
    stability * 0.20
)
```

#### 3. Participation Score (30% weight)
Source: PMA membership and contribution data

```python
active_ratio = active_contributors / total_trust_holders
avg_contribution = avg_quarterly_score / target_score
retention = members_retained / members_start

participation_score = (
    active_ratio * 0.50 +
    min(1.0, avg_contribution) * 0.30 +
    retention * 0.20
)
```

---

## API Endpoints

### GET /api/trust-index
Returns current Trust Index and components.

**Response:**
```json
{
  "trust_index": 0.72,
  "components": {
    "solvency": {
      "score": 0.85,
      "weight": 0.40,
      "contribution": 0.34,
      "source": "fp-credits-gateway",
      "raw_ths": 1.28
    },
    "commons_health": {
      "score": 0.65,
      "weight": 0.30,
      "contribution": 0.195,
      "reserve_ratio": 1.30,
      "liquidity_ratio": 0.75,
      "stability": 0.80
    },
    "participation": {
      "score": 0.62,
      "weight": 0.30,
      "contribution": 0.186,
      "active_ratio": 0.55,
      "avg_contribution": 0.70,
      "retention": 0.85
    }
  },
  "policy_posture": "balanced",
  "timestamp": "2025-12-11T18:00:00Z",
  "next_update": "2025-12-11T19:00:00Z"
}
```

### GET /api/trust-index/history
Returns historical Trust Index values.

**Query Parameters:**
- `period`: `1d`, `7d`, `30d`, `90d` (default: `7d`)
- `granularity`: `hourly`, `daily` (default: `daily`)

### GET /api/trust-index/policy
Returns current policy parameters based on Trust Index.

**Response:**
```json
{
  "trust_index": 0.72,
  "posture": "generous",
  "parameters": {
    "safety_buffer": 1.20,
    "distribution_categories": ["survival", "stability", "growth", "contribution", "infrastructure"],
    "max_single_allocation": 0.05,
    "daily_change_limit": 0.05
  },
  "guardrails": {
    "min_reserve_ratio": 1.20,
    "emergency_freeze_threshold": 0.20,
    "human_override": true
  }
}
```

### POST /api/trust-index/simulate
Simulate Trust Index under hypothetical conditions.

**Request:**
```json
{
  "ths_override": 1.5,
  "reserve_ratio_override": 1.8,
  "active_ratio_override": 0.70
}
```

---

## Data Sources

| Component | Source | Endpoint |
|-----------|--------|----------|
| Treasury Health Score | fp-credits-gateway | `/api/treasury/health` |
| Commons Reserve | Sunheart Trust metrics | Internal |
| Committed Needs | Needs Allocation Engine | `/api/needs/committed` |
| Active Contributors | PMA membership system | `/api/members/active` |
| Contribution Scores | Contribution tracker | `/api/contributions/aggregate` |

---

## Policy Thresholds

| Trust Index | Posture | Actions |
|-------------|---------|---------|
| < 0.3 | Conservative | Survival only, 200% buffer, reduced distributions |
| 0.3 - 0.7 | Balanced | Survival + Stability, 150% buffer, standard distributions |
| > 0.7 | Generous | All categories, 120% buffer, expanded distributions |

---

## Events / Webhooks

The service publishes events to the event bus:

| Event | Trigger | Payload |
|-------|---------|---------|
| `trust_index.updated` | Every calculation | Full index data |
| `trust_index.threshold_crossed` | Posture change | Old/new posture, index |
| `trust_index.emergency` | Index < 0.2 | Alert data |

---

## Hard Guardrails

These are enforced regardless of Trust Index:

```python
GUARDRAILS = {
    "min_reserve_ratio": 1.20,
    "max_daily_change": 0.05,
    "emergency_freeze": 0.20,  # Trust Index below this freezes distributions
    "human_override": True,  # Always available
    "max_single_allocation": 0.05  # 5% of monthly budget
}
```

---

## Integration

### With AI Stewardship
```python
# AI systems query Trust Index to adjust policy
trust_index = await get_trust_index()
policy = get_policy_for_index(trust_index)
apply_policy(policy)
```

### With Needs Allocation
```python
# Needs engine uses Trust Index for budget
trust_index = await get_trust_index()
available_budget = calculate_budget(trust_index, commons_reserve)
```

### With God Mode Dashboard
```python
# Dashboard displays Trust Index widget
GET /api/trust-index -> Display ring chart
GET /api/trust-index/history -> Display trend line
```

---

## Tech Stack

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL (for history)
- **Cache:** Redis (for current values)
- **Scheduler:** APScheduler (hourly calculations)

---

## File Structure

```
SERVICES/trust-index/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── models.py            # Pydantic models
│   ├── calculator.py        # Trust Index calculation
│   ├── policy.py            # Policy determination
│   ├── sources/
│   │   ├── solvency.py      # THS integration
│   │   ├── commons.py       # Reserve metrics
│   │   └── participation.py # Member metrics
│   └── routers/
│       ├── index.py         # Main endpoints
│       └── admin.py         # Admin endpoints
├── tests/
├── Dockerfile
├── requirements.txt
└── SPEC.md
```

---

## Deployment

```yaml
# docker-compose snippet
trust-index:
  build: ./SERVICES/trust-index
  ports:
    - "8560:8560"
  environment:
    - DATABASE_URL=postgresql://...
    - REDIS_URL=redis://...
    - CREDITS_GATEWAY_URL=http://fp-credits-gateway:8765
  depends_on:
    - postgres
    - redis
    - fp-credits-gateway
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-11 | Initial specification |

---

**END OF SPEC**










