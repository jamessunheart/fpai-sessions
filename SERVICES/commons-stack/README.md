# Commons Ministry Token Stack

**Reference:** `docs/protocols/TOKENS_STRATEGY.md` v1.0.0

## Overview

The Commons Ministry Token Stack provides the AI-governed infrastructure for the TRUST token and needs-based ministry benefits.

## Services

| Service | Port | Description |
|---------|------|-------------|
| Trust Index | 8560 | Calculates Trust Index from solvency, commons health, participation |
| Contribution Tracker | 8570 | Tracks contributions, issues TRUST tokens |
| Needs Allocation | 8565 | Distributes ministry benefits to eligible members |

## Quick Start

```bash
# Start all services
cd SERVICES/commons-stack
docker-compose up -d

# Check health
curl http://localhost:8560/health  # Trust Index
curl http://localhost:8570/health  # Contribution Tracker
curl http://localhost:8565/health  # Needs Allocation
```

## API Overview

### Trust Index (8560)
```bash
# Get current Trust Index
curl http://localhost:8560/api/trust-index

# Get policy parameters
curl http://localhost:8560/api/trust-index/policy

# Simulate with overrides
curl -X POST http://localhost:8560/api/trust-index/simulate \
  -H "Content-Type: application/json" \
  -d '{"ths_override": 1.5}'
```

### Contribution Tracker (8570)
```bash
# Log a contribution
curl -X POST http://localhost:8570/api/contributions/log \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": "member_123",
    "type": "service",
    "description": "Community mentoring",
    "hours": 2
  }'

# Get member score
curl http://localhost:8570/api/contributions/score/member_123

# Get TRUST balance
curl http://localhost:8570/api/trust/balance/member_123
```

### Needs Allocation (8565)
```bash
# Check eligibility
curl http://localhost:8565/api/needs/eligibility/member_123

# Submit request
curl -X POST http://localhost:8565/api/needs/request \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": "member_123",
    "category": "survival",
    "description": "Rent assistance",
    "amount_uc": 500,
    "urgency": "high"
  }'

# Get budget
curl http://localhost:8565/api/needs/budget
```

## Token Stack

| Token | Purpose | This Stack |
|-------|---------|------------|
| UC | Spend / Cash Rail | Used for needs amounts |
| TRUST | Commons Membership | Issued by Contribution Tracker |
| $FI | FI-Art Domain | Separate system |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   TRUST INDEX                        │
│  Solvency (40%) + Commons (30%) + Participation (30%)│
│                    Port 8560                         │
└───────────────────────┬─────────────────────────────┘
                        │ Policy Parameters
        ┌───────────────┴───────────────┐
        ▼                               ▼
┌───────────────────┐         ┌───────────────────┐
│ CONTRIBUTION      │         │ NEEDS ALLOCATION  │
│ TRACKER           │◄───────►│ ENGINE            │
│ Port 8570         │         │ Port 8565         │
│                   │         │                   │
│ - Log contrib     │         │ - Check elig      │
│ - Issue TRUST     │         │ - Request support │
│ - Score members   │         │ - Fulfill needs   │
└───────────────────┘         └───────────────────┘
```

## Guardrails (Hard Limits)

These cannot be overridden by AI:

| Guardrail | Value |
|-----------|-------|
| Min reserve ratio | 120% |
| Max daily change | 5% |
| Emergency freeze | Trust Index < 0.2 |
| Max single allocation | 5% of monthly budget |
| Human override | Always available |

## Legal Compliance

All communications must use approved language:

❌ **Forbidden:** investment, profit, yield, dividend, ROI, guaranteed
✅ **Use instead:** contribution, blessings, abundance, ministry benefits

See: `docs/legal/LEGAL_QUICK_REFERENCE.md`

---

*Commons Ministry | Church of Consciousness*
*"Contribution creates abundance for all"*










