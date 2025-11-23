from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

class VerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    ERROR = "error"

class CheckResult(BaseModel):
    name: str
    status: VerificationStatus
    details: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

class VerificationReport(BaseModel):
    id: str
    service_id: str
    status: VerificationStatus
    score: int
    results: List[CheckResult]
    created_at: datetime

# UDC Models
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime

class CapabilityResponse(BaseModel):
    name: str
    version: str
    capabilities: list[str]

