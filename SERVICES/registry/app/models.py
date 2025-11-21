"""Pydantic models for Registry service."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# ============================================================================
# UDC COMPLIANCE MODELS
# ============================================================================

class HealthResponse(BaseModel):
    """UDC /health endpoint response."""

    status: Literal["active", "inactive", "error"]
    service: str = "registry"
    version: str = "1.0.0"
    timestamp: Optional[str] = None


class CapabilitiesResponse(BaseModel):
    """UDC /capabilities endpoint response."""

    version: str
    features: List[str]
    dependencies: List[str]
    udc_version: str = "1.0"
    metadata: Optional[Dict[str, Any]] = None


class StateResponse(BaseModel):
    """UDC /state endpoint response."""

    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    uptime_seconds: int
    requests_total: int = 0
    requests_per_minute: Optional[float] = None
    errors_last_hour: int = 0
    last_restart: Optional[str] = None


class DependencyStatus(BaseModel):
    """Dependency status model."""

    id: Optional[int] = None
    name: str
    status: str  # connected, available, unavailable


class DependenciesResponse(BaseModel):
    """UDC /dependencies endpoint response."""

    required: List[DependencyStatus]
    optional: List[DependencyStatus]
    missing: List[str] = []


class MessageRequest(BaseModel):
    """UDC /message endpoint request."""

    trace_id: str
    source: str
    target: str = "registry"
    message_type: Literal["status", "event", "command", "query"]
    payload: Dict[str, Any] = {}
    timestamp: str
    signature: Optional[str] = None


class MessageResponse(BaseModel):
    """UDC /message endpoint response."""

    received: bool = True
    trace_id: str
    processed_at: str
    result: Literal["success", "queued", "error"] = "success"


class SendRequest(BaseModel):
    """UDC /send endpoint request."""

    target: str
    message_type: Literal["status", "event", "command", "query"]
    payload: Dict[str, Any] = {}
    priority: Literal["high", "normal", "low"] = "normal"
    retry_count: int = 3


class SendResponse(BaseModel):
    """UDC /send endpoint response."""

    sent: bool
    trace_id: str
    target: str
    timestamp: str
    result: Literal["success", "queued", "error"]


# ============================================================================
# REGISTRY-SPECIFIC MODELS
# ============================================================================

class Droplet(BaseModel):
    """Droplet registration model."""

    id: int
    name: str
    steward: Optional[str] = None
    status: Literal["active", "inactive", "error"] = "active"
    endpoint: str
    proof: Optional[str] = None
    cost_usd: float = 0.0
    yield_usd: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    registered_at: Optional[str] = None
    updated_at: Optional[str] = None


class RegisterDropletRequest(BaseModel):
    """Request to register a new droplet."""

    id: Optional[int] = None
    name: str
    steward: Optional[str] = None
    endpoint: str
    metadata: Optional[Dict[str, Any]] = None


class UpdateDropletRequest(BaseModel):
    """Request to update droplet information."""

    status: Optional[Literal["active", "inactive", "error"]] = None
    endpoint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    proof: Optional[str] = None
    cost_usd: Optional[float] = None
    yield_usd: Optional[float] = None


class DropletsListResponse(BaseModel):
    """Response for listing all droplets."""

    droplets: List[Droplet]
    total: int
    timestamp: str


class DropletResponse(BaseModel):
    """Response for single droplet query."""

    droplet: Droplet
    timestamp: str


class DeleteResponse(BaseModel):
    """Response for droplet deletion."""

    success: bool
    message: str
    deleted_at: str


# ============================================================================
# ERROR MODELS
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail object."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response (UDC format)."""

    status: Literal["error"] = "error"
    error: ErrorDetail
