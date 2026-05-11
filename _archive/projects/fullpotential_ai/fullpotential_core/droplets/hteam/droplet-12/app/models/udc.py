"""
UDC Standard Models
Per UDC_COMPLIANCE.md
"""

from pydantic import BaseModel, Field, validator
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime
import uuid


class HealthResponse(BaseModel):
    """
    Health check response.
    Per UDC_COMPLIANCE.md - required endpoint.
    """
    id: int
    name: str
    steward: str
    status: Literal["active", "inactive", "error"]  # Exact enum values required
    endpoint: str
    proof: Optional[str] = None
    cost_usd: float = 0.02
    yield_usd: float = 0.00
    updated_at: str  # ISO 8601 format
    
    @validator("updated_at", pre=True, always=True)
    def set_updated_at(cls, v):
        """Ensure updated_at is ISO 8601"""
        if v is None or v == "":
            return datetime.utcnow().isoformat() + "Z"
        return v


class CapabilitiesResponse(BaseModel):
    """
    Capabilities declaration.
    Per UDC_COMPLIANCE.md - required endpoint.
    """
    version: str
    features: List[str]
    dependencies: List[str]
    udc_version: str = "1.0"
    metadata: Optional[Dict[str, Any]] = None


class StateResponse(BaseModel):
    """
    Resource usage and performance metrics.
    Per UDC_COMPLIANCE.md - required endpoint.
    """
    cpu_percent: float
    memory_mb: int
    uptime_seconds: int
    requests_total: int
    requests_per_minute: int
    errors_last_hour: int
    last_restart: str  # ISO 8601 format


class DependencyStatus(BaseModel):
    """Dependency status information"""
    id: int
    name: str
    status: Literal["connected", "available", "unavailable"]


class DependenciesResponse(BaseModel):
    """
    Dependencies declaration.
    Per UDC_COMPLIANCE.md - required endpoint.
    """
    required: List[DependencyStatus]
    optional: List[DependencyStatus]
    missing: List[str] = []


class VersionResponse(BaseModel):
    """
    Version response.
    Per UDC_COMPLIANCE.md - required endpoint.
    """
    version: str
    build_date: str
    commit_hash: str
    environment: str
    deployed_by: str

class UDCMessage(BaseModel):
    """
    Standard UDC message format.
    Per UDC_COMPLIANCE.md - required for /message endpoint.
    """
    trace_id: str = Field(..., min_length=36, max_length=36)
    source: str
    target: str
    message_type: Literal["status", "event", "command", "query"]
    payload: Dict[str, Any]
    timestamp: str
    signature: Optional[str] = None
    
    @validator("trace_id")
    def validate_trace_id(cls, v):
        """Ensure trace_id is valid UUID"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("trace_id must be valid UUID v4")
        return v
    
    @validator("timestamp")
    def validate_timestamp(cls, v):
        """Ensure timestamp is ISO 8601"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("timestamp must be ISO 8601 format")
        return v


class UDCMessageResponse(BaseModel):
    """
    Response to UDC message.
    Per UDC_COMPLIANCE.md - required for /message endpoint.
    """
    received: bool
    trace_id: str
    processed_at: str
    result: Literal["success", "queued", "error"]


class SendMessageRequest(BaseModel):
    """
    Send message request.
    Per UDC_COMPLIANCE.md - required for /send endpoint.
    """
    target: str
    message_type: Literal["status", "event", "command", "query"]
    payload: Dict[str, Any]
    priority: Literal["high", "normal", "low"] = "normal"
    retry_count: int = 3


class ErrorResponse(BaseModel):
    """
    Standard error response.
    Per UDC_COMPLIANCE.md - standard error format.
    """
    status: Literal["error"] = "error"
    error: Dict[str, Any]
    timestamp: str
    
    @validator("timestamp", pre=True, always=True)
    def set_timestamp(cls, v):
        """Ensure timestamp is set"""
        if v is None or v == "":
            return datetime.utcnow().isoformat() + "Z"
        return v


class SuccessResponse(BaseModel):
    """
    Standard success response.
    Per UDC_COMPLIANCE.md - standard success format.
    """
    status: Literal["success"] = "success"
    data: Dict[str, Any]
    timestamp: str
    
    @validator("timestamp", pre=True, always=True)
    def set_timestamp(cls, v):
        """Ensure timestamp is set"""
        if v is None or v == "":
            return datetime.utcnow().isoformat() + "Z"
        return v


# ==============================================================================
# Models for Orchestrator #10 Communication
# Based on the new UDC API Reference
# ==============================================================================

class TaskPayload(BaseModel):
    """
    The inner 'payload' of a task, containing the actual data needed
    for a worker droplet to perform the task. This is generic.
    """
    class Config:
        extra = "allow"  # Allow any fields in the payload

class TaskCreate(BaseModel):
    """
    Model for creating a new task via `POST /tasks`.
    This model goes inside the UDC 'payload' field.
    """
    task_type: str = Field(..., description="The type of task, e.g., 'verify', 'summarize'.")
    title: str = Field(..., description="A human-readable title for the task.")
    description: Optional[str] = Field(None, description="A more detailed description of the task.")
    priority: int = Field(3, ge=1, le=5, description="Task priority from 1 (highest) to 5 (lowest).")
    deadline: Optional[datetime] = Field(None, description="The deadline for task completion in ISO 8601 format.")
    max_retries: int = Field(3, ge=0, description="Maximum number of times the task can be retried.")
    required_capability: str = Field(..., description="The capability a droplet must have to execute this task.")
    payload: TaskPayload = Field(..., description="The specific data needed to execute the task.")

class DropletRegister(BaseModel):
    """
    Model for registering this droplet with the orchestrator via `POST /droplets/register`.
    This model goes inside the UDC 'payload' field.
    """
    droplet_id: int
    name: str
    endpoint: str
    steward: str
    capabilities: List[str]

class HeartbeatMetrics(BaseModel):
    """Metrics payload for the heartbeat."""
    cpu_percent: float
    memory_mb: int
    requests_per_minute: int

class DropletHeartbeat(BaseModel):
    """
    Model for sending a heartbeat to the orchestrator.
    This model goes inside the UDC 'payload' field.
    """
    status: Literal["active", "inactive", "error"]
    metrics: HeartbeatMetrics


class HeartbeatPayload(BaseModel):
    """Payload for a received heartbeat."""
    metrics: Dict[str, Any]
    status: Literal["active", "inactive", "error"]

class HeartbeatMessage(UDCMessage):
    """UDC Message with a heartbeat payload."""
    payload: HeartbeatPayload


class HeartbeatResponsePayload(BaseModel):
    """Response payload for a received heartbeat."""
    received: bool
    next_heartbeat_deadline: float


class HeartbeatResponseMessage(BaseModel):
    """Full UDC response for a received heartbeat."""
    udc_version: str = "1.0"
    trace_id: str
    source: str
    target: str
    message_type: Literal["response"] = "response"
    timestamp: str
    payload: HeartbeatResponsePayload