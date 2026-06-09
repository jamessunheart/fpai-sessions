"""
WhiteRock Blessings Engine - Service Hours Endpoints
Logging and verification of community service hours.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Member, ServiceHours
from app.schemas import ServiceHoursLog, ServiceHoursResponse, ServiceHoursVerify
from app.auth import get_current_member, require_admin
from app.services.cora_service import CoraService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/service", tags=["Service Hours"])


@router.post("/log", response_model=ServiceHoursResponse)
async def log_service_hours(
    service_data: ServiceHoursLog,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Log service hours for community activities.
    Updates last_engagement_date.
    """
    service = ServiceHours(
        member_id=member.id,
        hours=service_data.hours,
        activity_type=service_data.activity_type,
        activity_date=service_data.activity_date,
        description=service_data.description
    )
    
    db.add(service)
    
    # Update engagement date
    member.last_engagement_date = datetime.utcnow()
    
    await db.flush()
    
    # Audit log
    audit = AuditService(db)
    await audit.log(
        action="service_hours_logged",
        entity_type="service_hours",
        entity_id=service.id,
        actor_id=member.id,
        actor_role="member",
        new_values={
            "hours": float(service_data.hours),
            "activity_type": service_data.activity_type,
            "activity_date": service_data.activity_date.isoformat()
        }
    )
    
    return ServiceHoursResponse(
        id=service.id,
        hours=float(service.hours),
        activity_type=service.activity_type,
        activity_date=service.activity_date,
        description=service.description,
        verified_at=service.verified_at,
        cora_granted=service.cora_granted,
        created_at=service.created_at
    )


@router.get("/me")
async def get_my_service_hours(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current member's service hours summary.
    """
    # Get all service hours
    result = await db.execute(
        select(ServiceHours).where(ServiceHours.member_id == member.id)
        .order_by(ServiceHours.created_at.desc())
    )
    services = result.scalars().all()
    
    total_hours = sum(float(s.hours) for s in services)
    pending_hours = sum(float(s.hours) for s in services if not s.verified_at)
    verified_hours = sum(float(s.hours) for s in services if s.verified_at)
    
    history = [
        ServiceHoursResponse(
            id=s.id,
            hours=float(s.hours),
            activity_type=s.activity_type,
            activity_date=s.activity_date,
            description=s.description,
            verified_at=s.verified_at,
            cora_granted=s.cora_granted,
            created_at=s.created_at
        )
        for s in services
    ]
    
    return {
        "total_hours": round(total_hours, 2),
        "pending_hours": round(pending_hours, 2),
        "verified_hours": round(verified_hours, 2),
        "history": history
    }


@router.get("/pending")
async def get_pending_service_hours(
    admin: Member = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending (unverified) service hours.
    Admin only.
    """
    result = await db.execute(
        select(ServiceHours, Member).join(Member).where(
            ServiceHours.verified_at.is_(None)
        ).order_by(ServiceHours.created_at.asc())
    )
    
    pending = []
    for service, member in result:
        pending.append({
            "id": service.id,
            "member_id": member.id,
            "member_name": member.full_name,
            "member_tier": member.membership_tier,
            "hours": float(service.hours),
            "activity_type": service.activity_type,
            "activity_date": service.activity_date.isoformat(),
            "description": service.description,
            "created_at": service.created_at.isoformat()
        })
    
    return {"pending_service_hours": pending}


@router.post("/{service_id}/verify")
async def verify_service_hours(
    service_id: int,
    verification: ServiceHoursVerify,
    admin: Member = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify service hours and optionally grant CORA.
    Admin only.
    """
    result = await db.execute(
        select(ServiceHours).where(ServiceHours.id == service_id)
    )
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service hours record not found"
        )
    
    if service.verified_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service hours already verified"
        )
    
    # Mark as verified
    service.verified_by = admin.id
    service.verified_at = datetime.utcnow()
    
    # Grant CORA if specified
    if verification.cora_grant_amount > 0:
        cora_service = CoraService(db)
        _, new_balance = await cora_service.grant_cora(
            member_id=service.member_id,
            amount=verification.cora_grant_amount,
            transaction_type="service_grant",
            description=f"Service hours: {float(service.hours)} hrs {service.activity_type}",
            granted_by=admin.id
        )
        service.cora_granted = verification.cora_grant_amount
    
    # Audit log
    audit = AuditService(db)
    await audit.log(
        action="service_hours_verified",
        entity_type="service_hours",
        entity_id=service.id,
        actor_id=admin.id,
        actor_role="admin",
        new_values={
            "verified": True,
            "cora_granted": verification.cora_grant_amount
        }
    )
    
    return {
        "verified": True,
        "cora_granted": service.cora_granted,
        "verified_at": service.verified_at.isoformat()
    }



