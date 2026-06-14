"""
WhiteRock Blessings Engine - Tithe Endpoints
Tithe processing with compliance tracking.
v2.2 - With rate limiting
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Member, Tithe, DisclosureVersion
from app.schemas import TitheCreate, TitheResponse, TitheListResponse
from app.auth import get_current_member, get_client_ip, get_user_agent
from app.services.stripe_service import StripeService
from app.services.email_service import EmailService
from app.services.cora_service import CoraService
from app.services.audit_service import AuditService
from app.middleware.rate_limit import limiter
from app.config import settings

router = APIRouter(prefix="/tithes", tags=["Tithes"])


@router.post("", response_model=TitheResponse)
@limiter.limit(settings.RATE_LIMIT_TITHE)
async def submit_tithe(
    request: Request,
    tithe_data: TitheCreate,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a tithe contribution.
    Rate limited to 20 requests per hour per user.
    
    REQUIRES:
    - disclosure_acknowledged = true
    - disclosure_scrolled = true  
    - disclosure_version must match current
    """
    # Validate disclosure confirmation
    if not tithe_data.disclosure_acknowledged or not tithe_data.disclosure_scrolled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both disclosure acknowledgment and scroll confirmation required"
        )
    
    # Get current disclosure
    result = await db.execute(
        select(DisclosureVersion).where(DisclosureVersion.is_current == True)
    )
    current_disclosure = result.scalar_one_or_none()
    
    if not current_disclosure:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No disclosure version configured"
        )
    
    if tithe_data.disclosure_version != current_disclosure.version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disclosure version mismatch. Please refresh and re-acknowledge."
        )
    
    # Process payment through Stripe
    stripe_service = StripeService()
    payment_id, client_secret = await stripe_service.create_payment_intent(
        amount_cents=tithe_data.amount_cents,
        member_id=member.id,
        member_email=member.email,
        description=f"WhiteRock Tithe - Member #{member.id}"
    )
    
    if not payment_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing failed"
        )
    
    # Confirm payment
    success, payment_status = await stripe_service.confirm_payment(
        payment_id, tithe_data.payment_method_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment failed: {payment_status}"
        )
    
    # Create tithe record
    tithe = Tithe(
        member_id=member.id,
        amount_cents=tithe_data.amount_cents,
        currency="USD",
        stripe_payment_id=payment_id,
        stripe_payment_status=payment_status,
        disclosure_acknowledged=True,
        disclosure_text=current_disclosure.disclosure_text,
        disclosure_version=current_disclosure.version,
        disclosure_scrolled_confirmed=True
    )
    
    db.add(tithe)
    await db.flush()
    
    # Update member engagement
    member.last_engagement_date = datetime.utcnow()
    
    # Calculate cumulative tithes for milestone check
    result = await db.execute(
        select(func.sum(Tithe.amount_cents)).where(Tithe.member_id == member.id)
    )
    cumulative_cents = result.scalar_one() or 0
    
    # Check and grant CORA for milestones
    cora_service = CoraService(db)
    cora_granted = await cora_service.check_tithe_milestones(member.id, cumulative_cents)
    tithe.cora_granted = cora_granted
    
    # Audit log
    audit_service = AuditService(db)
    await audit_service.log_tithe(
        tithe_id=tithe.id,
        member_id=member.id,
        amount_cents=tithe_data.amount_cents,
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else None
    )
    
    # Send receipt email
    email_service = EmailService()
    await email_service.send_tithe_receipt(
        to_email=member.email,
        member_name=member.full_name,
        amount_cents=tithe.amount_cents,
        tithe_id=tithe.id,
        disclosure_version=tithe.disclosure_version,
        created_at=tithe.created_at
    )
    
    tithe.receipt_sent_at = datetime.utcnow()
    
    return tithe


@router.get("/me", response_model=TitheListResponse)
async def get_my_tithes(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current member's tithe history.
    """
    result = await db.execute(
        select(Tithe).where(Tithe.member_id == member.id)
        .order_by(Tithe.created_at.desc())
    )
    tithes = result.scalars().all()
    
    total_contributed = sum(t.amount_cents for t in tithes)
    
    return TitheListResponse(
        tithes=[TitheResponse.model_validate(t) for t in tithes],
        total_contributed_cents=total_contributed
    )


@router.get("/{tithe_id}", response_model=TitheResponse)
async def get_tithe(
    tithe_id: int,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific tithe record.
    """
    result = await db.execute(
        select(Tithe).where(
            Tithe.id == tithe_id,
            Tithe.member_id == member.id
        )
    )
    tithe = result.scalar_one_or_none()
    
    if not tithe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tithe not found"
        )
    
    return tithe


@router.get("/{tithe_id}/receipt")
async def get_tithe_receipt(
    tithe_id: int,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate PDF receipt for a tithe.
    """
    result = await db.execute(
        select(Tithe).where(
            Tithe.id == tithe_id,
            Tithe.member_id == member.id
        )
    )
    tithe = result.scalar_one_or_none()
    
    if not tithe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tithe not found"
        )
    
    # Generate simple HTML receipt (could be enhanced with proper PDF generation)
    receipt_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WhiteRock Tithe Receipt #{tithe_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
            .header {{ text-align: center; border-bottom: 2px solid #1e3a8a; padding-bottom: 20px; }}
            .amount {{ font-size: 36px; color: #10b981; text-align: center; margin: 30px 0; }}
            .details {{ background: #f9fafb; padding: 20px; border-radius: 8px; }}
            .disclaimer {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin-top: 30px; font-size: 12px; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>WhiteRock Church Trust</h1>
            <p>508(c)(1)(A) Religious Organization</p>
            <h2>Tithe Receipt</h2>
        </div>
        
        <div class="amount">
            ${tithe.amount_cents / 100:,.2f} USD
        </div>
        
        <div class="details">
            <p><strong>Receipt Number:</strong> {tithe.id}</p>
            <p><strong>Member:</strong> {member.full_name}</p>
            <p><strong>Email:</strong> {member.email}</p>
            <p><strong>Date:</strong> {tithe.created_at.strftime('%B %d, %Y at %I:%M %p UTC')}</p>
            <p><strong>Disclosure Version:</strong> {tithe.disclosure_version}</p>
            <p><strong>Payment Reference:</strong> {tithe.stripe_payment_id or 'N/A'}</p>
        </div>
        
        <div class="disclaimer">
            <strong>IMPORTANT DISCLOSURE</strong><br><br>
            {tithe.disclosure_text}
        </div>
        
        <div class="footer">
            <p>This receipt was generated electronically and is valid without signature.</p>
            <p>WhiteRock Church Trust | whiterock.us</p>
        </div>
    </body>
    </html>
    """
    
    return StreamingResponse(
        iter([receipt_html.encode()]),
        media_type="text/html",
        headers={
            "Content-Disposition": f"inline; filename=tithe-receipt-{tithe_id}.html"
        }
    )

