"""Data models for Deployer"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class DeploymentStatus(str, Enum):
    """Status of deployment"""
    PENDING = "pending"
    VALIDATING = "validating"
    TRANSFERRING = "transferring"
    BUILDING = "building"
    STARTING = "starting"
    REGISTERING = "registering"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class DeploymentMethod(str, Enum):
    """Deployment method"""
    DOCKER = "docker"
    SYSTEMD = "systemd"
    MANUAL = "manual"


class DeployRequest(BaseModel):
    """Request to deploy a service"""
    service_path: str  # Local path to service
    service_name: str  # Name of service
    droplet_id: Optional[int] = None  # Droplet ID (auto-assigned if None)
    service_port: int  # Port service will run on
    verification_job_id: Optional[str] = None  # Verifier job ID (optional)
    deployment_method: DeploymentMethod = DeploymentMethod.DOCKER
    environment_vars: Dict[str, str] = Field(default_factory=dict)
    auto_register: bool = True  # Register with Registry after deployment


class DeploymentPhase(BaseModel):
    """One phase of deployment"""
    phase: str
    status: str  # success, failed, skipped
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    details: str = ""
    error: Optional[str] = None


class RegistrationInfo(BaseModel):
    """Registry registration details"""
    droplet_id: int
    service_name: str
    endpoint: str
    registered_at: datetime
    registry_response: Optional[Dict[str, Any]] = None


class DeployJobResponse(BaseModel):
    """Response when deployment job is created"""
    deploy_job_id: str
    service_name: str
    status: DeploymentStatus
    created_at: datetime = Field(default_factory=datetime.now)


class DeployJobStatus(BaseModel):
    """Status of a deployment job"""
    deploy_job_id: str
    service_name: str
    service_path: str
    status: DeploymentStatus
    droplet_id: Optional[int] = None
    service_port: int
    service_url: Optional[str] = None

    # Phases
    phases: List[DeploymentPhase] = Field(default_factory=list)

    # Registration
    registration: Optional[RegistrationInfo] = None

    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    # Result
    success: bool = False
    error: Optional[str] = None
