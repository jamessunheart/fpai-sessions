"""
WhiteRock Blessings Engine - Stripe Service
Payment processing for tithe contributions.
"""

import stripe
from datetime import datetime
from typing import Optional, Tuple
from app.config import settings

# Configure Stripe
if settings.STRIPE_API_KEY:
    stripe.api_key = settings.STRIPE_API_KEY


class StripeService:
    """Service for Stripe payment processing."""
    
    def __init__(self):
        self.api_key = settings.STRIPE_API_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    async def create_payment_intent(
        self,
        amount_cents: int,
        member_id: int,
        member_email: str,
        description: str = "WhiteRock Tithe Contribution"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Create a Stripe PaymentIntent for tithe processing.
        
        Returns:
            Tuple of (payment_intent_id, client_secret) or (None, None) on error
        """
        if not self.api_key:
            # Development mode - return mock
            return f"pi_mock_{member_id}_{datetime.utcnow().timestamp()}", "mock_secret"
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                metadata={
                    "member_id": str(member_id),
                    "type": "tithe",
                    "source": "whiterock"
                },
                receipt_email=member_email,
                description=description,
                statement_descriptor="WHITEROCK TITHE"
            )
            return intent.id, intent.client_secret
        except stripe.error.StripeError as e:
            print(f"[STRIPE] Payment intent failed: {e}")
            return None, None
    
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str
    ) -> Tuple[bool, str]:
        """
        Confirm a payment intent with a payment method.
        
        Returns:
            Tuple of (success, status/error_message)
        """
        if not self.api_key:
            # Development mode - simulate success
            return True, "succeeded"
        
        try:
            intent = stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method=payment_method_id
            )
            return intent.status == "succeeded", intent.status
        except stripe.error.CardError as e:
            return False, f"Card error: {e.user_message}"
        except stripe.error.StripeError as e:
            return False, f"Payment failed: {str(e)}"
    
    async def get_payment_status(self, payment_intent_id: str) -> str:
        """Get the status of a payment intent."""
        if not self.api_key:
            return "succeeded"
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return intent.status
        except stripe.error.StripeError as e:
            print(f"[STRIPE] Get status failed: {e}")
            return "unknown"
    
    async def create_checkout_session(
        self,
        amount_cents: int,
        member_id: int,
        member_email: str,
        success_url: str,
        cancel_url: str
    ) -> Optional[str]:
        """
        Create a Stripe Checkout Session for tithe contribution.
        
        Returns:
            Checkout session URL or None on error
        """
        if not self.api_key:
            return f"https://checkout.stripe.com/mock?amount={amount_cents}"
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card", "us_bank_account"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": amount_cents,
                        "product_data": {
                            "name": "WhiteRock Tithe Contribution",
                            "description": "Sacred contribution to WhiteRock Church Trust"
                        }
                    },
                    "quantity": 1
                }],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=member_email,
                metadata={
                    "member_id": str(member_id),
                    "type": "tithe",
                    "source": "whiterock"
                }
            )
            return session.url
        except stripe.error.StripeError as e:
            print(f"[STRIPE] Checkout session failed: {e}")
            return None
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> Optional[dict]:
        """
        Verify and parse a Stripe webhook event.
        
        Returns:
            Event dict or None if verification fails
        """
        if not self.webhook_secret:
            # Dev mode - parse without verification
            import json
            try:
                return json.loads(payload)
            except Exception:
                return None
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            return event
        except (stripe.error.SignatureVerificationError, ValueError) as e:
            print(f"[STRIPE] Webhook verification failed: {e}")
            return None
    
    async def process_successful_payment(
        self,
        payment_intent_id: str
    ) -> dict:
        """
        Extract payment details from a successful payment intent.
        
        Returns:
            Dict with amount_cents, member_id, receipt_url
        """
        if not self.api_key:
            return {
                "amount_cents": 0,
                "member_id": None,
                "receipt_url": None
            }
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Get receipt URL from charges
            receipt_url = None
            if intent.latest_charge:
                charge = stripe.Charge.retrieve(intent.latest_charge)
                receipt_url = charge.receipt_url
            
            return {
                "amount_cents": intent.amount,
                "member_id": int(intent.metadata.get("member_id", 0)),
                "receipt_url": receipt_url
            }
        except stripe.error.StripeError as e:
            print(f"[STRIPE] Get payment details failed: {e}")
            return {
                "amount_cents": 0,
                "member_id": None,
                "receipt_url": None
            }



