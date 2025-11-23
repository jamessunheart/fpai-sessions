from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProxyConfig(BaseModel):
    droplet_name: str = Field(..., min_length=1, description="Unique name of the droplet")
    domain: str = Field(..., min_length=3, description="External domain name")
    upstream_host: str = Field("localhost", description="Internal host where service is running")
    upstream_port: int = Field(..., ge=1, le=65535, description="Internal port")
    enable_ssl: bool = Field(False, description="Whether to enable HTTPS")
    require_healthy: bool = Field(True, description="Check health before applying config")

class ProxyStatus(BaseModel):
    droplet_name: str
    domain: str
    upstream: str
    ssl_enabled: bool
    status: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class SSLRequest(BaseModel):
    email: Optional[str] = None
    force_renew: bool = False

class HealthStatus(BaseModel):
    status: str
    nginx: dict
    ssl: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)

