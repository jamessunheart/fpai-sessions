"""
Jobs API Router
Handles job posting, application management, and AI screening
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import json
from pathlib import Path
import uuid
import logging
from app.services.hiring_coordinator import hiring_coordinator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs")

# Data storage path
import os
# Use local data directory instead of /app/data (which is read-only)
DATA_PATH = Path(os.getenv("DATA_PATH", str(Path(__file__).parent.parent.parent / "data")))
JOBS_FILE = DATA_PATH / "jobs.json"
APPLICATIONS_FILE = DATA_PATH / "applications.json"

# Ensure data directory exists
DATA_PATH.mkdir(parents=True, exist_ok=True)
if not JOBS_FILE.exists():
    JOBS_FILE.write_text("[]")
if not APPLICATIONS_FILE.exists():
    APPLICATIONS_FILE.write_text("[]")


class JobPost(BaseModel):
    """Job posting model"""
    title: str
    description: str
    requirements: List[str]
    responsibilities: List[str]
    budget: float
    duration: str
    skills: List[str]
    remote: bool = True
    delegation_id: Optional[str] = None


class Application(BaseModel):
    """Job application model"""
    job_id: str
    name: str
    email: str
    portfolio_url: Optional[str] = None
    cover_letter: str
    experience_years: int
    relevant_skills: List[str]
    availability: str


@router.post("/post")
async def post_job(job: JobPost) -> Dict:
    """
    Post a new job (called by AI or admin)

    Args:
        job: Job posting details

    Returns:
        Created job with ID and public URL
    """
    try:
        # Load existing jobs
        jobs = json.loads(JOBS_FILE.read_text())

        # Create job with ID
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            **job.dict(),
            "posted_at": datetime.utcnow().isoformat(),
            "status": "open",
            "applications_count": 0
        }

        jobs.append(job_data)
        JOBS_FILE.write_text(json.dumps(jobs, indent=2))

        logger.info(f"✅ Job posted: {job.title} (ID: {job_id})")

        return {
            "status": "success",
            "job_id": job_id,
            "url": f"http://198.54.123.234:8008/jobs/{job_id}",
            "job": job_data
        }

    except Exception as e:
        logger.error(f"Error posting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_jobs(status: str = "open") -> Dict:
    """
    List all jobs

    Args:
        status: Filter by status (open, closed, all)

    Returns:
        List of jobs
    """
    try:
        jobs = json.loads(JOBS_FILE.read_text())

        if status != "all":
            jobs = [j for j in jobs if j["status"] == status]

        # Sort by posted date (newest first)
        jobs.sort(key=lambda x: x["posted_at"], reverse=True)

        return {
            "status": "success",
            "count": len(jobs),
            "jobs": jobs
        }

    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
async def get_job(job_id: str) -> Dict:
    """
    Get specific job details

    Args:
        job_id: Job ID

    Returns:
        Job details
    """
    try:
        jobs = json.loads(JOBS_FILE.read_text())
        job = next((j for j in jobs if j["id"] == job_id), None)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return {
            "status": "success",
            "job": job
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def submit_application(application: Application) -> Dict:
    """
    Submit job application

    Args:
        application: Application details

    Returns:
        Application confirmation with screening status
    """
    try:
        # Verify job exists
        jobs = json.loads(JOBS_FILE.read_text())
        job = next((j for j in jobs if j["id"] == application.job_id), None)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Load applications
        applications = json.loads(APPLICATIONS_FILE.read_text())

        # Create application
        app_id = str(uuid.uuid4())
        app_data = {
            "id": app_id,
            **application.dict(),
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "ai_screening_status": "pending"
        }

        applications.append(app_data)
        APPLICATIONS_FILE.write_text(json.dumps(applications, indent=2))

        # Update job applications count
        for j in jobs:
            if j["id"] == application.job_id:
                j["applications_count"] = j.get("applications_count", 0) + 1
        JOBS_FILE.write_text(json.dumps(jobs, indent=2))

        logger.info(f"📝 Application received: {application.name} for {job['title']}")

        # Trigger AI screening (async)
        # This will be picked up by a background process

        return {
            "status": "success",
            "application_id": app_id,
            "message": "Application submitted successfully",
            "next_steps": [
                "AI will screen your application within 24 hours",
                "Top candidates will be contacted for interview",
                "You'll receive an email update within 2 business days"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/applications")
async def get_job_applications(job_id: str) -> Dict:
    """
    Get all applications for a job (admin endpoint)

    Args:
        job_id: Job ID

    Returns:
        List of applications
    """
    try:
        applications = json.loads(APPLICATIONS_FILE.read_text())
        job_apps = [a for a in applications if a["job_id"] == job_id]

        # Sort by submitted date
        job_apps.sort(key=lambda x: x["submitted_at"], reverse=True)

        return {
            "status": "success",
            "job_id": job_id,
            "count": len(job_apps),
            "applications": job_apps
        }

    except Exception as e:
        logger.error(f"Error getting applications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/close")
async def close_job(job_id: str) -> Dict:
    """
    Close a job posting

    Args:
        job_id: Job ID

    Returns:
        Updated job status
    """
    try:
        jobs = json.loads(JOBS_FILE.read_text())

        for job in jobs:
            if job["id"] == job_id:
                job["status"] = "closed"
                job["closed_at"] = datetime.utcnow().isoformat()
                break
        else:
            raise HTTPException(status_code=404, detail="Job not found")

        JOBS_FILE.write_text(json.dumps(jobs, indent=2))

        logger.info(f"🔒 Job closed: {job_id}")

        return {
            "status": "success",
            "message": "Job closed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hire")
async def hire_candidate(hire_request: Dict) -> Dict:
    """
    Hire a candidate and initiate onboarding workflow

    This endpoint:
    1. Validates application and job
    2. Generates onboarding materials
    3. Creates delegation in coordination system
    4. Prepares offer package
    5. Updates job and application status

    Args:
        hire_request: {
            "application_id": "uuid",
            "job_id": "uuid",
            "approved_by": "coordinator_name"
        }

    Returns:
        Complete hiring result with onboarding materials and delegation info
    """
    try:
        application_id = hire_request.get("application_id")
        job_id = hire_request.get("job_id")
        approved_by = hire_request.get("approved_by", "human_coordinator")

        if not application_id or not job_id:
            raise HTTPException(
                status_code=400,
                detail="Both application_id and job_id are required"
            )

        # Load application
        applications = json.loads(APPLICATIONS_FILE.read_text())
        application = next(
            (a for a in applications if a["id"] == application_id),
            None
        )

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        if application["job_id"] != job_id:
            raise HTTPException(
                status_code=400,
                detail="Application does not match job_id"
            )

        # Load job
        jobs = json.loads(JOBS_FILE.read_text())
        job = next((j for j in jobs if j["id"] == job_id), None)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Execute hiring workflow
        logger.info(f"🎯 Initiating hire: {application['name']} for {job['title']}")

        hire_result = await hiring_coordinator.hire_candidate(
            application=application,
            job=job,
            approved_by=approved_by
        )

        if hire_result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Hiring failed: {hire_result.get('error')}"
            )

        # Update application status
        for app in applications:
            if app["id"] == application_id:
                app["status"] = "hired"
                app["hired_at"] = datetime.utcnow().isoformat()
                app["delegation_id"] = hire_result.get("delegation_id")

        APPLICATIONS_FILE.write_text(json.dumps(applications, indent=2))

        # Update job status
        for j in jobs:
            if j["id"] == job_id:
                j["status"] = "filled"
                j["hired_candidate"] = application["name"]
                j["hired_at"] = datetime.utcnow().isoformat()

        JOBS_FILE.write_text(json.dumps(jobs, indent=2))

        logger.info(f"✅ Hired: {application['name']} - Delegation: {hire_result.get('delegation_id')}")

        return {
            "status": "success",
            "message": f"Successfully hired {application['name']}",
            **hire_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error hiring candidate: {e}")
        raise HTTPException(status_code=500, detail=str(e))
