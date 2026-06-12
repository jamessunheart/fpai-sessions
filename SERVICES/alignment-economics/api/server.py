#!/usr/bin/env python3
"""
ALIGNMENT ECONOMICS - API SERVER
==================================

REST API for the Bank of Blessings ledger system.
"""

import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models.core import (
    Position, PositionType,
    Debt, DebtClassification,
    Flow, FlowPurpose,
    Institution, InstitutionType
)
from ledger.storage import (
    PositionStore, DebtStore, FlowStore,
    calculate_health, init_db
)
from rules.engine import (
    RoutingEngine, ForgivenessEngine,
    generate_daily_checklist
)


# ============================================================================
# APP SETUP
# ============================================================================

app = FastAPI(
    title="Alignment Economics API",
    description="Bank of Blessings - Value optimized for circulation, not accumulation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST MODELS
# ============================================================================

class CreatePositionRequest(BaseModel):
    name: str
    type: str  # equity, debt, cash, stake, receivable
    value: str  # Decimal as string
    source: str = ""
    notes: str = ""
    tags: List[str] = []


class CreateDebtRequest(BaseModel):
    name: str
    classification: str  # productive, transitional, extractive
    principal: str  # Decimal as string
    interest_rate: str = "0"
    lender: str
    notes: str = ""


class CreateFlowRequest(BaseModel):
    from_position: str
    to_position: str
    amount: str  # Decimal as string
    purpose: str  # relief, productive, trust, institutional, reserve, return
    description: str = ""


class UpdateParticipationRequest(BaseModel):
    participation_score: float


class AddYieldRequest(BaseModel):
    amount: str  # Decimal as string


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@app.get("/")
async def root():
    return {
        "service": "alignment-economics",
        "status": "running",
        "version": "1.0.0",
        "description": "Bank of Blessings - Circulation over accumulation"
    }


@app.get("/health")
async def health():
    health = calculate_health()
    return health.to_dict()


@app.get("/checklist")
async def daily_checklist():
    """Get the daily circulation checklist."""
    return generate_daily_checklist()


# ============================================================================
# POSITIONS
# ============================================================================

@app.post("/positions")
async def create_position(req: CreatePositionRequest):
    """Create a new capital position."""
    try:
        position_type = PositionType(req.type)
    except ValueError:
        raise HTTPException(400, f"Invalid position type: {req.type}")
    
    position = Position(
        name=req.name,
        type=position_type,
        value=Decimal(req.value),
        source=req.source,
        notes=req.notes,
        tags=req.tags
    )
    
    created = PositionStore.create(position)
    return created.to_dict()


@app.get("/positions")
async def list_positions(type: Optional[str] = None, idle_only: bool = False):
    """List all positions."""
    if idle_only:
        positions = PositionStore.get_idle()
    elif type:
        try:
            position_type = PositionType(type)
            positions = PositionStore.get_by_type(position_type)
        except ValueError:
            raise HTTPException(400, f"Invalid position type: {type}")
    else:
        positions = PositionStore.list_all()
    
    return [p.to_dict() for p in positions]


@app.get("/positions/{position_id}")
async def get_position(position_id: str):
    """Get a specific position."""
    position = PositionStore.get(position_id)
    if not position:
        raise HTTPException(404, f"Position {position_id} not found")
    return position.to_dict()


# ============================================================================
# DEBTS
# ============================================================================

@app.post("/debts")
async def create_debt(req: CreateDebtRequest):
    """Create a new debt."""
    try:
        classification = DebtClassification(req.classification)
    except ValueError:
        raise HTTPException(400, f"Invalid classification: {req.classification}")
    
    debt = Debt(
        name=req.name,
        classification=classification,
        principal=Decimal(req.principal),
        interest_rate=Decimal(req.interest_rate),
        lender=req.lender,
        notes=req.notes
    )
    
    created = DebtStore.create(debt)
    return created.to_dict()


@app.get("/debts")
async def list_debts(active_only: bool = True):
    """List all debts."""
    if active_only:
        debts = DebtStore.list_active()
    else:
        # TODO: Add list_all method
        debts = DebtStore.list_active()
    
    return [d.to_dict() for d in debts]


@app.get("/debts/{debt_id}")
async def get_debt(debt_id: str):
    """Get a specific debt."""
    debt = DebtStore.get(debt_id)
    if not debt:
        raise HTTPException(404, f"Debt {debt_id} not found")
    return debt.to_dict()


@app.patch("/debts/{debt_id}/participation")
async def update_participation(debt_id: str, req: UpdateParticipationRequest):
    """Update participation score for a debt."""
    debt = DebtStore.get(debt_id)
    if not debt:
        raise HTTPException(404, f"Debt {debt_id} not found")
    
    debt.participation_score = min(1.0, max(0.0, req.participation_score))
    updated = DebtStore.update(debt)
    return updated.to_dict()


@app.post("/debts/{debt_id}/yield")
async def add_yield(debt_id: str, req: AddYieldRequest):
    """Add yield accumulated for a debt."""
    debt = DebtStore.get(debt_id)
    if not debt:
        raise HTTPException(404, f"Debt {debt_id} not found")
    
    debt.yield_accumulated += Decimal(req.amount)
    updated = DebtStore.update(debt)
    return updated.to_dict()


@app.post("/debts/{debt_id}/payment")
async def make_payment(debt_id: str, req: AddYieldRequest):
    """Record a payment on a debt."""
    debt = DebtStore.get(debt_id)
    if not debt:
        raise HTTPException(404, f"Debt {debt_id} not found")
    
    payment = Decimal(req.amount)
    debt.payments_made += payment
    updated = DebtStore.update(debt)
    
    # Record flow
    flow = Flow(
        from_position="cash",
        to_position=debt.lender,
        amount=payment,
        purpose=FlowPurpose.RELIEF,
        description=f"Payment on {debt.name}"
    )
    FlowStore.create(flow)
    
    return updated.to_dict()


# ============================================================================
# FORGIVENESS
# ============================================================================

@app.get("/forgiveness/ready")
async def check_forgiveness():
    """Check which debts are ready for forgiveness."""
    engine = ForgivenessEngine()
    ready = engine.check_all()
    
    return [
        {
            "debt_id": r.debt.id,
            "debt_name": r.debt.name,
            "remaining": str(r.debt.remaining),
            "trigger": r.trigger,
            "reasoning": r.reasoning,
            "requires_approval": r.requires_approval
        }
        for r in ready
    ]


@app.post("/forgiveness/{debt_id}")
async def execute_forgiveness(debt_id: str, approved_by: str = "steward"):
    """Execute forgiveness on a debt."""
    engine = ForgivenessEngine()
    
    try:
        debt = engine.execute_forgiveness(debt_id, approved_by)
        return {
            "success": True,
            "message": f"Debt {debt.name} has been forgiven",
            "debt": debt.to_dict()
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


# ============================================================================
# FLOWS
# ============================================================================

@app.post("/flows")
async def create_flow(req: CreateFlowRequest):
    """Create a new capital flow."""
    try:
        purpose = FlowPurpose(req.purpose)
    except ValueError:
        raise HTTPException(400, f"Invalid purpose: {req.purpose}")
    
    flow = Flow(
        from_position=req.from_position,
        to_position=req.to_position,
        amount=Decimal(req.amount),
        purpose=purpose,
        description=req.description
    )
    
    created = FlowStore.create(flow)
    
    # Update position last_flow_at
    from_pos = PositionStore.get(req.from_position)
    if from_pos:
        from_pos.last_flow_at = datetime.now()
        from_pos.value -= Decimal(req.amount)
        PositionStore.update(from_pos)
    
    to_pos = PositionStore.get(req.to_position)
    if to_pos:
        to_pos.last_flow_at = datetime.now()
        to_pos.value += Decimal(req.amount)
        PositionStore.update(to_pos)
    
    return created.to_dict()


@app.get("/flows")
async def list_flows(days: int = 30):
    """List recent flows."""
    flows = FlowStore.list_recent(days)
    return [f.to_dict() for f in flows]


@app.get("/flows/velocity")
async def get_velocity(days: int = 30):
    """Get capital velocity."""
    velocity = FlowStore.get_velocity(days)
    return {
        "velocity": velocity,
        "period_days": days,
        "interpretation": (
            "Healthy" if velocity > 0.5 else
            "Moderate" if velocity > 0.3 else
            "Low - capital may be stagnating"
        )
    }


# ============================================================================
# ROUTING
# ============================================================================

@app.get("/routing/recommendations")
async def get_routing_recommendations():
    """Get recommendations for routing idle capital."""
    engine = RoutingEngine()
    recs = engine.get_recommendations()
    
    return [
        {
            "priority": r.priority,
            "from_position": r.from_position.name,
            "to_target": r.to_target,
            "amount": str(r.amount),
            "purpose": r.purpose.value,
            "urgency": r.urgency,
            "reasoning": r.reasoning,
            "requires_approval": r.requires_approval
        }
        for r in recs
    ]


@app.get("/routing/health")
async def check_routing_health():
    """Check if routing follows allocation rules."""
    engine = RoutingEngine()
    return engine.check_routing_health()


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Initialize database
    init_db()
    
    port = int(os.getenv("AE_PORT", "8760"))
    print(f"Starting Alignment Economics API on port {port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)


