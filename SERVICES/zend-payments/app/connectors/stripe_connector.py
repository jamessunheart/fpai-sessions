"""Stripe connector for Zend Payments.

Per docs/protocols/ZEND_REGENERATIVE_SPEC.md Part 7.1:
- Mode: Hosted checkout (non-custodial)
- Flow: Create checkout session → redirect user → webhook confirms payment
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)

# Lazy import stripe
stripe = None


def _get_stripe():
    """Lazy load Stripe SDK."""
    global stripe
    if stripe is None:
        try:
            import stripe as stripe_module
            stripe = stripe_module
            stripe.api_key = settings.STRIPE_SECRET_KEY
        except ImportError:
            logger.warning("Stripe SDK not installed")
            return None
    return stripe


class StripeConnector:
    """Stripe hosted checkout connector."""

    def __init__(self):
        self.enabled = settings.STRIPE_ENABLED and bool(settings.STRIPE_SECRET_KEY)

    async def create_checkout_session(
        self,
        intent_id: str,
        amount: float,
        currency: str,
        recipient_name: str,
        note: Optional[str] = None,
        success_url: str = None,
        cancel_url: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe hosted checkout session.
        Returns checkout URL and session ID.
        """
        if not self.enabled:
            return None

        stripe = _get_stripe()
        if not stripe:
            return None

        try:
            # Convert amount to cents
            amount_cents = int(amount * 100)

            # Build line items
            line_items = [{
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {
                        "name": f"Zend to {recipient_name}",
                        "description": note or "Zend Money Transfer",
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }]

            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=success_url or f"{settings.ZENDLINK_BASE_URL}/success?intent={intent_id}",
                cancel_url=cancel_url or f"{settings.ZENDLINK_BASE_URL}/cancel?intent={intent_id}",
                metadata={
                    "intent_id": intent_id,
                    "source": "zend-payments",
                    **(metadata or {}),
                },
                expires_at=int((datetime.utcnow().timestamp()) + settings.INTENT_EXPIRY_MINUTES * 60),
            )

            return {
                "checkout_session_id": session.id,
                "checkout_url": session.url,
                "payment_intent_id": session.payment_intent,
            }

        except Exception as e:
            logger.error(f"Stripe checkout creation failed: {e}")
            return None

    async def verify_webhook(self, payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
        """Verify and parse Stripe webhook."""
        if not self.enabled:
            return None

        stripe = _get_stripe()
        if not stripe:
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET,
            )
            return {
                "type": event["type"],
                "data": event["data"]["object"],
            }
        except Exception as e:
            logger.error(f"Stripe webhook verification failed: {e}")
            return None

    async def get_payment_status(self, payment_intent_id: str) -> Optional[Dict[str, Any]]:
        """Get payment intent status from Stripe."""
        if not self.enabled:
            return None

        stripe = _get_stripe()
        if not stripe:
            return None

        try:
            pi = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "status": pi.status,
                "amount": pi.amount / 100,
                "currency": pi.currency.upper(),
                "payment_method": pi.payment_method,
                "receipt_email": pi.receipt_email,
            }
        except Exception as e:
            logger.error(f"Stripe payment status fetch failed: {e}")
            return None


# Singleton
stripe_connector = StripeConnector()




