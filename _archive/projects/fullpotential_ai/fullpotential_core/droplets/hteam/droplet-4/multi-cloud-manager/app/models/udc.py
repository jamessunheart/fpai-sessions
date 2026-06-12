"""
UDC v1.0 Standard Pydantic Models
All UDC-compliant endpoints use these models
"""

from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """UDC /health endpoint response"""
    id: int
    name: str
    steward: str
    status: Literal["active", "inactive", "error"]
    endpoint: str
    updated_at: str
    version: str
    dependencies: List[str]


class CapabilitiesResponse(BaseModel):
    """UDC /capabilities endpoint response"""
    version: str
    udc_version: str
    features: List[str]
    dependencies: List[str]
    backward_compatible: List[str] = Field(default_factory=list)


class StateResponse(BaseModel):
    """UDC /state endpoint response"""
    cpu_percent: float
    memory_mb: float
    uptime_seconds: int
    requests_total: int
    errors_total: int
    status: str


class DependencyInfo(BaseModel):
    """Single dependency information"""
    id: int
    name: str
    status: str


class DependenciesResponse(BaseModel):
    """UDC /dependencies endpoint response"""
    required: List[DependencyInfo]
    optional: List[DependencyInfo]
    connected: List[str]


class UDCMessage(BaseModel):
    """UDC /message endpoint request"""
    trace_id: str
    source: int
    target: int
    message_type: Literal["event", "query", "command", "response"]
    payload: Dict[str, Any]
    timestamp: str


class MessageResponse(BaseModel):
    """UDC /message endpoint response"""
    received: bool
    trace_id: str
    processed_at: str
    result: Literal["success", "queued", "error"]


class SendMessageRequest(BaseModel):
    """UDC /send endpoint request"""
    target: str  # droplet_id or name
    message_type: Literal["event", "query", "command", "response"]
    payload: Dict[str, Any]
    priority: Literal["high", "normal", "low"] = "normal"
    retry_count: int = 3


class VersionResponse(BaseModel):
    """UDC /version endpoint response"""
    version: str
    udc_version: str
    build_date: str
    droplet_id: int
    name: str
    environment: str = "production"


class ReloadConfigRequest(BaseModel):
    """UDC /reload-config endpoint request"""
    config_path: Optional[str] = None


class ShutdownRequest(BaseModel):
    """UDC /shutdown endpoint request"""
    delay_seconds: int = 10
    reason: str = "maintenance"


class ProofResponse(BaseModel):
    """UDC /proof endpoint response"""
    action: str
    timestamp: str
    trace_id: str
    droplet_id: int
    signature: str
