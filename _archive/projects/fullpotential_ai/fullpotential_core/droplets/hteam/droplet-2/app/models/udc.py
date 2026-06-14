from pydantic import BaseModel, Field, validator
from typing import Literal, Dict, Any, List, Union
from datetime import datetime
import uuid


class UDCMessage(BaseModel):
    """UDC-compliant message format"""
    trace_id: str = Field(..., min_length=36, max_length=36)
    source: Union[int, str]
    target: Union[int, str]
    message_type: Literal["status", "event", "command", "query"]
    payload: Dict[Any, Any]
    timestamp: str
    signature: str = ""  # JWT token (optional for demo)

    @validator("trace_id")
    def validate_trace_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("trace_id must be valid UUID")
        return v

    @validator("timestamp")
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("timestamp must be ISO 8601 format")
        return v


class UDCResponse(BaseModel):
    """Standard UDC response format"""
    received: bool
    trace_id: str
    processed_at: str
    result: Literal["success", "queued", "error"]


class HealthResponse(BaseModel):
    """UDC health endpoint response"""
    id: int
    name: str
    steward: str
    status: Literal["active", "inactive", "error"]
    endpoint: str
    proof: str = "sha256_placeholder"
    cost_usd: float = 0.00
    yield_usd: float = 0.00
    updated_at: str


class CapabilitiesResponse(BaseModel):
    """UDC capabilities endpoint response"""
    version: str
    features: List[str]
    dependencies: List[str]
    udc_version: str
    metadata: Dict[str, Any] = {}


class StateResponse(BaseModel):
    """UDC state endpoint response"""
    cpu_percent: float
    memory_mb: int
    uptime_seconds: int
    requests_total: int
    requests_per_minute: int
    errors_last_hour: int
    last_restart: str


class DependencyInfo(BaseModel):
    """Dependency information"""
    id: int
    name: str
    status: Literal["connected", "disconnected", "available", "unavailable"]


class DependenciesResponse(BaseModel):
    """UDC dependencies endpoint response"""
    required: List[DependencyInfo]
    optional: List[DependencyInfo]
    missing: List[DependencyInfo] = []