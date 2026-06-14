# GOVERNANCE - Technical Specification

**Service Name:** governance
**Version:** 1.0.0



---

## Purpose

AI-powered governance engine that validates intent alignment with system blueprint and makes autonomous approval decisions. Enables the system to build itself responsibly by ensuring new services align with strategic goals, while allowing human oversight through configurable policies.

The governance brain that enables "autonomous mode while you're away."

---

## Capabilities

This service provides the following capabilities as part of the FPAI droplet mesh:

### Primary Functions

See 'Core Capabilities' section below for detailed descriptions.

## Core Capabilities

- **Blueprint Alignment Check:** Claude API validates intent against system blueprint
- **Policy Engine:** Rule-based governance decisions
- **Auto-Approval Logic:** Autonomous decision-making based on alignment + policies
- **Risk Assessment:** Evaluate potential impacts of new services
- **Governance Modes:** Supervised / Autonomous / Aggressive
- **Audit Trail:** Complete record of all decisions and reasoning
- **User Policies:** Configurable rules for auto-approval
- **Override Mechanism:** Human can override any decision

---

## UDC Endpoints (5/5)

### 1. GET /health
**Returns:** Service health status
```json
{
  "status": "active",
  "service": "governance",
  "version": "1.0.0",
  "timestamp": "2025-11-16T00:00:00Z",
  "current_mode": "autonomous",
  "claude_api": "connected",
  "decisions_today": 45
}
```

### 2. GET /capabilities
**Returns:** Service capabilities and metadata
```json
{
  "version": "1.0.0",
  "features": [
    "blueprint_alignment",
    "policy_engine",
    "auto_approval",
    "risk_assessment",
    "governance_modes",
    "audit_trail"
  ],
  "dependencies": ["registry", "intent-queue"],
  "udc_version": "1.0",
  "metadata": {
    "claude_model": "claude-sonnet-4-5-20250929",
    "supported_modes": ["supervised", "autonomous", "aggressive"],
    "alignment_threshold": 0.85
  }
}
```

### 3. GET /state
**Returns:** Current service state and metrics
```json
{
  "uptime_seconds": 86400,
  "requests_total": 200,
  "errors_last_hour": 0,
  "last_restart": "2025-11-16T00:00:00Z",
  "decisions_today": 45,
  "auto_approved": 40,
  "requires_approval": 3,
  "blocked": 2,
  "current_mode": "autonomous"
}
```

### 4. GET /dependencies
**Returns:** Service dependency status
```json
{
  "required": [
    {"name": "registry", "status": "available", "url": "http://localhost:8000"}
  ],
  "optional": [
    {"name": "intent-queue", "status": "available", "url": "http://localhost:8212"}
  ],
  "missing": []
}
```

### 5. POST /message
**Returns:** Message acknowledgment
```json
{
  "trace_id": "uuid",
  "source": "intent-queue",
  "target": "governance",
  "message_type": "command",
  "payload": {
    "action": "check_alignment",
    "intent_id": "uuid"
  },
  "timestamp": "2025-11-16T00:00:00Z"
}
```

---

## Service Endpoints

### POST /governance/check-alignment
Check if intent aligns with blueprint
```json
// Request
{
  "intent": {
    "service_name": "analytics-engine",
    "purpose": "Real-time user behavior analytics",
    "key_features": ["event streaming", "dashboards"],
    "target_tier": 2
  },
  "blueprint_context": "Focus on data-driven decision making and revenue optimization"
}

// Response
{
  "aligned": true,
  "alignment_score": 0.92,
  "reasoning": "This service directly supports data-driven decision making, a core blueprint goal. Real-time analytics enables faster iteration and revenue optimization. Highly aligned with strategic objectives.",
  "decision": "auto_approve",
  "policy_applied": "auto_approve_tier2_aligned",
  "risk_level": "low",
  "risk_factors": [],
  "recommendations": [
    "Ensure analytics data feeds into revenue dashboard",
    "Consider privacy/compliance requirements for user data"
  ],
  "timestamp": "2025-11-16T01:00:00Z"
}
```

### POST /governance/decide
Make governance decision for intent
```json
// Request
{
  "intent_id": "uuid",
  "intent": {...},
  "check_alignment": true,
  "apply_policies": true
}

// Response
{
  "intent_id": "uuid",
  "decision": "auto_approve",
  "reasoning": "Blueprint aligned (0.92) + TIER 2 + low risk = auto approve per policy 'auto_approve_tier2_aligned'",
  "alignment_score": 0.92,
  "risk_level": "low",
  "policy_matched": "auto_approve_tier2_aligned",
  "next_action": "forward_to_spec_assembly",
  "timestamp": "2025-11-16T01:00:00Z"
}
```

### GET /governance/mode
Get current governance mode
```json
{
  "mode": "autonomous",
  "active_policies": [
    "auto_approve_tier2_aligned",
    "auto_approve_tier1_aligned",
    "require_approval_tier0",
    "block_misaligned"
  ],
  "user_present": false,
  "active_hours": "08:00-18:00 PST",
  "autonomous_hours": "18:00-08:00 PST",
  "current_time": "22:00 PST",
  "current_mode_reason": "autonomous_hours"
}
```

### POST /governance/mode
Set governance mode
```json
// Request
{
  "mode": "autonomous",
  "active_policies": [
    "auto_approve_tier2_aligned",
    "auto_approve_tier1_aligned_while_away"
  ],
  "schedule": {
    "supervised_hours": "08:00-18:00 PST",
    "autonomous_hours": "18:00-08:00 PST"
  }
}

// Response
{
  "mode": "autonomous",
  "previous_mode": "supervised",
  "active_policies": 4,
  "auto_approve_enabled": true,
  "schedule_enabled": true,
  "updated_at": "2025-11-16T18:00:00Z"
}
```

### GET /governance/policies
List all governance policies
```json
{
  "policies": [
    {
      "policy_id": "auto_approve_tier2_aligned",
      "name": "Auto-approve aligned TIER 2+ services",
      "rule": "alignment_score >= 0.85 AND tier >= 2 AND risk_level == 'low'",
      "action": "auto_approve",
      "active": true,
      "priority": 1
    },
    {
      "policy_id": "require_approval_tier0",
      "name": "Require approval for TIER 0",
      "rule": "tier == 0",
      "action": "requires_approval",
      "active": true,
      "priority": 10
    },
    {
      "policy_id": "auto_approve_while_away",
      "name": "Auto-approve TIER 1 while user away",
      "rule": "user_present == false AND tier == 1 AND alignment_score >= 0.90",
      "action": "auto_approve",
      "active": true,
      "priority": 5
    },
    {
      "policy_id": "block_misaligned",
      "name": "Block misaligned intents",
      "rule": "alignment_score < 0.70",
      "action": "blocked",
      "active": true,
      "priority": 100
    }
  ],
  "total": 4,
  "active": 4
}
```

### POST /governance/policies
Create new governance policy
```json
// Request
{
  "name": "Emergency auto-approve",
  "rule": "priority == 'critical' AND alignment_score >= 0.80",
  "action": "auto_approve",
  "priority": 2
}

// Response
{
  "policy_id": "emergency_auto_approve",
  "created_at": "2025-11-16T01:00:00Z",
  "active": true
}
```

### GET /governance/decisions
List recent decisions
```json
// Query: ?decision=auto_approve&limit=20
{
  "decisions": [
    {
      "decision_id": "uuid",
      "intent_id": "uuid",
      "service_name": "analytics-engine",
      "decision": "auto_approve",
      "alignment_score": 0.92,
      "risk_level": "low",
      "policy_applied": "auto_approve_tier2_aligned",
      "decided_at": "2025-11-16T01:00:00Z"
    }
  ],
  "total_today": 45,
  "auto_approved_today": 40,
  "requires_approval_today": 3,
  "blocked_today": 2
}
```

### GET /governance/audit
Get audit trail
```json
// Query: ?intent_id=uuid
{
  "audit_trail": [
    {
      "timestamp": "2025-11-16T01:00:00Z",
      "action": "alignment_check_requested",
      "intent_id": "uuid",
      "details": {}
    },
    {
      "timestamp": "2025-11-16T01:00:02Z",
      "action": "claude_api_called",
      "intent_id": "uuid",
      "details": {"model": "claude-sonnet-4-5", "tokens": 1500}
    },
    {
      "timestamp": "2025-11-16T01:00:05Z",
      "action": "alignment_score_computed",
      "intent_id": "uuid",
      "details": {"score": 0.92}
    },
    {
      "timestamp": "2025-11-16T01:00:06Z",
      "action": "policy_evaluation",
      "intent_id": "uuid",
      "details": {"matched_policy": "auto_approve_tier2_aligned"}
    },
    {
      "timestamp": "2025-11-16T01:00:07Z",
      "action": "decision_made",
      "intent_id": "uuid",
      "details": {"decision": "auto_approve"}
    }
  ]
}
```

### POST /governance/override
Human override of governance decision
```json
// Request
{
  "intent_id": "uuid",
  "override_decision": "requires_approval",
  "reason": "Want to review this one manually despite alignment",
  "overridden_by": "user"
}

// Response
{
  "intent_id": "uuid",
  "original_decision": "auto_approve",
  "new_decision": "requires_approval",
  "overridden_by": "user",
  "overridden_at": "2025-11-16T01:00:00Z"
}
```

---

## Architecture


### Tech Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite (local), PostgreSQL (production)
- **API:** RESTful + WebSocket
- **Authentication:** JWT tokens
- **Deployment:** Docker + systemd

### Technology Stack
- **Framework:** FastAPI (Python 3.11+)
- **AI:** Claude API (Anthropic) for alignment checking
- **Database:** SQLite (local), PostgreSQL (production)
- **Policy Engine:** Python rule evaluation
- **Cache:** In-memory for policies

### Blueprint Alignment Process

```
Intent received
     ↓
Load system blueprint
     ↓
Construct alignment prompt:
  "Blueprint: {blueprint_goals}
   Intent: {intent_details}
   
   Question: Does this intent align with the blueprint?
   Consider: strategic goals, architecture principles, resource constraints
   
   Provide:
   1. Alignment score (0-1)
   2. Reasoning
   3. Risk factors
   4. Recommendations"
     ↓
Call Claude API
     ↓
Parse response
     ↓
Extract alignment_score, reasoning, risks
     ↓
Apply policy rules
     ↓
Make decision: auto_approve / requires_approval / blocked
```

### Policy Evaluation Engine

```python
def evaluate_policies(intent, alignment_score, risk_level):
    # Sort policies by priority (higher priority = evaluated first)
    sorted_policies = sort_by_priority(active_policies)
    
    for policy in sorted_policies:
        context = {
            "alignment_score": alignment_score,
            "tier": intent.target_tier,
            "risk_level": risk_level,
            "user_present": check_user_presence(),
            "priority": intent.priority
        }
        
        if eval_rule(policy.rule, context):
            return policy.action  # auto_approve, requires_approval, blocked
    
    # Default: requires_approval
    return "requires_approval"
```

---

## Data Models

```python
class GovernanceDecision(BaseModel):
    decision_id: str = Field(default_factory=uuid4)
    intent_id: str
    service_name: str
    
    # Alignment
    alignment_score: float  # 0-1
    aligned: bool  # True if score >= threshold (0.85)
    alignment_reasoning: str
    
    # Risk
    risk_level: str  # low, medium, high
    risk_factors: List[str]
    
    # Decision
    decision: str  # auto_approve, requires_approval, blocked
    policy_matched: str
    decision_reasoning: str
    
    # Recommendations
    recommendations: List[str]
    
    # Override
    overridden: bool = False
    override_decision: Optional[str] = None
    override_reason: Optional[str] = None
    overridden_by: Optional[str] = None
    overridden_at: Optional[datetime] = None
    
    # Metadata
    decided_at: datetime = Field(default_factory=datetime.now)
    claude_api_cost: float = 0.0
    processing_time_ms: int = 0

class GovernancePolicy(BaseModel):
    policy_id: str
    name: str
    description: str
    rule: str  # Python expression evaluated with context
    action: str  # auto_approve, requires_approval, blocked
    priority: int  # Higher priority evaluated first
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class GovernanceMode(BaseModel):
    mode: str  # supervised, autonomous, aggressive
    active_policies: List[str]
    schedule: Optional[dict] = None
    user_present: bool = False
    updated_at: datetime = Field(default_factory=datetime.now)
```

---


## File Structure

```
governance/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic models
│   ├── config.py         # Configuration
│   ├── endpoints/
│   │   ├── udc.py       # UDC endpoints
│   │   └── service.py   # Business endpoints
│   └── utils/
│       ├── registry.py  # Registry integration
│       └── logger.py    # Logging utilities
├── tests/
│   ├── test_main.py
│   ├── test_udc.py
│   └── test_integration.py
├── SPEC.md
├── README.md
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Dependencies

### Required Services
- **registry** (8000) - Service discovery

### Optional Services
- **intent-queue** (8212) - Intent lifecycle tracking

### External APIs
- **Anthropic Claude API** - Blueprint alignment checking

---

## Deployment

```bash
# Local
cd /Users/jamessunheart/Development/SERVICES/governance
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic sqlalchemy httpx anthropic
echo "ANTHROPIC_API_KEY=your-key" > .env
uvicorn app.main:app --host 0.0.0.0 --port 8213

# Production
docker build -t fpai-governance .
docker run -d --name governance \
  -p 8213:8213 \
  -v /opt/fpai/data:/app/data \
  --env-file .env \
  fpai-governance
```

---

## Success Criteria

- [ ] Check blueprint alignment using Claude API
- [ ] Compute alignment scores (0-1 scale)
- [ ] Evaluate governance policies correctly
- [ ] Make auto-approval decisions
- [ ] Track all decisions in audit trail
- [ ] Support governance modes (supervised/autonomous/aggressive)
- [ ] Allow human overrides
- [ ] API response time < 3 seconds (Claude API call)
- [ ] 95%+ decision accuracy
- [ ] Complete audit trail for compliance
- [ ] 99.9% uptime

---

## Performance Targets

- **Alignment Check:** < 3 seconds (Claude API call)
- **Policy Evaluation:** < 50ms
- **Decision Making:** < 100ms (after alignment check)
- **API Response:** < 3.5 seconds total
- **Concurrent Requests:** 20+ simultaneous
- **Claude API Cost:** < $0.02 per alignment check
- **Uptime:** 99.9%

---

## Integration Examples

### Check Alignment
```bash
curl -X POST http://localhost:8213/governance/check-alignment \
  -H "Content-Type: application/json" \
  -d '{
    "intent": {
      "service_name": "analytics-engine",
      "purpose": "Real-time user analytics",
      "target_tier": 2
    },
    "blueprint_context": "Focus on data-driven decisions"
  }'
```

### Make Decision
```bash
curl -X POST http://localhost:8213/governance/decide \
  -H "Content-Type: application/json" \
  -d '{
    "intent_id": "uuid",
    "intent": {...}
  }'
```

### Set Autonomous Mode
```bash
curl -X POST http://localhost:8213/governance/mode \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "autonomous",
    "schedule": {
      "supervised_hours": "08:00-18:00",
      "autonomous_hours": "18:00-08:00"
    }
  }'
```

---

## Governance Modes Explained

### Supervised Mode
**When:** You're present and want to review everything
**Behavior:**
- TIER 0: Requires approval
- TIER 1: Requires approval
- TIER 2+: Auto-approve if aligned (score >= 0.90)
**Use Case:** Active development, learning the system

### Autonomous Mode
**When:** You're away, system can build itself
**Behavior:**
- TIER 0: Requires approval (infrastructure is critical)
- TIER 1: Auto-approve if aligned (score >= 0.90)
- TIER 2+: Auto-approve if aligned (score >= 0.85)
**Use Case:** Overnight, weekends, vacation

### Aggressive Mode
**When:** Full trust, maximum autonomy
**Behavior:**
- TIER 0: Auto-approve if aligned (score >= 0.95)
- TIER 1: Auto-approve if aligned (score >= 0.90)
- TIER 2+: Auto-approve if aligned (score >= 0.80)
**Use Case:** Mature system, high confidence in blueprint

---

## Error Handling

### Claude API Failure
```json
{
  "error": "claude_api_unavailable",
  "message": "Cannot check alignment, Claude API not responding",
  "fallback_decision": "requires_approval",
  "retry_recommended": true
}
```

### Low Alignment Score
```json
{
  "decision": "blocked",
  "alignment_score": 0.45,
  "reasoning": "Intent does not align with blueprint goals. Appears to contradict revenue optimization focus.",
  "recommendation": "Revise intent to better align with strategic goals"
}
```

---

## Future Enhancements

- [ ] ML-based alignment prediction (learn from past decisions)
- [ ] Multi-blueprint support (different projects)
- [ ] Confidence intervals for alignment scores
- [ ] A/B testing of policy rules
- [ ] Automated policy suggestion
- [ ] Visual policy builder
- [ ] Slack/email notifications for decisions
- [ ] Integration with project management tools

---

**The governance brain that enables autonomous self-building while maintaining strategic alignment!**
