"""
Pydantic Schemas for API validation
"""
from app.schemas.offer import OfferCreate, OfferUpdate, OfferResponse, OfferList
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse, CampaignList
from app.schemas.creative import CreativeCreate, CreativeUpdate, CreativeResponse, CreativeGenerate
from app.schemas.analytics import (
    AnalyticsOverview, 
    CampaignPerformance, 
    DailyMetrics, 
    CreativePerformance
)

__all__ = [
    "OfferCreate", "OfferUpdate", "OfferResponse", "OfferList",
    "CampaignCreate", "CampaignUpdate", "CampaignResponse", "CampaignList",
    "CreativeCreate", "CreativeUpdate", "CreativeResponse", "CreativeGenerate",
    "AnalyticsOverview", "CampaignPerformance", "DailyMetrics", "CreativePerformance"
]


