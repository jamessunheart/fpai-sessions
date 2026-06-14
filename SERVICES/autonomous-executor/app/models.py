"""Data models for Autonomous Executor"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime
from enum import Enum


class ApprovalMode(str, Enum):
    """Build approval modes"""
    AUTO = "auto"  # No human approval needed
    CHECKPOINTS = "checkpoints"  # Approve at major milestones
    FINAL = "final"  # Approve only before deployment


class BuildStatus(str, Enum):
    """Build status states"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class SacredLoopStep(str, Enum):
    """Sacred Loop steps"""
    INTENT = "intent"
    SPEC_GENERATION = "spec_generation"
    COORDINATOR_PACKAGE = "coordinator_package"
    APPRENTICE_BUILD = "apprentice_build"
    VERIFIER = "verifier"
    DEPLOYER = "deployer"
    REGISTRY_UPDATE = "registry_update"
    COMPLETE = "complete"


class BuildRequest(BaseModel):
    """Request to build a new droplet autonomously"""
    architect_intent: str = Field(..., description="Architect's intent for the droplet")
    droplet_id: Optional[int] = Field(None, description="Droplet ID (auto-assigned if not provided)")
    droplet_name: Optional[str] = Field(None, description="Droplet name (derived from intent if not provided)")
    approval_mode: ApprovalMode = Field(ApprovalMode.FINAL, description="When to require human approval")
    notify_channels: List[str] = Field(default_factory=list, description="Notification channels (slack, email)")
    auto_deploy: bool = Field(True, description="Automatically deploy after successful build")


class StepProgress(BaseModel):
    """Progress for a single Sacred Loop step"""
    step: SacredLoopStep
    step_number: int
    name: str
    status: Literal["pending", "in_progress", "completed", "failed"]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    details: dict = Field(default_factory=dict)
    error: Optional[str] = None


class BuildProgress(BaseModel):
    """Overall build progress"""
    build_id: str
    droplet_id: int
    droplet_name: str
    status: BuildStatus
    current_step: SacredLoopStep
    current_step_number: int
    progress_percent: int
    started_at: datetime
    estimated_completion: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps: List[StepProgress]
    files_created: List[str] = Field(default_factory=list)
    repository_path: Optional[str] = None
    repository_url: Optional[str] = None
    deployment_url: Optional[str] = None


class BuildResponse(BaseModel):
    """Response after initiating a build"""
    build_id: str
    status: BuildStatus
    droplet_id: int
    droplet_name: str
    estimated_completion: Optional[datetime]
    stream_url: str
    status_url: str


class ApprovalRequest(BaseModel):
    """Request to approve a checkpoint"""
    approved: bool
    feedback: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    uptime_seconds: int
    active_builds: int
    total_builds_completed: int
    claude_api_available: bool
    github_api_available: bool


class CapabilitiesResponse(BaseModel):
    """Capabilities response"""
    can_build_droplets: bool
    can_generate_specs: bool
    can_deploy: bool
    can_use_claude_api: bool
    can_use_github_api: bool
    max_concurrent_builds: int
    supported_approval_modes: List[str]


# UDC-Compliant Models

class UDCHealthResponse(BaseModel):
    """UDC /health endpoint response"""
    status: Literal["active", "inactive", "error"]
    service: str = "autonomous-executor"
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
    target: str = "autonomous-executor"
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
