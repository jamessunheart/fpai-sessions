"""Models for the Proxy Manager."""
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field

class ProxyConfigRequest(BaseModel):
    """Request to configure a proxy."""
    domain: str = Field(..., description="The domain name to route (e.g. registry.fpai.io)")
    upstream_host: str = Field(..., description="The internal IP or hostname of the service")
    upstream_port: int = Field(..., description="The internal port of the service")
    ssl_enabled: bool = Field(False, description="Whether to enable SSL (requires valid domain)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProxyConfig(ProxyConfigRequest):
    """Internal proxy configuration model."""
    droplet_name: str
    status: str = "inactive"
    last_health_status: Optional[str] = None
    last_health_checked_at: Optional[datetime] = None

class ProxyConfigResponse(ProxyConfig):
    """Response model for proxy configuration."""
    pass

class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str
    message: str

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail

class MessageRequest(BaseModel):
    """UDC Message Request."""
    sender: str
    content: Dict[str, Any]
    timestamp: datetime

class MessageResponse(BaseModel):
    """UDC Message Response."""
    received: bool
    processed_at: datetime
