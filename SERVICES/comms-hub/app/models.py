from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


Source = Literal["terminal", "obsidian", "telegram", "system", "builder"]
Audience = Literal["james", "system", "builder", "all"]
Priority = Literal["low", "normal", "high", "urgent"]
Status = Literal["queued", "delivered", "failed", "blocked", "dry_run"]
Surface = Literal["terminal", "obsidian", "telegram", "voice", "inbox"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Attachment(BaseModel):
    type: str
    file_id: str | None = None
    duration: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageInput(BaseModel):
    source: Source = "system"
    audience: Audience = "james"
    priority: Priority = "normal"
    topic: str = "coordination"
    body: str
    route: list[Surface] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageRecord(MessageInput):
    id: str
    created_at: str = Field(default_factory=now_iso)
    status: Status = "queued"
    dedupe_key: str


class DeliveryAttempt(BaseModel):
    message_id: str
    surface: Surface
    status: Status
    created_at: str = Field(default_factory=now_iso)
    detail: str = ""
    dry_run: bool = True


class DeliveryPlan(BaseModel):
    message_id: str
    surfaces: list[Surface] = Field(default_factory=list)
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)


class DeliveryResult(BaseModel):
    status: Literal["delivered", "failed", "blocked", "dry_run"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    service: str
    version: str
    dry_run: bool
    runtime_paused: bool
