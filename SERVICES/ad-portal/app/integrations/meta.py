"""
Meta (Facebook) Marketing API Integration

Handles:
- Campaign creation and management
- Ad Set creation
- Ad creation
- Insights/metrics retrieval
"""
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from app.config import settings


class MetaAdsClient:
    """
    Client for Meta Marketing API
    
    Documentation: https://developers.facebook.com/docs/marketing-api
    """
    
    BASE_URL = "https://graph.facebook.com/v19.0"
    
    def __init__(self, access_token: str = None, ad_account_id: str = None):
        self.access_token = access_token or settings.META_ACCESS_TOKEN
        self.ad_account_id = ad_account_id or settings.META_AD_ACCOUNT_ID
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make authenticated request to Meta API"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Add access token to params
        if params is None:
            params = {}
        params["access_token"] = self.access_token
        
        try:
            if method == "GET":
                response = await self.client.get(url, params=params)
            elif method == "POST":
                response = await self.client.post(url, params=params, json=data)
            elif method == "DELETE":
                response = await self.client.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            raise MetaAPIError(
                message=error_data.get("error", {}).get("message", str(e)),
                code=error_data.get("error", {}).get("code"),
                subcode=error_data.get("error", {}).get("error_subcode")
            )
    
    async def create_campaign(self, campaign) -> Dict:
        """
        Create a new campaign on Meta
        
        Args:
            campaign: Campaign model instance
            
        Returns:
            Dict with campaign_id, adset_id
        """
        # Create Campaign
        campaign_data = {
            "name": campaign.name,
            "objective": campaign.objective,
            "status": "PAUSED",  # Start paused, activate after review
            "special_ad_categories": []
        }
        
        campaign_result = await self._request(
            "POST",
            f"{self.ad_account_id}/campaigns",
            data=campaign_data
        )
        meta_campaign_id = campaign_result.get("id")
        
        # Create Ad Set
        targeting = campaign.targeting or {}
        adset_data = {
            "name": f"AdSet - {campaign.name}",
            "campaign_id": meta_campaign_id,
            "daily_budget": int(float(campaign.daily_budget) * 100),  # Convert to cents
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {
                "age_min": targeting.get("age_min", 25),
                "age_max": targeting.get("age_max", 55),
                "genders": targeting.get("genders", [1, 2]),
                "geo_locations": {
                    "countries": targeting.get("countries", ["US"])
                },
                "publisher_platforms": ["facebook", "instagram"],
                "facebook_positions": ["feed", "story"],
                "instagram_positions": ["stream", "story"]
            },
            "status": "PAUSED"
        }
        
        if campaign.start_date:
            adset_data["start_time"] = campaign.start_date.isoformat()
        if campaign.end_date:
            adset_data["end_time"] = campaign.end_date.isoformat()
        
        adset_result = await self._request(
            "POST",
            f"{self.ad_account_id}/adsets",
            data=adset_data
        )
        meta_adset_id = adset_result.get("id")
        
        # Create Ads for each creative
        ad_ids = []
        for creative in campaign.creatives:
            if creative.active:
                ad_result = await self.create_ad(
                    adset_id=meta_adset_id,
                    creative=creative,
                    offer=campaign.offer
                )
                ad_ids.append(ad_result.get("id"))
                creative.meta_ad_id = ad_result.get("id")
        
        # Activate campaign
        await self.update_campaign_status(meta_campaign_id, "ACTIVE")
        await self._request(
            "POST",
            meta_adset_id,
            data={"status": "ACTIVE"}
        )
        
        return {
            "campaign_id": meta_campaign_id,
            "adset_id": meta_adset_id,
            "ad_ids": ad_ids
        }
    
    async def create_ad(self, adset_id: str, creative, offer) -> Dict:
        """Create an ad from a creative"""
        
        # First create the ad creative
        creative_data = {
            "name": f"Creative - {creative.name or creative.headline[:30]}",
            "object_story_spec": {
                "page_id": settings.META_PAGE_ID if hasattr(settings, 'META_PAGE_ID') else None,
                "link_data": {
                    "link": offer.landing_url,
                    "message": creative.primary_text,
                    "name": creative.headline,
                    "description": creative.description or "",
                    "call_to_action": {
                        "type": creative.call_to_action,
                        "value": {
                            "link": offer.landing_url
                        }
                    }
                }
            }
        }
        
        if creative.image_url:
            creative_data["object_story_spec"]["link_data"]["image_url"] = creative.image_url
        
        creative_result = await self._request(
            "POST",
            f"{self.ad_account_id}/adcreatives",
            data=creative_data
        )
        meta_creative_id = creative_result.get("id")
        creative.meta_creative_id = meta_creative_id
        
        # Create the ad
        ad_data = {
            "name": f"Ad - {creative.variation} - {creative.headline[:20]}",
            "adset_id": adset_id,
            "creative": {"creative_id": meta_creative_id},
            "status": "ACTIVE"
        }
        
        return await self._request(
            "POST",
            f"{self.ad_account_id}/ads",
            data=ad_data
        )
    
    async def update_campaign_status(self, campaign_id: str, status: str) -> Dict:
        """Update campaign status (ACTIVE, PAUSED, DELETED)"""
        return await self._request(
            "POST",
            campaign_id,
            data={"status": status}
        )
    
    async def get_insights(
        self, 
        object_id: str, 
        date_preset: str = "last_7d",
        breakdown: str = None,
        level: str = "campaign"
    ) -> List[Dict]:
        """
        Get performance insights for an object
        
        Args:
            object_id: Campaign, AdSet, or Ad ID
            date_preset: last_7d, last_30d, this_month, etc.
            breakdown: Optional breakdown (age, gender, device, etc.)
            level: campaign, adset, ad
        """
        params = {
            "fields": "impressions,reach,clicks,spend,actions,action_values,cpm,cpc,ctr",
            "date_preset": date_preset,
            "level": level
        }
        
        if breakdown:
            params["breakdowns"] = breakdown
        
        result = await self._request("GET", f"{object_id}/insights", params=params)
        return result.get("data", [])
    
    async def get_daily_insights(
        self,
        object_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get day-by-day insights for date range"""
        params = {
            "fields": "impressions,reach,clicks,spend,actions,cpm,cpc,ctr",
            "time_range": {
                "since": start_date.isoformat(),
                "until": end_date.isoformat()
            },
            "time_increment": 1  # Daily breakdown
        }
        
        result = await self._request("GET", f"{object_id}/insights", params=params)
        return result.get("data", [])
    
    async def sync_metrics(self, campaign) -> List[Dict]:
        """
        Sync latest metrics from Meta for a campaign
        
        Returns list of metrics to save
        """
        if not campaign.meta_campaign_id:
            return []
        
        # Get last 7 days of data
        insights = await self.get_daily_insights(
            campaign.meta_campaign_id,
            date.today() - timedelta(days=7),
            date.today()
        )
        
        metrics = []
        for day in insights:
            # Extract conversions from actions
            conversions = 0
            for action in day.get("actions", []):
                if action.get("action_type") == "purchase":
                    conversions += int(action.get("value", 0))
            
            metrics.append({
                "date": date.fromisoformat(day.get("date_start")),
                "impressions": int(day.get("impressions", 0)),
                "reach": int(day.get("reach", 0)),
                "clicks": int(day.get("clicks", 0)),
                "spend": float(day.get("spend", 0)),
                "conversions": conversions
            })
        
        return metrics


class MetaAPIError(Exception):
    """Custom exception for Meta API errors"""
    
    def __init__(self, message: str, code: int = None, subcode: int = None):
        self.message = message
        self.code = code
        self.subcode = subcode
        super().__init__(message)
    
    def __str__(self):
        return f"MetaAPIError [{self.code}:{self.subcode}]: {self.message}"


