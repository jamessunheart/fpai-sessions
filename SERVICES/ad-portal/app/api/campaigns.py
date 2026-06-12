"""
Campaigns API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from app.database import get_db
from app.models import Campaign, Offer, Creative, AdMetrics, Conversion
from app.schemas.campaign import (
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignList,
    CampaignMetricsSummary, CampaignLaunchResponse
)
from app.integrations.meta import MetaAdsClient

router = APIRouter()


async def get_campaign_metrics(db: AsyncSession, campaign_id: UUID) -> CampaignMetricsSummary:
    """Calculate metrics summary for a campaign"""
    # Get ad metrics totals
    metrics_result = await db.execute(
        select(
            func.coalesce(func.sum(AdMetrics.spend), 0).label('spend'),
            func.coalesce(func.sum(AdMetrics.impressions), 0).label('impressions'),
            func.coalesce(func.sum(AdMetrics.clicks), 0).label('clicks')
        ).where(AdMetrics.campaign_id == campaign_id)
    )
    metrics = metrics_result.first()
    
    # Get conversions
    conv_result = await db.execute(
        select(
            func.count(Conversion.id).label('count'),
            func.coalesce(func.sum(Conversion.amount), 0).label('revenue')
        ).where(Conversion.campaign_id == campaign_id)
    )
    conversions = conv_result.first()
    
    spend = Decimal(str(metrics.spend or 0))
    impressions = metrics.impressions or 0
    clicks = metrics.clicks or 0
    conv_count = conversions.count or 0
    revenue = Decimal(str(conversions.revenue or 0))
    
    return CampaignMetricsSummary(
        total_spend=spend,
        total_impressions=impressions,
        total_clicks=clicks,
        total_conversions=conv_count,
        total_revenue=revenue,
        ctr=round((clicks / impressions * 100) if impressions > 0 else 0, 2),
        cpc=Decimal(str(round(float(spend) / clicks, 2) if clicks > 0 else 0)),
        cpa=Decimal(str(round(float(spend) / conv_count, 2) if conv_count > 0 else 0)),
        roas=round(float(revenue) / float(spend), 2) if float(spend) > 0 else 0,
        profit=revenue - spend
    )


@router.get("", response_model=CampaignList)
async def list_campaigns(
    status: Optional[str] = Query(None, description="Filter by status"),
    offer_id: Optional[UUID] = Query(None, description="Filter by offer"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all campaigns with optional filtering"""
    query = select(Campaign).options(selectinload(Campaign.offer))
    
    if status:
        query = query.where(Campaign.status == status)
    if offer_id:
        query = query.where(Campaign.offer_id == offer_id)
    
    query = query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    campaigns = result.scalars().all()
    
    # Get total count
    count_query = select(func.count(Campaign.id))
    if status:
        count_query = count_query.where(Campaign.status == status)
    if offer_id:
        count_query = count_query.where(Campaign.offer_id == offer_id)
    total = await db.execute(count_query)
    
    # Enrich with metrics
    enriched = []
    for campaign in campaigns:
        metrics = await get_campaign_metrics(db, campaign.id)
        creative_count = await db.execute(
            select(func.count(Creative.id)).where(Creative.campaign_id == campaign.id)
        )
        
        enriched.append(CampaignResponse(
            **{k: v for k, v in campaign.__dict__.items() if not k.startswith('_')},
            days_running=campaign.days_running,
            creative_count=creative_count.scalar() or 0,
            metrics=metrics
        ))
    
    return CampaignList(campaigns=enriched, total=total.scalar())


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    campaign: CampaignCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new campaign"""
    # Verify offer exists
    offer_result = await db.execute(select(Offer).where(Offer.id == campaign.offer_id))
    offer = offer_result.scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    campaign_data = campaign.model_dump()
    if campaign_data.get('targeting'):
        campaign_data['targeting'] = campaign_data['targeting'].model_dump() if hasattr(campaign_data['targeting'], 'model_dump') else campaign_data['targeting']
    
    db_campaign = Campaign(**campaign_data)
    db.add(db_campaign)
    await db.flush()
    await db.refresh(db_campaign)
    
    return CampaignResponse(
        **{k: v for k, v in db_campaign.__dict__.items() if not k.startswith('_')},
        days_running=0,
        creative_count=0,
        metrics=CampaignMetricsSummary()
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get campaign by ID with full metrics"""
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.offer))
        .where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    metrics = await get_campaign_metrics(db, campaign.id)
    creative_count = await db.execute(
        select(func.count(Creative.id)).where(Creative.campaign_id == campaign.id)
    )
    
    return CampaignResponse(
        **{k: v for k, v in campaign.__dict__.items() if not k.startswith('_')},
        days_running=campaign.days_running,
        creative_count=creative_count.scalar() or 0,
        metrics=metrics
    )


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    campaign_update: CampaignUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a campaign"""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_data = campaign_update.model_dump(exclude_unset=True)
    if 'targeting' in update_data and update_data['targeting']:
        update_data['targeting'] = update_data['targeting'].model_dump() if hasattr(update_data['targeting'], 'model_dump') else update_data['targeting']
    
    for field, value in update_data.items():
        setattr(campaign, field, value)
    
    await db.flush()
    await db.refresh(campaign)
    
    metrics = await get_campaign_metrics(db, campaign.id)
    creative_count = await db.execute(
        select(func.count(Creative.id)).where(Creative.campaign_id == campaign.id)
    )
    
    return CampaignResponse(
        **{k: v for k, v in campaign.__dict__.items() if not k.startswith('_')},
        days_running=campaign.days_running,
        creative_count=creative_count.scalar() or 0,
        metrics=metrics
    )


@router.post("/{campaign_id}/launch", response_model=CampaignLaunchResponse)
async def launch_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Launch campaign to Meta Ads"""
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.offer), selectinload(Campaign.creatives))
        .where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign.status}")
    
    if not campaign.creatives:
        raise HTTPException(status_code=400, detail="Campaign has no creatives. Add at least one creative before launching.")
    
    # Launch to Meta
    try:
        meta_client = MetaAdsClient()
        launch_result = await meta_client.create_campaign(campaign)
        
        # Update campaign with Meta IDs
        campaign.meta_campaign_id = launch_result.get('campaign_id')
        campaign.meta_adset_id = launch_result.get('adset_id')
        campaign.status = "active"
        campaign.launched_at = datetime.utcnow()
        
        await db.flush()
        
        return CampaignLaunchResponse(
            success=True,
            campaign_id=campaign.id,
            meta_campaign_id=campaign.meta_campaign_id,
            meta_adset_id=campaign.meta_adset_id,
            message="Campaign launched successfully",
            launched_at=campaign.launched_at
        )
        
    except Exception as e:
        return CampaignLaunchResponse(
            success=False,
            campaign_id=campaign.id,
            message=f"Launch failed: {str(e)}"
        )


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Pause an active campaign"""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != "active":
        raise HTTPException(status_code=400, detail="Campaign is not active")
    
    # Pause on Meta
    if campaign.meta_campaign_id:
        try:
            meta_client = MetaAdsClient()
            await meta_client.update_campaign_status(campaign.meta_campaign_id, "PAUSED")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to pause on Meta: {str(e)}")
    
    campaign.status = "paused"
    await db.flush()
    await db.refresh(campaign)
    
    metrics = await get_campaign_metrics(db, campaign.id)
    return CampaignResponse(
        **{k: v for k, v in campaign.__dict__.items() if not k.startswith('_')},
        days_running=campaign.days_running,
        creative_count=len(campaign.creatives) if campaign.creatives else 0,
        metrics=metrics
    )


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Resume a paused campaign"""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != "paused":
        raise HTTPException(status_code=400, detail="Campaign is not paused")
    
    # Resume on Meta
    if campaign.meta_campaign_id:
        try:
            meta_client = MetaAdsClient()
            await meta_client.update_campaign_status(campaign.meta_campaign_id, "ACTIVE")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to resume on Meta: {str(e)}")
    
    campaign.status = "active"
    await db.flush()
    await db.refresh(campaign)
    
    metrics = await get_campaign_metrics(db, campaign.id)
    return CampaignResponse(
        **{k: v for k, v in campaign.__dict__.items() if not k.startswith('_')},
        days_running=campaign.days_running,
        creative_count=len(campaign.creatives) if campaign.creatives else 0,
        metrics=metrics
    )


@router.delete("/{campaign_id}", status_code=204)
async def archive_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Archive a campaign"""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # If active, pause on Meta first
    if campaign.status == "active" and campaign.meta_campaign_id:
        try:
            meta_client = MetaAdsClient()
            await meta_client.update_campaign_status(campaign.meta_campaign_id, "PAUSED")
        except:
            pass  # Best effort
    
    campaign.status = "archived"
    await db.flush()
    
    return None


