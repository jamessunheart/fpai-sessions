"""Business logic for mission status aggregation."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import MissionState, MissionStatus
from app.models import TelemetryEvent


async def aggregate_mission_status(
    session: AsyncSession, mission_id: str
) -> Optional[MissionStatus]:
    """
    Reconstruct mission status by replaying telemetry events.

    This is a simplified event sourcing implementation. In a production
    system, this would likely be cached or updated incrementally.
    """
    # 1. Fetch all events for this mission, ordered chronologically
    # We assume 'mission_id' is passed in the payload or we filter by a
    # convention. For now, we'll assume the payload contains 'mission_id'.
    # Note: This requires a JSON query which is DB-specific.
    # For SQLite simplicity, we'll fetch relevant events and filter in python
    # if strictly needed, or ideally, we add a mission_id column to TelemetryEvent.
    # For now, let's fetch recent events that might be related.
    
    # Optimization: Let's query strictly on the payload -> mission_id if possible,
    # but JSON querying in pure SQL/SQLite via SQLAlchemy can be tricky cross-DB.
    # Plan B (Robust): We really should have `mission_id` on the TelemetryEvent table.
    # But following "Step 2" specs, we only have a generic payload.
    
    # Let's iterate all events for the mission (inefficient at scale, fine for MVP).
    # We will filter in memory for this iteration.
    
    query = (
        select(TelemetryEvent)
        .order_by(TelemetryEvent.timestamp.asc())
    )
    result = await session.execute(query)
    all_events = result.scalars().all()

    mission_events = [
        e for e in all_events 
        if e.payload.get("mission_id") == mission_id
    ]

    if not mission_events:
        return None

    # 2. Replay Logic
    current_state = MissionState.PENDING
    active_agents = set()
    current_objective = "Initializing..."
    last_timestamp = mission_events[-1].timestamp

    for event in mission_events:
        etype = event.event_type
        payload = event.payload

        # State Transitions
        if etype == "mission_start":
            current_state = MissionState.IN_PROGRESS
        elif etype == "mission_complete":
            current_state = MissionState.COMPLETED
        elif etype == "mission_failed":
            current_state = MissionState.FAILED
        elif etype == "mission_blocked":
            current_state = MissionState.BLOCKED
        
        # Context Updates
        if "objective" in payload:
            current_objective = payload["objective"]
        
        # Agent tracking
        if etype == "agent_active":
            active_agents.add(event.source)
        elif etype == "agent_idle":
            active_agents.discard(event.source)

    return MissionStatus(
        mission_id=mission_id,
        state=current_state,
        last_updated=last_timestamp.isoformat(),
        active_agents=len(active_agents),
        current_objective=current_objective,
        progress_percentage=None, # TODO: Calculate based on subtasks
    )

