"""
WhiteRock Blessings Engine - Blessing Request Endpoints
Blessing requests with strict state machine.
v2.2 - With rate limiting
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Member, BlessingRequest, BlessingDisbursement, CommunityCapacity, Tithe
from app.schemas import (
    BlessingEligibilityResponse, BlessingRequestCreate, BlessingRequestResponse,
    BlessingTransition, BlessingDisburseRequest, BlessingPendingResponse,
    BlessingStatusEnum, CapacityLevelEnum
)
from app.auth import get_current_member, require_committee, require_admin, get_client_ip, get_user_agent
from app.state_machine import (
    validate_transition, create_transition_log_entry, 
    sanitize_state_history_for_member, get_member_notification_message
)
from app.services.audit_service import AuditService
from app.services.email_service import EmailService
from app.config import settings
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/blessings", tags=["Blessings"])


@router.get("/eligibility", response_model=BlessingEligibilityResponse)
async def check_blessing_eligibility(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if the current member can request a blessing.
    """
    reasons = []
    
    if not member.profile_complete:
        reasons.append("profile_incomplete")
    
    if not member.disclosure_signed_at:
        reasons.append("disclosure_not_signed")
    
    days_as_member = (datetime.utcnow() - member.created_at).days
    if days_as_member < settings.MIN_MEMBERSHIP_DAYS_FOR_BLESSING:
        reasons.append(f"member_under_{settings.MIN_MEMBERSHIP_DAYS_FOR_BLESSING}_days")
    
    # Get capacity
    result = await db.execute(
        select(CommunityCapacity).order_by(CommunityCapacity.updated_at.desc()).limit(1)
    )
    capacity = result.scalar_one_or_none()
    capacity_level = CapacityLevelEnum(capacity.capacity_level) if capacity else CapacityLevelEnum.HIGH
    
    if capacity_level == CapacityLevelEnum.PAUSED:
        reasons.append("community_capacity_paused")
    
    return BlessingEligibilityResponse(
        eligible=len(reasons) == 0,
        reasons=reasons,
        community_capacity=capacity_level
    )


@router.post("/request", response_model=BlessingRequestResponse)
@limiter.limit(settings.RATE_LIMIT_BLESSING)
async def create_blessing_request(
    request: Request,
    request_data: BlessingRequestCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new blessing request.
    Member must pass eligibility check.
    Rate limited to 5 requests per day per user.
    """
    # Check eligibility
    eligibility = await check_blessing_eligibility(member, db)
    
    if not eligibility.eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not eligible for blessing request: {', '.join(eligibility.reasons)}"
        )
    
    if eligibility.community_capacity == CapacityLevelEnum.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Community blessing capacity is currently paused"
        )
    
    # Create request
    blessing = BlessingRequest(
        member_id=member.id,
        category=request_data.category.value,
        description=request_data.description,
        amount_requested_cents=request_data.amount_requested_cents,
        vendor_name=request_data.vendor_name,
        vendor_contact=request_data.vendor_contact,
        supporting_docs_url=request_data.supporting_docs_url,
        status="draft",
        state_transition_log=[]
    )
    
    db.add(blessing)
    await db.flush()
    
    # Auto-transition from draft to pending
    blessing.status = "pending"
    blessing.state_transition_log = [
        create_transition_log_entry("draft", "pending", member.id)
    ]
    
    # Update engagement
    member.last_engagement_date = datetime.utcnow()
    
    # Audit log
    audit = AuditService(db)
    await audit.log_blessing_state_change(
        blessing_id=blessing.id,
        old_state="draft",
        new_state="pending",
        actor_id=member.id,
        actor_role="member",
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else None
    )
    
    return BlessingRequestResponse(
        id=blessing.id,
        category=blessing.category,
        description=blessing.description,
        amount_requested_cents=blessing.amount_requested_cents,
        vendor_name=blessing.vendor_name,
        vendor_contact=blessing.vendor_contact,
        status=blessing.status,
        amount_approved_cents=blessing.amount_approved_cents,
        denial_reason=blessing.denial_reason,
        created_at=blessing.created_at,
        updated_at=blessing.updated_at,
        state_history=sanitize_state_history_for_member(blessing.state_transition_log)
    )


@router.get("/me")
async def get_my_blessing_requests(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current member's blessing requests.
    """
    result = await db.execute(
        select(BlessingRequest).where(BlessingRequest.member_id == member.id)
        .order_by(BlessingRequest.created_at.desc())
    )
    requests = result.scalars().all()
    
    return {
        "requests": [
            BlessingRequestResponse(
                id=r.id,
                category=r.category,
                description=r.description,
                amount_requested_cents=r.amount_requested_cents,
                vendor_name=r.vendor_name,
                vendor_contact=r.vendor_contact,
                status=r.status,
                amount_approved_cents=r.amount_approved_cents,
                denial_reason=r.denial_reason,
                created_at=r.created_at,
                updated_at=r.updated_at,
                state_history=sanitize_state_history_for_member(r.state_transition_log or [])
            )
            for r in requests
        ]
    }


@router.get("/pending")
async def get_pending_blessing_requests(
    committee: Member = Depends(require_committee),
    db: AsyncSession = Depends(get_db)
):
    """
    Get pending blessing requests for committee review.
    Committee only.
    
    Optimized: Uses subqueries to fetch all data in a single database round-trip.
    """
    from sqlalchemy.orm import aliased
    from sqlalchemy import literal_column
    
    # Subquery for prior blessings count and sum per member
    prior_blessings_subq = (
        select(
            BlessingRequest.member_id,
            func.count(BlessingRequest.id).label("prior_count"),
            func.coalesce(func.sum(BlessingRequest.amount_approved_cents), 0).label("prior_sum")
        )
        .where(BlessingRequest.status == "disbursed")
        .group_by(BlessingRequest.member_id)
        .subquery()
    )
    
    # Main query with LEFT JOIN to include prior blessings stats
    result = await db.execute(
        select(
            BlessingRequest,
            Member,
            func.coalesce(prior_blessings_subq.c.prior_count, 0).label("prior_blessings_count"),
            func.coalesce(prior_blessings_subq.c.prior_sum, 0).label("prior_blessings_total")
        )
        .join(Member, BlessingRequest.member_id == Member.id)
        .outerjoin(prior_blessings_subq, Member.id == prior_blessings_subq.c.member_id)
        .where(BlessingRequest.status.in_(["pending", "committee_review", "info_requested"]))
        .order_by(BlessingRequest.created_at.asc())
    )
    
    pending = []
    for row in result:
        request = row[0]
        member = row[1]
        prior_count = row[2]
        prior_sum = row[3]
        
        # Calculate tenure
        tenure_months = (datetime.utcnow() - member.created_at).days // 30
        
        pending.append({
            "id": request.id,
            "member_summary": {
                "id": member.id,
                "name": member.full_name,
                "tenure_months": tenure_months,
                "cora_balance": member.cora_balance,
                "tier": member.membership_tier,
                "prior_blessings_count": prior_count,
                "prior_blessings_total_cents": prior_sum
            },
            "category": request.category,
            "amount_requested_cents": request.amount_requested_cents,
            "vendor_name": request.vendor_name,
            "vendor_contact": request.vendor_contact,
            "description": request.description,
            "status": request.status,
            "compliance_flag": request.compliance_flag,
            "created_at": request.created_at.isoformat(),
            "state_transition_log": request.state_transition_log or []
        })
    
    return {"requests": pending}


@router.get("/{blessing_id}")
async def get_blessing_request(
    blessing_id: int,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific blessing request.
    Members can only view their own requests.
    Committee/Admin can view all.
    """
    result = await db.execute(
        select(BlessingRequest).where(BlessingRequest.id == blessing_id)
    )
    blessing = result.scalar_one_or_none()
    
    if not blessing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blessing request not found"
        )
    
    # Check access
    is_owner = blessing.member_id == member.id
    is_authorized = member.is_committee or member.is_admin
    
    if not is_owner and not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request"
        )
    
    # Sanitize history for members
    state_history = blessing.state_transition_log or []
    if not is_authorized:
        state_history = sanitize_state_history_for_member(state_history)
    
    return BlessingRequestResponse(
        id=blessing.id,
        category=blessing.category,
        description=blessing.description,
        amount_requested_cents=blessing.amount_requested_cents,
        vendor_name=blessing.vendor_name,
        vendor_contact=blessing.vendor_contact,
        status=blessing.status,
        amount_approved_cents=blessing.amount_approved_cents,
        denial_reason=blessing.denial_reason,
        created_at=blessing.created_at,
        updated_at=blessing.updated_at,
        state_history=state_history
    )


@router.put("/{blessing_id}/transition")
async def transition_blessing_state(
    blessing_id: int,
    transition: BlessingTransition,
    committee: Member = Depends(require_committee),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Transition a blessing request to a new state.
    Committee only. Validates state machine rules.
    """
    result = await db.execute(
        select(BlessingRequest, Member).join(Member).where(BlessingRequest.id == blessing_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blessing request not found"
        )
    
    blessing, member = row
    
    # Validate transition
    is_valid, error = validate_transition(
        current_state=blessing.status,
        new_state=transition.new_status.value,
        compliance_flag=transition.compliance_flag,
        amount_approved_cents=transition.amount_approved_cents,
        denial_reason=transition.denial_reason
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    old_status = blessing.status
    
    # Apply transition
    blessing.status = transition.new_status.value
    blessing.reviewed_by = committee.id
    blessing.reviewed_at = datetime.utcnow()
    
    if transition.internal_notes:
        blessing.internal_notes = transition.internal_notes
    
    if transition.compliance_flag is not None:
        blessing.compliance_flag = transition.compliance_flag
    
    if transition.amount_approved_cents is not None:
        blessing.amount_approved_cents = transition.amount_approved_cents
    
    if transition.denial_reason:
        blessing.denial_reason = transition.denial_reason
    
    # Log transition
    log_entry = create_transition_log_entry(
        from_state=old_status,
        to_state=transition.new_status.value,
        actor_id=committee.id,
        notes=transition.internal_notes
    )
    
    if blessing.state_transition_log is None:
        blessing.state_transition_log = []
    blessing.state_transition_log = blessing.state_transition_log + [log_entry]
    
    # Audit log
    audit = AuditService(db)
    await audit.log_blessing_state_change(
        blessing_id=blessing.id,
        old_state=old_status,
        new_state=transition.new_status.value,
        actor_id=committee.id,
        actor_role="committee",
        compliance_flag=transition.compliance_flag,
        amount_approved_cents=transition.amount_approved_cents,
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else None
    )
    
    # Send notification email to member
    email_service = EmailService()
    notification_message = get_member_notification_message(
        transition.new_status.value,
        transition.denial_reason
    )
    
    await email_service.send_blessing_status_update(
        to_email=member.email,
        member_name=member.full_name,
        blessing_id=blessing.id,
        new_status=transition.new_status.value,
        message=notification_message,
        include_footer=True
    )
    
    return BlessingRequestResponse(
        id=blessing.id,
        category=blessing.category,
        description=blessing.description,
        amount_requested_cents=blessing.amount_requested_cents,
        vendor_name=blessing.vendor_name,
        vendor_contact=blessing.vendor_contact,
        status=blessing.status,
        amount_approved_cents=blessing.amount_approved_cents,
        denial_reason=blessing.denial_reason,
        created_at=blessing.created_at,
        updated_at=blessing.updated_at,
        state_history=blessing.state_transition_log or []
    )


@router.post("/{blessing_id}/disburse")
async def disburse_blessing(
    blessing_id: int,
    disburse: BlessingDisburseRequest,
    admin: Member = Depends(require_admin),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Disburse an approved blessing.
    Admin only. Defaults to vendor-direct payment.
    """
    result = await db.execute(
        select(BlessingRequest, Member).join(Member).where(BlessingRequest.id == blessing_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blessing request not found"
        )
    
    blessing, member = row
    
    if blessing.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot disburse: request is '{blessing.status}', must be 'approved'"
        )
    
    # Cash to member override requires extra validation
    if disburse.cash_to_member_override:
        if not disburse.override_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Override reason required for cash-to-member disbursement"
            )
    
    # Create disbursement record
    disbursement = BlessingDisbursement(
        blessing_request_id=blessing.id,
        amount_cents=disburse.amount_cents,
        disbursement_method=disburse.disbursement_method,
        payment_direct_to_vendor=not disburse.cash_to_member_override,
        vendor_name=disburse.vendor_name or blessing.vendor_name,
        vendor_contact=disburse.vendor_contact or blessing.vendor_contact,
        disbursement_reference=disburse.disbursement_reference,
        disbursed_by=admin.id,
        cash_to_member_override=disburse.cash_to_member_override,
        override_approved_by=admin.id if disburse.cash_to_member_override else None,
        override_reason=disburse.override_reason
    )
    
    db.add(disbursement)
    await db.flush()
    
    # Transition to disbursed
    old_status = blessing.status
    blessing.status = "disbursed"
    
    log_entry = create_transition_log_entry(
        from_state=old_status,
        to_state="disbursed",
        actor_id=admin.id
    )
    
    if blessing.state_transition_log is None:
        blessing.state_transition_log = []
    blessing.state_transition_log = blessing.state_transition_log + [log_entry]
    
    # Audit log - CRITICAL if cash to member
    audit = AuditService(db)
    await audit.log_disbursement(
        disbursement_id=disbursement.id,
        blessing_id=blessing.id,
        amount_cents=disburse.amount_cents,
        actor_id=admin.id,
        payment_direct_to_vendor=not disburse.cash_to_member_override,
        cash_to_member_override=disburse.cash_to_member_override,
        override_reason=disburse.override_reason,
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else None
    )
    
    # Send notification
    email_service = EmailService()
    await email_service.send_blessing_status_update(
        to_email=member.email,
        member_name=member.full_name,
        blessing_id=blessing.id,
        new_status="disbursed",
        message="Your blessing has been disbursed. Thank you for being part of the WhiteRock community.",
        include_footer=True
    )
    
    # Auto-transition to closed
    blessing.status = "closed"
    close_entry = create_transition_log_entry(
        from_state="disbursed",
        to_state="closed",
        actor_id=admin.id
    )
    blessing.state_transition_log = blessing.state_transition_log + [close_entry]
    
    return {
        "disbursement_id": disbursement.id,
        "blessing_id": blessing.id,
        "amount_cents": disbursement.amount_cents,
        "method": disbursement.disbursement_method,
        "vendor_direct": disbursement.payment_direct_to_vendor,
        "status": blessing.status
    }

