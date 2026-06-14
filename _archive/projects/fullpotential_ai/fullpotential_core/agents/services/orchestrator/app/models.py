"""Data models for Orchestrator."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict
from datetime import datetime


class Droplet(BaseModel):
    """Represents a droplet in the system.

    Schema aligned with Registry format:
    - Uses 'endpoint' (not 'url')
    - Stores version in metadata dict
    - Includes all Registry fields for full compatibility
    """

    id: int
    name: str
    endpoint: str  # Registry field name
    metadata: Dict[str, Any] = {}  # Contains version and other data
    steward: Optional[str] = None
    status: str = "active"
    proof: Optional[str] = None
    cost_usd: float = 0.0
    yield_usd: float = 0.0
    registered_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def url(self) -> str:
        """Compatibility property for code expecting 'url' field."""
        return self.endpoint

    @property
    def version(self) -> str:
        """Extract version from metadata."""
        return self.metadata.get('version', 'unknown')


class TaskRequest(BaseModel):
    """Request body for task submission."""

    droplet_name: str = Field(..., min_length=1, max_length=255)
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "GET"
    path: str = Field(..., min_length=1, max_length=2048)
    payload: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, str]] = None


class Task(BaseModel):
    """Internal task representation."""

    id: str
    droplet_name: str
    target_url: str
    method: str
    status: Literal["queued", "success", "error", "timeout"]
    response_status: Optional[int] = None
    response_body: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    created_at: float
    completed_at: Optional[float] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None


class TaskResponse(BaseModel):
    """Response body for task submission."""

    task_id: str
    status: Literal["success", "error", "timeout"]
    target_url: str
    response_status: Optional[int] = None
    response_body: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    duration_ms: Optional[int] = None


class TaskListResponse(BaseModel):
    """Response body for task list."""

    tasks: list[Task]
    total: int
    limit: int


class DropletsResponse(BaseModel):
    """Response body for droplet list."""

    droplets: list[Droplet]
    cache_status: Literal["active", "stale", "unavailable"]
    served_from: Literal["registry", "cache"]


class InfoResponse(BaseModel):
    """Response body for info endpoint."""

    id: int
    name: str
    version: str
    registry_url: str
    registered: bool
    last_registry_sync: Optional[float] = None
    cache_status: Literal["active", "stale", "unavailable"]
    cache_age_seconds: int = 0


class ErrorDetail(BaseModel):
    """Error detail object."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response (UDC format)."""

    status: Literal["error"] = "error"
    error: ErrorDetail


class TaskMetrics(BaseModel):
    """Task performance metrics."""

    total: int = 0
    success: int = 0
    error: int = 0
    timeout: int = 0
    success_rate_percent: float = 0.0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0


class RetryMetrics(BaseModel):
    """Retry performance metrics."""

    total_retries: int = 0
    retry_success_count: int = 0
    retry_final_fail_count: int = 0


class RegistryMetrics(BaseModel):
    """Registry interaction metrics."""

    syncs_total: int = 0
    syncs_success: int = 0
    syncs_error: int = 0
    last_sync: Optional[float] = None
    last_sync_duration_ms: float = 0.0
    cache_age_seconds: int = 0
    cache_status: Literal["active", "stale", "unavailable"]


class MetricsResponse(BaseModel):
    """Response body for metrics endpoint."""

    service: str
    version: str
    uptime_seconds: int
    tasks: TaskMetrics
    retry: RetryMetrics
    registry: RegistryMetrics
    droplets_known: int
    droplets_reachable: int


class CapabilitiesResponse(BaseModel):
    """Response body for UDC /capabilities endpoint."""

    version: str
    features: list[str]
    dependencies: list[str]
    udc_version: str = "1.0"
    metadata: Optional[Dict[str, Any]] = None


class StateResponse(BaseModel):
    """Response body for UDC /state endpoint."""

    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    uptime_seconds: int
    requests_total: int
    requests_per_minute: Optional[float] = None
    errors_last_hour: int = 0
    last_restart: Optional[str] = None


class DependencyStatus(BaseModel):
    """Dependency status model for UDC compliance."""

    id: Optional[int] = None
    name: str
    status: str  # connected, available, unavailable


class DependenciesResponse(BaseModel):
    """Response body for UDC /dependencies endpoint."""

    required: list[DependencyStatus]
    optional: list[DependencyStatus]
    missing: list[str] = []


class MessageRequest(BaseModel):
    """Request body for UDC /message endpoint."""

    trace_id: str
    source: str
    target: str
    message_type: Literal["status", "event", "command", "query"]
    payload: Dict[str, Any]
    timestamp: Optional[str] = None


class MessageResponse(BaseModel):
    """Response body for UDC /message endpoint."""

    received: bool
    trace_id: str
    processed_at: str
    result: str = "success"


class SendRequest(BaseModel):
    """Request body for UDC /send endpoint."""

    target: str
    message_type: Literal["status", "event", "command", "query"]
    payload: Dict[str, Any] = {}
    priority: Literal["high", "normal", "low"] = "normal"
    retry_count: int = 3


class SendResponse(BaseModel):
    """Response body for UDC /send endpoint."""

    sent: bool
    trace_id: str
    target: str
    timestamp: str
    result: Literal["success", "queued", "error"]
