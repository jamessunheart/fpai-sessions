"""
WhiteRock Blessings Engine - Member Endpoints
Member registration, profile management, and authentication.
v2.2 - With rate limiting
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models import Member, DisclosureVersion, Tithe, CoraTransaction, ServiceHours
from app.schemas import (
    MemberRegister, MemberUpdate, MemberLogin, MemberResponse, 
    MemberMeResponse, DisclosureAcknowledge, TokenResponse,
    RefreshTokenRequest, LogoutRequest
)
from app.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    get_current_member, get_client_ip, get_user_agent, blacklist_token,
    refresh_access_token, bearer_scheme
)
from fastapi.security import HTTPAuthorizationCredentials
from app.config import settings
from app.services.audit_service import AuditService
from app.services.email_service import EmailService
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/members", tags=["Members"])


@router.post("/register", response_model=MemberResponse)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register_member(
    request: Request,
    member_data: MemberRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new member account.
    Rate limited to 5 requests per hour per IP.
    """
    # Check if email already exists
    result = await db.execute(
        select(Member).where(Member.email == member_data.email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create member
    member = Member(
        email=member_data.email,
        password_hash=hash_password(member_data.password),
        full_name=member_data.full_name,
        phone=member_data.phone,
        address_line1=member_data.address_line1,
        address_line2=member_data.address_line2,
        city=member_data.city,
        state=member_data.state,
        zip_code=member_data.zip_code,
        membership_tier="seedling",
        cora_balance=0,
        cora_cap=1000,
        last_engagement_date=datetime.utcnow()
    )
    
    # Check profile completeness
    member.profile_complete = all([
        member.full_name,
        member.address_line1,
        member.city,
        member.state,
        member.zip_code
    ])
    
    db.add(member)
    await db.flush()
    
    # Audit log
    audit = AuditService(db)
    await audit.log(
        action="member_registered",
        entity_type="member",
        entity_id=member.id,
        actor_id=member.id,
        actor_role="member",
        new_values={"email": member.email},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    # Send welcome email
    email_service = EmailService()
    await email_service.send_welcome_email(member.email, member.full_name)
    
    return member


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    credentials: MemberLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate and get access and refresh tokens.
    Rate limited to 10 requests per minute per IP.
    """
    result = await db.execute(
        select(Member).where(
            Member.email == credentials.email,
            Member.is_active == True
        )
    )
    member = result.scalar_one_or_none()
    
    if not member or not verify_password(credentials.password, member.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create tokens
    token_data = {
        "sub": str(member.id),
        "email": member.email,
        "tier": member.membership_tier,
        "is_admin": member.is_admin,
        "is_committee": member.is_committee,
        "is_auditor": member.is_auditor
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Update engagement
    member.last_engagement_date = datetime.utcnow()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
        refresh_expires_in=settings.JWT_REFRESH_EXPIRATION_DAYS * 86400
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest
):
    """
    Refresh access token using a valid refresh token.
    The old refresh token will be blacklisted (token rotation).
    """
    new_access, new_refresh = await refresh_access_token(refresh_request.refresh_token)
    
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
        refresh_expires_in=settings.JWT_REFRESH_EXPIRATION_DAYS * 86400
    )


@router.post("/logout")
async def logout(
    request: Request,
    logout_request: LogoutRequest = None,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    """
    Logout and blacklist the current access token.
    Optionally also blacklist the refresh token.
    """
    # Blacklist the access token
    if credentials:
        blacklist_token(credentials.credentials)
    
    # Blacklist the refresh token if provided
    if logout_request and logout_request.refresh_token:
        blacklist_token(logout_request.refresh_token)
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=MemberMeResponse)
async def get_current_member_profile(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current authenticated member's profile with computed fields.
    """
    # Calculate days until decay warning
    months_since_engagement = (datetime.utcnow() - member.last_engagement_date).days // 30
    days_until_decay = None
    
    if member.cora_balance > 0:
        decay_start_date = member.last_engagement_date + timedelta(days=365)
        days_until_decay = (decay_start_date - datetime.utcnow()).days
        if days_until_decay < 0:
            days_until_decay = 0  # Already decaying
    
    # Check blessing eligibility
    days_as_member = (datetime.utcnow() - member.created_at).days
    can_request_blessing = all([
        member.profile_complete,
        member.disclosure_signed_at is not None,
        days_as_member >= settings.MIN_MEMBERSHIP_DAYS_FOR_BLESSING
    ])
    
    # Get recent activity
    recent_activity = []
    
    # Recent tithes
    result = await db.execute(
        select(Tithe).where(Tithe.member_id == member.id)
        .order_by(Tithe.created_at.desc()).limit(5)
    )
    for tithe in result.scalars():
        recent_activity.append({
            "type": "tithe",
            "description": f"Tithe received - ${tithe.amount_cents / 100:,.2f}",
            "date": tithe.created_at.isoformat()
        })
    
    # Recent service hours
    result = await db.execute(
        select(ServiceHours).where(ServiceHours.member_id == member.id)
        .order_by(ServiceHours.created_at.desc()).limit(5)
    )
    for service in result.scalars():
        recent_activity.append({
            "type": "service",
            "description": f"Service logged - {service.hours} hrs {service.activity_type}",
            "date": service.created_at.isoformat()
        })
    
    # Recent CORA transactions
    result = await db.execute(
        select(CoraTransaction).where(CoraTransaction.member_id == member.id)
        .order_by(CoraTransaction.created_at.desc()).limit(5)
    )
    for tx in result.scalars():
        sign = "+" if tx.amount > 0 else ""
        recent_activity.append({
            "type": "cora",
            "description": f"CORA {tx.transaction_type} - {sign}{tx.amount}",
            "date": tx.created_at.isoformat()
        })
    
    # Sort by date and limit
    recent_activity.sort(key=lambda x: x["date"], reverse=True)
    recent_activity = recent_activity[:10]
    
    return MemberMeResponse(
        id=member.id,
        email=member.email,
        full_name=member.full_name,
        phone=member.phone,
        address_line1=member.address_line1,
        address_line2=member.address_line2,
        city=member.city,
        state=member.state,
        zip_code=member.zip_code,
        membership_tier=member.membership_tier,
        cora_balance=member.cora_balance,
        cora_cap=member.cora_cap,
        last_engagement_date=member.last_engagement_date,
        disclosure_signed_at=member.disclosure_signed_at,
        disclosure_version=member.disclosure_version,
        profile_complete=member.profile_complete,
        is_active=member.is_active,
        created_at=member.created_at,
        days_until_decay_warning=days_until_decay,
        can_request_blessing=can_request_blessing,
        recent_activity=recent_activity
    )


@router.put("/me", response_model=MemberResponse)
async def update_member_profile(
    updates: MemberUpdate,
    member: Member = Depends(get_current_member),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current member's profile.
    """
    old_values = {}
    new_values = {}
    
    if updates.full_name is not None:
        old_values["full_name"] = member.full_name
        member.full_name = updates.full_name
        new_values["full_name"] = updates.full_name
    
    if updates.phone is not None:
        old_values["phone"] = member.phone
        member.phone = updates.phone
        new_values["phone"] = updates.phone
    
    if updates.address_line1 is not None:
        old_values["address_line1"] = member.address_line1
        member.address_line1 = updates.address_line1
        new_values["address_line1"] = updates.address_line1
    
    if updates.address_line2 is not None:
        old_values["address_line2"] = member.address_line2
        member.address_line2 = updates.address_line2
        new_values["address_line2"] = updates.address_line2
    
    if updates.city is not None:
        old_values["city"] = member.city
        member.city = updates.city
        new_values["city"] = updates.city
    
    if updates.state is not None:
        old_values["state"] = member.state
        member.state = updates.state
        new_values["state"] = updates.state
    
    if updates.zip_code is not None:
        old_values["zip_code"] = member.zip_code
        member.zip_code = updates.zip_code
        new_values["zip_code"] = updates.zip_code
    
    # Recalculate profile completeness
    member.profile_complete = all([
        member.full_name,
        member.address_line1,
        member.city,
        member.state,
        member.zip_code
    ])
    
    # Update engagement date
    member.last_engagement_date = datetime.utcnow()
    
    # Audit log
    if new_values:
        audit = AuditService(db)
        await audit.log_member_action(
            action="profile_updated",
            member_id=member.id,
            actor_id=member.id,
            actor_role="member",
            old_values=old_values,
            new_values=new_values,
            ip_address=get_client_ip(request) if request else None,
            user_agent=get_user_agent(request) if request else None
        )
    
    return member


@router.post("/me/acknowledge-disclosure")
async def acknowledge_disclosure(
    acknowledgment: DisclosureAcknowledge,
    member: Member = Depends(get_current_member),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Acknowledge the membership disclosure.
    Both scrolled and checkbox confirmations are required.
    """
    # Verify disclosure version exists
    result = await db.execute(
        select(DisclosureVersion).where(
            DisclosureVersion.version == acknowledgment.disclosure_version,
            DisclosureVersion.is_current == True
        )
    )
    disclosure = result.scalar_one_or_none()
    
    if not disclosure:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or outdated disclosure version"
        )
    
    # Update member
    member.disclosure_signed_at = datetime.utcnow()
    member.disclosure_version = acknowledgment.disclosure_version
    member.last_engagement_date = datetime.utcnow()
    
    # Audit log
    audit = AuditService(db)
    await audit.log_disclosure_signed(
        member_id=member.id,
        disclosure_version=acknowledgment.disclosure_version,
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else None
    )
    
    return {
        "acknowledged": True,
        "timestamp": member.disclosure_signed_at.isoformat(),
        "version": acknowledgment.disclosure_version
    }


@router.get("/disclosure/current")
async def get_current_disclosure(db: AsyncSession = Depends(get_db)):
    """
    Get the current disclosure text.
    """
    result = await db.execute(
        select(DisclosureVersion).where(DisclosureVersion.is_current == True)
    )
    disclosure = result.scalar_one_or_none()
    
    if not disclosure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current disclosure found"
        )
    
    return {
        "version": disclosure.version,
        "text": disclosure.disclosure_text,
        "created_at": disclosure.created_at.isoformat()
    }

