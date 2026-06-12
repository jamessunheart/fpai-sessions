"""
WhiteRock Blessings Engine - CORA Endpoints
CORA vitality credit management.
v2.2 - With Redis caching

CORA is NOT monetary value - it represents community vitality and standing.
CORA is NON-TRANSFERABLE by design.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Member, MembershipTier
from app.schemas import (
    CoraBalanceResponse, CoraGrant, CoraGrantResponse, 
    CoraTierResponse, CoraTransactionType
)
from app.auth import get_current_member, require_admin
from app.services.cora_service import CoraService
from app.services.cache_service import get_cache, CacheService
from app.config import settings

router = APIRouter(prefix="/cora", tags=["CORA"])


@router.get("/balance", response_model=CoraBalanceResponse)
async def get_cora_balance(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current member's CORA balance and status.
    """
    cora_service = CoraService(db)
    
    # Calculate months since engagement
    months_since = (datetime.utcnow() - member.last_engagement_date).days // 30
    
    # Check if decay warning should be shown
    decay_warning = (
        months_since >= (settings.CORA_DECAY_THRESHOLD_MONTHS - 1) and 
        member.cora_balance > 0
    )
    
    # Get next tier info
    result = await db.execute(
        select(MembershipTier).where(
            MembershipTier.cora_threshold > member.cora_balance
        ).order_by(MembershipTier.cora_threshold.asc()).limit(1)
    )
    next_tier = result.scalar_one_or_none()
    
    # Get transaction history
    history = await cora_service.get_transaction_history(member.id, limit=20)
    
    return CoraBalanceResponse(
        balance=member.cora_balance,
        cap=member.cora_cap,
        tier=member.membership_tier,
        next_tier_threshold=next_tier.cora_threshold if next_tier else None,
        last_engagement_date=member.last_engagement_date,
        months_since_engagement=months_since,
        decay_warning=decay_warning,
        transaction_history=history
    )


@router.get("/tiers", response_model=list[CoraTierResponse])
async def get_cora_tiers(
    response: Response,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """
    Get all CORA tier definitions.
    Public endpoint. Cached for 1 hour.
    """
    # Try cache first
    cached = await cache.get_tiers()
    if cached:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = f"max-age={settings.CACHE_TTL_TIERS}"
        return [CoraTierResponse(**t) for t in cached]
    
    # Cache miss - fetch from DB
    result = await db.execute(
        select(MembershipTier).order_by(MembershipTier.cora_threshold.asc())
    )
    tiers = result.scalars().all()
    
    tier_list = [
        CoraTierResponse(
            name=tier.name,
            threshold=tier.cora_threshold,
            cap=tier.cora_cap,
            privileges=tier.access_privileges or {}
        )
        for tier in tiers
    ]
    
    # Cache the result
    await cache.set_tiers([t.model_dump() for t in tier_list])
    
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = f"max-age={settings.CACHE_TTL_TIERS}"
    
    return tier_list


@router.post("/grant", response_model=CoraGrantResponse)
async def grant_cora(
    grant: CoraGrant,
    admin: Member = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Grant CORA credits to a member.
    Admin only.
    """
    # Verify target member exists
    result = await db.execute(
        select(Member).where(Member.id == grant.member_id, Member.is_active == True)
    )
    target_member = result.scalar_one_or_none()
    
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Grant CORA
    cora_service = CoraService(db)
    transaction_id, new_balance = await cora_service.grant_cora(
        member_id=grant.member_id,
        amount=grant.amount,
        transaction_type=grant.transaction_type.value,
        description=grant.description,
        granted_by=admin.id
    )
    
    if transaction_id == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Member at CORA cap ({target_member.cora_cap}). No credits granted."
        )
    
    return CoraGrantResponse(
        transaction_id=transaction_id,
        new_balance=new_balance
    )


@router.get("/decay-preview")
async def get_decay_preview(
    admin: Member = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get preview of members approaching CORA decay.
    Admin only.
    """
    cora_service = CoraService(db)
    members_approaching = await cora_service.get_members_approaching_decay()
    
    return {
        "members_approaching_decay": members_approaching,
        "decay_rate": settings.CORA_DECAY_RATE,
        "decay_threshold_months": settings.CORA_DECAY_THRESHOLD_MONTHS,
        "warning_days": settings.CORA_DECAY_WARNING_DAYS
    }


@router.get("/circulation")
async def get_cora_circulation(
    admin: Member = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get total CORA in circulation.
    Admin only.
    """
    cora_service = CoraService(db)
    
    total = await cora_service.get_total_circulation()
    average = await cora_service.get_average_member_cora()
    
    return {
        "total_circulation": total,
        "average_per_member": round(average, 2),
        "timestamp": datetime.utcnow().isoformat()
    }

