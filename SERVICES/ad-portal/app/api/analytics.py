"""
Analytics API Endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.database import get_db
from app.models import Campaign, Offer, AdMetrics, Conversion, ProfitReport
from app.schemas.analytics import (
    AnalyticsOverview, 
    CampaignPerformance, CampaignPerformanceList,
    DailyMetrics, DailyMetricsList,
    HourlyMetrics, HourlyMetricsList,
    CreativePerformance, CreativePerformanceList
)

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard overview statistics"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    prev_start = start_date - timedelta(days=days)
    
    # Current period metrics
    current_metrics = await db.execute(
        select(
            func.coalesce(func.sum(AdMetrics.spend), 0).label('spend'),
            func.coalesce(func.sum(AdMetrics.impressions), 0).label('impressions'),
            func.coalesce(func.sum(AdMetrics.clicks), 0).label('clicks')
        ).where(
            and_(AdMetrics.date >= start_date, AdMetrics.date <= end_date)
        )
    )
    current = current_metrics.first()
    
    # Current period conversions
    conv_result = await db.execute(
        select(
            func.count(Conversion.id).label('count'),
            func.coalesce(func.sum(Conversion.amount), 0).label('revenue')
        ).where(
            func.date(Conversion.converted_at) >= start_date
        )
    )
    conversions = conv_result.first()
    
    # Previous period (for trends)
    prev_metrics = await db.execute(
        select(
            func.coalesce(func.sum(AdMetrics.spend), 0).label('spend')
        ).where(
            and_(AdMetrics.date >= prev_start, AdMetrics.date < start_date)
        )
    )
    prev = prev_metrics.first()
    
    prev_conv = await db.execute(
        select(
            func.coalesce(func.sum(Conversion.amount), 0).label('revenue')
        ).where(
            and_(
                func.date(Conversion.converted_at) >= prev_start,
                func.date(Conversion.converted_at) < start_date
            )
        )
    )
    prev_revenue = prev_conv.first()
    
    # Counts
    active_campaigns = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.status == 'active')
    )
    active_offers = await db.execute(
        select(func.count(Offer.id)).where(Offer.active == True)
    )
    
    spend = Decimal(str(current.spend or 0))
    revenue = Decimal(str(conversions.revenue or 0))
    profit = revenue - spend
    impressions = current.impressions or 0
    clicks = current.clicks or 0
    conv_count = conversions.count or 0
    
    prev_spend = float(prev.spend or 1)  # Avoid division by zero
    prev_rev = float(prev_revenue.revenue or 1)
    
    return AnalyticsOverview(
        total_spend=spend,
        total_revenue=revenue,
        total_profit=profit,
        total_conversions=conv_count,
        overall_roas=round(float(revenue) / float(spend), 2) if float(spend) > 0 else 0,
        avg_cpa=Decimal(str(round(float(spend) / conv_count, 2) if conv_count > 0 else 0)),
        avg_ctr=round((clicks / impressions * 100) if impressions > 0 else 0, 2),
        active_campaigns=active_campaigns.scalar() or 0,
        active_offers=active_offers.scalar() or 0,
        total_impressions=impressions,
        total_clicks=clicks,
        period_start=start_date,
        period_end=end_date,
        spend_trend=round(((float(spend) - prev_spend) / prev_spend) * 100, 1),
        revenue_trend=round(((float(revenue) - prev_rev) / prev_rev) * 100, 1),
        profit_trend=round(((float(profit) - (prev_rev - prev_spend)) / max(prev_rev - prev_spend, 1)) * 100, 1),
        roas_trend=0  # TODO: Calculate ROAS trend
    )


@router.get("/campaigns", response_model=CampaignPerformanceList)
async def get_campaign_performance(
    days: int = Query(30, ge=1, le=365),
    sort_by: str = Query("profit", description="Sort by: profit, spend, revenue, roas"),
    db: AsyncSession = Depends(get_db)
):
    """Get performance comparison across campaigns"""
    start_date = date.today() - timedelta(days=days)
    
    # Get all campaigns with their offers
    campaigns_result = await db.execute(
        select(Campaign, Offer.name.label('offer_name'))
        .join(Offer)
        .where(Campaign.status.in_(['active', 'paused', 'completed']))
    )
    campaigns = campaigns_result.all()
    
    performances = []
    total_spend = Decimal("0")
    total_revenue = Decimal("0")
    
    for campaign, offer_name in campaigns:
        # Get metrics
        metrics = await db.execute(
            select(
                func.coalesce(func.sum(AdMetrics.spend), 0).label('spend'),
                func.coalesce(func.sum(AdMetrics.impressions), 0).label('impressions'),
                func.coalesce(func.sum(AdMetrics.clicks), 0).label('clicks')
            ).where(
                and_(
                    AdMetrics.campaign_id == campaign.id,
                    AdMetrics.date >= start_date
                )
            )
        )
        m = metrics.first()
        
        # Get conversions
        conv = await db.execute(
            select(
                func.count(Conversion.id).label('count'),
                func.coalesce(func.sum(Conversion.amount), 0).label('revenue'),
                func.max(Conversion.converted_at).label('last_conv')
            ).where(
                and_(
                    Conversion.campaign_id == campaign.id,
                    func.date(Conversion.converted_at) >= start_date
                )
            )
        )
        c = conv.first()
        
        spend = Decimal(str(m.spend or 0))
        revenue = Decimal(str(c.revenue or 0))
        impressions = m.impressions or 0
        clicks = m.clicks or 0
        conv_count = c.count or 0
        
        total_spend += spend
        total_revenue += revenue
        
        performances.append(CampaignPerformance(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            offer_name=offer_name,
            status=campaign.status,
            spend=spend,
            revenue=revenue,
            profit=revenue - spend,
            conversions=conv_count,
            impressions=impressions,
            clicks=clicks,
            roas=round(float(revenue) / float(spend), 2) if float(spend) > 0 else 0,
            ctr=round((clicks / impressions * 100) if impressions > 0 else 0, 2),
            cpc=Decimal(str(round(float(spend) / clicks, 2) if clicks > 0 else 0)),
            cpa=Decimal(str(round(float(spend) / conv_count, 2) if conv_count > 0 else 0)),
            days_running=campaign.days_running,
            last_conversion=c.last_conv
        ))
    
    # Sort
    sort_key = {
        "profit": lambda x: x.profit,
        "spend": lambda x: x.spend,
        "revenue": lambda x: x.revenue,
        "roas": lambda x: x.roas
    }.get(sort_by, lambda x: x.profit)
    
    performances.sort(key=sort_key, reverse=True)
    
    return CampaignPerformanceList(
        campaigns=performances,
        total=len(performances),
        sort_by=sort_by,
        total_spend=total_spend,
        total_revenue=total_revenue,
        total_profit=total_revenue - total_spend
    )


@router.get("/daily", response_model=DailyMetricsList)
async def get_daily_metrics(
    days: int = Query(30, ge=1, le=365),
    campaign_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get daily metrics breakdown"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    # Build query
    query = select(
        AdMetrics.date,
        func.sum(AdMetrics.spend).label('spend'),
        func.sum(AdMetrics.impressions).label('impressions'),
        func.sum(AdMetrics.clicks).label('clicks')
    ).where(
        and_(AdMetrics.date >= start_date, AdMetrics.date <= end_date)
    )
    
    if campaign_id:
        query = query.where(AdMetrics.campaign_id == campaign_id)
    
    query = query.group_by(AdMetrics.date).order_by(AdMetrics.date)
    
    result = await db.execute(query)
    daily_metrics = result.all()
    
    # Get daily conversions
    conv_query = select(
        func.date(Conversion.converted_at).label('date'),
        func.count(Conversion.id).label('count'),
        func.sum(Conversion.amount).label('revenue')
    ).where(
        func.date(Conversion.converted_at) >= start_date
    )
    
    if campaign_id:
        conv_query = conv_query.where(Conversion.campaign_id == campaign_id)
    
    conv_query = conv_query.group_by(func.date(Conversion.converted_at))
    conv_result = await db.execute(conv_query)
    conv_by_date = {r.date: r for r in conv_result.all()}
    
    metrics_list = []
    total_spend = Decimal("0")
    total_revenue = Decimal("0")
    
    for m in daily_metrics:
        conv = conv_by_date.get(m.date)
        spend = Decimal(str(m.spend or 0))
        revenue = Decimal(str(conv.revenue if conv else 0))
        conv_count = conv.count if conv else 0
        
        total_spend += spend
        total_revenue += revenue
        
        metrics_list.append(DailyMetrics(
            date=m.date,
            spend=spend,
            revenue=revenue,
            profit=revenue - spend,
            conversions=conv_count,
            impressions=m.impressions or 0,
            clicks=m.clicks or 0,
            roas=round(float(revenue) / float(spend), 2) if float(spend) > 0 else 0,
            cpa=Decimal(str(round(float(spend) / conv_count, 2) if conv_count > 0 else 0))
        ))
    
    num_days = len(metrics_list) or 1
    
    return DailyMetricsList(
        metrics=metrics_list,
        period_start=start_date,
        period_end=end_date,
        total_spend=total_spend,
        total_revenue=total_revenue,
        total_profit=total_revenue - total_spend,
        avg_daily_spend=Decimal(str(round(float(total_spend) / num_days, 2))),
        avg_daily_revenue=Decimal(str(round(float(total_revenue) / num_days, 2)))
    )


@router.get("/hourly/{target_date}", response_model=HourlyMetricsList)
async def get_hourly_metrics(
    target_date: date,
    campaign_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get hourly breakdown for a specific date"""
    query = select(
        AdMetrics.hour,
        func.sum(AdMetrics.spend).label('spend'),
        func.sum(AdMetrics.impressions).label('impressions'),
        func.sum(AdMetrics.clicks).label('clicks')
    ).where(
        and_(AdMetrics.date == target_date, AdMetrics.hour.isnot(None))
    )
    
    if campaign_id:
        query = query.where(AdMetrics.campaign_id == campaign_id)
    
    query = query.group_by(AdMetrics.hour).order_by(AdMetrics.hour)
    
    result = await db.execute(query)
    hourly = result.all()
    
    # Get hourly conversions
    conv_query = select(
        func.extract('hour', Conversion.converted_at).label('hour'),
        func.count(Conversion.id).label('count'),
        func.sum(Conversion.amount).label('revenue')
    ).where(
        func.date(Conversion.converted_at) == target_date
    )
    
    if campaign_id:
        conv_query = conv_query.where(Conversion.campaign_id == campaign_id)
    
    conv_query = conv_query.group_by(func.extract('hour', Conversion.converted_at))
    conv_result = await db.execute(conv_query)
    conv_by_hour = {int(r.hour): r for r in conv_result.all()}
    
    metrics_list = []
    peak_hour = 0
    peak_conversions = 0
    
    for h in hourly:
        conv = conv_by_hour.get(h.hour, None)
        conv_count = conv.count if conv else 0
        revenue = Decimal(str(conv.revenue if conv else 0))
        
        if conv_count > peak_conversions:
            peak_conversions = conv_count
            peak_hour = h.hour
        
        metrics_list.append(HourlyMetrics(
            hour=h.hour,
            spend=Decimal(str(h.spend or 0)),
            impressions=h.impressions or 0,
            clicks=h.clicks or 0,
            conversions=conv_count,
            revenue=revenue
        ))
    
    return HourlyMetricsList(
        date=target_date,
        metrics=metrics_list,
        peak_hour=peak_hour,
        peak_conversions=peak_conversions
    )


