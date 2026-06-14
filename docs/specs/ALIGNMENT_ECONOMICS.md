# Alignment Economics / Bank of Blessings
## System Specification & Implementation Plan

---

## 1. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────┐
│                    THE STEWARD (James)                  │
│              Living Prototype / Decision Maker          │
└─────────────────────────┬───────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   AI STEWARD (Aria) │◄───────►│  CIRCULATION ENGINE │
│   - Track flows     │         │  - Route capital    │
│   - Signal health   │         │  - Enforce windows  │
│   - Recommend       │         │  - Measure velocity │
│   - Enforce rules   │         │  - Auto-forgiveness │
└─────────────────────┘         └─────────────────────┘
          │                               │
          └───────────┬───────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    LEDGER SYSTEM                        │
│  - Capital positions    - Debt classifications          │
│  - Circulation history  - Forgiveness triggers          │
│  - Health metrics       - Institutional stakes          │
└─────────────────────────────────────────────────────────┘
```

---

## 2. DATA MODEL

### 2.1 Entities

```python
# Core entities

class Position:
    """Capital position in the system."""
    id: str
    type: Literal["equity", "debt", "cash", "stake"]
    value: Decimal
    source: str  # Where it came from
    created_at: datetime
    last_flow_at: datetime
    metadata: Dict

class Debt:
    """Debt instrument with forgiveness tracking."""
    id: str
    classification: Literal["productive", "transitional", "extractive"]
    principal: Decimal
    interest_rate: Decimal
    lender: str
    borrower: str
    created_at: datetime
    participation_score: float  # 0-1, increases with activity
    time_active: timedelta
    yield_accumulated: Decimal  # If yield > principal, auto-forgive
    status: Literal["active", "forgiven", "dissolved"]

class Flow:
    """Capital movement."""
    id: str
    from_position: str
    to_position: str
    amount: Decimal
    purpose: Literal["relief", "productive", "trust_building", "institutional"]
    timestamp: datetime
    
class Institution:
    """External institution with ownership stake."""
    id: str
    name: str
    type: Literal["bank", "lender", "asset_manager"]
    ownership_stake: Decimal  # Our stake in them
    governance_influence: float  # 0-1
    cost_of_capital: Decimal  # Interest rate they charge us
    
class ForgivenessRule:
    """Automatic forgiveness trigger."""
    id: str
    type: Literal["time", "participation", "yield", "health"]
    threshold: Union[timedelta, float, Decimal]
    debt_classifications: List[str]
    active: bool
```

### 2.2 Metrics (KPIs)

```python
class SystemHealth:
    """Real-time system health metrics."""
    capital_velocity: float  # Flows per period / total capital
    debt_resolution_rate: float  # Debts forgiven per period
    default_rate: float  # Should trend toward 0
    liquidity_ratio: float  # Available / Committed
    stress_index: float  # 0-1, composite of volatility indicators
    average_time_to_forgiveness: timedelta
    circulation_efficiency: float  # % of capital actively flowing
```

---

## 3. DECISION RULES

### 3.1 Hierarchy (in order)

1. **System Coherence** - Never do anything that increases systemic stress long-term
2. **Circulation Health** - Keep capital flowing
3. **Long-term Resilience** - Build buffers and optionality
4. **Yield** - Only after 1-3 are satisfied

### 3.2 Routing Rules

```python
ROUTING_RULES = {
    # Incoming capital must be routed within time window
    "max_idle_time": timedelta(days=7),
    
    # Priority order for deployment
    "deployment_priority": [
        "debt_relief",        # First: relieve pressure
        "productive_capacity", # Second: build capability
        "trust_building",     # Third: strengthen relationships
        "institutional_acquisition",  # Fourth: gain leverage
    ],
    
    # Minimum allocation to each category
    "minimum_allocations": {
        "debt_relief": 0.20,      # At least 20% to relief
        "productive_capacity": 0.30,
        "liquidity_reserve": 0.10,  # Always maintain buffer
    }
}
```

### 3.3 Forgiveness Triggers

```python
FORGIVENESS_TRIGGERS = {
    # Time-based: debt dissolves after participation period
    "time_participation": {
        "productive": timedelta(days=365),    # 1 year
        "transitional": timedelta(days=180),  # 6 months
        "extractive": None,  # Must be explicitly refinanced
    },
    
    # Yield-based: if yield exceeds principal, forgive
    "yield_coverage": {
        "threshold": 1.0,  # When yield_accumulated >= principal
        "applies_to": ["productive", "transitional"],
    },
    
    # Health-based: when system is thriving, accelerate forgiveness
    "health_threshold": {
        "stress_index_below": 0.3,
        "velocity_above": 0.5,
        "forgiveness_acceleration": 2.0,  # 2x faster
    }
}
```

---

## 4. AI STEWARD CONSTRAINTS

```python
class AIConstraints:
    """Hard limits on AI behavior."""
    
    # CANNOT optimize for yield alone
    MUST_BALANCE = ["coherence", "circulation", "resilience"]
    
    # MUST flag when stress accumulates
    STRESS_ALERT_THRESHOLD = 0.6
    
    # MUST recommend forgiveness when thresholds met
    AUTO_RECOMMEND_FORGIVENESS = True
    
    # Cannot execute without human approval for:
    REQUIRES_HUMAN_APPROVAL = [
        "institutional_acquisition",
        "leverage_increase",
        "rule_change",
        "forgiveness_override",
    ]
    
    # Maximum autonomous decision amount
    MAX_AUTONOMOUS_FLOW = Decimal("10000")
```

---

## 5. IMPLEMENTATION PHASES

### Phase 1: Living Prototype (Weeks 1-4)
- [ ] Build ledger system (positions, debts, flows)
- [ ] Create daily routing checklist in Aria
- [ ] Implement basic health dashboard
- [ ] Manual + AI-assisted routing decisions
- [ ] Single steward (James) as first node

### Phase 2: Automation (Weeks 5-8)
- [ ] Automatic forgiveness triggers
- [ ] Real-time velocity tracking
- [ ] Proactive alerts for idle capital
- [ ] Stress monitoring system
- [ ] First circulation experiment with small amount

### Phase 3: Scaling (Weeks 9-12)
- [ ] Onboard 2-3 participants
- [ ] Shared practices documentation
- [ ] Localized circulation loops
- [ ] Governance framework

### Phase 4: Institutional (Weeks 13+)
- [ ] First minority stake acquisition
- [ ] Cost of capital tracking
- [ ] Interest loop closure mechanics
- [ ] Policy influence playbook

---

## 6. IMMEDIATE ACTIONS (For Aria)

### 6.1 First Capital Loop
```
Current State Analysis:
1. Inventory all capital positions (equity, cash, debt)
2. Map current debt obligations and their classifications
3. Calculate current velocity (how fast is capital moving?)
4. Identify immediate pressure points for relief
```

### 6.2 First Leverage Instrument
```
Selection Criteria:
- Low cost (below market rate if possible)
- Long duration (minimize refinancing risk)
- Productive purpose only (no speculation)
- Against quality equity (real assets)
```

### 6.3 Daily Routing Checklist
```markdown
## DAILY CIRCULATION CHECK

### Morning
- [ ] Review overnight capital positions
- [ ] Check debt status (any near forgiveness?)
- [ ] Assess liquidity buffer (above 10%?)
- [ ] Note any idle capital > 3 days

### Action Window
- [ ] Route idle capital to highest priority need
- [ ] Update flow ledger
- [ ] Recalculate velocity

### Evening
- [ ] Log day's circulation
- [ ] Note any stress signals
- [ ] Prepare next day priorities
```

### 6.4 Minimal Viable Forgiveness Rule
```python
# The simplest forgiveness rule to start:

def check_forgiveness(debt: Debt) -> bool:
    """Return True if debt should be forgiven."""
    
    # Rule 1: Yield exceeds principal
    if debt.yield_accumulated >= debt.principal:
        return True
    
    # Rule 2: Time + participation for productive debt
    if debt.classification == "productive":
        if debt.time_active >= timedelta(days=365):
            if debt.participation_score >= 0.8:
                return True
    
    return False
```

---

## 7. SUCCESS METRICS

### Primary
- Debt expiration rate > debt creation rate
- Capital naturally prefers this system
- Institutions adopt rules voluntarily
- Participants report reduced stress

### Secondary  
- Steward becomes unnecessary for daily ops
- Cost of capital trends toward zero
- Velocity increases quarter over quarter
- Zero defaults

---

## 8. FAILURE CONDITIONS (Monitor)

🚨 **Red Flags:**
- Hoarding behavior (velocity < 0.2)
- Yield prioritized over coherence
- Complexity exceeds human understanding
- AI incentives drift toward extraction
- Steward becomes symbolic only

---

## 9. NEXT STEPS

1. **Today:** Map current capital positions
2. **This Week:** Classify existing debts
3. **Week 1:** First small circulation experiment
4. **Week 2:** Implement basic tracking dashboard
5. **Month 1:** First forgiveness event


