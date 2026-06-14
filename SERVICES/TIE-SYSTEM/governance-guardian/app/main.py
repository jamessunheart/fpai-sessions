"""
governance-guardian - TIE Governance Control Monitoring & Circuit Breaker
Port 8926
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .database import init_db, get_db
from .models import (
    GuardianStatusResponse,
    GovernanceMetricsResponse,
    AlertHistoryResponse,
    GovernanceEventsResponse,
    PauseRequest,
    PauseResponse,
    ResumeRequest,
    ResumeResponse,
    SystemRulesResponse,
    HealthResponse
)
from . import crud
from .monitor import GovernanceMonitor

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global monitor instance
monitor: Optional[GovernanceMonitor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    global monitor

    logger.info("🛡️  Starting governance-guardian (Port 8926)")

    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # Start governance monitoring
    monitor = GovernanceMonitor()
    asyncio.create_task(monitor.start_monitoring())
    logger.info("✅ Governance monitoring active")

    yield

    # Cleanup
    if monitor:
        await monitor.stop_monitoring()
    logger.info("👋 Shutdown complete")


app = FastAPI(
    title="governance-guardian",
    description="TIE Governance Control Monitoring & Circuit Breaker",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/guardian/status", response_model=GuardianStatusResponse)
async def get_guardian_status(db: AsyncSession = Depends(get_db)):
    """Get current guardian monitoring status."""
    try:
        status = await monitor.get_status()
        return status

    except Exception as e:
        logger.error(f"Failed to get guardian status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/guardian/governance", response_model=GovernanceMetricsResponse)
async def get_governance_metrics(db: AsyncSession = Depends(get_db)):
    """Get current governance metrics from voting-weight-tracker."""
    try:
        metrics = await monitor.get_current_governance()
        return metrics

    except Exception as e:
        logger.error(f"Failed to get governance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/guardian/alerts", response_model=AlertHistoryResponse)
async def get_alert_history(
    limit: int = Query(default=20, ge=1, le=100),
    resolved: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get alert history (optionally filtered by resolved status)."""
    try:
        alerts = await crud.get_alerts(db, limit=limit, resolved=resolved)
        return AlertHistoryResponse(alerts=alerts)

    except Exception as e:
        logger.error(f"Failed to get alert history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/guardian/events", response_model=GovernanceEventsResponse)
async def get_governance_events(
    limit: int = Query(default=50, ge=1, le=200),
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get governance event audit log."""
    try:
        events = await crud.get_events(db, limit=limit, event_type=event_type)
        return GovernanceEventsResponse(events=events)

    except Exception as e:
        logger.error(f"Failed to get governance events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/guardian/pause", response_model=PauseResponse)
async def pause_system(
    request: PauseRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually pause the system (admin only).

    Requires authorization signature.
    """
    try:
        # TODO: Verify authorization signature

        logger.warning(f"🚨 MANUAL PAUSE REQUESTED: {request.reason}")

        # Pause system
        pause_record = await monitor.pause_system(
            db=db,
            reason=request.reason,
            pause_type="manual",
            holder_control=await monitor.get_current_holder_control()
        )

        return PauseResponse(
            paused=True,
            paused_at=pause_record.paused_at,
            reason=pause_record.pause_reason,
            resume_requires="admin_approval"
        )

    except Exception as e:
        logger.error(f"Failed to pause system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/guardian/resume", response_model=ResumeResponse)
async def resume_system(
    request: ResumeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resume system operations (admin only).

    Requires authorization signature and governance verification.
    """
    try:
        # TODO: Verify authorization signature

        if not request.governance_verified:
            raise HTTPException(
                status_code=400,
                detail="Governance must be verified before resuming"
            )

        # Check current holder control
        current_control = await monitor.get_current_holder_control()

        if current_control < 51.0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume: Holder control at {current_control}% (must be >51%)"
            )

        logger.info(f"✅ RESUMING SYSTEM: Holder control at {current_control}%")

        # Resume system
        pause_record = await monitor.resume_system(db=db, resumed_by="admin")

        return ResumeResponse(
            paused=False,
            resumed_at=pause_record.resumed_at,
            current_holder_control=current_control,
            safe_to_resume=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/guardian/rules", response_model=SystemRulesResponse)
async def get_system_rules():
    """Get current governance rules and thresholds."""
    return monitor.get_rules()


@app.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Check if monitoring is active
        monitoring_active = monitor is not None and monitor.monitoring_active

        # Check voting tracker connection
        voting_tracker_connected = await monitor.check_voting_tracker_connection() if monitor else False

        # Check database
        await db.execute("SELECT 1")

        # Get last check time
        last_check = monitor.last_check if monitor else None
        seconds_since_last_check = (
            (datetime.utcnow() - last_check).total_seconds()
            if last_check else None
        )

        return HealthResponse(
            status="healthy",
            monitoring_active=monitoring_active,
            voting_tracker_connected=voting_tracker_connected,
            database="connected",
            last_governance_check=last_check,
            seconds_since_last_check=seconds_since_last_check
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            monitoring_active=False,
            voting_tracker_connected=False,
            database="error",
            last_governance_check=None,
            seconds_since_last_check=None
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "governance-guardian",
        "version": "1.0.0",
        "port": 8926,
        "status": "monitoring",
        "purpose": "TIE Governance Control Monitoring & Circuit Breaker"
    }
