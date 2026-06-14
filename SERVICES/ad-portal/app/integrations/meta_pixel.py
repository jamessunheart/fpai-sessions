"""
Meta Conversions API (Server-Side Pixel)

Send server-side events for reliable conversion tracking.
Documentation: https://developers.facebook.com/docs/marketing-api/conversions-api
"""
import httpx
import hashlib
import time
from typing import Dict, List, Optional
from app.config import settings


class MetaPixelClient:
    """
    Client for Meta Conversions API (CAPI)
    
    Used for server-side conversion tracking to improve attribution
    and handle iOS 14+ privacy changes.
    """
    
    BASE_URL = "https://graph.facebook.com/v19.0"
    
    def __init__(self, pixel_id: str = None, access_token: str = None):
        self.pixel_id = pixel_id or settings.META_PIXEL_ID
        self.access_token = access_token or settings.META_ACCESS_TOKEN
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @staticmethod
    def hash_pii(value: str) -> Optional[str]:
        """
        Hash PII data using SHA256 as required by Meta
        
        Args:
            value: Plain text value (email, phone, etc.)
            
        Returns:
            SHA256 hashed value or None if empty
        """
        if not value:
            return None
        
        # Normalize: lowercase, strip whitespace
        normalized = value.lower().strip()
        
        # SHA256 hash
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    async def send_event(self, event: Dict) -> Dict:
        """
        Send a single event to Conversions API
        
        Args:
            event: Event data following CAPI schema
            
        Returns:
            API response
        """
        return await self.send_events([event])
    
    async def send_events(self, events: List[Dict]) -> Dict:
        """
        Send multiple events to Conversions API
        
        Args:
            events: List of event data
            
        Returns:
            API response with events_received count
        """
        url = f"{self.BASE_URL}/{self.pixel_id}/events"
        
        payload = {
            "data": events,
            "access_token": self.access_token
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            raise MetaPixelError(
                message=error_data.get("error", {}).get("message", str(e)),
                events_received=error_data.get("events_received", 0)
            )
    
    async def send_purchase_event(self, conversion) -> Dict:
        """
        Send Purchase event from conversion record
        
        Args:
            conversion: Conversion model instance
            
        Returns:
            API response
        """
        event = {
            "event_name": "Purchase",
            "event_time": int(conversion.converted_at.timestamp()),
            "event_id": str(conversion.id),  # Deduplication ID
            "action_source": "website",
            "user_data": self._build_user_data(conversion),
            "custom_data": {
                "currency": conversion.currency,
                "value": float(conversion.amount),
                "content_type": "product"
            }
        }
        
        # Add content IDs if offer is linked
        if conversion.offer_id:
            event["custom_data"]["content_ids"] = [str(conversion.offer_id)]
        
        # Add event source URL
        if conversion.landing_page:
            event["event_source_url"] = conversion.landing_page
        
        return await self.send_event(event)
    
    async def send_lead_event(
        self,
        email: str = None,
        phone: str = None,
        fbclid: str = None,
        fbc: str = None,
        fbp: str = None,
        ip_address: str = None,
        user_agent: str = None,
        event_source_url: str = None
    ) -> Dict:
        """
        Send Lead event (form submission, signup, etc.)
        """
        event = {
            "event_name": "Lead",
            "event_time": int(time.time()),
            "action_source": "website",
            "user_data": {
                "em": [self.hash_pii(email)] if email else None,
                "ph": [self.hash_pii(phone)] if phone else None,
                "fbc": fbc,
                "fbp": fbp,
                "client_ip_address": ip_address,
                "client_user_agent": user_agent
            }
        }
        
        if event_source_url:
            event["event_source_url"] = event_source_url
        
        # Clean up None values
        event["user_data"] = {k: v for k, v in event["user_data"].items() if v is not None}
        
        return await self.send_event(event)
    
    async def send_page_view(
        self,
        url: str,
        fbclid: str = None,
        fbc: str = None,
        fbp: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict:
        """
        Send PageView event for landing page tracking
        """
        event = {
            "event_name": "PageView",
            "event_time": int(time.time()),
            "action_source": "website",
            "event_source_url": url,
            "user_data": {
                "fbc": fbc,
                "fbp": fbp,
                "client_ip_address": ip_address,
                "client_user_agent": user_agent
            }
        }
        
        event["user_data"] = {k: v for k, v in event["user_data"].items() if v is not None}
        
        return await self.send_event(event)
    
    async def send_initiate_checkout(
        self,
        value: float,
        currency: str = "USD",
        offer_id: str = None,
        email: str = None,
        fbc: str = None,
        fbp: str = None,
        ip_address: str = None,
        user_agent: str = None,
        event_source_url: str = None
    ) -> Dict:
        """
        Send InitiateCheckout event
        """
        event = {
            "event_name": "InitiateCheckout",
            "event_time": int(time.time()),
            "action_source": "website",
            "user_data": {
                "em": [self.hash_pii(email)] if email else None,
                "fbc": fbc,
                "fbp": fbp,
                "client_ip_address": ip_address,
                "client_user_agent": user_agent
            },
            "custom_data": {
                "currency": currency,
                "value": value,
                "content_type": "product"
            }
        }
        
        if offer_id:
            event["custom_data"]["content_ids"] = [offer_id]
        
        if event_source_url:
            event["event_source_url"] = event_source_url
        
        event["user_data"] = {k: v for k, v in event["user_data"].items() if v is not None}
        
        return await self.send_event(event)
    
    def _build_user_data(self, conversion) -> Dict:
        """Build user_data object from conversion"""
        user_data = {}
        
        if conversion.customer_email:
            user_data["em"] = [self.hash_pii(conversion.customer_email)]
        
        if conversion.fbc:
            user_data["fbc"] = conversion.fbc
        
        if conversion.fbp:
            user_data["fbp"] = conversion.fbp
        
        if conversion.ip_address:
            user_data["client_ip_address"] = conversion.ip_address
        
        if conversion.user_agent:
            user_data["client_user_agent"] = conversion.user_agent
        
        return user_data


class MetaPixelError(Exception):
    """Custom exception for Meta Pixel errors"""
    
    def __init__(self, message: str, events_received: int = 0):
        self.message = message
        self.events_received = events_received
        super().__init__(message)


