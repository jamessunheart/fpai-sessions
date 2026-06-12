"""
UDC /capabilities endpoint
NO AUTHENTICATION REQUIRED per UDC spec
"""

from fastapi import APIRouter

from app.config import settings
from app.models.udc import CapabilitiesResponse

router = APIRouter()


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities():
    """
    UDC Compliant: Declared capabilities and features
    Lists all features this droplet supports
    """
    return {
        "version": settings.version,
        "udc_version": settings.udc_version,
        "features": [
            "multi-cloud-management",
            "digitalocean-api",
            "hetzner-api",
            "vultr-api",
            "unified-listing",
            "power-management",
            "jwt-jwks-authentication",
            "structured-logging",
            "event-tracking",
            "auto-registry-registration",
            "prometheus-metrics",
            "instance-creation",
            "instance-deletion"
        ],
        "dependencies": ["registry"],
        "backward_compatible": ["0.9"]
    }
