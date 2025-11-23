"""API route aggregation."""
from fastapi import APIRouter

from . import health, missions, telemetry

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(telemetry.router)
api_router.include_router(missions.router)

__all__ = ("api_router",)
