from fastapi import APIRouter, Depends
from typing import Dict, Any
from ...models.udc import HealthResponse, CapabilitiesResponse, StateResponse, DependenciesResponse, DependencyInfo
from ...config import settings
from ...utils.metrics import metrics
from ...utils.auth import verify_jwt_token

router = APIRouter(tags=["UDC Core"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """UDC-compliant health check endpoint"""
    return HealthResponse(
        id=settings.droplet_id,
        name=settings.droplet_name,
        steward=settings.droplet_steward,
        status="active",
        endpoint=settings.droplet_url,
        updated_at=metrics.get_current_timestamp()
    )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Declare droplet capabilities"""
    return CapabilitiesResponse(
        version="1.0.0",
        features=[
            "udc_compliance",
            "health_monitoring",
            "message_handling",
            "metrics_collection"
        ],
        dependencies=["registry", "orchestrator"],
        udc_version="1.0",
        metadata={
            "build_date": "2025-11-08",
            "commit_hash": "dev",
            "environment": settings.environment
        }
    )


@router.get("/state", response_model=StateResponse)
async def state(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Report resource usage and performance metrics"""
    state_metrics = metrics.get_state_metrics()
    return StateResponse(**state_metrics)


@router.get("/dependencies", response_model=DependenciesResponse)
async def dependencies(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """List other droplets this one connects to"""
    return DependenciesResponse(
        required=[
            DependencyInfo(id=1, name="Registry", status="connected"),
            DependencyInfo(id=10, name="Orchestrator", status="connected")
        ],
        optional=[
            DependencyInfo(id=2, name="Dashboard", status="available")
        ],
        missing=[]
    )