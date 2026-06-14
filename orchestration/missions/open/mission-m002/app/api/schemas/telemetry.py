"""Pydantic models for Telemetry."""
import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class TelemetryEventBase(BaseModel):
    """Base properties for telemetry events."""

    source: str = Field(..., description="Source of the event (e.g., builder-agent-1)")
    event_type: str = Field(
        ..., description="Type of event (e.g., build_started, error)"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Flexible event context data"
    )


class TelemetryEventCreate(TelemetryEventBase):
    """Payload for creating a new telemetry event."""

    pass


class TelemetryEventRead(TelemetryEventBase):
    """Response model for a telemetry event."""

    id: uuid.UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

