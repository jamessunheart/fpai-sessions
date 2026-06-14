"""Health and readiness endpoints."""
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service liveness probe")
async def health_check() -> dict[str, str]:
    """Return static information confirming the service is running."""

    return {
        "status": "ok",
        "service": settings.service_name,
        "environment": settings.environment,
        "version": settings.version,
    }
