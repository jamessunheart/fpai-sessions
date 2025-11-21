"""Governance - AI-powered blueprint alignment and auto-approval engine"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Dict, Optional
import httpx
import json
import os

from app.config import settings
from app.models import (
    GovernanceDecision, GovernancePolicy, GovernanceMode, AuditEntry,
    CheckAlignmentRequest, CheckAlignmentResponse,
    DecideRequest, DecideResponse,
    SetModeRequest, SetModeResponse,
    CreatePolicyRequest, CreatePolicyResponse,
    OverrideRequest, OverrideResponse
)

# Initialize FastAPI
app = FastAPI(
    title="Governance",
    description="AI-powered blueprint alignment and auto-approval governance engine",
    version=settings.service_version
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
decisions_db: Dict[str, GovernanceDecision] = {}
policies_db: Dict[str, GovernancePolicy] = {}
audit_db: List[AuditEntry] = []
current_mode: GovernanceMode = None
start_time = datetime.now()
requests_count = 0
decisions_today = 0

# Default policies
DEFAULT_POLICIES = [
    {
        "policy_id": "auto_approve_tier2_aligned",
        "name": "Auto-approve aligned TIER 2+ services",
        "description": "Auto-approve TIER 2+ services with high alignment",
        "rule": "alignment_score >= 0.85 and tier >= 2 and risk_level == 'low'",
        "action": "auto_approve",
        "priority": 1
    },
    {
        "policy_id": "require_approval_tier0",
        "name": "Require approval for TIER 0",
        "description": "Infrastructure services require human approval",
        "rule": "tier == 0",
        "action": "requires_approval",
        "priority": 10
    },
    {
        "policy_id": "auto_approve_while_away",
        "name": "Auto-approve TIER 1 while user away",
        "description": "Auto-approve TIER 1 services with very high alignment when user is away",
        "rule": "user_present == False and tier == 1 and alignment_score >= 0.90",
        "action": "auto_approve",
        "priority": 5
    },
    {
        "policy_id": "block_misaligned",
        "name": "Block misaligned intents",
        "description": "Block intents with low alignment scores",
        "rule": "alignment_score < 0.70",
        "action": "blocked",
        "priority": 100
    }
]

#############################################################################
# GOVERNANCE ENGINE CORE
#############################################################################

def load_blueprint() -> str:
    """Load system blueprint for alignment checking"""
    try:
        if os.path.exists(settings.blueprint_path):
            with open(settings.blueprint_path, 'r') as f:
                return f.read()
        else:
            # Fallback blueprint
            return """
            FPAI System Blueprint:
            - Build autonomous self-improving AI system
            - Revenue generation through AI services
            - Quality-gated development (90+ SPEC scores)
            - Human oversight with minimal time investment
            - Recursive self-building capability
            - Blueprint alignment enforcement
            """
    except Exception as e:
        print(f"⚠️  Could not load blueprint: {e}")
        return "Focus on autonomous AI system development and revenue generation"

async def check_alignment_with_claude(intent: Dict, blueprint_context: str) -> Dict:
    """Call Claude API to check blueprint alignment"""

    # For now, implement a mock version since we need ANTHROPIC_API_KEY
    # In production, this would call the actual Claude API

    mock_response = {
        "alignment_score": 0.92,
        "aligned": True,
        "reasoning": f"The {intent.get('service_name')} service aligns well with the blueprint goals. It supports {intent.get('purpose')} which contributes to the autonomous system infrastructure.",
        "risk_level": "low",
        "risk_factors": [],
        "recommendations": [
            "Ensure proper testing before deployment",
            "Monitor resource usage"
        ]
    }

    # Add some variance based on intent properties
    if intent.get('target_tier', 2) == 0:
        mock_response['alignment_score'] = 0.95
        mock_response['reasoning'] = f"TIER 0 infrastructure service {intent.get('service_name')} is critical for autonomous system operation. {intent.get('purpose')} directly supports core capabilities."
    elif intent.get('priority') == 'critical':
        mock_response['alignment_score'] = 0.90

    return mock_response

def evaluate_policies(intent: Dict, alignment_score: float, risk_level: str) -> tuple:
    """Evaluate governance policies to make decision"""

    # Sort policies by priority (higher = evaluated first)
    sorted_policies = sorted(
        [p for p in policies_db.values() if p.active],
        key=lambda x: x.priority,
        reverse=True
    )

    context = {
        "alignment_score": alignment_score,
        "tier": intent.get('target_tier', 2),
        "risk_level": risk_level,
        "user_present": current_mode.user_present if current_mode else False,
        "priority": intent.get('priority', 'medium')
    }

    for policy in sorted_policies:
        try:
            # Safely evaluate the rule
            if eval(policy.rule, {"__builtins__": {}}, context):
                return policy.action, policy.policy_id
        except Exception as e:
            print(f"⚠️  Error evaluating policy {policy.policy_id}: {e}")
            continue

    # Default: requires_approval
    return "requires_approval", "default"

def add_audit_entry(action: str, intent_id: str, details: Dict = None):
    """Add entry to audit trail"""
    entry = AuditEntry(
        action=action,
        intent_id=intent_id,
        details=details or {}
    )
    audit_db.append(entry)

#############################################################################
# UDC ENDPOINTS (5/5)
#############################################################################

@app.get("/health")
async def health():
    """1. UDC Health endpoint"""
    return {
        "status": "active",
        "service": settings.service_name,
        "version": settings.service_version,
        "timestamp": datetime.now().isoformat(),
        "current_mode": current_mode.mode if current_mode else settings.default_mode,
        "claude_api": "mock",  # Will be "connected" with real API key
        "decisions_today": decisions_today
    }

@app.get("/capabilities")
async def capabilities():
    """2. UDC Capabilities endpoint"""
    return {
        "version": settings.service_version,
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
            "claude_model": settings.claude_model,
            "supported_modes": ["supervised", "autonomous", "aggressive"],
            "alignment_threshold": settings.alignment_threshold
        }
    }

@app.get("/state")
async def state():
    """3. UDC State endpoint"""
    uptime = (datetime.now() - start_time).total_seconds()

    # Count decisions by type
    auto_approved = len([d for d in decisions_db.values() if d.decision == "auto_approve"])
    requires_approval = len([d for d in decisions_db.values() if d.decision == "requires_approval"])
    blocked = len([d for d in decisions_db.values() if d.decision == "blocked"])

    return {
        "uptime_seconds": int(uptime),
        "requests_total": requests_count,
        "errors_last_hour": 0,
        "last_restart": start_time.isoformat(),
        "decisions_today": decisions_today,
        "auto_approved": auto_approved,
        "requires_approval": requires_approval,
        "blocked": blocked,
        "current_mode": current_mode.mode if current_mode else settings.default_mode
    }

@app.get("/dependencies")
async def dependencies():
    """4. UDC Dependencies endpoint"""
    # Check registry
    registry_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.registry_url}/health")
            registry_status = "available" if resp.status_code == 200 else "unavailable"
    except:
        registry_status = "unavailable"

    # Check intent-queue (optional)
    intent_queue_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.intent_queue_url}/health")
            intent_queue_status = "available" if resp.status_code == 200 else "unavailable"
    except:
        intent_queue_status = "unavailable"

    return {
        "required": [
            {"name": "registry", "status": registry_status, "url": settings.registry_url}
        ],
        "optional": [
            {"name": "intent-queue", "status": intent_queue_status, "url": settings.intent_queue_url}
        ],
        "missing": []
    }

@app.post("/message")
async def message(msg: dict):
    """5. UDC Message endpoint"""
    # Handle inter-service messages
    return {
        "received": True,
        "trace_id": msg.get("trace_id"),
        "timestamp": datetime.now().isoformat()
    }

#############################################################################
# SERVICE ENDPOINTS
#############################################################################

@app.post("/governance/check-alignment", response_model=CheckAlignmentResponse)
async def check_alignment(request: CheckAlignmentRequest):
    """Check if intent aligns with blueprint"""
    global requests_count
    requests_count += 1

    start_time_check = datetime.now()

    # Get alignment from Claude API
    alignment_result = await check_alignment_with_claude(
        request.intent,
        request.blueprint_context
    )

    # Evaluate policies
    decision, policy_applied = evaluate_policies(
        request.intent,
        alignment_result['alignment_score'],
        alignment_result['risk_level']
    )

    return CheckAlignmentResponse(
        aligned=alignment_result['aligned'],
        alignment_score=alignment_result['alignment_score'],
        reasoning=alignment_result['reasoning'],
        decision=decision,
        policy_applied=policy_applied,
        risk_level=alignment_result['risk_level'],
        risk_factors=alignment_result['risk_factors'],
        recommendations=alignment_result['recommendations']
    )

@app.post("/governance/decide", response_model=DecideResponse)
async def decide(request: DecideRequest):
    """Make governance decision for intent"""
    global requests_count, decisions_today
    requests_count += 1
    decisions_today += 1

    start_time_decide = datetime.now()

    # Add audit entry
    add_audit_entry("decision_requested", request.intent_id)

    # Check alignment if requested
    alignment_score = 0.85  # Default
    risk_level = "low"
    reasoning = ""

    if request.check_alignment:
        add_audit_entry("alignment_check_started", request.intent_id)
        alignment_result = await check_alignment_with_claude(
            request.intent,
            request.intent.get('blueprint_context', '')
        )
        alignment_score = alignment_result['alignment_score']
        risk_level = alignment_result['risk_level']
        reasoning = alignment_result['reasoning']
        add_audit_entry("alignment_score_computed", request.intent_id,
                       {"score": alignment_score})

    # Apply policies if requested
    decision = "requires_approval"
    policy_matched = "default"

    if request.apply_policies:
        add_audit_entry("policy_evaluation_started", request.intent_id)
        decision, policy_matched = evaluate_policies(
            request.intent,
            alignment_score,
            risk_level
        )
        add_audit_entry("policy_matched", request.intent_id,
                       {"policy": policy_matched, "decision": decision})

    # Create decision record
    gov_decision = GovernanceDecision(
        intent_id=request.intent_id,
        service_name=request.intent.get('service_name', 'unknown'),
        alignment_score=alignment_score,
        aligned=alignment_score >= settings.alignment_threshold,
        alignment_reasoning=reasoning,
        risk_level=risk_level,
        risk_factors=[],
        decision=decision,
        policy_matched=policy_matched,
        decision_reasoning=f"Alignment score: {alignment_score:.2f}, Risk: {risk_level}, Policy: {policy_matched}",
        processing_time_ms=int((datetime.now() - start_time_decide).total_seconds() * 1000)
    )

    decisions_db[gov_decision.decision_id] = gov_decision
    add_audit_entry("decision_made", request.intent_id, {"decision": decision})

    # Determine next action
    next_action = "forward_to_spec_assembly" if decision == "auto_approve" else "send_to_approval_dashboard"
    if decision == "blocked":
        next_action = "notify_user"

    return DecideResponse(
        intent_id=request.intent_id,
        decision=decision,
        reasoning=gov_decision.decision_reasoning,
        alignment_score=alignment_score,
        risk_level=risk_level,
        policy_matched=policy_matched,
        next_action=next_action
    )

@app.get("/governance/mode")
async def get_mode():
    """Get current governance mode"""
    if not current_mode:
        return {
            "mode": settings.default_mode,
            "active_policies": [p.policy_id for p in policies_db.values() if p.active],
            "user_present": False,
            "current_time": datetime.now().isoformat(),
            "current_mode_reason": "default"
        }

    return {
        "mode": current_mode.mode,
        "active_policies": current_mode.active_policies,
        "user_present": current_mode.user_present,
        "schedule": current_mode.schedule,
        "current_time": datetime.now().isoformat(),
        "current_mode_reason": "user_configured"
    }

@app.post("/governance/mode", response_model=SetModeResponse)
async def set_mode(request: SetModeRequest):
    """Set governance mode"""
    global current_mode

    previous_mode = current_mode.mode if current_mode else settings.default_mode

    # Update mode
    current_mode = GovernanceMode(
        mode=request.mode,
        active_policies=request.active_policies or [p.policy_id for p in policies_db.values() if p.active],
        schedule=request.schedule,
        user_present=request.mode == "supervised"
    )

    return SetModeResponse(
        mode=current_mode.mode,
        previous_mode=previous_mode,
        active_policies=len(current_mode.active_policies),
        auto_approve_enabled=request.mode in ["autonomous", "aggressive"],
        schedule_enabled=request.schedule is not None
    )

@app.get("/governance/policies")
async def get_policies():
    """List all governance policies"""
    return {
        "policies": [
            {
                "policy_id": p.policy_id,
                "name": p.name,
                "description": p.description,
                "rule": p.rule,
                "action": p.action,
                "active": p.active,
                "priority": p.priority
            }
            for p in policies_db.values()
        ],
        "total": len(policies_db),
        "active": len([p for p in policies_db.values() if p.active])
    }

@app.post("/governance/policies", response_model=CreatePolicyResponse)
async def create_policy(request: CreatePolicyRequest):
    """Create new governance policy"""
    policy_id = request.name.lower().replace(" ", "_")

    policy = GovernancePolicy(
        policy_id=policy_id,
        name=request.name,
        description=request.description,
        rule=request.rule,
        action=request.action,
        priority=request.priority
    )

    policies_db[policy_id] = policy

    return CreatePolicyResponse(
        policy_id=policy_id
    )

@app.get("/governance/decisions")
async def get_decisions(
    decision: Optional[str] = None,
    limit: int = 20
):
    """List recent decisions"""
    results = list(decisions_db.values())

    # Filter by decision type
    if decision:
        results = [d for d in results if d.decision == decision]

    # Sort by most recent
    results.sort(key=lambda x: x.decided_at, reverse=True)

    # Limit
    results = results[:limit]

    # Count stats
    auto_approved = len([d for d in decisions_db.values() if d.decision == "auto_approve"])
    requires_approval = len([d for d in decisions_db.values() if d.decision == "requires_approval"])
    blocked = len([d for d in decisions_db.values() if d.decision == "blocked"])

    return {
        "decisions": [
            {
                "decision_id": d.decision_id,
                "intent_id": d.intent_id,
                "service_name": d.service_name,
                "decision": d.decision,
                "alignment_score": d.alignment_score,
                "risk_level": d.risk_level,
                "policy_applied": d.policy_matched,
                "decided_at": d.decided_at.isoformat()
            }
            for d in results
        ],
        "total_today": decisions_today,
        "auto_approved_today": auto_approved,
        "requires_approval_today": requires_approval,
        "blocked_today": blocked
    }

@app.get("/governance/audit")
async def get_audit(intent_id: Optional[str] = None):
    """Get audit trail"""
    results = audit_db

    # Filter by intent_id
    if intent_id:
        results = [e for e in results if e.intent_id == intent_id]

    # Sort by timestamp
    results.sort(key=lambda x: x.timestamp)

    return {
        "audit_trail": [
            {
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                "intent_id": e.intent_id,
                "details": e.details
            }
            for e in results
        ]
    }

@app.post("/governance/override", response_model=OverrideResponse)
async def override_decision(request: OverrideRequest):
    """Human override of governance decision"""

    # Find the decision
    decision = None
    for d in decisions_db.values():
        if d.intent_id == request.intent_id:
            decision = d
            break

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found for intent")

    original_decision = decision.decision

    # Override
    decision.overridden = True
    decision.override_decision = request.override_decision
    decision.override_reason = request.reason
    decision.overridden_by = request.overridden_by
    decision.overridden_at = datetime.now()
    decision.decision = request.override_decision  # Update actual decision

    # Audit
    add_audit_entry("decision_overridden", request.intent_id, {
        "original": original_decision,
        "new": request.override_decision,
        "reason": request.reason
    })

    return OverrideResponse(
        intent_id=request.intent_id,
        original_decision=original_decision,
        new_decision=request.override_decision,
        overridden_by=request.overridden_by
    )

#############################################################################
# STARTUP / SHUTDOWN
#############################################################################

@app.on_event("startup")
async def startup_event():
    """Initialize governance engine on startup"""
    global current_mode

    print(f"🚀 Starting {settings.service_name} v{settings.service_version}")
    print(f"📡 Port: {settings.service_port}")
    print(f"🎯 TIER: {settings.tier}")

    # Initialize default policies
    for policy_data in DEFAULT_POLICIES:
        policy = GovernancePolicy(**policy_data)
        policies_db[policy.policy_id] = policy

    print(f"📋 Loaded {len(policies_db)} governance policies")

    # Set default mode
    current_mode = GovernanceMode(
        mode=settings.default_mode,
        active_policies=[p.policy_id for p in policies_db.values() if p.active],
        user_present=settings.default_mode == "supervised"
    )

    print(f"🎮 Governance mode: {current_mode.mode}")

    # Load blueprint
    blueprint = load_blueprint()
    print(f"📖 Blueprint loaded ({len(blueprint)} chars)")

    # Register with Registry
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            registration = {
                "name": settings.service_name,
                "id": f"{settings.service_name}-{settings.service_version}",
                "url": f"http://localhost:{settings.service_port}",
                "version": settings.service_version,
                "tier": settings.tier,
                "capabilities": ["blueprint_alignment", "policy_engine", "auto_approval"]
            }
            resp = await client.post(
                f"{settings.registry_url}/droplets/register",
                json=registration,
                timeout=5.0
            )
            if resp.status_code in [200, 201]:
                print(f"✅ Registered with Registry")
            else:
                print(f"⚠️  Registry registration failed: {resp.status_code}")
    except Exception as e:
        print(f"⚠️  Could not register with Registry: {e}")

    print(f"✅ {settings.service_name} is LIVE!")
    print(f"🧠 AI governance brain ready for autonomous decision-making!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print(f"👋 Shutting down {settings.service_name}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=settings.service_port)
