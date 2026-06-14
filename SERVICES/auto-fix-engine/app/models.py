"""Data models for Auto-Fix Engine"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class IssueType(str, Enum):
    """Types of issues that can be fixed"""
    STARTUP_FAILURE = "startup_failure"
    TEST_FAILURE = "test_failure"
    IMPORT_ERROR = "import_error"
    DEPENDENCY_MISSING = "dependency_missing"
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    CONFIGURATION = "configuration"


class FixStatus(str, Enum):
    """Status of a fix attempt"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPLIED = "applied"
    FAILED = "failed"
    VERIFIED = "verified"


class Issue(BaseModel):
    """An issue found by Verifier"""
    type: IssueType
    severity: str  # critical, important, minor
    description: str
    phase: str  # Which verification phase found it
    details: Optional[Dict[str, Any]] = None


class Fix(BaseModel):
    """A fix to be applied"""
    issue: Issue
    fix_type: str  # code_change, dependency_add, config_update
    description: str
    files_to_modify: List[str] = Field(default_factory=list)
    changes: Dict[str, str] = Field(default_factory=dict)  # file_path -> new_content
    commands: List[str] = Field(default_factory=list)  # Shell commands to run
    reasoning: str = ""


class FixRequest(BaseModel):
    """Request to auto-fix a service"""
    droplet_path: str
    droplet_name: str
    verification_job_id: str
    max_iterations: int = 3


class FixIteration(BaseModel):
    """One iteration of fix attempt"""
    iteration: int
    issues_found: List[Issue]
    fixes_attempted: List[Fix]
    verification_result: Optional[str] = None  # APPROVED, FIXES_REQUIRED, FAILED
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class FixJobResponse(BaseModel):
    """Response when fix job is created"""
    fix_job_id: str
    droplet_name: str
    status: FixStatus
    max_iterations: int
    created_at: datetime = Field(default_factory=datetime.now)


class FixJobStatus(BaseModel):
    """Status of a fix job"""
    fix_job_id: str
    droplet_name: str
    status: FixStatus
    current_iteration: int
    max_iterations: int
    iterations: List[FixIteration]
    final_decision: Optional[str] = None  # APPROVED, FIXES_REQUIRED, ABANDONED
    total_fixes_applied: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
