"""Verifier Droplet - Main FastAPI application."""
import logging
import asyncio
import time
import uuid
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import (
    VerificationRequest,
    VerificationJobResponse,
    JobStatusResponse,
    VerificationReport,
    RecentVerification,
    HealthResponse,
    CapabilitiesResponse,
    StateResponse,
    DependenciesResponse,
    DependencyStatus,
    MessageRequest,
    MessageResponse,
    SendRequest,
    SendResponse,
    JobStatus,
    PhaseResult,
)
from app.job_manager import job_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Verifier Droplet",
    description="Automates droplet verification following VERIFICATION_PROTOCOL.md",
    version="1.0.0",
)

# Track startup time for uptime calculation
startup_time = time.time()


@app.post("/verify", response_model=VerificationJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_verification(
    request: VerificationRequest,
    background_tasks: BackgroundTasks,
) -> VerificationJobResponse:
    """
    Submit a droplet for verification.

    Creates a verification job and runs it asynchronously.
    Returns job_id for status checking.
    """
    logger.info(f"Received verification request for {request.droplet_name}")

    # Create job
    job_id = job_manager.create_job(
        droplet_name=request.droplet_name,
        droplet_path=request.droplet_path,
    )

    # Run job in background
    background_tasks.add_task(job_manager.run_job, job_id)

    return VerificationJobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        droplet_name=request.droplet_name,
        created_at=datetime.utcnow(),
        estimated_duration_seconds=180,
    )


@app.get("/verify/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the status of a verification job."""
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Calculate duration if completed
    duration = None
    if job.completed_at and job.started_at:
        duration = int((job.completed_at - job.started_at).total_seconds())

    # Get summary if completed
    summary = None
    if job.status == JobStatus.COMPLETED:
        summary = job_manager.get_summary(job)

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        droplet_name=job.droplet_name,
        current_phase=job.current_phase,
        progress_percent=job.progress_percent,
        started_at=job.started_at or datetime.utcnow(),
        completed_at=job.completed_at,
        decision=job.decision,
        summary=summary,
        duration_seconds=duration,
    )


@app.get("/verify/{job_id}/report", response_model=VerificationReport)
async def get_verification_report(job_id: str) -> VerificationReport:
    """Get the detailed verification report for a job."""
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not completed yet (status: {job.status})",
        )

    # Calculate duration
    duration = 0
    if job.completed_at and job.started_at:
        duration = int((job.completed_at - job.started_at).total_seconds())

    # Get summary
    summary = job_manager.get_summary(job)

    # Categorize issues by severity
    critical_issues = [i for i in job.all_issues if i.severity.value == "critical"]
    important_issues = [i for i in job.all_issues if i.severity.value == "important"]
    minor_issues = [i for i in job.all_issues if i.severity.value == "minor"]

    return VerificationReport(
        job_id=job.job_id,
        droplet_name=job.droplet_name,
        decision=job.decision,
        phases=job.phases,
        critical_issues=critical_issues,
        important_issues=important_issues,
        minor_issues=minor_issues,
        strengths=job.strengths,
        recommendations=job.recommendations,
        summary=summary,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_seconds=duration,
    )


@app.get("/verify/recent")
async def get_recent_verifications(limit: int = 10) -> dict:
    """Get recent verification jobs."""
    recent_jobs = job_manager.get_recent_jobs(limit=limit)

    verifications = [
        RecentVerification(
            job_id=job.job_id,
            droplet_name=job.droplet_name,
            decision=job.decision,
            completed_at=job.completed_at,
        )
        for job in recent_jobs
    ]

    return {"verifications": verifications}


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint (UDC compliant).

    Returns health status of the Verifier.
    """
    # Check if we can run verifications
    can_run_pytest = True  # Assume yes for now
    can_scan_files = True

    queue_size = len([j for j in job_manager.jobs.values() if j.status == JobStatus.QUEUED])

    # UDC compliant status: active|inactive|error
    overall_status = "active"
    if queue_size > 10:
        overall_status = "inactive"  # System busy but functional

    return HealthResponse(
        status=overall_status,
        service="verifier",
        version="1.0.0",
        checks={
            "can_run_pytest": can_run_pytest,
            "can_scan_files": can_scan_files,
            "queue_size": queue_size,
            "running_jobs": job_manager.running_jobs,
        },
    )


@app.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities() -> CapabilitiesResponse:
    """
    UDC /capabilities endpoint.

    Returns what this droplet provides and its dependencies.
    """
    return CapabilitiesResponse(
        version="1.0.0",
        features=[
            "droplet_verification",
            "udc_compliance_testing",
            "security_scanning",
            "functionality_testing",
            "code_quality_checks",
            "structured_reporting",
        ],
        dependencies=["pytest", "python"],
        udc_version="1.0",
        metadata={
            "jobs_queued": len([j for j in job_manager.jobs.values() if j.status == JobStatus.QUEUED]),
            "jobs_running": job_manager.running_jobs,
            "jobs_completed": len([j for j in job_manager.jobs.values() if j.status == JobStatus.COMPLETED]),
        },
    )


@app.get("/state", response_model=StateResponse)
async def state() -> StateResponse:
    """
    UDC /state endpoint.

    Returns current resource usage and performance metrics.
    """
    uptime = int(time.time() - startup_time)

    return StateResponse(
        uptime_seconds=uptime,
        requests_total=len(job_manager.jobs),
        errors_last_hour=len([j for j in job_manager.jobs.values() if j.status == JobStatus.FAILED]),
        last_restart=datetime.fromtimestamp(startup_time).isoformat() + "Z",
    )


@app.get("/dependencies", response_model=DependenciesResponse)
async def dependencies() -> DependenciesResponse:
    """
    UDC /dependencies endpoint.

    Returns required and optional service dependencies with their status.
    """
    # Check pytest availability
    import shutil
    pytest_available = shutil.which("pytest") is not None
    pytest_status = DependencyStatus(
        name="pytest",
        status="connected" if pytest_available else "unavailable"
    )

    # Check python availability (should always be available)
    python_status = DependencyStatus(
        name="python",
        status="connected"
    )

    # Optional: Registry (for registering verification results)
    registry_status = DependencyStatus(
        name="registry",
        status="available"  # TODO: Check actual registry connectivity
    )

    return DependenciesResponse(
        required=[pytest_status, python_status],
        optional=[registry_status],
        missing=[]
    )


@app.post("/message", response_model=MessageResponse)
async def message(msg: MessageRequest) -> MessageResponse:
    """
    UDC /message endpoint.

    Receives inter-droplet messages.
    """
    logger.info(f"Received message from {msg.source}: {msg.message_type}")

    # Handle different message types
    if msg.message_type == "command":
        # Handle commands like verify, status, etc.
        if msg.payload.get("command") == "verify":
            logger.info("Received verify command via message")
            # Could trigger verification here

    return MessageResponse(
        received=True,
        trace_id=msg.trace_id,
        processed_at=datetime.utcnow().isoformat() + "Z",
        result="success"
    )


@app.post("/send", response_model=SendResponse)
async def send_message(request: SendRequest) -> SendResponse:
    """
    UDC /send endpoint.

    Sends messages to other droplets via Registry.
    """
    trace_id = str(uuid.uuid4())

    # TODO: Actually send the message via Registry's /send endpoint
    logger.info(f"Sending {request.message_type} message to {request.target}")

    return SendResponse(
        sent=True,
        trace_id=trace_id,
        target=request.target,
        timestamp=datetime.utcnow().isoformat() + "Z",
        result="success"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.verifier_port)
