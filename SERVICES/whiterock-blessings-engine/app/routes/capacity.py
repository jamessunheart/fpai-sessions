"""
WhiteRock Blessings Engine - Community Capacity Endpoint
Oracle pattern - READ ONLY from this system.
v2.2 - With Redis caching
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database import get_db
from app.models import CommunityCapacity
from app.schemas import CapacityResponse, CapacityLevelEnum
from app.auth import get_current_member
from app.services.cache_service import get_cache, CacheService
from app.config import settings

router = APIRouter(prefix="/capacity", tags=["Capacity"])


@router.get("", response_model=CapacityResponse)
async def get_community_capacity(
    response: Response,
    _: any = Depends(get_current_member),  # Auth required
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache)
):
    """
    Get current community blessing capacity.
    
    This is a READ-ONLY endpoint. Capacity is set externally
    through the Oracle pattern - this system never writes to it.
    
    Returns level as string (high/medium/low/paused), NEVER dollar amounts.
    Cached for 1 minute.
    """
    # Try cache first
    cached = await cache.get_capacity()
    if cached:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = f"max-age={settings.CACHE_TTL_CAPACITY}"
        return CapacityResponse(
            level=CapacityLevelEnum(cached["level"]),
            updated_at=datetime.fromisoformat(cached["updated_at"]) if cached.get("updated_at") else None
        )
    
    # Cache miss - fetch from DB
    result = await db.execute(
        select(CommunityCapacity).order_by(CommunityCapacity.updated_at.desc()).limit(1)
    )
    capacity = result.scalar_one_or_none()
    
    if not capacity:
        # Default to high if no record exists
        response.headers["X-Cache"] = "MISS"
        return CapacityResponse(
            level=CapacityLevelEnum.HIGH,
            updated_at=None
        )
    
    # Cache the result
    await cache.set_capacity(
        capacity.capacity_level,
        capacity.updated_at.isoformat() if capacity.updated_at else None
    )
    
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = f"max-age={settings.CACHE_TTL_CAPACITY}"
    
    return CapacityResponse(
        level=CapacityLevelEnum(capacity.capacity_level),
        updated_at=capacity.updated_at
    )
