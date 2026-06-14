"""
Deployer - FastAPI Application
Sacred Loop Steps 6-7 - Automated Deployment + Registry Registration
"""

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import uuid
from datetime import datetime

from .config import settings
from .models import (
    DeployRequest,
    DeployJobResponse,
    DeployJobStatus,
    DeploymentStatus
)
from .deployment_orchestrator import DeploymentOrchestrator

# Initialize application
app = FastAPI(
    title="Deployer",
    description="Automated deployment and registry registration - Completes Sacred Loop Steps 6-7",
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

# Deployment orchestrator
orchestrator = DeploymentOrchestrator()

# Track active deployment jobs
active_jobs: Dict[str, DeployJobStatus] = {}


@app.post("/deploy", response_model=DeployJobResponse)
async def submit_deployment(
    request: DeployRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a service for deployment.

    Deploys service to production server and registers with Registry.
    """
    deploy_job_id = f"deploy-{uuid.uuid4().hex[:8]}"

    # Create job status
    job_status = DeployJobStatus(
        deploy_job_id=deploy_job_id,
        service_name=request.service_name,
        service_path=request.service_path,
        status=DeploymentStatus.PENDING,
        service_port=request.service_port,
        droplet_id=request.droplet_id,
        started_at=datetime.now()
    )

    # Store job
    active_jobs[deploy_job_id] = job_status

    # Start deployment in background
    background_tasks.add_task(
        execute_deployment,
        deploy_job_id=deploy_job_id,
        request=request
    )

    response = DeployJobResponse(
        deploy_job_id=deploy_job_id,
        service_name=request.service_name,
        status=DeploymentStatus.PENDING
    )

    return response


async def execute_deployment(deploy_job_id: str, request: DeployRequest):
    """Execute deployment in background"""
    job_status = active_jobs[deploy_job_id]

    # Execute deployment
    updated_status = await orchestrator.execute_deployment(request, job_status)

    # Update stored status
    active_jobs[deploy_job_id] = updated_status


@app.get("/deploy/{deploy_job_id}", response_model=DeployJobStatus)
async def get_deployment_status(deploy_job_id: str):
    """Get status of a deployment job"""
    if deploy_job_id not in active_jobs:
        return {"error": "Job not found"}

    return active_jobs[deploy_job_id]


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Deployer",
        "version": "1.0.0",
        "description": "Automated deployment and registry registration",
        "sacred_loop_steps": ["6", "7"],
        "capabilities": [
            "SSH file transfer to production server",
            "Docker-based deployment",
            "Systemd-based deployment",
            "Automatic Registry registration",
            "Service health verification",
            "Complete Sacred Loop automation"
        ],
        "endpoints": {
            "/deploy": "Submit service for deployment",
            "/deploy/{job_id}": "Get deployment job status"
        },
        "server": {
            "host": settings.server_host,
            "deployment_method": settings.deployment_method,
            "registry_url": settings.registry_url
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    # Check SSH connectivity
    from .ssh_manager import SSHManager

    ssh_available = False
    try:
        with SSHManager() as ssh:
            ssh_available = ssh.client is not None
    except:
        pass

    # Check Registry connectivity
    from .registry_client import RegistryClient
    import httpx

    registry_available = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.registry_url}/health", timeout=3.0)
            registry_available = response.status_code == 200
    except:
        pass

    return {
        "status": "healthy",
        "service": "deployer",
        "version": "1.0.0",
        "dependencies": {
            "ssh_server": {
                "status": "available" if ssh_available else "unavailable",
                "host": settings.server_host
            },
            "registry": {
                "status": "available" if registry_available else "unavailable",
                "url": settings.registry_url
            }
        }
    }


@app.get("/capabilities")
async def capabilities():
    """UDC Capabilities endpoint"""
    return {
        "service": "deployer",
        "version": "1.0.0",
        "sacred_loop_steps": [6, 7],
        "deployment_methods": ["docker", "systemd"],
        "features": [
            "ssh_file_transfer",
            "docker_deployment",
            "registry_auto_registration",
            "health_verification",
            "rollback_support"
        ],
        "limits": {
            "max_concurrent_deployments": 5,
            "deployment_timeout_seconds": settings.deployment_timeout
        }
    }


@app.get("/state")
async def state():
    """UDC State endpoint"""
    active_count = sum(
        1 for job in active_jobs.values()
        if job.status in [DeploymentStatus.PENDING, DeploymentStatus.VALIDATING,
                         DeploymentStatus.TRANSFERRING, DeploymentStatus.BUILDING,
                         DeploymentStatus.STARTING, DeploymentStatus.REGISTERING]
    )

    completed_count = sum(
        1 for job in active_jobs.values()
        if job.status == DeploymentStatus.COMPLETED
    )

    failed_count = sum(
        1 for job in active_jobs.values()
        if job.status == DeploymentStatus.FAILED
    )

    return {
        "active_deployments": active_count,
        "completed_deployments": completed_count,
        "failed_deployments": failed_count,
        "total_jobs": len(active_jobs),
        "server_connected": True,  # TODO: Check actual SSH status
        "registry_connected": True  # TODO: Check actual Registry status
    }


@app.get("/dependencies")
async def dependencies():
    """UDC Dependencies endpoint"""
    return {
        "required": [
            {
                "name": "registry",
                "url": settings.registry_url,
                "purpose": "Service registration",
                "status": "required"
            },
            {
                "name": "ssh_server",
                "host": settings.server_host,
                "purpose": "Deployment target",
                "status": "required"
            }
        ],
        "optional": [
            {
                "name": "verifier",
                "url": settings.verifier_url,
                "purpose": "Pre-deployment validation",
                "status": "optional"
            }
        ]
    }


@app.post("/message")
async def message(payload: dict):
    """UDC Message endpoint"""
    return {
        "status": "received",
        "message": "Deployer message endpoint",
        "capabilities": ["deploy_request", "status_query", "health_check"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True
    )
