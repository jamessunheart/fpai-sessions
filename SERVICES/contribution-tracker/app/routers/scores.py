"""Score and aggregate endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..db_models import ContributionRecord, TrustBalance, QuarterlyScore
from ..models import MemberScore, AggregateMetrics, Leaderboard, MemberTier
from ..scoring import (
    get_current_quarter, calculate_tier, get_voting_multiplier,
    get_eligible_categories, get_benefit_eligibility, get_next_tier_info
)

router = APIRouter(prefix="/api", tags=["scores"])


@router.get("/contributions/score/{member_id}", response_model=MemberScore)
async def get_member_score(
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current contribution score for a member."""
    
    quarter = get_current_quarter()
    score_id = f"{member_id}_{quarter}"
    
    # Get quarterly score
    result = await db.execute(
        select(QuarterlyScore).where(QuarterlyScore.id == score_id)
    )
    score_record = result.scalar_one_or_none()
    
    # Get trust balance
    result = await db.execute(
        select(TrustBalance).where(TrustBalance.member_id == member_id)
    )
    balance = result.scalar_one_or_none()
    
    quarterly_score = score_record.score if score_record else 0
    is_founder = balance.is_founder if balance else False
    trust_balance = balance.balance if balance else 0
    
    tier = calculate_tier(quarterly_score, is_founder)
    voting_multiplier = get_voting_multiplier(tier, quarterly_score)
    eligible_categories = get_eligible_categories(tier)
    benefit_eligible = get_benefit_eligibility(tier)
    next_tier, points_needed = get_next_tier_info(tier, quarterly_score)
    
    return MemberScore(
        member_id=member_id,
        current_quarter=quarter,
        quarterly_score=quarterly_score,
        tier=tier,
        trust_balance=trust_balance,
        voting_multiplier=voting_multiplier,
        benefit_eligible=benefit_eligible,
        eligible_categories=eligible_categories,
        is_founder=is_founder,
        next_tier=next_tier,
        points_to_next_tier=points_needed
    )


@router.get("/contributions/aggregate", response_model=AggregateMetrics)
async def get_aggregate_metrics(
    period: str = Query("quarter", regex="^(quarter|month|year)$"),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregate contribution metrics (for Trust Index)."""
    
    quarter = get_current_quarter()
    
    # Get all balances
    result = await db.execute(select(TrustBalance))
    balances = result.scalars().all()
    total_members = len(balances)
    
    # Get quarterly scores
    result = await db.execute(
        select(QuarterlyScore).where(QuarterlyScore.quarter == quarter)
    )
    scores = result.scalars().all()
    
    active_contributors = sum(1 for s in scores if s.score >= 100)
    active_ratio = active_contributors / total_members if total_members > 0 else 0
    avg_score = sum(s.score for s in scores) / len(scores) if scores else 0
    
    # Total TRUST issued
    total_trust = sum(b.total_earned for b in balances)
    
    # By type
    by_type = {
        "service": sum(s.service_score or 0 for s in scores),
        "governance": sum(s.governance_score or 0 for s in scores),
        "art": sum(s.art_score or 0 for s in scores),
        "referral": sum(s.referral_score or 0 for s in scores),
        "financial": sum(s.financial_score or 0 for s in scores),
        "community": sum(s.community_score or 0 for s in scores)
    }
    
    return AggregateMetrics(
        period=quarter,
        total_members=total_members,
        active_contributors=active_contributors,
        active_ratio=round(active_ratio, 3),
        avg_quarterly_score=round(avg_score, 1),
        total_trust_issued=total_trust,
        by_type=by_type
    )


@router.get("/contributions/leaderboard", response_model=Leaderboard)
async def get_leaderboard(
    period: str = Query("quarter", regex="^(week|month|quarter|year)$"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get top contributors."""
    
    quarter = get_current_quarter()
    
    # Get top scores for current quarter
    result = await db.execute(
        select(QuarterlyScore)
        .where(QuarterlyScore.quarter == quarter)
        .order_by(QuarterlyScore.score.desc())
        .limit(limit)
    )
    scores = result.scalars().all()
    
    entries = []
    for i, score in enumerate(scores, 1):
        entries.append({
            "rank": i,
            "member_id": score.member_id,
            "score": score.score,
            "tier": score.tier,
            "breakdown": {
                "service": score.service_score or 0,
                "governance": score.governance_score or 0,
                "art": score.art_score or 0,
                "referral": score.referral_score or 0,
                "financial": score.financial_score or 0,
                "community": score.community_score or 0
            }
        })
    
    return Leaderboard(
        period=quarter,
        entries=entries
    )


@router.get("/trust/balance/{member_id}")
async def get_trust_balance(
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get TRUST token balance for a member."""
    
    result = await db.execute(
        select(TrustBalance).where(TrustBalance.member_id == member_id)
    )
    balance = result.scalar_one_or_none()
    
    if not balance:
        return {
            "member_id": member_id,
            "balance": 0,
            "total_earned": 0,
            "is_founder": False
        }
    
    return {
        "member_id": member_id,
        "balance": balance.balance,
        "total_earned": balance.total_earned,
        "is_founder": balance.is_founder,
        "joined_at": balance.joined_at.isoformat() if balance.joined_at else None
    }










