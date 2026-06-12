"""
Jobs Service - Sovereign Job Board
Full Potential AI autonomous recruitment platform
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path
import logging
import time
from datetime import datetime
from app.udc_models import (
    UDCHealthResponse,
    UDCCapabilitiesResponse,
    UDCStateResponse,
    UDCDependenciesResponse,
    DependencyStatus,
    UDCMessageRequest,
    UDCMessageResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Full Potential Jobs",
    description="Sovereign job board for autonomous recruitment",
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

# Mount static files and templates
static_path = Path(__file__).parent / "static"
templates_path = Path(__file__).parent / "templates"

static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
templates = Jinja2Templates(directory=str(templates_path))

# Import routers
from app.routers import jobs_api, jobs_web

app.include_router(jobs_api.router, tags=["Jobs API"])
app.include_router(jobs_web.router, tags=["Jobs Web"])

# Track startup time for uptime calculation
start_time = time.time()


# ========================================
# UDC-Compliant Endpoints (TIER 1 Integration)
# ========================================

@app.get("/health", response_model=UDCHealthResponse)
async def health():
    """UDC /health endpoint - Standard compliance"""
    return UDCHealthResponse(
        status="active",  # Jobs service is operational
        service="jobs",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/capabilities", response_model=UDCCapabilitiesResponse)
async def capabilities():
    """UDC /capabilities endpoint - Standard compliance"""
    return UDCCapabilitiesResponse(
        version="1.0.0",
        features=[
            "job_board",
            "ai_screening",
            "ai_interviews",
            "labor_coordination",
            "milestone_verification",
            "social_media_recruitment",
            "helper_onboarding"
        ],
        dependencies=["claude_api", "database"],
        udc_version="1.0",
        metadata={
            "recruitment_automation": True,
            "hiring_time_reduction": "95%"
        }
    )


@app.get("/state", response_model=UDCStateResponse)
async def state():
    """UDC /state endpoint - Standard compliance"""
    uptime = int(time.time() - start_time)
    return UDCStateResponse(
        uptime_seconds=uptime,
        requests_total=0,  # TODO: Track requests
        errors_last_hour=0,  # TODO: Track errors
        last_restart=datetime.fromtimestamp(start_time).isoformat() + "Z",
        resource_usage={
            "active_jobs": 0,  # TODO: Get from database
            "pending_applications": 0
        }
    )


@app.get("/dependencies", response_model=UDCDependenciesResponse)
async def dependencies():
    """UDC /dependencies endpoint - Standard compliance"""
    claude_status = DependencyStatus(
        name="claude_api",
        status="available"  # TODO: Check actual Claude API connectivity
    )

    db_status = DependencyStatus(
        name="database",
        status="connected"  # TODO: Check actual database connectivity
    )

    registry_status = DependencyStatus(
        name="registry",
        status="available"  # TODO: Check actual registry connectivity
    )

    return UDCDependenciesResponse(
        required=[db_status],
        optional=[claude_status, registry_status],
        missing=[]
    )


@app.post("/message", response_model=UDCMessageResponse)
async def message(msg: UDCMessageRequest):
    """UDC /message endpoint - Standard compliance

    Handles inter-droplet messages for job coordination,
    recruitment queries, and helper management.
    """
    logger.info(f"Received UDC message from {msg.source}: {msg.message_type}")

    # Handle different message types
    if msg.message_type == "query":
        # Respond to queries about jobs, applicants
        logger.info(f"Processing query: {msg.payload}")
    elif msg.message_type == "command":
        # Handle commands like post_job, screen_candidate
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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - redirect to jobs"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/jobs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8008,
        reload=True,
        log_level="info"
    )
