"""
Zend Payments Service v1.0 - External Settlement Layer
=======================================================

Service: zend-payments
Port: 8581

Implements:
- PaymentIntent creation and management
- ZendLink (Blessing Links) resolution
- Stripe hosted checkout integration
- Solana USDC payment requests
- Settlement receipts

Source of truth:
- docs/protocols/ZEND_REGENERATIVE_SPEC.md (v2.0)
"""
from __future__ import annotations

import secrets
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import httpx
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import settings
from .database import get_db, init_db
from .db_models import PaymentIntentRecord, ZendReceiptRecord, MerchantRecord
from .models import (
    CreateIntentRequest, PaymentIntent, ConfirmIntentRequest, IntentResponse,
    ZendLinkResponse, ZendReceipt, CreateInvoiceRequest, InvoiceResponse,
    IntentStatus, RailPolicy, ConfirmLevel
)
from .connectors.stripe_connector import stripe_connector
from .connectors.solana_connector import solana_connector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _generate_code(length: int = 8) -> str:
    """Generate a short alphanumeric code for ZendLinks."""
    return secrets.token_urlsafe(length)[:length].lower()


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Zend Payments",
    version=settings.SERVICE_VERSION,
    description="External settlement layer for Zend Money",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "rails": {
            "stripe": stripe_connector.enabled,
            "solana": solana_connector.enabled,
        },
        "timestamp": _utc_now_iso(),
    }


# ============================================================
# PAYMENT INTENTS
# ============================================================

async def _assess_risk(amount: float, payer_id: Optional[str], recipient_id: str) -> tuple[float, ConfirmLevel]:
    """Simple risk assessment. Returns (risk_score, confirm_level)."""
    risk_score = 0.0

    if amount > 1000:
        risk_score += 0.3
    if amount > 5000:
        risk_score += 0.3
    if not payer_id:
        risk_score += 0.1  # Open payment request
    
    # Confirm level based on risk
    if risk_score >= 0.5:
        return risk_score, ConfirmLevel.FULL
    if risk_score >= 0.2:
        return risk_score, ConfirmLevel.LIGHT
    return risk_score, ConfirmLevel.NONE


@app.post("/api/intents", response_model=PaymentIntent)
async def create_intent(
    request: CreateIntentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new payment intent.
    Returns intent with ZendLink and available rails.
    """
    # Validate amount
    if request.amount > settings.MAX_INTENT_AMOUNT:
        raise HTTPException(400, f"Amount exceeds max ({settings.MAX_INTENT_AMOUNT})")

    # Generate IDs
    intent_id = f"pi_{secrets.token_hex(12)}"
    zend_link_code = _generate_code(8)

    # Risk assessment
    risk_score, confirm_level = await _assess_risk(
        request.amount, request.payer_id, request.recipient_id
    )

    # Calculate expiry
    expires_at = _utc_now() + timedelta(minutes=request.expires_in_minutes)

    # Create intent record
    record = PaymentIntentRecord(
        intent_id=intent_id,
        payer_id=request.payer_id,
        recipient_id=request.recipient_id,
        amount=request.amount,
        currency=request.currency,
        rail_policy=request.rail_policy.value,
        commons_contribution_pct=request.commons_contribution_pct,
        note=request.note,
        risk_score=risk_score,
        confirm_level=confirm_level.value,
        status=IntentStatus.PENDING.value,
        expires_at=expires_at,
        zend_link_code=zend_link_code,
        extra_data=request.metadata,
    )

    # Create Stripe checkout if enabled
    stripe_checkout_url = None
    if stripe_connector.enabled and request.rail_policy in (RailPolicy.STRIPE_FIRST, RailPolicy.USER_CHOICE):
        stripe_result = await stripe_connector.create_checkout_session(
            intent_id=intent_id,
            amount=request.amount,
            currency=request.currency,
            recipient_name=request.recipient_id,
            note=request.note,
            metadata={"zend_link_code": zend_link_code},
        )
        if stripe_result:
            record.stripe_checkout_session_id = stripe_result["checkout_session_id"]
            record.stripe_checkout_url = stripe_result["checkout_url"]
            record.stripe_payment_intent_id = stripe_result.get("payment_intent_id")
            stripe_checkout_url = stripe_result["checkout_url"]

    # Create Solana payment request if enabled
    solana_payment_request = None
    if solana_connector.enabled and request.rail_policy in (RailPolicy.SOLANA_FIRST, RailPolicy.USER_CHOICE):
        # For now, we'd need recipient's Solana wallet
        # This would come from merchant record or user profile
        pass

    db.add(record)
    await db.commit()

    zend_link = f"{settings.ZENDLINK_BASE_URL}/{zend_link_code}"

    return PaymentIntent(
        intent_id=intent_id,
        payer_id=request.payer_id,
        recipient_id=request.recipient_id,
        amount=request.amount,
        currency=request.currency,
        rail_policy=request.rail_policy,
        commons_contribution_pct=request.commons_contribution_pct,
        note=request.note,
        risk_score=risk_score,
        confirm_level=confirm_level,
        status=IntentStatus.PENDING,
        created_at=record.created_at,
        expires_at=expires_at,
        settled_at=None,
        zend_link=zend_link,
        zend_link_code=zend_link_code,
        stripe_checkout_url=stripe_checkout_url,
        stripe_payment_intent_id=record.stripe_payment_intent_id,
        solana_payment_request=solana_payment_request,
        solana_tx_signature=None,
    )


@app.get("/api/intents/{intent_id}", response_model=PaymentIntent)
async def get_intent(intent_id: str, db: AsyncSession = Depends(get_db)):
    """Get a payment intent by ID."""
    result = await db.execute(
        select(PaymentIntentRecord).where(PaymentIntentRecord.intent_id == intent_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(404, "Intent not found")

    return PaymentIntent(
        intent_id=record.intent_id,
        payer_id=record.payer_id,
        recipient_id=record.recipient_id,
        amount=record.amount,
        currency=record.currency,
        rail_policy=RailPolicy(record.rail_policy),
        commons_contribution_pct=record.commons_contribution_pct,
        note=record.note,
        risk_score=record.risk_score,
        confirm_level=ConfirmLevel(record.confirm_level),
        status=IntentStatus(record.status),
        created_at=record.created_at,
        expires_at=record.expires_at,
        settled_at=record.settled_at,
        zend_link=f"{settings.ZENDLINK_BASE_URL}/{record.zend_link_code}",
        zend_link_code=record.zend_link_code,
        stripe_checkout_url=record.stripe_checkout_url,
        stripe_payment_intent_id=record.stripe_payment_intent_id,
        solana_payment_request=record.solana_payment_request,
        solana_tx_signature=record.solana_tx_signature,
    )


@app.post("/api/intents/{intent_id}/confirm", response_model=IntentResponse)
async def confirm_intent(
    intent_id: str,
    request: ConfirmIntentRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """
    Confirm a payment intent after settlement.
    For Stripe: Called by webhook.
    For Solana: Called with tx_signature after user signs.
    """
    result = await db.execute(
        select(PaymentIntentRecord).where(PaymentIntentRecord.intent_id == intent_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(404, "Intent not found")

    if record.status == IntentStatus.SETTLED.value:
        return IntentResponse(
            success=True,
            intent_id=intent_id,
            status=IntentStatus.SETTLED,
            message="Already settled",
            zend_link=f"{settings.ZENDLINK_BASE_URL}/{record.zend_link_code}",
        )

    if record.status != IntentStatus.PENDING.value:
        raise HTTPException(400, f"Intent not confirmable (status: {record.status})")

    # Check expiry
    if record.expires_at < _utc_now():
        record.status = IntentStatus.EXPIRED.value
        await db.commit()
        raise HTTPException(400, "Intent has expired")

    # Verify based on rail
    external_ref = None
    if request.rail == "stripe":
        if record.stripe_payment_intent_id:
            status = await stripe_connector.get_payment_status(record.stripe_payment_intent_id)
            if status and status.get("status") == "succeeded":
                external_ref = record.stripe_payment_intent_id
            else:
                raise HTTPException(400, "Stripe payment not confirmed")
        else:
            raise HTTPException(400, "No Stripe payment intent for this intent")

    elif request.rail == "solana":
        if not request.tx_signature:
            raise HTTPException(400, "tx_signature required for Solana confirmation")

        verification = await solana_connector.verify_transaction(
            request.tx_signature, record.amount, record.recipient_id
        )
        if verification and verification.get("status") == "confirmed":
            external_ref = request.tx_signature
            record.solana_tx_signature = request.tx_signature
        else:
            raise HTTPException(400, "Solana transaction not confirmed")

    else:
        raise HTTPException(400, f"Unknown rail: {request.rail}")

    # Mark as settled
    record.status = IntentStatus.SETTLED.value
    record.settled_at = _utc_now()
    record.confirmed_at = _utc_now()

    # Calculate Commons contribution
    commons_contributed = round(record.amount * record.commons_contribution_pct / 100, 2)

    # Create receipt
    receipt = ZendReceiptRecord(
        receipt_id=f"rcpt_{secrets.token_hex(8)}",
        intent_id=intent_id,
        rail=request.rail,
        external_ref=external_ref,
        amount_settled=record.amount,
        commons_contributed=commons_contributed,
        settled_at=_utc_now(),
        blessing_message=record.note,
        payer_id=record.payer_id,
        recipient_id=record.recipient_id,
    )
    db.add(receipt)

    await db.commit()

    # TODO: Trigger Credits Gateway Zend fee collection in background
    # if background_tasks and commons_contributed > 0:
    #     background_tasks.add_task(collect_zend_fee, commons_contributed)

    return IntentResponse(
        success=True,
        intent_id=intent_id,
        status=IntentStatus.SETTLED,
        message=f"Settled via {request.rail}",
        zend_link=f"{settings.ZENDLINK_BASE_URL}/{record.zend_link_code}",
    )


@app.post("/api/intents/{intent_id}/cancel", response_model=IntentResponse)
async def cancel_intent(intent_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel a pending payment intent."""
    result = await db.execute(
        select(PaymentIntentRecord).where(PaymentIntentRecord.intent_id == intent_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(404, "Intent not found")

    if record.status != IntentStatus.PENDING.value:
        raise HTTPException(400, f"Cannot cancel intent in status: {record.status}")

    record.status = IntentStatus.CANCELLED.value
    await db.commit()

    return IntentResponse(
        success=True,
        intent_id=intent_id,
        status=IntentStatus.CANCELLED,
        message="Intent cancelled",
    )


# ============================================================
# ZENDLINK RESOLUTION
# ============================================================

@app.get("/api/links/{code}", response_model=ZendLinkResponse)
async def resolve_zendlink(code: str, db: AsyncSession = Depends(get_db)):
    """
    Resolve a ZendLink code to its payment intent.
    This is what the zend.to/<code> page calls to get payment details.
    """
    result = await db.execute(
        select(PaymentIntentRecord).where(PaymentIntentRecord.zend_link_code == code)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(404, "Link not found")

    # Check expiry
    status = IntentStatus(record.status)
    if record.expires_at < _utc_now() and status == IntentStatus.PENDING:
        record.status = IntentStatus.EXPIRED.value
        await db.commit()
        status = IntentStatus.EXPIRED

    return ZendLinkResponse(
        code=code,
        intent_id=record.intent_id,
        recipient_id=record.recipient_id,
        recipient_name=None,  # Would come from user profile
        amount=record.amount,
        currency=record.currency,
        note=record.note,
        commons_badge=record.commons_contribution_pct > 0,
        status=status,
        expires_at=record.expires_at,
        stripe_available=bool(record.stripe_checkout_url),
        solana_available=bool(record.solana_payment_request),
    )


@app.get("/{code}")
async def redirect_zendlink(code: str, db: AsyncSession = Depends(get_db)):
    """
    Redirect short ZendLink to full payment page or Stripe checkout.
    """
    result = await db.execute(
        select(PaymentIntentRecord).where(PaymentIntentRecord.zend_link_code == code)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(404, "Link not found")

    # If Stripe checkout available, redirect directly
    if record.stripe_checkout_url and record.status == IntentStatus.PENDING.value:
        return RedirectResponse(url=record.stripe_checkout_url)

    # Otherwise redirect to payment page
    return RedirectResponse(url=f"{settings.ZENDLINK_BASE_URL}/pay/{code}")


# ============================================================
# RECEIPTS
# ============================================================

@app.get("/api/receipts/{receipt_id}", response_model=ZendReceipt)
async def get_receipt(receipt_id: str, db: AsyncSession = Depends(get_db)):
    """Get a settlement receipt."""
    result = await db.execute(
        select(ZendReceiptRecord).where(ZendReceiptRecord.receipt_id == receipt_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(404, "Receipt not found")

    return ZendReceipt(
        receipt_id=record.receipt_id,
        intent_id=record.intent_id,
        rail=record.rail,
        external_ref=record.external_ref,
        amount_settled=record.amount_settled,
        commons_contributed=record.commons_contributed,
        settled_at=record.settled_at,
        blessing_message=record.blessing_message,
        payer_id=record.payer_id,
        recipient_id=record.recipient_id,
    )


@app.get("/api/receipts/intent/{intent_id}", response_model=ZendReceipt)
async def get_receipt_by_intent(intent_id: str, db: AsyncSession = Depends(get_db)):
    """Get receipt for an intent."""
    result = await db.execute(
        select(ZendReceiptRecord).where(ZendReceiptRecord.intent_id == intent_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(404, "Receipt not found")

    return ZendReceipt(
        receipt_id=record.receipt_id,
        intent_id=record.intent_id,
        rail=record.rail,
        external_ref=record.external_ref,
        amount_settled=record.amount_settled,
        commons_contributed=record.commons_contributed,
        settled_at=record.settled_at,
        blessing_message=record.blessing_message,
        payer_id=record.payer_id,
        recipient_id=record.recipient_id,
    )


# ============================================================
# WEBHOOKS
# ============================================================

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Stripe webhooks for payment confirmations.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = await stripe_connector.verify_webhook(payload, sig_header)
    if not event:
        raise HTTPException(400, "Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]

    if event_type == "checkout.session.completed":
        # Find intent by Stripe session ID
        session_id = data.get("id")
        result = await db.execute(
            select(PaymentIntentRecord).where(
                PaymentIntentRecord.stripe_checkout_session_id == session_id
            )
        )
        record = result.scalar_one_or_none()

        if record and record.status == IntentStatus.PENDING.value:
            # Auto-confirm
            record.status = IntentStatus.SETTLED.value
            record.settled_at = _utc_now()
            record.confirmed_at = _utc_now()
            record.stripe_payment_intent_id = data.get("payment_intent")

            # Create receipt
            commons_contributed = round(record.amount * record.commons_contribution_pct / 100, 2)
            receipt = ZendReceiptRecord(
                receipt_id=f"rcpt_{secrets.token_hex(8)}",
                intent_id=record.intent_id,
                rail="stripe",
                external_ref=data.get("payment_intent") or session_id,
                amount_settled=record.amount,
                commons_contributed=commons_contributed,
                settled_at=_utc_now(),
                blessing_message=record.note,
                payer_id=data.get("customer_email"),
                recipient_id=record.recipient_id,
            )
            db.add(receipt)
            await db.commit()

            logger.info(f"Intent {record.intent_id} settled via Stripe webhook")

    return {"status": "ok"}


# ============================================================
# POS / MERCHANT
# ============================================================

@app.post("/api/invoices", response_model=InvoiceResponse)
async def create_invoice(
    request: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a merchant invoice (payment request).
    Used by POS systems (Telegram bot, etc.)
    """
    # Create underlying payment intent
    intent_request = CreateIntentRequest(
        recipient_id=request.merchant_id,
        amount=request.total,
        currency=request.currency,
        rail_policy=RailPolicy.STRIPE_FIRST,
        commons_contribution_pct=request.commons_tithe_pct,
        note=request.note,
        expires_in_minutes=request.expires_in_minutes,
        metadata={"items": request.items, "type": "invoice"},
    )

    intent = await create_intent(intent_request, db)

    # Generate QR code URL (would need QR generation endpoint)
    qr_code_url = f"/api/qr/{intent.zend_link_code}"

    return InvoiceResponse(
        invoice_id=intent.intent_id,
        intent_id=intent.intent_id,
        zend_link=intent.zend_link,
        qr_code_url=qr_code_url,
        amount=request.total,
        currency=request.currency,
        status=intent.status,
        expires_at=intent.expires_at,
    )


@app.get("/api/qr/{code}")
async def get_qr_code(code: str):
    """Generate QR code for a ZendLink."""
    try:
        import qrcode
        import io
        from fastapi.responses import StreamingResponse

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f"{settings.ZENDLINK_BASE_URL}/{code}")
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return StreamingResponse(buf, media_type="image/png")
    except ImportError:
        raise HTTPException(501, "QR code generation not available")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT)




