"""
WhiteRock Blessings Engine - UDC Health Endpoints
Standard UDC endpoints for service registry integration.
"""

import time
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from app.database import get_db
from app.config import settings
from app.models import Member, BlessingRequest, CommunityCapacity, CoraDecayEvent
from app.schemas import (
    HealthResponse, CapabilitiesResponse, StateResponse,
    DependenciesResponse, DependencyStatus, ServiceStatusEnum
)

router = APIRouter(tags=["UDC"])

# Track startup time for uptime calculation
START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    UDC Health Check Endpoint.
    Returns service health status.
    """
    # Check database connection
    db_connected = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_connected = False
    
    status = ServiceStatusEnum.ACTIVE if db_connected else ServiceStatusEnum.ERROR
    
    return HealthResponse(
        status=status,
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        uptime_seconds=time.time() - START_TIME,
        database_connected=db_connected
    )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities():
    """
    UDC Capabilities Endpoint.
    Declares features and integrations.
    """
    return CapabilitiesResponse(
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        features=[
            "member_management",
            "tithe_processing",
            "cora_vitality_credits",
            "cora_decay_system",
            "blessing_requests",
            "blessing_state_machine",
            "vendor_direct_disbursement",
            "community_capacity_oracle",
            "compliance_audit_logging",
            "disclosure_tracking"
        ],
        integrations=[
            "stripe_payments",
            "sendgrid_email",
            "celery_background_tasks",
            "registry_service",
            "orchestrator_service"
        ],
        firewall_enforced=[
            "zero_treasury_integration",
            "zero_trading_integration",
            "zero_market_data_access",
            "cora_non_transferable",
            "cora_non_redeemable"
        ]
    )


@router.get("/state", response_model=StateResponse)
async def service_state(db: AsyncSession = Depends(get_db)):
    """
    UDC State Endpoint.
    Returns current resource usage and state metrics.
    """
    # Get total members
    result = await db.execute(
        select(func.count(Member.id)).where(Member.is_active == True)
    )
    total_members = result.scalar_one()
    
    # Get active blessing requests
    result = await db.execute(
        select(func.count(BlessingRequest.id)).where(
            BlessingRequest.status.in_([
                "pending", "committee_review", "info_requested", "approved"
            ])
        )
    )
    active_requests = result.scalar_one()
    
    # Get CORA in circulation
    result = await db.execute(
        select(func.sum(Member.cora_balance)).where(Member.is_active == True)
    )
    cora_circulation = result.scalar_one() or 0
    
    # Get capacity level
    result = await db.execute(
        select(CommunityCapacity).order_by(CommunityCapacity.updated_at.desc()).limit(1)
    )
    capacity = result.scalar_one_or_none()
    capacity_level = capacity.capacity_level if capacity else "high"
    
    # Get last decay run
    result = await db.execute(
        select(CoraDecayEvent.created_at).order_by(CoraDecayEvent.created_at.desc()).limit(1)
    )
    last_decay = result.scalar_one_or_none()
    
    return StateResponse(
        total_members=total_members,
        active_blessing_requests=active_requests,
        cora_in_circulation=cora_circulation,
        capacity_level=capacity_level,
        last_decay_run=last_decay
    )


@router.get("/dependencies", response_model=DependenciesResponse)
async def dependencies(db: AsyncSession = Depends(get_db)):
    """
    UDC Dependencies Endpoint.
    Returns status of external dependencies.
    """
    dependencies = []
    
    # Database
    db_status = "healthy"
    db_latency = None
    try:
        start = time.time()
        await db.execute(text("SELECT 1"))
        db_latency = (time.time() - start) * 1000
    except Exception:
        db_status = "unhealthy"
    
    dependencies.append(DependencyStatus(
        name="postgresql",
        status=db_status,
        latency_ms=db_latency
    ))
    
    # Stripe (check if configured)
    stripe_status = "configured" if settings.STRIPE_API_KEY else "not_configured"
    dependencies.append(DependencyStatus(
        name="stripe",
        status=stripe_status,
        latency_ms=None
    ))
    
    # SendGrid (check if configured)
    sendgrid_status = "configured" if settings.SENDGRID_API_KEY else "not_configured"
    dependencies.append(DependencyStatus(
        name="sendgrid",
        status=sendgrid_status,
        latency_ms=None
    ))
    
    # Redis (for Celery)
    redis_status = "configured"  # Would need to actually ping Redis
    dependencies.append(DependencyStatus(
        name="redis",
        status=redis_status,
        latency_ms=None
    ))
    
    return DependenciesResponse(dependencies=dependencies)


@router.post("/message")
async def handle_udc_message(message: dict):
    """
    UDC Message Handler.
    Receives messages from orchestrator.
    """
    message_type = message.get("type")
    payload = message.get("payload", {})
    
    if message_type == "ping":
        return {"type": "pong", "service": settings.SERVICE_ID}
    
    if message_type == "status_request":
        return {
            "type": "status_response",
            "service": settings.SERVICE_ID,
            "status": "active"
        }
    
    if message_type == "decay_trigger":
        # Trigger CORA decay check
        return {
            "type": "decay_acknowledged",
            "service": settings.SERVICE_ID,
            "message": "Decay check will run on next scheduled interval"
        }
    
    return {
        "type": "unknown_message",
        "received_type": message_type
    }



