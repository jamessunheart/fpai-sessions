"""
Webhooks API - Receive events from Stripe, Meta, UC Credits
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
import json
import hmac
import hashlib

from app.database import get_db
from app.models import Conversion, Campaign, Offer
from app.config import settings
from app.integrations.meta_pixel import MetaPixelClient

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events
    
    Events handled:
    - payment_intent.succeeded: Record conversion
    - charge.refunded: Adjust revenue (TODO)
    """
    payload = await request.body()
    
    # Verify signature in production
    if settings.STRIPE_WEBHOOK_SECRET and stripe_signature:
        try:
            import stripe
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {str(e)}")
    else:
        # Development mode - parse directly
        event = json.loads(payload)
    
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    
    if event_type == "payment_intent.succeeded":
        # Extract payment details
        amount = data.get("amount", 0) / 100  # Convert cents to dollars
        currency = data.get("currency", "USD").upper()
        payment_id = data.get("id")
        metadata = data.get("metadata", {})
        
        # Extract attribution data from metadata
        campaign_id = metadata.get("campaign_id")
        offer_id = metadata.get("offer_id")
        utm_source = metadata.get("utm_source")
        utm_medium = metadata.get("utm_medium")
        utm_campaign = metadata.get("utm_campaign")
        utm_content = metadata.get("utm_content")
        fbclid = metadata.get("fbclid")
        fbc = metadata.get("fbc")
        fbp = metadata.get("fbp")
        
        # Customer info
        customer_email = data.get("receipt_email") or metadata.get("customer_email")
        customer_name = metadata.get("customer_name")
        
        # If no campaign_id in metadata, try to attribute via fbclid
        if not campaign_id and fbclid:
            # Look up campaign by recent fbclid (TODO: implement click tracking)
            pass
        
        # Create conversion record
        conversion = Conversion(
            campaign_id=UUID(campaign_id) if campaign_id else None,
            offer_id=UUID(offer_id) if offer_id else None,
            source="stripe",
            external_id=payment_id,
            amount=amount,
            currency=currency,
            customer_email=customer_email,
            customer_name=customer_name,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            fbclid=fbclid,
            fbc=fbc,
            fbp=fbp
        )
        
        db.add(conversion)
        await db.flush()
        
        # Send conversion to Meta Conversions API
        if fbclid or fbc or fbp:
            try:
                pixel_client = MetaPixelClient()
                await pixel_client.send_purchase_event(conversion)
            except Exception as e:
                # Log but don't fail - conversion is still recorded
                print(f"Failed to send to Meta CAPI: {e}")
        
        return {"status": "success", "conversion_id": str(conversion.id)}
    
    elif event_type == "charge.refunded":
        # TODO: Handle refunds - adjust revenue
        return {"status": "acknowledged", "event": "refund"}
    
    return {"status": "ignored", "event": event_type}


@router.post("/uc")
async def uc_credits_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle UC Credits transaction webhook
    
    Called when a purchase is made with UC credits
    """
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Expected payload
    transaction_id = data.get("transaction_id")
    amount_uc = data.get("amount_uc", 0)
    amount_usd = data.get("amount_usd", amount_uc)  # 1 UC = $1
    product_id = data.get("product_id")
    user_id = data.get("user_id")
    metadata = data.get("metadata", {})
    
    # Extract attribution
    campaign_id = metadata.get("campaign_id")
    offer_id = product_id or metadata.get("offer_id")
    utm_source = metadata.get("utm_source")
    utm_campaign = metadata.get("utm_campaign")
    fbclid = metadata.get("fbclid")
    customer_email = metadata.get("email")
    
    # Verify offer exists if provided
    if offer_id:
        offer_result = await db.execute(
            select(Offer).where(Offer.id == UUID(offer_id))
        )
        offer = offer_result.scalar_one_or_none()
        if not offer:
            offer_id = None
    
    # Create conversion
    conversion = Conversion(
        campaign_id=UUID(campaign_id) if campaign_id else None,
        offer_id=UUID(offer_id) if offer_id else None,
        source="uc_credits",
        external_id=transaction_id,
        amount=amount_usd,
        currency="USD",
        customer_email=customer_email,
        utm_source=utm_source,
        utm_campaign=utm_campaign,
        fbclid=fbclid,
        fbc=metadata.get("fbc"),
        fbp=metadata.get("fbp")
    )
    
    db.add(conversion)
    await db.flush()
    
    # Send to Meta CAPI if attributed
    if fbclid or metadata.get("fbc") or metadata.get("fbp"):
        try:
            pixel_client = MetaPixelClient()
            await pixel_client.send_purchase_event(conversion)
        except Exception as e:
            print(f"Failed to send to Meta CAPI: {e}")
    
    return {"status": "success", "conversion_id": str(conversion.id)}


@router.post("/meta")
async def meta_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Meta webhook callbacks
    
    Used for:
    - Webhook verification (GET with hub.challenge)
    - Lead form submissions
    - Other Meta events
    """
    # Check if this is a verification request
    params = dict(request.query_params)
    if "hub.verify_token" in params:
        # Verification request
        verify_token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")
        
        # TODO: Use configured verify token
        if verify_token == "ad_portal_verify":
            return int(challenge)
        raise HTTPException(status_code=403, detail="Invalid verify token")
    
    # Handle webhook event
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Process based on event type
    entry = data.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    
    field = changes.get("field")
    value = changes.get("value", {})
    
    if field == "leadgen":
        # Lead form submission
        lead_id = value.get("leadgen_id")
        form_id = value.get("form_id")
        # TODO: Fetch lead data and process
        return {"status": "acknowledged", "lead_id": lead_id}
    
    return {"status": "ignored", "field": field}


