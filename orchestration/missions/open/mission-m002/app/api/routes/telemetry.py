"""Telemetry ingestion endpoints."""
from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import TelemetryEventCreate, TelemetryEventRead
from app.core.database import get_db
from app.models import TelemetryEvent

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post(
    "",
    response_model=TelemetryEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest telemetry event",
)
async def create_telemetry_event(
    event_in: TelemetryEventCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TelemetryEvent:
    """Record a new telemetry event from an agent."""
    event = TelemetryEvent(**event_in.model_dump())
    session.add(event)
    await session.commit()
    await session.refresh(event)
    await request.app.state.telemetry_bus.broadcast(
        {
            "id": str(event.id),
            "source": event.source,
            "event_type": event.event_type,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat(),
        }
    )
    return event


@router.get(
    "",
    response_model=List[TelemetryEventRead],
    summary="List telemetry events",
)
async def list_telemetry_events(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_db),
) -> List[TelemetryEvent]:
    """Retrieve a paginated list of telemetry events."""
    query = (
        select(TelemetryEvent)
        .order_by(TelemetryEvent.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())

