from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional

from app.models import (
    VerificationRequest,
    VerificationJobResponse,
    VerificationReport,
    JobStatus,
)
from app.job_manager import job_manager

router = APIRouter()


@router.post("/verify", response_model=VerificationJobResponse, status_code=202)
async def verify_droplet(
    request: VerificationRequest, background_tasks: BackgroundTasks
):
    """Submit a droplet for verification."""
    try:
        job_id = job_manager.create_job(request.droplet_name, request.droplet_path)
        
        # Run job in background
        background_tasks.add_task(job_manager.run_job, job_id)

        return VerificationJobResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            droplet_name=request.droplet_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{job_id}", response_model=dict)
async def get_job_status(job_id: str):
    """Get verification job status."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "droplet_name": job.droplet_name,
        "current_phase": job.current_phase,
        "progress_percent": job.progress_percent,
        "decision": job.decision,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


@router.get("/verify/{job_id}/report", response_model=VerificationReport)
async def get_job_report(job_id: str):
    """Get detailed verification report."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED and job.status != JobStatus.FAILED:
        raise HTTPException(status_code=409, detail="Verification not complete")

    # Categorize issues
    critical = [i for i in job.all_issues if i.severity == "critical"]
    important = [i for i in job.all_issues if i.severity == "important"]
    minor = [i for i in job.all_issues if i.severity == "minor"]

    summary = job_manager.get_summary(job)
    
    duration = 0
    if job.completed_at and job.started_at:
        duration = int((job.completed_at - job.started_at).total_seconds())

    return VerificationReport(
        job_id=job.job_id,
        droplet_name=job.droplet_name,
        decision=job.decision,
        phases=job.phases,
        critical_issues=critical,
        important_issues=important,
        minor_issues=minor,
        strengths=job.strengths,
        recommendations=job.recommendations,
        summary=summary,
        completed_at=job.completed_at,
        duration_seconds=duration,
    )


@router.get("/verify/recent", response_model=List[dict])
async def list_recent_jobs(limit: int = 10):
    """List recent verification jobs."""
    jobs = job_manager.get_recent_jobs(limit)
    return [
        {
            "job_id": j.job_id,
            "droplet_name": j.droplet_name,
            "status": j.status,
            "decision": j.decision,
            "completed_at": j.completed_at,
        }
        for j in jobs
    ]
