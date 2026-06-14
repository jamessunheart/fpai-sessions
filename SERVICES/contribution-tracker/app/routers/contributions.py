"""Contribution endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
import httpx
import logging

from ..database import get_db
from ..db_models import ContributionRecord, TrustBalance, TrustTransaction, QuarterlyScore
from ..models import (
    ContributionCreate, ContributionVerify, ContributionResponse,
    Contribution, ContributionType, ContributionStatus, MemberContributions
)
from ..scoring import (
    calculate_trust_amount, get_verification_method, is_auto_verified,
    get_current_quarter
)
from ..config import settings

router = APIRouter(prefix="/api/contributions", tags=["contributions"])
logger = logging.getLogger(__name__)


def _trust_issuance_multiplier_from_posture(posture: str) -> float:
    """
    Map Trust Index policy posture → TRUST issuance multiplier.

    This is intentionally simple and conservative:
    - emergency: freeze issuance
    - conservative: slow issuance
    - balanced: normal issuance
    - generous: slight boost
    """
    p = (posture or "").lower().strip()
    if p == "emergency":
        return 0.0
    if p == "conservative":
        return 0.5
    if p == "generous":
        return 1.2
    return 1.0


async def _get_trust_policy_snapshot() -> Dict[str, Any]:
    """Fetch current Trust Index policy snapshot (best-effort)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.TRUST_INDEX_URL}/api/trust-index/policy")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch Trust Index policy: {e}")

    # Safe fallback: balanced defaults (no boost, no freeze)
    return {
        "trust_index": None,
        "posture": "balanced",
        "parameters": {"safety_buffer": 1.5},
        "guardrails": {},
        "source": "fallback"
    }


@router.post("/log", response_model=ContributionResponse)
async def log_contribution(
    contribution: ContributionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Log a new contribution."""
    
    # Calculate TRUST potential
    trust_potential = calculate_trust_amount(
        contribution_type=contribution.type,
        hours=contribution.hours,
        amount=contribution.amount,
        is_founding_period=True  # TODO: Check actual founding status
    )

    # Apply policy guardrails (best-effort)
    policy = await _get_trust_policy_snapshot()
    posture = policy.get("posture") or policy.get("policy_posture") or "balanced"
    trust_index_value = policy.get("trust_index")
    issuance_multiplier = _trust_issuance_multiplier_from_posture(posture)
    trust_issuable = max(0, int(trust_potential * issuance_multiplier))
    
    # Determine verification method
    verification_method = get_verification_method(contribution.type)
    auto_verify = is_auto_verified(contribution.type)
    
    # Set expiration for verification
    expires_at = None
    if not auto_verify:
        expires_at = datetime.utcnow() + timedelta(days=settings.VERIFICATION_TIMEOUT_DAYS)
    
    # Create contribution record
    contribution_id = f"contrib_{uuid.uuid4().hex[:12]}"

    # Preserve user-provided metadata, add policy snapshot (audit-friendly)
    extra_data: Dict[str, Any] = {}
    if contribution.metadata and isinstance(contribution.metadata, dict):
        extra_data.update(contribution.metadata)
    extra_data["policy_snapshot"] = {
        "trust_index": trust_index_value,
        "posture": posture,
        "issuance_multiplier": issuance_multiplier,
        "trust_potential": trust_potential,
        "trust_issuable": trust_issuable,
        "trust_index_url": settings.TRUST_INDEX_URL,
        "fetched_at": datetime.utcnow().isoformat()
    }

    record = ContributionRecord(
        id=contribution_id,
        member_id=contribution.member_id,
        type=contribution.type.value,
        description=contribution.description,
        status="verified" if auto_verify else "pending",
        trust_potential=trust_potential,
        trust_issued=trust_issuable if auto_verify else 0,
        hours=contribution.hours,
        amount=contribution.amount,
        recipient_id=contribution.recipient_id,
        reference_id=contribution.reference_id,
        evidence=contribution.evidence,
        extra_data=extra_data,
        expires_at=expires_at,
        verified_at=datetime.utcnow() if auto_verify else None
    )
    
    db.add(record)
    
    # If auto-verified, issue TRUST immediately
    if auto_verify:
        await _issue_trust(db, contribution.member_id, trust_issuable, contribution_id, contribution.type.value)
    
    await db.commit()
    
    return ContributionResponse(
        contribution_id=contribution_id,
        member_id=contribution.member_id,
        type=contribution.type,
        status=ContributionStatus.VERIFIED if auto_verify else ContributionStatus.PENDING,
        trust_potential=trust_potential,
        verification_method=verification_method,
        verification_deadline=expires_at
    )


@router.post("/verify/{contribution_id}")
async def verify_contribution(
    contribution_id: str,
    verification: ContributionVerify,
    db: AsyncSession = Depends(get_db)
):
    """Verify a contribution."""
    
    # Get contribution
    result = await db.execute(
        select(ContributionRecord).where(ContributionRecord.id == contribution_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Contribution not found")
    
    if record.status != "pending":
        raise HTTPException(status_code=400, detail=f"Contribution already {record.status}")
    
    # Update status
    if verification.verified:
        record.status = "verified"
        # Apply policy guardrails at issuance time (conservative)
        policy_now = await _get_trust_policy_snapshot()
        posture_now = policy_now.get("posture") or policy_now.get("policy_posture") or "balanced"
        multiplier_now = _trust_issuance_multiplier_from_posture(posture_now)

        multiplier_at_log = 1.0
        if record.extra_data and isinstance(record.extra_data, dict):
            snap = record.extra_data.get("policy_snapshot") or {}
            try:
                multiplier_at_log = float(snap.get("issuance_multiplier", 1.0))
            except Exception:
                multiplier_at_log = 1.0

        # Never issue more than what would be allowed now
        effective_multiplier = min(multiplier_at_log, multiplier_now)
        issued = max(0, int((record.trust_potential or 0) * effective_multiplier))
        record.trust_issued = issued
        record.verifier_id = verification.verifier_id
        record.verified_at = datetime.utcnow()
        record.verification_notes = verification.notes

        if isinstance(record.extra_data, dict):
            extra = dict(record.extra_data)
            extra["policy_issue"] = {
                "posture_now": posture_now,
                "multiplier_now": multiplier_now,
                "multiplier_at_log": multiplier_at_log,
                "effective_multiplier": effective_multiplier,
                "trust_issued": issued,
                "fetched_at": datetime.utcnow().isoformat()
            }
            record.extra_data = extra
        
        # Issue TRUST
        await _issue_trust(
            db, record.member_id, record.trust_issued,
            contribution_id, record.type
        )
    else:
        record.status = "denied"
        record.verifier_id = verification.verifier_id
        record.verification_notes = verification.notes
    
    await db.commit()
    
    return {
        "contribution_id": contribution_id,
        "status": record.status,
        "trust_issued": record.trust_issued if verification.verified else 0
    }


@router.get("/member/{member_id}", response_model=MemberContributions)
async def get_member_contributions(
    member_id: str,
    period: str = Query("quarter", regex="^(quarter|year|all)$"),
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get member's contribution history."""
    
    quarter = get_current_quarter()
    
    # Build query
    query = select(ContributionRecord).where(
        ContributionRecord.member_id == member_id
    )
    
    if period == "quarter":
        # Filter to current quarter
        year, q = quarter.split("-Q")
        quarter_start = datetime(int(year), (int(q) - 1) * 3 + 1, 1)
        query = query.where(ContributionRecord.created_at >= quarter_start)
    elif period == "year":
        year_start = datetime(datetime.utcnow().year, 1, 1)
        query = query.where(ContributionRecord.created_at >= year_start)
    
    if type:
        query = query.where(ContributionRecord.type == type)
    
    query = query.order_by(ContributionRecord.created_at.desc())
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    # Calculate totals
    total_score = sum(r.trust_issued for r in records if r.status == "verified")
    
    # Group by type
    by_type = {}
    for r in records:
        if r.status == "verified":
            by_type[r.type] = by_type.get(r.type, 0) + r.trust_issued
    
    # Get tier
    from ..scoring import calculate_tier
    tier = calculate_tier(total_score)
    
    contributions = [
        Contribution(
            id=r.id,
            member_id=r.member_id,
            type=ContributionType(r.type),
            description=r.description,
            status=ContributionStatus(r.status),
            trust_potential=r.trust_potential,
            trust_issued=r.trust_issued,
            hours=r.hours,
            amount=r.amount,
            recipient_id=r.recipient_id,
            reference_id=r.reference_id,
            verifier_id=r.verifier_id,
            verified_at=r.verified_at,
            created_at=r.created_at,
            expires_at=r.expires_at
        )
        for r in records
    ]
    
    return MemberContributions(
        member_id=member_id,
        period=quarter if period == "quarter" else period,
        total_score=total_score,
        tier=tier,
        trust_earned=total_score,
        contributions=contributions,
        by_type=by_type
    )


@router.get("/aggregate")
async def get_aggregate_metrics_redirect(
    period: str = Query("quarter", regex="^(quarter|month|year)$"),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregate contribution metrics (for Trust Index) - routed here to avoid /{id} catch."""
    from .scores import get_aggregate_metrics
    return await get_aggregate_metrics(period, db)


@router.get("/{contribution_id}", response_model=Contribution)
async def get_contribution(
    contribution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific contribution."""
    
    result = await db.execute(
        select(ContributionRecord).where(ContributionRecord.id == contribution_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Contribution not found")
    
    return Contribution(
        id=record.id,
        member_id=record.member_id,
        type=ContributionType(record.type),
        description=record.description,
        status=ContributionStatus(record.status),
        trust_potential=record.trust_potential,
        trust_issued=record.trust_issued,
        hours=record.hours,
        amount=record.amount,
        recipient_id=record.recipient_id,
        reference_id=record.reference_id,
        verifier_id=record.verifier_id,
        verified_at=record.verified_at,
        created_at=record.created_at,
        expires_at=record.expires_at
    )


async def _issue_trust(
    db: AsyncSession,
    member_id: str,
    amount: int,
    contribution_id: str,
    contribution_type: str
):
    """Issue TRUST tokens to member."""

    if amount <= 0:
        return
    
    # Get or create balance
    result = await db.execute(
        select(TrustBalance).where(TrustBalance.member_id == member_id)
    )
    balance = result.scalar_one_or_none()
    
    if not balance:
        balance = TrustBalance(
            member_id=member_id,
            balance=0,
            total_earned=0,
            is_founder=True  # TODO: Check actual founding status
        )
        db.add(balance)
    
    # Update balance
    balance.balance += amount
    balance.total_earned += amount
    
    # Create transaction
    transaction = TrustTransaction(
        id=f"tx_{uuid.uuid4().hex[:12]}",
        member_id=member_id,
        amount=amount,
        type="earn",
        reason=f"contribution_{contribution_type}",
        contribution_id=contribution_id
    )
    db.add(transaction)
    
    # Update quarterly score
    quarter = get_current_quarter()
    score_id = f"{member_id}_{quarter}"
    
    result = await db.execute(
        select(QuarterlyScore).where(QuarterlyScore.id == score_id)
    )
    score = result.scalar_one_or_none()
    
    if not score:
        score = QuarterlyScore(
            id=score_id,
            member_id=member_id,
            quarter=quarter,
            score=0
        )
        db.add(score)
    
    score.score += amount
    
    # Update type-specific score
    type_field = f"{contribution_type}_score"
    if hasattr(score, type_field):
        current = getattr(score, type_field) or 0
        setattr(score, type_field, current + amount)
    
    # Update tier
    from ..scoring import calculate_tier
    score.tier = calculate_tier(score.score, balance.is_founder).value

