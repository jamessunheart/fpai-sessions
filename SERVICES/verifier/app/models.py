"""Models for Verifier Service."""
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    MINOR = "minor"


class PhaseStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MINOR_ISSUES = "MINOR_ISSUES"
    SKIPPED = "SKIPPED"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Decision(str, Enum):
    APPROVED = "APPROVED"
    APPROVED_WITH_NOTES = "APPROVED_WITH_NOTES"
    FIXES_REQUIRED = "FIXES_REQUIRED"


class Check(BaseModel):
    name: str
    status: str
    details: Optional[str] = None
    response: Optional[Dict[str, Any]] = None


class Issue(BaseModel):
    severity: IssueSeverity
    category: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    suggestion: Optional[str] = None


class PhaseResult(BaseModel):
    phase: str
    status: PhaseStatus
    duration_seconds: int
    checks: List[Check]


class VerificationSummary(BaseModel):
    critical_issues: int
    important_issues: int
    minor_issues: int
    tests_passing: str
    coverage_percent: Optional[int] = None


class VerificationReport(BaseModel):
    job_id: str
    droplet_name: str
    decision: Optional[Decision]
    phases: List[PhaseResult]
    critical_issues: List[Issue]
    important_issues: List[Issue]
    minor_issues: List[Issue]
    strengths: List[str]
    recommendations: List[str]
    summary: Optional[VerificationSummary] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class VerificationRequest(BaseModel):
    droplet_path: str
    droplet_name: str
    quick_mode: bool = False


class VerificationJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    droplet_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_duration_seconds: int = 180
