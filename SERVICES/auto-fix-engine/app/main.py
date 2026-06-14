"""
Auto-Fix Engine - FastAPI Application
Sacred Loop Step 5.5 - Automatic Issue Resolution
"""

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import uuid

from .config import settings
from .models import FixRequest, FixJobResponse, FixJobStatus, FixStatus
from .auto_fix_loop import AutoFixLoop

# Initialize application
app = FastAPI(
    title="Auto-Fix Engine",
    description="Automatically fixes issues found by Verifier - completes the Sacred Loop",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-fix loop
auto_fix_loop = AutoFixLoop()

# Track active fix jobs
active_jobs: Dict[str, FixJobStatus] = {}


@app.post("/fix", response_model=FixJobResponse)
async def submit_fix_job(
    request: FixRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a service for auto-fixing.

    Takes a Verifier job ID and automatically fixes all issues found.
    """
    fix_job_id = f"fix-{uuid.uuid4().hex[:8]}"

    response = FixJobResponse(
        fix_job_id=fix_job_id,
        droplet_name=request.droplet_name,
        status=FixStatus.PENDING,
        max_iterations=request.max_iterations
    )

    # Start fix loop in background
    background_tasks.add_task(
        execute_fix_job,
        fix_job_id=fix_job_id,
        request=request
    )

    return response


async def execute_fix_job(fix_job_id: str, request: FixRequest):
    """Execute fix job in background"""
    status = await auto_fix_loop.execute_fix_loop(
        droplet_path=request.droplet_path,
        droplet_name=request.droplet_name,
        initial_verification_job_id=request.verification_job_id,
        max_iterations=request.max_iterations
    )

    # Store result
    active_jobs[fix_job_id] = status


@app.get("/fix/{fix_job_id}", response_model=FixJobStatus)
async def get_fix_status(fix_job_id: str):
    """Get status of a fix job"""
    if fix_job_id not in active_jobs:
        return {"error": "Job not found"}

    return active_jobs[fix_job_id]


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Auto-Fix Engine",
        "version": "1.0.0",
        "description": "Automatically fixes issues found by Verifier",
        "sacred_loop_step": "5.5",
        "capabilities": [
            "Analyzes Verifier reports",
            "Generates fixes using Claude API",
            "Applies fixes automatically",
            "Re-verifies until APPROVED",
            "Completes the Sacred Loop"
        ],
        "endpoints": {
            "/fix": "Submit service for auto-fixing",
            "/fix/{job_id}": "Get fix job status"
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "auto-fix-engine",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True
    )
