"""
Stripe Subscription Management — FP Index Pro/Premium Tiers
=============================================================

Handles checkout session creation, webhook processing, and
subscriber status tracking.

Pro:     $49/mo — weekly allocation report, daily briefing email, API access
Premium: $199/mo — daily allocation, real-time alerts, priority API
"""

import logging
import os
import secrets
from datetime import datetime, timezone

import stripe
from sqlalchemy import select

from .models.database import async_session, EmailSubscriberRow

logger = logging.getLogger("fp_index.subscriptions")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

PRODUCTS = {
    "pro": {
        "name": "FP Index Pro",
        "price_cents": 4900,
        "interval": "month",
        "features": [
            "Weekly FP Frontier Allocation Report",
            "Daily AI briefing email",
            "Full dimension breakdown",
            "Top signals + sector analysis",
            "API access (2,000 calls/hr)",
            "Rebalance alerts",
        ],
    },
    "premium": {
        "name": "FP Index Premium",
        "price_cents": 19900,
        "interval": "month",
        "features": [
            "Daily allocation updates",
            "Real-time rebalance alerts",
            "Displacement investment signals",
            "Custom sector watchlists",
            "Hypothetical portfolio tracker",
            "Priority API (10,000 calls/hr) + webhooks",
        ],
    },
}

_price_cache: dict[str, str] = {}


async def _get_or_create_price(tier: str) -> str:
    """Get or create a Stripe Price for the given tier."""
    if tier in _price_cache:
        return _price_cache[tier]

    product_config = PRODUCTS[tier]

    prices = stripe.Price.list(
        lookup_keys=[f"fp_index_{tier}"],
        active=True,
        limit=1,
    )
    if prices.data:
        _price_cache[tier] = prices.data[0].id
        return prices.data[0].id

    products = stripe.Product.list(limit=100)
    product_id = None
    for p in products.data:
        if p.name == product_config["name"] and p.active:
            product_id = p.id
            break

    if not product_id:
        product = stripe.Product.create(
            name=product_config["name"],
            description=f"Full Potential Index — {tier.title()} tier subscription",
        )
        product_id = product.id

    price = stripe.Price.create(
        product=product_id,
        unit_amount=product_config["price_cents"],
        currency="usd",
        recurring={"interval": product_config["interval"]},
        lookup_key=f"fp_index_{tier}",
    )
    _price_cache[tier] = price.id
    return price.id


async def create_checkout_session(tier: str, success_url: str, cancel_url: str) -> dict:
    """Create a Stripe Checkout Session for a subscription."""
    if tier not in PRODUCTS:
        raise ValueError(f"Unknown tier: {tier}")

    price_id = await _get_or_create_price(tier)

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tier": tier, "product": "fp_index"},
    )

    return {
        "checkout_url": session.url,
        "session_id": session.id,
    }


def generate_api_key() -> str:
    """Generate a unique API key for a Pro/Premium subscriber."""
    return f"fpi_{secrets.token_urlsafe(32)}"


async def handle_webhook_event(payload: bytes, sig_header: str) -> dict:
    """Process a Stripe webhook event."""
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        return {"error": "Invalid signature"}
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return {"error": str(e)}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_details", {}).get("email", "")
        tier = session.get("metadata", {}).get("tier", "pro")
        customer_id = session.get("customer", "")
        subscription_id = session.get("subscription", "")

        api_key = generate_api_key()

        async with async_session() as db:
            existing = (await db.execute(
                select(EmailSubscriberRow).where(EmailSubscriberRow.email == customer_email)
            )).scalar_one_or_none()

            if existing:
                existing.tier = tier
                existing.stripe_customer_id = customer_id
                existing.stripe_subscription_id = subscription_id
                existing.api_key = api_key
                existing.subscribed_at = datetime.now(timezone.utc)
            else:
                db.add(EmailSubscriberRow(
                    email=customer_email,
                    tier=tier,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id,
                    api_key=api_key,
                ))
            await db.commit()

        logger.info(f"New {tier} subscriber: {customer_email} (sub: {subscription_id})")
        return {"status": "provisioned", "tier": tier, "email": customer_email}

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        sub_id = subscription.get("id", "")

        async with async_session() as db:
            existing = (await db.execute(
                select(EmailSubscriberRow).where(
                    EmailSubscriberRow.stripe_subscription_id == sub_id
                )
            )).scalar_one_or_none()
            if existing:
                existing.tier = "free"
                existing.api_key = None
                await db.commit()
                logger.info(f"Subscription cancelled: {existing.email}")

        return {"status": "cancelled", "subscription_id": sub_id}

    return {"status": "ignored", "type": event["type"]}


async def validate_subscriber_key(api_key: str) -> dict | None:
    """Validate a subscriber API key and return tier info."""
    if not api_key or not api_key.startswith("fpi_"):
        return None

    async with async_session() as db:
        result = await db.execute(
            select(EmailSubscriberRow).where(
                EmailSubscriberRow.api_key == api_key,
                EmailSubscriberRow.active == True,
            )
        )
        subscriber = result.scalar_one_or_none()
        if not subscriber:
            return None

        tier = subscriber.tier or "free"
        if tier == "free":
            return None

        rate_limits = {"pro": 2000, "premium": 10000}

        return {
            "email": subscriber.email,
            "tier": tier,
            "rate_limit_per_hour": rate_limits.get(tier, 100),
            "subscribed_at": subscriber.subscribed_at.isoformat() if subscriber.subscribed_at else None,
        }
