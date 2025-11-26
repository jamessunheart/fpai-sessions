"""Pydantic schemas for tasks."""
import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class TaskAssignment(BaseModel):
    from_service: str
    message_type: str = Field("task_assignment")
    payload: Dict[str, Any]


class TaskRead(BaseModel):
    task_id: uuid.UUID
    status: str
    priority: int
    result: Dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

