"""Mission status endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import MissionStatus
from app.core.database import get_db
from app.services import aggregate_mission_status

router = APIRouter(prefix="/missions", tags=["Missions"])


@router.get(
    "/{mission_id}/status",
    response_model=MissionStatus,
    summary="Get mission status",
)
async def get_mission_status(
    mission_id: str,
    session: AsyncSession = Depends(get_db),
) -> MissionStatus:
    """
    Aggregate telemetry to determine the current status of a mission.
    """
    status_obj = await aggregate_mission_status(session, mission_id)
    
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission {mission_id} not found or has no telemetry.",
        )
    
    return status_obj

