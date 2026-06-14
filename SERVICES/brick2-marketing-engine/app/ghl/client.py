"""
BRICK 2 GoHighLevel (GHL) Client
================================
Handles communication with the GoHighLevel API (v2).
Supports:
- Contact Management (Sync)
- Tagging (Trigger Workflows)
- Custom Fields (Commission Tracking)
- Conversations (AI Chat)

Note: API Keys/OAuth tokens are loaded from environment.
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class GHLClient:
    """
    Client for GoHighLevel API v2.
    """
    
    def __init__(self, access_token: str = None, location_id: str = None):
        self.base_url = "https://services.leadconnectorhq.com"
        self.access_token = access_token or os.getenv("GHL_ACCESS_TOKEN")
        self.location_id = location_id or os.getenv("GHL_LOCATION_ID")
        
        if not self.access_token:
            logger.warning("GHL Client initialized without Access Token. API calls will fail until token is provided.")
            
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """Get a contact by ID"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/contacts/{contact_id}",
                headers=self.headers
            )
            resp.raise_for_status()
            return resp.json().get("contact", {})

    async def search_contact(self, email: str) -> Optional[Dict[str, Any]]:
        """Find contact by email"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/contacts/search/duplicate",
                params={"locationId": self.location_id, "email": email},
                headers=self.headers
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("contact")
            return None

    async def create_update_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a contact"""
        # Ensure location ID is present
        if "locationId" not in data:
            data["locationId"] = self.location_id
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/contacts/",
                json=data,
                headers=self.headers
            )
            resp.raise_for_status()
            return resp.json().get("contact", {})

    async def add_tag(self, contact_id: str, tag: str) -> bool:
        """Add a tag to a contact (triggers workflows)"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/contacts/{contact_id}/tags",
                json={"tags": [tag]},
                headers=self.headers
            )
            return resp.status_code in [200, 201]

    async def update_custom_field(self, contact_id: str, field_id: str, value: Any) -> bool:
        """Update a custom field (e.g. 'Referrer ID')"""
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/contacts/{contact_id}",
                json={"customFields": [{"id": field_id, "value": value}]},
                headers=self.headers
            )
            return resp.status_code == 200

    async def send_email(self, contact_id: str, subject: str, html_body: str):
        """Send an email to a contact (via GHL conversation)"""
        # Note: This usually requires the 'Conversations' scope
        # and a POST to /conversations/messages
        pass

# Singleton instance for easy import
ghl_client = GHLClient()

