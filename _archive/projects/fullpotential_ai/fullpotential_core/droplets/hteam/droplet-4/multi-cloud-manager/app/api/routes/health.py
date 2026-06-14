"""
UDC /health endpoint
NO AUTHENTICATION REQUIRED per UDC spec
"""

from datetime import datetime
from fastapi import APIRouter

from app.config import settings
from app.models.udc import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    """
    UDC Compliant: Health status endpoint
    Returns droplet identification and status
    """
    return {
        "id": settings.droplet_id,
        "name": settings.droplet_name,
        "steward": settings.steward,
        "status": "active",
        "endpoint": f"https://{settings.droplet_domain}",
        "updated_at": datetime.utcnow().isoformat(),
        "version": settings.version,
        "dependencies": ["registry"]
    }
