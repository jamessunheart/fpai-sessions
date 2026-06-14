"""
WhiteRock Blessings Engine - Routes
"""

from app.routes.health import router as health_router
from app.routes.members import router as members_router
from app.routes.tithes import router as tithes_router
from app.routes.cora import router as cora_router
from app.routes.service import router as service_router
from app.routes.blessings import router as blessings_router
from app.routes.reports import router as reports_router
from app.routes.audit import router as audit_router
from app.routes.capacity import router as capacity_router
from app.routes.metrics import router as metrics_router

__all__ = [
    "health_router",
    "members_router", 
    "tithes_router",
    "cora_router",
    "service_router",
    "blessings_router",
    "reports_router",
    "audit_router",
    "capacity_router",
    "metrics_router"
]
