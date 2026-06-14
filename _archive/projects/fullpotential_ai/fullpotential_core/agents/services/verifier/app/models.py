"""Pydantic models for Verifier Droplet."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Status of a verification job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Decision(str, Enum):
    """Verification decision."""

    APPROVED = "APPROVED"
    APPROVED_WITH_NOTES = "APPROVED_WITH_NOTES"
    FIXES_REQUIRED = "FIXES_REQUIRED"


class PhaseStatus(str, Enum):
    """Status of a verification phase."""

    PASS = "PASS"
    FAIL = "FAIL"
    MINOR_ISSUES = "MINOR_ISSUES"


class IssueSeverity(str, Enum):
    """Severity of an issue."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    MINOR = "minor"


class VerificationRequest(BaseModel):
    """Request to verify a droplet."""

    droplet_path: str = Field(..., description="Path to droplet codebase")
    droplet_name: str = Field(..., description="Name of the droplet")
    quick_mode: bool = Field(default=False, description="Skip some checks for speed")


class VerificationJobResponse(BaseModel):
    """Response when submitting a verification job."""

    job_id: str
    status: JobStatus
    droplet_name: str
    created_at: datetime
    estimated_duration_seconds: int = 180


class Check(BaseModel):
    """A single verification check."""

    name: str
    status: str  # "PASS" or "FAIL" or issue description
    details: Optional[str] = None
    response: Optional[Dict[str, Any]] = None


class PhaseResult(BaseModel):
    """Result of a verification phase."""

    phase: str
    status: PhaseStatus
    duration_seconds: int
    checks: List[Check]


class Issue(BaseModel):
    """An issue found during verification."""

    severity: IssueSeverity
    category: str
    file: Optional[str] = None
    line: Optional[int] = None
    message: str
    suggestion: Optional[str] = None


class VerificationSummary(BaseModel):
    """Summary of verification results."""

    critical_issues: int
    important_issues: int
    minor_issues: int
    tests_passing: str
    coverage_percent: Optional[int] = None


class JobStatusResponse(BaseModel):
    """Response for job status query."""

    job_id: str
    status: JobStatus
    droplet_name: str
    current_phase: Optional[str] = None
    progress_percent: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    decision: Optional[Decision] = None
    summary: Optional[VerificationSummary] = None
    duration_seconds: Optional[int] = None


class VerificationReport(BaseModel):
    """Full verification report."""

    job_id: str
    droplet_name: str
    decision: Decision
    phases: List[PhaseResult]
    critical_issues: List[Issue]
    important_issues: List[Issue]
    minor_issues: List[Issue]
    strengths: List[str]
    recommendations: List[str]
    summary: VerificationSummary
    started_at: datetime
    completed_at: datetime
    duration_seconds: int


class RecentVerification(BaseModel):
    """Recent verification entry."""

    job_id: str
    droplet_name: str
    decision: Decision
    completed_at: datetime


class HealthResponse(BaseModel):
    """Health check response (UDC compliant)."""

    status: Literal["active", "inactive", "error"]
    service: str = "verifier"
    version: str = "1.0.0"
    checks: Dict[str, Any]


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
    target: str = "verifier"
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
