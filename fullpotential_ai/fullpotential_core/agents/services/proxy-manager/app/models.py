"""Pydantic models for Proxy Manager API."""
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
from datetime import datetime


class ProxyConfigRequest(BaseModel):
    """Request to create/update a proxy configuration."""

    domain: str = Field(..., description="External domain for the proxy")
    upstream_host: str = Field(default="localhost", description="Upstream host")
    upstream_port: int = Field(..., description="Upstream port", gt=0, lt=65536)
    require_healthy: bool = Field(
        default=True, description="Require upstream health check before activation"
    )
    enable_ssl: bool = Field(
        default=True, description="Enable SSL for this proxy"
    )


class ProxyConfig(BaseModel):
    """Proxy configuration model."""

    droplet_name: str
    domain: str
    upstream_host: str
    upstream_port: int
    ssl_enabled: bool
    status: str = "active"
    last_health_status: Optional[str] = None
    last_health_checked_at: Optional[datetime] = None

    @property
    def upstream(self) -> str:
        """Formatted upstream URL."""
        return f"http://{self.upstream_host}:{self.upstream_port}"


class ProxyConfigResponse(BaseModel):
    """Response after creating/updating a proxy."""

    droplet_name: str
    domain: str
    upstream: str
    ssl_enabled: bool
    status: str


class SSLRequest(BaseModel):
    """Request to issue/renew SSL certificate."""

    email: Optional[str] = Field(
        default=None, description="Email for Let's Encrypt notifications"
    )
    force_renew: bool = Field(
        default=False, description="Force certificate renewal"
    )


class SSLResponse(BaseModel):
    """Response after SSL issuance."""

    domain: str
    status: str
    expiry: Optional[str] = None
    issuer: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response (UDC compliant)."""

    status: Literal["active", "inactive", "error"]
    nginx: dict
    ssl: dict


class ErrorDetail(BaseModel):
    """Error details for UDC-compliant error responses."""

    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    """UDC-compliant error response."""

    error: ErrorDetail


class CapabilitiesResponse(BaseModel):
    """UDC /capabilities endpoint response."""

    version: str
    features: list[str]
    dependencies: list[str]
    udc_version: str = "1.0"
    metadata: Optional[dict] = None


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

    required: list[DependencyStatus]
    optional: list[DependencyStatus]
    missing: list[str] = []


class MessageRequest(BaseModel):
    """UDC /message endpoint request."""

    trace_id: str
    source: str
    target: str = "proxy-manager"
    message_type: Literal["status", "event", "command", "query"]
    payload: Dict[str, Any] = {}
    timestamp: str
    signature: Optional[str] = None


class MessageResponse(BaseModel):
    """UDC /message endpoint response."""

    received: bool = True
    trace_id: str
    processed_at: str
    result: Optional[str] = "success"
