"""
WhiteRock Blessings Engine - Celery Tasks
Background tasks for CORA decay, warnings, and maintenance.
v2.2 - Fixed asyncio patterns with retry logic
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from worker.celery_app import celery_app

# Database connection for async tasks
import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/whiterock"
)


def get_async_session():
    """Create async session for tasks."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def run_async(coro):
    """
    Run async coroutine in a new event loop.
    Safe pattern for Celery tasks.
    """
    try:
        # Try to get existing loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    else:
        # Already in an async context
        return asyncio.ensure_future(coro)


@celery_app.task(
    bind=True,
    name="worker.tasks.run_cora_decay",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def run_cora_decay(self) -> dict:
    """
    Monthly CORA decay task.
    Runs on the 1st of each month.
    
    Decays CORA by 10% for members inactive > 12 months.
    """
    return run_async(_async_run_decay())


async def _async_run_decay() -> dict:
    """Async implementation of CORA decay."""
    from app.models import Member, CoraDecayEvent, CoraTransaction
    from app.services.email_service import EmailService
    from app.logging_config import logger
    
    AsyncSessionLocal = get_async_session()
    
    async with AsyncSessionLocal() as db:
        # Get members for decay
        threshold_date = datetime.utcnow() - timedelta(days=365)
        
        result = await db.execute(
            select(Member).where(
                Member.is_active == True,
                Member.cora_balance > 0,
                Member.last_engagement_date < threshold_date
            )
        )
        members = result.scalars().all()
        
        decay_count = 0
        total_decayed = 0
        email_service = EmailService()
        
        for member in members:
            try:
                # Calculate months inactive
                months_inactive = (datetime.utcnow() - member.last_engagement_date).days // 30
                
                # Calculate decay (10%)
                decay_amount = int(member.cora_balance * 0.10)
                if decay_amount < 1:
                    decay_amount = 1  # Minimum decay of 1
                
                balance_before = member.cora_balance
                balance_after = max(0, balance_before - decay_amount)
                
                # Create decay event
                decay_event = CoraDecayEvent(
                    member_id=member.id,
                    amount_decayed=decay_amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    decay_reason="inactivity_12mo",
                    months_inactive=months_inactive,
                    notification_sent=True
                )
                db.add(decay_event)
                
                # Create transaction
                transaction = CoraTransaction(
                    member_id=member.id,
                    amount=-decay_amount,
                    transaction_type="decay_inactivity",
                    description=f"Monthly decay after {months_inactive} months inactivity"
                )
                db.add(transaction)
                
                # Update balance
                member.cora_balance = balance_after
                
                # Send notification
                await email_service.send_email(
                    to_email=member.email,
                    subject="WhiteRock Ministry - CORA Decay Notice",
                    html_content=f"""
                    <p>Dear {member.full_name},</p>
                    <p>Due to {months_inactive} months of inactivity, your CORA vitality credits 
                    have been reduced by {decay_amount}.</p>
                    <p>Previous balance: {balance_before}</p>
                    <p>New balance: {balance_after}</p>
                    <p>To prevent further decay, please engage with the WhiteRock community through 
                    tithes, service hours, or other activities.</p>
                    <p>Visit <a href="https://whiterock.us">whiterock.us</a> to check in.</p>
                    """
                )
                
                decay_count += 1
                total_decayed += decay_amount
                
                logger.info(
                    "cora_decay_applied",
                    member_id=member.id,
                    amount_decayed=decay_amount,
                    balance_after=balance_after
                )
                
            except Exception as e:
                logger.error(
                    "cora_decay_member_failed",
                    member_id=member.id,
                    error=str(e)
                )
        
        await db.commit()
        
        logger.info(
            "cora_decay_completed",
            members_decayed=decay_count,
            total_cora_decayed=total_decayed
        )
        
        return {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "members_decayed": decay_count,
            "total_cora_decayed": total_decayed
        }


@celery_app.task(
    bind=True,
    name="worker.tasks.send_decay_warnings",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def send_decay_warnings(self) -> dict:
    """
    Daily task to send decay warnings.
    Warns members 30 days before their first decay event.
    """
    return run_async(_async_send_warnings())


async def _async_send_warnings() -> dict:
    """Async implementation of decay warnings."""
    from app.models import Member
    from app.services.email_service import EmailService
    from app.config import settings
    from app.logging_config import logger
    
    AsyncSessionLocal = get_async_session()
    
    async with AsyncSessionLocal() as db:
        # Find members approaching decay
        warning_start = datetime.utcnow() - timedelta(days=365 - settings.CORA_DECAY_WARNING_DAYS)
        threshold_date = datetime.utcnow() - timedelta(days=365)
        
        result = await db.execute(
            select(Member).where(
                Member.is_active == True,
                Member.cora_balance > 0,
                Member.last_engagement_date < warning_start,
                Member.last_engagement_date >= threshold_date,
                Member.decay_warning_sent_at.is_(None)
            )
        )
        members = result.scalars().all()
        
        warnings_sent = 0
        email_service = EmailService()
        
        for member in members:
            try:
                days_until_decay = (member.last_engagement_date + timedelta(days=365) - datetime.utcnow()).days
                projected_decay = int(member.cora_balance * 0.10)
                
                success = await email_service.send_decay_warning(
                    to_email=member.email,
                    member_name=member.full_name,
                    current_balance=member.cora_balance,
                    projected_decay=projected_decay,
                    days_until_decay=max(0, days_until_decay)
                )
                
                if success:
                    member.decay_warning_sent_at = datetime.utcnow()
                    warnings_sent += 1
                    
                    logger.info(
                        "decay_warning_sent",
                        member_id=member.id,
                        days_until_decay=days_until_decay
                    )
            except Exception as e:
                logger.error(
                    "decay_warning_failed",
                    member_id=member.id,
                    error=str(e)
                )
        
        await db.commit()
        
        logger.info(
            "decay_warnings_completed",
            warnings_sent=warnings_sent
        )
        
        return {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "warnings_sent": warnings_sent
        }


@celery_app.task(
    bind=True,
    name="worker.tasks.health_check",
    max_retries=3,
    default_retry_delay=30
)
def health_check(self) -> dict:
    """
    Daily health check task.
    Verifies system integrity and logs status.
    """
    return run_async(_async_health_check())


async def _async_health_check() -> dict:
    """Async implementation of health check."""
    from app.logging_config import logger
    
    AsyncSessionLocal = get_async_session()
    
    async with AsyncSessionLocal() as db:
        # Check database connection
        try:
            await db.execute(text("SELECT 1"))
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Get basic stats
        result = await db.execute(text("SELECT COUNT(*) FROM members WHERE is_active = true"))
        member_count = result.scalar_one()
        
        result = await db.execute(text("SELECT COUNT(*) FROM blessing_requests WHERE status IN ('pending', 'committee_review')"))
        pending_blessings = result.scalar_one()
        
        result = await db.execute(text("SELECT COALESCE(SUM(cora_balance), 0) FROM members WHERE is_active = true"))
        cora_total = result.scalar_one()
        
        status = "healthy" if db_status == "healthy" else "degraded"
        
        logger.info(
            "health_check_completed",
            status=status,
            active_members=member_count,
            pending_blessings=pending_blessings,
            cora_circulation=cora_total
        )
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
            "metrics": {
                "active_members": member_count,
                "pending_blessings": pending_blessings,
                "cora_circulation": cora_total
            }
        }


@celery_app.task(
    bind=True,
    name="worker.tasks.process_tithe_receipts",
    max_retries=5,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300
)
def process_tithe_receipts(self, tithe_id: int) -> dict:
    """
    Process and send tithe receipt asynchronously.
    Called after successful tithe submission.
    """
    return run_async(_async_send_receipt(tithe_id))


async def _async_send_receipt(tithe_id: int) -> dict:
    """Async implementation of receipt sending."""
    from app.models import Tithe, Member
    from app.services.email_service import EmailService
    from app.logging_config import logger
    
    AsyncSessionLocal = get_async_session()
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Tithe, Member).join(Member).where(Tithe.id == tithe_id)
        )
        row = result.first()
        
        if not row:
            logger.warning("tithe_receipt_not_found", tithe_id=tithe_id)
            return {"status": "error", "message": f"Tithe {tithe_id} not found"}
        
        tithe, member = row
        
        email_service = EmailService()
        success = await email_service.send_tithe_receipt(
            to_email=member.email,
            member_name=member.full_name,
            amount_cents=tithe.amount_cents,
            tithe_id=tithe.id,
            disclosure_version=tithe.disclosure_version,
            created_at=tithe.created_at
        )
        
        if success:
            tithe.receipt_sent_at = datetime.utcnow()
            await db.commit()
            
            logger.info("tithe_receipt_sent", tithe_id=tithe_id, member_id=member.id)
        else:
            logger.error("tithe_receipt_failed", tithe_id=tithe_id)
        
        return {
            "status": "sent" if success else "failed",
            "tithe_id": tithe_id,
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(
    bind=True,
    name="worker.tasks.cleanup_old_audit_logs",
    max_retries=2
)
def cleanup_old_audit_logs(self, days_to_keep: int = 365) -> dict:
    """
    Periodic task to archive/cleanup old audit logs.
    Keeps detailed logs for compliance period, archives older.
    """
    return run_async(_async_cleanup_audit_logs(days_to_keep))


async def _async_cleanup_audit_logs(days_to_keep: int) -> dict:
    """Async implementation of audit log cleanup."""
    from app.logging_config import logger
    
    AsyncSessionLocal = get_async_session()
    
    async with AsyncSessionLocal() as db:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count records to be archived
        result = await db.execute(
            text("SELECT COUNT(*) FROM audit_log WHERE created_at < :cutoff AND severity = 'info'"),
            {"cutoff": cutoff_date}
        )
        count = result.scalar_one()
        
        # In production, you'd archive these before deleting
        # For now, just log the count
        
        logger.info(
            "audit_cleanup_scan",
            records_eligible=count,
            cutoff_date=cutoff_date.isoformat()
        )
        
        return {
            "status": "completed",
            "records_scanned": count,
            "cutoff_date": cutoff_date.isoformat()
        }
