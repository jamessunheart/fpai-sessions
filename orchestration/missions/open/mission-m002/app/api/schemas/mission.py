"""Mission domain models."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MissionState(str, Enum):
    """Standard mission execution states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class MissionStatus(BaseModel):
    """Aggregated status of a specific mission."""

    mission_id: str = Field(..., description="Unique mission identifier (e.g., M001)")
    state: MissionState = Field(
        default=MissionState.PENDING, description="Current high-level state"
    )
    last_updated: str = Field(..., description="ISO timestamp of last activity")
    active_agents: int = Field(default=0, description="Count of currently active agents")
    progress_percentage: Optional[int] = Field(
        default=None, description="Estimated completion percentage"
    )
    current_objective: Optional[str] = Field(
        default=None, description="Description of current focus"
    )

