#!/usr/bin/env python3
"""
Presence API
============
API endpoints for presence status.

Endpoints:
- GET /presence - Current status
- GET /presence/status - Short status
- POST /presence/state - Set state
- POST /presence/activity - Log activity
- GET /presence/queue - Get queue
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from .engine import (
    get_presence_engine, PresenceState, 
    log_activity, set_current_activity, queue_item
)
from .status import get_status_for_api, get_status_short, get_status_for_telegram

router = APIRouter(prefix="/presence", tags=["presence"])


class SetStateRequest(BaseModel):
    state: str  # online, focusing, away, offline
    reason: Optional[str] = ""
    expires_in_hours: Optional[int] = None


class LogActivityRequest(BaseModel):
    activity_type: str
    description: str
    outcome: Optional[str] = "handled"


class QueueItemRequest(BaseModel):
    item_type: str
    description: str
    priority: Optional[int] = 3
    source: Optional[str] = ""


@router.get("")
async def get_presence():
    """Get full presence status as JSON."""
    return get_status_for_api()


@router.get("/status")
async def get_status():
    """Get short status string."""
    return {"status": get_status_short()}


@router.get("/telegram")
async def get_telegram_status():
    """Get status formatted for Telegram."""
    return {"message": get_status_for_telegram()}


@router.post("/state")
async def set_state(request: SetStateRequest):
    """Set presence state."""
    engine = get_presence_engine()
    
    try:
        state = PresenceState(request.state)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {request.state}")
    
    if state == PresenceState.ONLINE:
        engine.go_online(request.reason or "Available")
    elif state == PresenceState.FOCUSING:
        engine.go_focusing(request.reason or "Deep work", request.expires_in_hours or 2)
    elif state == PresenceState.AWAY:
        engine.go_away(request.reason or "Away", request.expires_in_hours or 4)
    elif state == PresenceState.OFFLINE:
        engine.go_offline(request.reason or "System paused")
    
    return {"success": True, "state": state.value}


@router.post("/activity")
async def post_activity(request: LogActivityRequest):
    """Log an activity."""
    activity_id = log_activity(request.activity_type, request.description, request.outcome or "handled")
    return {"success": True, "activity_id": activity_id}


@router.post("/current")
async def set_current(activity: str):
    """Set current activity."""
    set_current_activity(activity)
    return {"success": True}


@router.delete("/current")
async def clear_current():
    """Clear current activity."""
    engine = get_presence_engine()
    engine.clear_current_activity()
    return {"success": True}


@router.get("/queue")
async def get_queue():
    """Get queued items."""
    engine = get_presence_engine()
    return {"items": engine.get_queue()}


@router.post("/queue")
async def add_to_queue(request: QueueItemRequest):
    """Add item to queue."""
    queue_item(request.item_type, request.description, request.priority or 3)
    return {"success": True}


@router.post("/queue/{item_id}/process")
async def process_item(item_id: str):
    """Mark queue item as processed."""
    engine = get_presence_engine()
    engine.process_queue_item(item_id)
    return {"success": True}


@router.get("/channels")
async def get_channels():
    """Get monitored channels."""
    engine = get_presence_engine()
    return {"channels": engine.get_monitored_channels()}


@router.post("/channels")
async def register_channel(channel_name: str, channel_type: str):
    """Register a channel."""
    engine = get_presence_engine()
    engine.register_channel(channel_name, channel_type)
    return {"success": True}


@router.get("/activities")
async def get_activities():
    """Get today's activities."""
    engine = get_presence_engine()
    activities = engine.get_activities_today()
    return {
        "count": len(activities),
        "activities": [
            {
                "id": a.id,
                "type": a.activity_type,
                "description": a.description,
                "outcome": a.outcome,
                "timestamp": a.timestamp
            }
            for a in activities
        ]
    }








