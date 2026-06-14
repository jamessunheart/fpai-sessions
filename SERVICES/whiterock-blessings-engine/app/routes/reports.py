"""
WhiteRock Blessings Engine - Reports Endpoints
Admin reporting for community metrics.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Member, Tithe, BlessingRequest, BlessingDisbursement
from app.schemas import CommunityReportResponse, BlessingsReportResponse, CoraHealthResponse
from app.auth import require_admin
from app.services.cora_service import CoraService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/community", response_model=CommunityReportResponse)
async def get_community_report(
    admin: Member = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get community metrics report.
    Admin only.
    """
    # Total members
    result = await db.execute(
        select(func.count(Member.id)).where(Member.is_active == True)
    )
    total_members = result.scalar_one()
    
    # Active members (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    result = await db.execute(
        select(func.count(Member.id)).where(
            Member.is_active == True,
            Member.last_engagement_date >= thirty_days_ago
        )
    )
    active_30d = result.scalar_one()
    
    # Total tithes YTD
    year_start = datetime(datetime.utcnow().year, 1, 1)
    result = await db.execute(
        select(func.sum(Tithe.amount_cents)).where(Tithe.created_at >= year_start)
    )
    tithes_ytd = result.scalar_one() or 0
    
    # Total blessings distributed YTD
    result = await db.execute(
        select(func.sum(BlessingDisbursement.amount_cents)).where(
            BlessingDisbursement.created_at >= year_start
        )
    )
    blessings_ytd = result.scalar_one() or 0
    
    # Blessings by category
    result = await db.execute(
        select(
            BlessingRequest.category,
            func.count(BlessingRequest.id),
            func.sum(BlessingRequest.amount_approved_cents)
        ).where(
            BlessingRequest.status == "closed",
            BlessingRequest.created_at >= year_start
        ).group_by(BlessingRequest.category)
    )
    by_category = {
        row[0]: {"count": row[1], "total_cents": row[2] or 0}
        for row in result
    }
    
    # CORA in circulation
    result = await db.execute(
        select(func.sum(Member.cora_balance)).where(Member.is_active == True)
    )
    cora_circulation = result.scalar_one() or 0
    
    # Average tenure
    result = await db.execute(
        select(func.avg(
            func.extract('epoch', datetime.utcnow() - Member.created_at) / (30 * 24 * 3600)
        )).where(Member.is_active == True)
    )
    avg_tenure = result.scalar_one() or 0
    
    return CommunityReportResponse(
        total_members=total_members,
        active_members_30d=active_30d,
        total_tithes_ytd_cents=tithes_ytd,
        total_blessings_distributed_ytd_cents=blessings_ytd,
        blessings_by_category=by_category,
        cora_in_circulation=cora_circulation,
        average_member_tenure_months=round(float(avg_tenure), 1)
    )


@router.get("/blessings", response_model=BlessingsReportResponse)
async def get_blessings_report(
    admin: Member = Depends(require_admin),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    category: str = Query(None),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get blessing requests report with filters.
    Admin only.
    """
    # Default date range (last 90 days)
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=90)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Base query
    query = select(BlessingRequest).where(
        BlessingRequest.created_at >= start_date,
        BlessingRequest.created_at <= end_date
    )
    
    if category:
        query = query.where(BlessingRequest.category == category)
    if status:
        query = query.where(BlessingRequest.status == status)
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    total = len(requests)
    approved = len([r for r in requests if r.status in ["approved", "disbursed", "closed"] and r.amount_approved_cents])
    denied = len([r for r in requests if r.status == "denied" or (r.status == "closed" and not r.amount_approved_cents)])
    
    # Calculate disbursed total
    disbursed_ids = [r.id for r in requests if r.status == "closed" and r.amount_approved_cents]
    total_disbursed = 0
    if disbursed_ids:
        result = await db.execute(
            select(func.sum(BlessingDisbursement.amount_cents)).where(
                BlessingDisbursement.blessing_request_id.in_(disbursed_ids)
            )
        )
        total_disbursed = result.scalar_one() or 0
    
    # Average processing time
    processed = [r for r in requests if r.status == "closed"]
    if processed:
        avg_days = sum(
            (r.updated_at - r.created_at).days for r in processed
        ) / len(processed)
    else:
        avg_days = 0
    
    # By category
    by_category = {}
    for r in requests:
        if r.category not in by_category:
            by_category[r.category] = {"count": 0, "approved": 0, "denied": 0}
        by_category[r.category]["count"] += 1
        if r.status in ["approved", "disbursed", "closed"] and r.amount_approved_cents:
            by_category[r.category]["approved"] += 1
        elif r.status == "denied":
            by_category[r.category]["denied"] += 1
    
    return BlessingsReportResponse(
        total_requests=total,
        approved_count=approved,
        denied_count=denied,
        total_disbursed_cents=total_disbursed,
        average_processing_days=round(avg_days, 1),
        by_category_summary=by_category
    )


@router.get("/cora-health", response_model=CoraHealthResponse)
async def get_cora_health_report(
    admin: Member = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get CORA system health report.
    Admin only.
    """
    cora_service = CoraService(db)
    
    total = await cora_service.get_total_circulation()
    average = await cora_service.get_average_member_cora()
    
    # Members at risk
    approaching = await cora_service.get_members_approaching_decay()
    at_risk = len(approaching)
    
    # Decay events last 90 days
    from app.models import CoraDecayEvent
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    result = await db.execute(
        select(func.count(CoraDecayEvent.id)).where(
            CoraDecayEvent.created_at >= ninety_days_ago
        )
    )
    decay_events = result.scalar_one()
    
    return CoraHealthResponse(
        total_cora_circulation=total,
        members_at_risk_of_decay=at_risk,
        decay_events_last_90_days=decay_events,
        average_member_cora=round(average, 2)
    )



