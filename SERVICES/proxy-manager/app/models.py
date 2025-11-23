from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProxyConfig(BaseModel):
    droplet_name: str
    domain: str
    upstream_host: str
    upstream_port: int
    ssl_enabled: bool = False
    require_healthy: bool = True

class ProxyStatus(BaseModel):
    droplet_name: str
    domain: str
    upstream: str
    ssl_enabled: bool
    status: str

class SSLCertRequest(BaseModel):
    email: Optional[str] = None
    force_renew: bool = False

class HealthResponse(BaseModel):
    status: str
    nginx: dict
    ssl: dict

