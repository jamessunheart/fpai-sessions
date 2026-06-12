"""
Offers API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from app.database import get_db
from app.models import Offer, Campaign, Conversion
from app.schemas.offer import OfferCreate, OfferUpdate, OfferResponse, OfferList

router = APIRouter()


@router.get("", response_model=OfferList)
async def list_offers(
    active_only: bool = Query(True, description="Only return active offers"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all offers with optional filtering"""
    query = select(Offer)
    
    if active_only:
        query = query.where(Offer.active == True)
    
    query = query.order_by(Offer.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    offers = result.scalars().all()
    
    # Get total count
    count_query = select(func.count(Offer.id))
    if active_only:
        count_query = count_query.where(Offer.active == True)
    total = await db.execute(count_query)
    total_count = total.scalar()
    
    # Enrich with computed fields
    enriched_offers = []
    for offer in offers:
        # Get campaign count
        camp_count = await db.execute(
            select(func.count(Campaign.id)).where(Campaign.offer_id == offer.id)
        )
        
        # Get total revenue
        rev_result = await db.execute(
            select(func.coalesce(func.sum(Conversion.amount), 0)).where(Conversion.offer_id == offer.id)
        )
        
        offer_dict = {
            **offer.__dict__,
            "display_price": f"${offer.price:,.2f} {offer.currency}",
            "campaign_count": camp_count.scalar() or 0,
            "total_revenue": Decimal(str(rev_result.scalar() or 0))
        }
        enriched_offers.append(OfferResponse(**offer_dict))
    
    return OfferList(offers=enriched_offers, total=total_count)


@router.post("", response_model=OfferResponse, status_code=201)
async def create_offer(
    offer: OfferCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new offer"""
    db_offer = Offer(**offer.model_dump())
    db.add(db_offer)
    await db.flush()
    await db.refresh(db_offer)
    
    return OfferResponse(
        **db_offer.__dict__,
        display_price=f"${db_offer.price:,.2f} {db_offer.currency}",
        campaign_count=0,
        total_revenue=Decimal("0.00")
    )


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get offer by ID"""
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    offer = result.scalar_one_or_none()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Get stats
    camp_count = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.offer_id == offer.id)
    )
    rev_result = await db.execute(
        select(func.coalesce(func.sum(Conversion.amount), 0)).where(Conversion.offer_id == offer.id)
    )
    
    return OfferResponse(
        **offer.__dict__,
        display_price=f"${offer.price:,.2f} {offer.currency}",
        campaign_count=camp_count.scalar() or 0,
        total_revenue=Decimal(str(rev_result.scalar() or 0))
    )


@router.put("/{offer_id}", response_model=OfferResponse)
async def update_offer(
    offer_id: UUID,
    offer_update: OfferUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an offer"""
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    offer = result.scalar_one_or_none()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Update fields
    update_data = offer_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(offer, field, value)
    
    await db.flush()
    await db.refresh(offer)
    
    # Get stats
    camp_count = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.offer_id == offer.id)
    )
    rev_result = await db.execute(
        select(func.coalesce(func.sum(Conversion.amount), 0)).where(Conversion.offer_id == offer.id)
    )
    
    return OfferResponse(
        **offer.__dict__,
        display_price=f"${offer.price:,.2f} {offer.currency}",
        campaign_count=camp_count.scalar() or 0,
        total_revenue=Decimal(str(rev_result.scalar() or 0))
    )


@router.delete("/{offer_id}", status_code=204)
async def delete_offer(
    offer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete an offer (set active=False)"""
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    offer = result.scalar_one_or_none()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    offer.active = False
    await db.flush()
    
    return None


