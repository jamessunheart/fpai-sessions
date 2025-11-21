"""
Autonomous Executor - Main FastAPI Application

This droplet enables TRUE self-optimization by accepting architect intent
and executing the entire Sacred Loop autonomously.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import time
from datetime import datetime, timedelta
import asyncio

from .models import (
    BuildRequest,
    BuildResponse,
    BuildProgress,
    BuildStatus,
    SacredLoopStep,
    ApprovalRequest,
    HealthResponse,
    CapabilitiesResponse,
    StepProgress,
    UDCHealthResponse,
    UDCCapabilitiesResponse,
    UDCStateResponse,
    UDCDependenciesResponse,
    DependencyStatus,
    UDCMessageRequest,
    UDCMessageResponse
)
from .config import settings
from .orchestrator import BuildOrchestrator
from .progress_tracker import ProgressTracker

# Initialize FastAPI app
app = FastAPI(
    title="Autonomous Executor API",
    description="Enables true self-optimization by executing Sacred Loop autonomously",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
start_time = time.time()
orchestrator = BuildOrchestrator()
progress_tracker = ProgressTracker()
active_websockets: Dict[str, List[WebSocket]] = {}


@app.post("/executor/build-droplet", response_model=BuildResponse)
async def build_droplet(request: BuildRequest, background_tasks: BackgroundTasks):
    """
    Initiate autonomous droplet build.

    This is the main entry point for TRUE self-optimization.
    Architect declares intent, system executes everything autonomously.
    """
    # Generate build ID
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    build_id = f"build-{request.droplet_id or 'auto'}-{timestamp}"

    # Initialize progress tracking
    progress = progress_tracker.create_build(
        build_id=build_id,
        droplet_id=request.droplet_id or 0,  # Auto-assign if not provided
        droplet_name=request.droplet_name or "auto-named",
        architect_intent=request.architect_intent
    )

    # Start autonomous build in background
    background_tasks.add_task(
        orchestrator.execute_autonomous_build,
        build_id=build_id,
        request=request,
        progress_tracker=progress_tracker
    )

    # Calculate estimated completion (2 hours)
    estimated_completion = datetime.utcnow() + timedelta(hours=2)

    return BuildResponse(
        build_id=build_id,
        status=BuildStatus.QUEUED,
        droplet_id=progress.droplet_id,
        droplet_name=progress.droplet_name,
        estimated_completion=estimated_completion,
        stream_url=f"ws://{settings.executor_host}:{settings.executor_port}/executor/builds/{build_id}/stream",
        status_url=f"http://{settings.executor_host}:{settings.executor_port}/executor/builds/{build_id}/status"
    )


@app.get("/executor/builds/{build_id}/status", response_model=BuildProgress)
async def get_build_status(build_id: str):
    """Get current status of a build"""
    progress = progress_tracker.get_progress(build_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    return progress


@app.websocket("/executor/builds/{build_id}/stream")
async def build_progress_stream(websocket: WebSocket, build_id: str):
    """
    WebSocket endpoint for real-time build progress streaming.

    Sends progress updates as they happen during the build.
    """
    await websocket.accept()

    # Register websocket
    if build_id not in active_websockets:
        active_websockets[build_id] = []
    active_websockets[build_id].append(websocket)

    try:
        # Send current progress immediately
        progress = progress_tracker.get_progress(build_id)
        if progress:
            await websocket.send_json(progress.model_dump(mode='json'))

        # Keep connection alive and send updates
        while True:
            await asyncio.sleep(5)  # Send updates every 5 seconds
            progress = progress_tracker.get_progress(build_id)
            if progress:
                await websocket.send_json(progress.model_dump(mode='json'))

                # Close if build complete
                if progress.status in [BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.CANCELLED]:
                    break

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        if build_id in active_websockets:
            active_websockets[build_id].remove(websocket)


@app.get("/executor/builds", response_model=List[BuildProgress])
async def list_builds(limit: int = 10, offset: int = 0):
    """List recent builds"""
    return progress_tracker.list_builds(limit=limit, offset=offset)


@app.post("/executor/builds/{build_id}/approve")
async def approve_checkpoint(build_id: str, request: ApprovalRequest):
    """Approve a build checkpoint (for checkpoint approval mode)"""
    progress = progress_tracker.get_progress(build_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    if request.approved:
        # Resume build
        await orchestrator.resume_build(build_id)
        return {"status": "approved", "message": "Build resuming"}
    else:
        # Cancel build
        progress_tracker.update_status(build_id, BuildStatus.CANCELLED)
        return {"status": "cancelled", "message": "Build cancelled by architect"}


@app.delete("/executor/builds/{build_id}")
async def cancel_build(build_id: str):
    """Cancel an in-progress build"""
    progress = progress_tracker.get_progress(build_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    if progress.status not in [BuildStatus.IN_PROGRESS, BuildStatus.QUEUED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel build in status: {progress.status}"
        )

    progress_tracker.update_status(build_id, BuildStatus.CANCELLED)
    return {"status": "cancelled", "build_id": build_id}


@app.post("/executor/builds/{build_id}/retry")
async def retry_build(build_id: str, background_tasks: BackgroundTasks, from_step: int = 1):
    """Retry a failed build from a specific step"""
    progress = progress_tracker.get_progress(build_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    # Reset to specified step
    progress_tracker.reset_to_step(build_id, from_step)

    # Restart build
    background_tasks.add_task(
        orchestrator.retry_build,
        build_id=build_id,
        from_step=from_step,
        progress_tracker=progress_tracker
    )

    return {"status": "retrying", "from_step": from_step}


@app.get("/executor/health", response_model=HealthResponse)
async def health_check():
    """UDC-compliant health check"""
    uptime = int(time.time() - start_time)

    # Check Claude API availability
    claude_available = bool(settings.anthropic_api_key)

    # Check GitHub API availability
    github_available = bool(settings.github_token)

    # Determine overall health
    if claude_available:
        status = "healthy"
    elif github_available:
        status = "degraded"
    else:
        status = "unhealthy"

    active_builds = len([
        p for p in progress_tracker.list_builds(limit=100)
        if p.status == BuildStatus.IN_PROGRESS
    ])

    total_completed = len([
        p for p in progress_tracker.list_builds(limit=1000)
        if p.status == BuildStatus.COMPLETED
    ])

    return HealthResponse(
        status=status,
        version="1.0.0",
        uptime_seconds=uptime,
        active_builds=active_builds,
        total_builds_completed=total_completed,
        claude_api_available=claude_available,
        github_api_available=github_available
    )


@app.get("/executor/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """UDC-compliant capabilities endpoint"""
    return CapabilitiesResponse(
        can_build_droplets=True,
        can_generate_specs=True,
        can_deploy=bool(settings.github_token),
        can_use_claude_api=bool(settings.anthropic_api_key),
        can_use_github_api=bool(settings.github_token),
        max_concurrent_builds=5,
        supported_approval_modes=["auto", "checkpoints", "final"]
    )


# ========================================
# UDC-Compliant Endpoints (TIER 0 Integration)
# ========================================

@app.get("/health", response_model=UDCHealthResponse)
async def udc_health():
    """UDC /health endpoint - Standard compliance"""
    uptime = int(time.time() - start_time)
    claude_available = bool(settings.anthropic_api_key)
    github_available = bool(settings.github_token)

    # UDC status: active, inactive, error
    if claude_available and github_available:
        status = "active"
    elif claude_available or github_available:
        status = "inactive"
    else:
        status = "error"

    return UDCHealthResponse(
        status=status,
        service="autonomous-executor",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/capabilities", response_model=UDCCapabilitiesResponse)
async def udc_capabilities():
    """UDC /capabilities endpoint - Standard compliance"""
    active_builds = len([
        p for p in progress_tracker.list_builds(limit=100)
        if p.status == BuildStatus.IN_PROGRESS
    ])

    return UDCCapabilitiesResponse(
        version="1.0.0",
        features=[
            "autonomous_droplet_building",
            "sacred_loop_execution",
            "spec_generation",
            "code_generation",
            "auto_deployment",
            "progress_streaming",
            "approval_workflows"
        ],
        dependencies=["claude_api", "github_api", "registry"],
        udc_version="1.0",
        metadata={
            "max_concurrent_builds": 5,
            "active_builds": active_builds,
            "approval_modes": ["auto", "checkpoints", "final"]
        }
    )


@app.get("/state", response_model=UDCStateResponse)
async def udc_state():
    """UDC /state endpoint - Standard compliance"""
    uptime = int(time.time() - start_time)
    total_builds = len(progress_tracker.list_builds(limit=1000))
    failed_builds = len([
        p for p in progress_tracker.list_builds(limit=100)
        if p.status == BuildStatus.FAILED
    ])
    active_builds = len([
        p for p in progress_tracker.list_builds(limit=100)
        if p.status == BuildStatus.IN_PROGRESS
    ])

    return UDCStateResponse(
        uptime_seconds=uptime,
        requests_total=total_builds,
        errors_last_hour=failed_builds,
        last_restart=datetime.fromtimestamp(start_time).isoformat() + "Z",
        resource_usage={
            "active_builds": active_builds,
            "websocket_connections": sum(len(ws) for ws in active_websockets.values())
        }
    )


@app.get("/dependencies", response_model=UDCDependenciesResponse)
async def udc_dependencies():
    """UDC /dependencies endpoint - Standard compliance"""
    claude_status = DependencyStatus(
        name="claude_api",
        status="connected" if settings.anthropic_api_key else "unavailable"
    )

    github_status = DependencyStatus(
        name="github_api",
        status="connected" if settings.github_token else "unavailable"
    )

    registry_status = DependencyStatus(
        name="registry",
        status="available"  # TODO: Check actual registry connectivity
    )

    return UDCDependenciesResponse(
        required=[claude_status, github_status],
        optional=[registry_status],
        missing=[]
    )


@app.post("/message", response_model=UDCMessageResponse)
async def udc_message(msg: UDCMessageRequest):
    """UDC /message endpoint - Standard compliance

    Handles inter-droplet messages for build coordination,
    status queries, and command execution.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Received UDC message from {msg.source}: {msg.message_type}")

    # Handle different message types
    if msg.message_type == "query":
        # Respond to queries about build status
        logger.info(f"Processing query: {msg.payload}")
    elif msg.message_type == "command":
        # Handle commands like trigger build, cancel build
        logger.info(f"Processing command: {msg.payload}")
    elif msg.message_type == "event":
        # Handle events from other droplets
        logger.info(f"Processing event: {msg.payload}")

    return UDCMessageResponse(
        received=True,
        trace_id=msg.trace_id,
        processed_at=datetime.utcnow().isoformat() + "Z",
        result="success"
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Autonomous Executor",
        "version": "1.0.0",
        "description": "Enables true self-optimization through autonomous Sacred Loop execution",
        "status": "operational",
        "endpoints": {
            "build": "POST /executor/build-droplet",
            "status": "GET /executor/builds/{build_id}/status",
            "stream": "WS /executor/builds/{build_id}/stream",
            "health": "GET /executor/health",
            "capabilities": "GET /executor/capabilities"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.executor_host,
        port=settings.executor_port,
        reload=True
    )
