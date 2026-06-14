"""
Stripe Integration

Handle Stripe payments and webhooks for conversion tracking.
"""
import stripe
from typing import Dict, Optional
from app.config import settings


class StripeClient:
    """
    Stripe API client for payment operations
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.STRIPE_SECRET_KEY
        stripe.api_key = self.api_key
    
    async def create_payment_link(
        self,
        offer_id: str,
        offer_name: str,
        price_cents: int,
        campaign_id: str = None,
        utm_source: str = None,
        utm_campaign: str = None,
        fbclid: str = None
    ) -> Dict:
        """
        Create a Stripe payment link with attribution metadata
        
        Args:
            offer_id: Internal offer ID
            offer_name: Display name
            price_cents: Price in cents
            campaign_id: Campaign ID for attribution
            utm_source: UTM source
            utm_campaign: UTM campaign
            fbclid: Facebook click ID
            
        Returns:
            Dict with payment link URL
        """
        # Build metadata for attribution
        metadata = {
            "offer_id": offer_id,
            "source": "ad_portal"
        }
        
        if campaign_id:
            metadata["campaign_id"] = campaign_id
        if utm_source:
            metadata["utm_source"] = utm_source
        if utm_campaign:
            metadata["utm_campaign"] = utm_campaign
        if fbclid:
            metadata["fbclid"] = fbclid
        
        # Create a price
        price = stripe.Price.create(
            currency="usd",
            unit_amount=price_cents,
            product_data={
                "name": offer_name,
                "metadata": metadata
            }
        )
        
        # Create payment link
        link = stripe.PaymentLink.create(
            line_items=[{
                "price": price.id,
                "quantity": 1
            }],
            metadata=metadata,
            after_completion={
                "type": "redirect",
                "redirect": {
                    "url": f"https://fullpotential.ai/thank-you?offer={offer_id}"
                }
            }
        )
        
        return {
            "url": link.url,
            "id": link.id,
            "price_id": price.id
        }
    
    async def create_checkout_session(
        self,
        offer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        customer_email: str = None,
        campaign_id: str = None,
        utm_params: Dict = None,
        fbclid: str = None,
        fbc: str = None,
        fbp: str = None
    ) -> Dict:
        """
        Create a Stripe Checkout session with full attribution
        
        Returns checkout URL to redirect customer to
        """
        metadata = {
            "offer_id": offer_id,
            "source": "ad_portal"
        }
        
        if campaign_id:
            metadata["campaign_id"] = campaign_id
        
        if utm_params:
            metadata.update({
                "utm_source": utm_params.get("utm_source"),
                "utm_medium": utm_params.get("utm_medium"),
                "utm_campaign": utm_params.get("utm_campaign"),
                "utm_content": utm_params.get("utm_content"),
                "utm_term": utm_params.get("utm_term")
            })
        
        if fbclid:
            metadata["fbclid"] = fbclid
        if fbc:
            metadata["fbc"] = fbc
        if fbp:
            metadata["fbp"] = fbp
        
        # Clean None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        session_params = {
            "mode": "payment",
            "line_items": [{
                "price": price_id,
                "quantity": 1
            }],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata,
            "payment_intent_data": {
                "metadata": metadata  # Also attach to payment intent
            }
        }
        
        if customer_email:
            session_params["customer_email"] = customer_email
        
        session = stripe.checkout.Session.create(**session_params)
        
        return {
            "url": session.url,
            "session_id": session.id
        }
    
    async def get_payment_intent(self, payment_intent_id: str) -> Dict:
        """Get payment intent details"""
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return {
            "id": intent.id,
            "amount": intent.amount / 100,
            "currency": intent.currency.upper(),
            "status": intent.status,
            "metadata": dict(intent.metadata),
            "receipt_email": intent.receipt_email
        }
    
    async def list_recent_payments(
        self,
        limit: int = 100,
        created_after: int = None
    ) -> list:
        """
        List recent successful payments
        
        Args:
            limit: Max number to return
            created_after: Unix timestamp
            
        Returns:
            List of payment intents
        """
        params = {
            "limit": limit,
            "expand": ["data.customer"]
        }
        
        if created_after:
            params["created"] = {"gte": created_after}
        
        intents = stripe.PaymentIntent.list(**params)
        
        return [
            {
                "id": intent.id,
                "amount": intent.amount / 100,
                "currency": intent.currency.upper(),
                "status": intent.status,
                "metadata": dict(intent.metadata),
                "receipt_email": intent.receipt_email,
                "created": intent.created
            }
            for intent in intents.data
            if intent.status == "succeeded"
        ]
    
    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> Dict:
        """
        Verify Stripe webhook signature
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
            secret: Webhook endpoint secret
            
        Returns:
            Parsed event if valid
            
        Raises:
            stripe.error.SignatureVerificationError if invalid
        """
        return stripe.Webhook.construct_event(payload, signature, secret)


