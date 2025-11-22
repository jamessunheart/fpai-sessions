"""
UDC Health Endpoints - ALREADY FULLY COMPLIANT
Standard health check, capabilities, state, and dependencies endpoints

NOTE: These endpoints are public UDC endpoints that return Pydantic
models directly. They are exempt from middleware wrapping.
Add to middleware SKIP_WRAPPING: /health, /capabilities, /state, /dependencies
"""
from datetime import datetime
from fastapi import APIRouter
import structlog

from app.config import settings
from app.models.udc import (
    HealthResponse, CapabilitiesResponse,
    StateResponse, DependenciesResponse, DependencyInfo
)
from app.utils.helpers import get_process_metrics
from app.database import get_database_stats
from app.services.registry_client import get_registry_status

log = structlog.get_logger()

router = APIRouter()


# ============================================================================
# UDC ENDPOINTS (Public - No Auth Required - Already Compliant)
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    GET /health - UDC health check endpoint
    Returns current operational status
    
    NO CHANGES NEEDED: Already returns UDC-compliant Pydantic model
    """
    return HealthResponse(
        id=settings.droplet_id,
        name=settings.droplet_name,
        steward=settings.droplet_steward,
        status="active",
        endpoint=settings.droplet_endpoint,
        updated_at=datetime.utcnow(),
        message="All systems operational"
    )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """
    GET /capabilities - UDC capabilities endpoint
    Returns list of supported features
    
    NO CHANGES NEEDED: Already returns UDC-compliant Pydantic model
    """
    return CapabilitiesResponse(
        version=settings.app_version,
        features=[
            "task_routing",
            "droplet_discovery",
            "health_monitoring",
            "workflow_management",
            "real_time_updates",
            "task_recovery",
            "state_machine_management",
            "priority_queuing",
            "automatic_retry"
        ],
        dependencies=["registry"],
        udc_version="1.0"
    )


@router.get("/state", response_model=StateResponse)
async def get_state():
    """
    GET /state - UDC state endpoint
    Returns current system resource usage and metrics
    
    NO CHANGES NEEDED: Already returns UDC-compliant Pydantic model
    """
    # Get process metrics
    metrics = get_process_metrics()
    
    # Get database stats
    db_stats = await get_database_stats()
    
    return StateResponse(
        cpu_percent=metrics.get("cpu_percent", 0.0),
        memory_mb=int(metrics.get("memory_mb", 0)),
        uptime_seconds=metrics.get("uptime_seconds", 0),
        custom_metrics={
            "tasks_active": db_stats.get("active_tasks_count", 0),
            "tasks_pending": db_stats.get("tasks_count", 0) - db_stats.get("active_tasks_count", 0),
            "droplets_active": db_stats.get("active_droplets_count", 0),
            "droplets_total": db_stats.get("droplets_count", 0),
            "num_threads": metrics.get("num_threads", 0)
        }
    )


@router.get("/dependencies", response_model=DependenciesResponse)
async def get_dependencies():
    """
    GET /dependencies - UDC dependencies endpoint
    Returns status of upstream and downstream dependencies
    
    NO CHANGES NEEDED: Already returns UDC-compliant Pydantic model
    """
    # Check Registry status
    registry_status = await get_registry_status()
    
    required_deps = []
    optional_deps = []
    missing_deps = []
    
    # Registry (required)
    if registry_status.get("connected"):
        required_deps.append(
            DependencyInfo(
                id=3,
                name="Registry v2",
                status="connected",
                last_check=datetime.utcnow()
            )
        )
    else:
        missing_deps.append("Registry v2 (#3)")
    
    # Dashboard (optional)
    optional_deps.append(
        DependencyInfo(
            id=5,
            name="Dashboard",
            status="unknown",
            last_check=None
        )
    )
    
    # Verifier (optional)
    optional_deps.append(
        DependencyInfo(
            id=8,
            name="Verifier",
            status="unknown",
            last_check=None
        )
    )
    
    return DependenciesResponse(
        required=required_deps,
        optional=optional_deps,
        missing=missing_deps
    )