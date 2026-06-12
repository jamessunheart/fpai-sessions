"""Needs request endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import httpx
import logging

from ..database import get_db
from ..db_models import NeedsRequestRecord, AllocationRecord, MonthlyBudget
from ..models import (
    NeedsRequestCreate, NeedsRequest, NeedsRequestResponse,
    RequestStatus, EligibilityResponse, CommittedNeedsResponse
)
from ..eligibility import check_eligibility, get_eligible_categories
from ..budget import get_current_budget, check_budget_available
from ..config import settings

router = APIRouter(prefix="/api/needs", tags=["needs"])
logger = logging.getLogger(__name__)


async def _transfer_to_escrow(
    amount_uc: float,
    request_id: str,
    member_id: str,
    category: str
) -> dict:
    """Move funds from Commons Reserve to escrow bucket in Credits Gateway."""
    if not settings.CREDITS_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Needs Allocation is missing NEEDS_CREDITS_API_KEY (Credits Gateway transfer disabled)"
        )

    payload = {
        "from_account": settings.COMMONS_RESERVE_ACCOUNT,
        "to_account": settings.ESCROW_ACCOUNT,
        "amount": float(amount_uc),
        "credit_type": settings.CREDITS_TRANSFER_CREDIT_TYPE,
        "reason": f"Needs escrow: {request_id} ({category})",
        "metadata": {
            "request_id": request_id,
            "member_id": member_id,
            "category": category,
            "service": settings.SERVICE_NAME,
            "timestamp": datetime.utcnow().isoformat()
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.CREDITS_GATEWAY_URL}/api/transfer",
                headers={"X-API-Key": settings.CREDITS_API_KEY},
                json=payload
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Credits Gateway transfer failed ({resp.status_code}): {resp.text}"
                )
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Credits Gateway transfer error: {e}")
        raise HTTPException(status_code=502, detail="Credits Gateway transfer error")


@router.post("/request", response_model=NeedsRequestResponse)
async def create_request(
    request: NeedsRequestCreate,
    db: AsyncSession = Depends(get_db)
):
    """Submit a needs-support request."""
    
    # Check eligibility
    eligibility, denial_reason = await check_eligibility(
        request.member_id,
        request.category,
        request.amount_uc
    )
    
    # Create request record
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    
    record = NeedsRequestRecord(
        id=request_id,
        member_id=request.member_id,
        category=request.category.value,
        subcategory=request.subcategory,
        description=request.description,
        amount_uc=request.amount_uc,
        urgency=request.urgency.value,
        status="pending" if eligibility.eligible else "denied",
        trust_held=eligibility.trust_held,
        contribution_score=eligibility.contribution_score,
        denial_reason=denial_reason if not eligibility.eligible else None,
        supporting_docs=request.supporting_docs,
        metadata=request.metadata
    )
    
    db.add(record)
    await db.commit()
    
    # If eligible, check budget and potentially auto-approve
    if eligibility.eligible:
        budget = await get_current_budget(db=db)
        if check_budget_available(request.category.value, request.amount_uc, budget):
            # Auto-approve for now (in production, may require human review)
            record.status = "approved"
            record.approved_amount = request.amount_uc
            await db.commit()
    
    return NeedsRequestResponse(
        request_id=request_id,
        status=RequestStatus(record.status),
        estimated_decision=datetime.utcnow() + timedelta(hours=24) if record.status == "pending" else None,
        eligibility=eligibility
    )


@router.get("/request/{request_id}", response_model=NeedsRequest)
async def get_request(
    request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific needs request."""
    
    result = await db.execute(
        select(NeedsRequestRecord).where(NeedsRequestRecord.id == request_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    
    from ..models import EligibilityCheck, NeedsCategory, Urgency
    
    return NeedsRequest(
        id=record.id,
        member_id=record.member_id,
        category=NeedsCategory(record.category),
        subcategory=record.subcategory,
        description=record.description,
        amount_uc=record.amount_uc,
        urgency=Urgency(record.urgency),
        status=RequestStatus(record.status),
        eligibility=EligibilityCheck(
            trust_held=record.trust_held,
            contribution_score=record.contribution_score,
            eligible=record.status != "denied",
            tier="active"  # TODO: Store tier
        ),
        approved_amount=record.approved_amount,
        denial_reason=record.denial_reason,
        fulfilled_at=record.fulfilled_at,
        created_at=record.created_at,
        updated_at=record.updated_at
    )


@router.post("/fulfill/{request_id}")
async def fulfill_request(
    request_id: str,
    fulfillment_type: str = "uc_credit",
    db: AsyncSession = Depends(get_db)
):
    """Mark a request as fulfilled."""
    
    result = await db.execute(
        select(NeedsRequestRecord).where(NeedsRequestRecord.id == request_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if record.status != "approved":
        raise HTTPException(status_code=400, detail=f"Cannot fulfill request with status {record.status}")
    
    amount_uc = float(record.approved_amount or record.amount_uc or 0)
    if amount_uc <= 0:
        raise HTTPException(status_code=400, detail="Invalid approved amount")

    # Check budget before fulfilling
    budget = await get_current_budget(db=db)
    if not check_budget_available(record.category, amount_uc, budget):
        raise HTTPException(status_code=400, detail="Insufficient category budget available")

    # Move funds to escrow (ledger-level safety)
    escrow_result = await _transfer_to_escrow(
        amount_uc=amount_uc,
        request_id=request_id,
        member_id=record.member_id,
        category=record.category
    )

    # Update status
    record.status = "fulfilled"
    record.fulfilled_at = datetime.utcnow()
    
    # Create allocation record
    allocation = AllocationRecord(
        id=f"alloc_{uuid.uuid4().hex[:12]}",
        request_id=request_id,
        member_id=record.member_id,
        category=record.category,
        amount_uc=amount_uc,
        fulfillment_type=fulfillment_type,
        fulfillment_details={
            "method": fulfillment_type,
            "credits_gateway": {
                "from": settings.COMMONS_RESERVE_ACCOUNT,
                "to": settings.ESCROW_ACCOUNT,
                "credit_type": settings.CREDITS_TRANSFER_CREDIT_TYPE,
                "result": escrow_result
            }
        }
    )
    db.add(allocation)

    # Track usage in MonthlyBudget
    now = datetime.utcnow()
    period = f"{now.year}-{now.month:02d}"
    result = await db.execute(select(MonthlyBudget).where(MonthlyBudget.id == period))
    mb = result.scalar_one_or_none()
    if mb is None:
        mb = MonthlyBudget(
            id=period,
            total_budget=float(budget.monthly_budget_uc),
            survival_used=0.0,
            stability_used=0.0,
            growth_used=0.0,
            contribution_used=0.0,
            infrastructure_used=0.0
        )
        db.add(mb)
    else:
        mb.total_budget = float(budget.monthly_budget_uc)

    field_map = {
        "survival": "survival_used",
        "stability": "stability_used",
        "growth": "growth_used",
        "contribution": "contribution_used",
        "infrastructure": "infrastructure_used"
    }
    used_field = field_map.get(record.category)
    if used_field:
        current_used = getattr(mb, used_field) or 0.0
        setattr(mb, used_field, float(current_used) + float(amount_uc))
    
    await db.commit()
    
    return {
        "request_id": request_id,
        "status": "fulfilled",
        "amount_uc": amount_uc,
        "fulfillment_type": fulfillment_type
    }


@router.get("/eligibility/{member_id}", response_model=EligibilityResponse)
async def check_member_eligibility(
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Check member's eligibility for needs-support."""
    
    # Get member data
    from ..eligibility import check_eligibility
    from ..models import NeedsCategory
    
    eligibility, _ = await check_eligibility(member_id, NeedsCategory.SURVIVAL, 100)
    
    # Get recent allocations
    result = await db.execute(
        select(AllocationRecord)
        .where(AllocationRecord.member_id == member_id)
        .where(AllocationRecord.created_at >= datetime.utcnow() - timedelta(days=30))
    )
    recent = result.scalars().all()
    
    recent_total = sum(a.amount_uc for a in recent)
    
    # Calculate remaining fairness limit
    budget = await get_current_budget(db=db)
    max_allocation = budget.monthly_budget_uc * settings.MAX_SINGLE_ALLOCATION_PERCENT
    remaining = max(0, max_allocation - recent_total)
    
    eligible_cats = get_eligible_categories(eligibility.tier, eligibility.trust_held)
    
    return EligibilityResponse(
        member_id=member_id,
        eligible=eligibility.eligible,
        trust_held=eligibility.trust_held,
        contribution_score=eligibility.contribution_score,
        contribution_tier=eligibility.tier,
        recent_allocations=len(recent),
        recent_total_uc=recent_total,
        fairness_limit_remaining=remaining,
        eligible_categories=eligible_cats
    )


@router.get("/committed", response_model=CommittedNeedsResponse)
async def get_committed_needs(
    db: AsyncSession = Depends(get_db)
):
    """Get total committed needs (for Trust Index calculation)."""
    
    # Get pending requests
    result = await db.execute(
        select(NeedsRequestRecord).where(NeedsRequestRecord.status == "pending")
    )
    pending = result.scalars().all()
    pending_total = sum(r.amount_uc for r in pending)
    
    # Get approved but not fulfilled
    result = await db.execute(
        select(NeedsRequestRecord).where(NeedsRequestRecord.status == "approved")
    )
    approved = result.scalars().all()
    approved_total = sum(r.approved_amount or 0 for r in approved)
    
    # Monthly projection (rough estimate)
    budget = await get_current_budget(db=db)
    monthly_projection = budget.monthly_budget_uc
    
    return CommittedNeedsResponse(
        total_committed_uc=approved_total + pending_total * 0.5,  # 50% approval rate estimate
        pending_requests_uc=pending_total,
        approved_pending_fulfillment_uc=approved_total,
        monthly_projection_uc=monthly_projection
    )




