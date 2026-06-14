"""UDC-Compliant Models for Jobs Service"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any


class UDCHealthResponse(BaseModel):
    """UDC /health endpoint response"""
    status: Literal["active", "inactive", "error"]
    service: str = "jobs"
    version: str = "1.0.0"
    timestamp: str


class UDCCapabilitiesResponse(BaseModel):
    """UDC /capabilities endpoint response"""
    version: str
    features: List[str]
    dependencies: List[str]
    udc_version: str = "1.0"
    metadata: Optional[Dict[str, Any]] = None


class UDCStateResponse(BaseModel):
    """UDC /state endpoint response"""
    uptime_seconds: int
    requests_total: int = 0
    requests_per_minute: Optional[float] = None
    errors_last_hour: int = 0
    last_restart: str
    resource_usage: Optional[Dict[str, Any]] = None


class DependencyStatus(BaseModel):
    """Dependency status model"""
    name: str
    status: str  # connected, available, unavailable


class UDCDependenciesResponse(BaseModel):
    """UDC /dependencies endpoint response"""
    required: List[DependencyStatus]
    optional: List[DependencyStatus]
    missing: List[str] = []


class UDCMessageRequest(BaseModel):
    """UDC /message endpoint request"""
    trace_id: str
    source: str
    target: str = "jobs"
    message_type: Literal["status", "event", "command", "query"]
    payload: Dict[str, Any] = {}
    timestamp: str
    signature: Optional[str] = None


class UDCMessageResponse(BaseModel):
    """UDC /message endpoint response"""
    received: bool = True
    trace_id: str
    processed_at: str
    result: Optional[str] = "success"
