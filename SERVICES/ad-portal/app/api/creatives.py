"""
Creatives API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models import Creative, Campaign, Offer, AdMetrics
from app.schemas.creative import (
    CreativeCreate, CreativeUpdate, CreativeResponse, 
    CreativeGenerate, CreativeGenerateResponse, GeneratedCreative,
    CreativeMetrics
)
from app.services.creative_ai import CreativeAIGenerator

router = APIRouter()


async def get_creative_metrics(db: AsyncSession, creative_id: UUID) -> CreativeMetrics:
    """Get performance metrics for a creative"""
    result = await db.execute(
        select(
            func.coalesce(func.sum(AdMetrics.impressions), 0).label('impressions'),
            func.coalesce(func.sum(AdMetrics.clicks), 0).label('clicks'),
            func.coalesce(func.sum(AdMetrics.spend), 0).label('spend')
        ).where(AdMetrics.creative_id == creative_id)
    )
    metrics = result.first()
    
    impressions = metrics.impressions or 0
    clicks = metrics.clicks or 0
    spend = float(metrics.spend or 0)
    
    return CreativeMetrics(
        impressions=impressions,
        clicks=clicks,
        spend=spend,
        ctr=round((clicks / impressions * 100) if impressions > 0 else 0, 2),
        cpc=round(spend / clicks, 2) if clicks > 0 else 0,
        conversions=0  # TODO: Link conversions to creatives
    )


@router.get("", response_model=List[CreativeResponse])
async def list_creatives(
    campaign_id: Optional[UUID] = Query(None, description="Filter by campaign"),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """List creatives, optionally filtered by campaign"""
    query = select(Creative)
    
    if campaign_id:
        query = query.where(Creative.campaign_id == campaign_id)
    if active_only:
        query = query.where(Creative.active == True)
    
    query = query.order_by(Creative.variation, Creative.created_at.desc())
    
    result = await db.execute(query)
    creatives = result.scalars().all()
    
    # Enrich with metrics
    enriched = []
    for creative in creatives:
        metrics = await get_creative_metrics(db, creative.id)
        enriched.append(CreativeResponse(
            **{k: v for k, v in creative.__dict__.items() if not k.startswith('_')},
            metrics=metrics
        ))
    
    return enriched


@router.post("", response_model=CreativeResponse, status_code=201)
async def create_creative(
    creative: CreativeCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new creative"""
    # Verify campaign exists
    campaign_result = await db.execute(
        select(Campaign).where(Campaign.id == creative.campaign_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Auto-assign variation letter if not specified
    if not creative.variation or creative.variation == "A":
        existing = await db.execute(
            select(func.count(Creative.id))
            .where(Creative.campaign_id == creative.campaign_id)
        )
        count = existing.scalar() or 0
        creative_data = creative.model_dump()
        creative_data['variation'] = chr(65 + count)  # A, B, C, etc.
    else:
        creative_data = creative.model_dump()
    
    db_creative = Creative(**creative_data)
    db.add(db_creative)
    await db.flush()
    await db.refresh(db_creative)
    
    return CreativeResponse(
        **{k: v for k, v in db_creative.__dict__.items() if not k.startswith('_')},
        metrics=CreativeMetrics()
    )


@router.get("/{creative_id}", response_model=CreativeResponse)
async def get_creative(
    creative_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get creative by ID"""
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")
    
    metrics = await get_creative_metrics(db, creative.id)
    
    return CreativeResponse(
        **{k: v for k, v in creative.__dict__.items() if not k.startswith('_')},
        metrics=metrics
    )


@router.put("/{creative_id}", response_model=CreativeResponse)
async def update_creative(
    creative_id: UUID,
    creative_update: CreativeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a creative"""
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")
    
    update_data = creative_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(creative, field, value)
    
    await db.flush()
    await db.refresh(creative)
    
    metrics = await get_creative_metrics(db, creative.id)
    
    return CreativeResponse(
        **{k: v for k, v in creative.__dict__.items() if not k.startswith('_')},
        metrics=metrics
    )


@router.delete("/{creative_id}", status_code=204)
async def delete_creative(
    creative_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a creative (soft delete)"""
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")
    
    creative.active = False
    await db.flush()
    
    return None


@router.post("/generate", response_model=CreativeGenerateResponse)
async def generate_creatives(
    request: CreativeGenerate,
    db: AsyncSession = Depends(get_db)
):
    """Generate creative variations using AI"""
    # Get offer details
    offer_result = await db.execute(select(Offer).where(Offer.id == request.offer_id))
    offer = offer_result.scalar_one_or_none()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Generate with AI
    generator = CreativeAIGenerator()
    generated = await generator.generate_variations(
        offer=offer,
        tone=request.tone,
        num_variations=request.num_variations,
        focus_points=request.focus_points,
        target_audience=request.target_audience
    )
    
    return CreativeGenerateResponse(
        creatives=generated,
        offer_name=offer.name,
        generated_at=datetime.utcnow()
    )


