"""
UDC /dependencies endpoint
Lists connected droplets and dependencies
"""

from fastapi import APIRouter, Depends

from app.models.udc import DependenciesResponse, DependencyInfo
from app.utils.auth import verify_jwt_token
from app.utils.state import connected_droplets

router = APIRouter()


@router.get("/dependencies", response_model=DependenciesResponse)
async def dependencies(token_data: dict = Depends(verify_jwt_token)):
    """
    UDC Compliant: Lists required and optional dependencies
    Shows which droplets this one connects to
    """
    return {
        "required": [
            DependencyInfo(id=18, name="Registry v2", status="connected"),
            DependencyInfo(id=10, name="Orchestrator", status="connected")
        ],
        "optional": [
            DependencyInfo(id=2, name="Dashboard", status="available")
        ],
        "connected": list(connected_droplets)
    }
