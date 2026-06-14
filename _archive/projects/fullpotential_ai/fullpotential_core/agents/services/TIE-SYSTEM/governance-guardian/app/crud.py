"""
CRUD operations for governance alerts and events
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .database import GovernanceAlertDB, GovernanceEventDB, SystemPauseDB
from .models import AlertResponse, GovernanceEventResponse

logger = logging.getLogger(__name__)


async def create_alert(
    db: AsyncSession,
    alert_type: str,
    holder_control: float,
    message: str,
    action_taken: str
) -> GovernanceAlertDB:
    """Create a new governance alert."""
    alert = GovernanceAlertDB(
        alert_type=alert_type,
        holder_control=holder_control,
        message=message,
        action_taken=action_taken,
        resolved=False
    )
    db.add(alert)
    await db.flush()

    logger.warning(f"⚠️  ALERT CREATED: {alert_type} - {message}")

    return alert


async def resolve_alert(
    db: AsyncSession,
    alert_id: int
) -> GovernanceAlertDB:
    """Mark an alert as resolved."""
    stmt = select(GovernanceAlertDB).where(GovernanceAlertDB.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise ValueError(f"Alert {alert_id} not found")

    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    await db.flush()

    logger.info(f"✅ ALERT RESOLVED: {alert_id}")

    return alert


async def get_alerts(
    db: AsyncSession,
    limit: int = 20,
    resolved: Optional[bool] = None
) -> List[AlertResponse]:
    """Get alert history (optionally filtered by resolved status)."""
    stmt = select(GovernanceAlertDB).order_by(desc(GovernanceAlertDB.timestamp)).limit(limit)

    if resolved is not None:
        stmt = stmt.where(GovernanceAlertDB.resolved == resolved)

    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return [
        AlertResponse(
            id=a.id,
            timestamp=a.timestamp,
            alert_type=a.alert_type,
            holder_control=float(a.holder_control),
            message=a.message,
            action_taken=a.action_taken,
            resolved=a.resolved,
            resolved_at=a.resolved_at
        )
        for a in alerts
    ]


async def get_active_alerts_count(db: AsyncSession) -> int:
    """Get count of active (unresolved) alerts."""
    stmt = select(func.count(GovernanceAlertDB.id)).where(GovernanceAlertDB.resolved == False)
    result = await db.execute(stmt)
    return result.scalar() or 0


async def log_governance_event(
    db: AsyncSession,
    event_type: str,
    holder_control: float,
    threshold_level: str,
    action: str,
    details: Optional[str] = None
) -> GovernanceEventDB:
    """Log a governance event to the audit log."""
    event = GovernanceEventDB(
        event_type=event_type,
        holder_control=holder_control,
        threshold_level=threshold_level,
        action=action,
        details=details
    )
    db.add(event)
    await db.flush()

    if action != "none":
        logger.info(f"📊 GOVERNANCE EVENT: {event_type} - {action}")

    return event


async def get_events(
    db: AsyncSession,
    limit: int = 50,
    event_type: Optional[str] = None
) -> List[GovernanceEventResponse]:
    """Get governance event audit log (optionally filtered by type)."""
    stmt = select(GovernanceEventDB).order_by(desc(GovernanceEventDB.timestamp)).limit(limit)

    if event_type:
        stmt = stmt.where(GovernanceEventDB.event_type == event_type)

    result = await db.execute(stmt)
    events = result.scalars().all()

    return [
        GovernanceEventResponse(
            id=e.id,
            timestamp=e.timestamp,
            event_type=e.event_type,
            holder_control=float(e.holder_control),
            threshold_level=e.threshold_level,
            action=e.action,
            details=e.details
        )
        for e in events
    ]


async def create_pause_record(
    db: AsyncSession,
    pause_reason: str,
    pause_type: str,
    holder_control: float
) -> SystemPauseDB:
    """Create a system pause record."""
    pause = SystemPauseDB(
        pause_reason=pause_reason,
        pause_type=pause_type,
        holder_control_at_pause=holder_control
    )
    db.add(pause)
    await db.flush()

    logger.error(f"🚨 SYSTEM PAUSED: {pause_reason}")

    return pause


async def resume_pause_record(
    db: AsyncSession,
    resumed_by: str,
    resume_reason: Optional[str] = None
) -> SystemPauseDB:
    """Resume the most recent system pause."""
    # Get most recent unresolved pause
    stmt = select(SystemPauseDB).where(
        SystemPauseDB.resumed_at.is_(None)
    ).order_by(desc(SystemPauseDB.paused_at)).limit(1)

    result = await db.execute(stmt)
    pause = result.scalar_one_or_none()

    if not pause:
        raise ValueError("No active pause found")

    pause.resumed_at = datetime.utcnow()
    pause.resumed_by = resumed_by
    pause.resume_reason = resume_reason or "Manual resume - governance verified"
    await db.flush()

    logger.info(f"✅ SYSTEM RESUMED by {resumed_by}")

    return pause


async def get_current_pause(db: AsyncSession) -> Optional[SystemPauseDB]:
    """Get current system pause if active."""
    stmt = select(SystemPauseDB).where(
        SystemPauseDB.resumed_at.is_(None)
    ).order_by(desc(SystemPauseDB.paused_at)).limit(1)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()
