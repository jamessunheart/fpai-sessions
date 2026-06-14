"""
WhiteRock Blessings Engine - Prometheus Metrics Endpoint
Exposes application metrics for monitoring.
"""

from fastapi import APIRouter, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from prometheus_client import (
    Counter, Gauge, Histogram, Info,
    generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
)
import time

from app.database import get_db
from app.models import Member, Tithe, BlessingRequest, CoraTransaction
from app.config import settings

router = APIRouter(tags=["Metrics"])

# Create a custom registry to avoid duplicate registration issues
REGISTRY = CollectorRegistry()

# Application info
APP_INFO = Info(
    "whiterock_app",
    "Application information",
    registry=REGISTRY
)
APP_INFO.info({
    "version": settings.APP_VERSION,
    "service": "whiterock-blessings-engine"
})

# Request metrics
REQUEST_COUNT = Counter(
    "whiterock_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY
)

REQUEST_DURATION = Histogram(
    "whiterock_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY
)

# Business metrics
MEMBERS_TOTAL = Gauge(
    "whiterock_members_total",
    "Total registered members",
    ["status"],
    registry=REGISTRY
)

TITHES_TOTAL = Counter(
    "whiterock_tithes_total_cents",
    "Total tithe amount in cents",
    registry=REGISTRY
)

BLESSINGS_BY_STATUS = Gauge(
    "whiterock_blessings_by_status",
    "Number of blessing requests by status",
    ["status"],
    registry=REGISTRY
)

CORA_CIRCULATION = Gauge(
    "whiterock_cora_circulation",
    "Total CORA in circulation",
    registry=REGISTRY
)

CORA_AVERAGE = Gauge(
    "whiterock_cora_average_per_member",
    "Average CORA per active member",
    registry=REGISTRY
)

CAPACITY_LEVEL = Gauge(
    "whiterock_capacity_level",
    "Community capacity level (high=3, medium=2, low=1, paused=0)",
    registry=REGISTRY
)


async def update_metrics(db: AsyncSession):
    """Update gauge metrics from database."""
    
    # Members count
    result = await db.execute(
        select(func.count(Member.id)).where(Member.is_active == True)
    )
    active_members = result.scalar_one() or 0
    MEMBERS_TOTAL.labels(status="active").set(active_members)
    
    result = await db.execute(
        select(func.count(Member.id)).where(Member.is_active == False)
    )
    inactive_members = result.scalar_one() or 0
    MEMBERS_TOTAL.labels(status="inactive").set(inactive_members)
    
    # CORA circulation
    result = await db.execute(
        select(func.sum(Member.cora_balance)).where(Member.is_active == True)
    )
    cora_total = result.scalar_one() or 0
    CORA_CIRCULATION.set(cora_total)
    
    # Average CORA
    if active_members > 0:
        CORA_AVERAGE.set(cora_total / active_members)
    else:
        CORA_AVERAGE.set(0)
    
    # Blessings by status
    blessing_statuses = [
        "draft", "pending", "committee_review", "info_requested",
        "approved", "denied", "disbursed", "closed"
    ]
    for status in blessing_statuses:
        result = await db.execute(
            select(func.count(BlessingRequest.id)).where(BlessingRequest.status == status)
        )
        count = result.scalar_one() or 0
        BLESSINGS_BY_STATUS.labels(status=status).set(count)
    
    # Capacity level
    from app.models import CommunityCapacity
    result = await db.execute(
        select(CommunityCapacity).order_by(CommunityCapacity.updated_at.desc()).limit(1)
    )
    capacity = result.scalar_one_or_none()
    if capacity:
        level_map = {"high": 3, "medium": 2, "low": 1, "paused": 0}
        CAPACITY_LEVEL.set(level_map.get(capacity.capacity_level, 0))


@router.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_db)):
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    # Update database-backed metrics
    await update_metrics(db)
    
    # Generate metrics output
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


# Middleware helper for tracking request metrics
class MetricsMiddleware:
    """Middleware to track request metrics."""
    
    @staticmethod
    def record_request(method: str, endpoint: str, status_code: int, duration: float):
        """Record a request in metrics."""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def record_tithe(amount_cents: int):
    """Record a tithe in metrics."""
    TITHES_TOTAL.inc(amount_cents)



