"""Asset management endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AssetCreate, AssetRead
from app.core.config import settings
from app.core.database import get_db
from app.models import Asset
from app.telemetry import client as telemetry_client

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(asset_in: AssetCreate, session: AsyncSession = Depends(get_db)) -> Asset:
    asset = Asset(**asset_in.model_dump())
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    if telemetry_client:
        telemetry_client.capture(
            settings.service_name,
            "asset_registered",
            {
                "mission_id": settings.mission_id,
                "asset_id": str(asset.id),
                "type": asset.type,
                "risk_level": asset.risk_level,
            },
        )
    return asset


@router.get("", response_model=list[AssetRead])
async def list_assets(session: AsyncSession = Depends(get_db)) -> list[Asset]:
    result = await session.execute(select(Asset).order_by(Asset.created_at.desc()))
    return result.scalars().all()

