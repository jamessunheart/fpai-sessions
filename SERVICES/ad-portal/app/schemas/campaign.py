"""
Campaign Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


class TargetingConfig(BaseModel):
    """Targeting configuration for Meta ads"""
    age_min: int = Field(default=25, ge=18, le=65)
    age_max: int = Field(default=55, ge=18, le=65)
    genders: List[int] = Field(default=[1, 2])  # 1=male, 2=female
    countries: List[str] = Field(default=["US"])
    interests: List[str] = Field(default=[])
    custom_audiences: List[str] = Field(default=[])
    lookalike_audiences: List[str] = Field(default=[])


class CampaignBase(BaseModel):
    """Base campaign fields"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    offer_id: UUID
    objective: str = Field(default="OUTCOME_SALES")
    daily_budget: Decimal = Field(..., gt=0)
    lifetime_budget: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    targeting: Optional[TargetingConfig] = None


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign"""
    pass


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    objective: Optional[str] = None
    daily_budget: Optional[Decimal] = Field(None, gt=0)
    lifetime_budget: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    targeting: Optional[TargetingConfig] = None
    status: Optional[str] = None


class CampaignMetricsSummary(BaseModel):
    """Summary metrics for a campaign"""
    total_spend: Decimal = Decimal("0.00")
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_revenue: Decimal = Decimal("0.00")
    ctr: float = 0.0
    cpc: Decimal = Decimal("0.00")
    cpa: Decimal = Decimal("0.00")
    roas: float = 0.0
    profit: Decimal = Decimal("0.00")


class CampaignResponse(CampaignBase):
    """Schema for campaign response"""
    id: UUID
    status: str
    meta_campaign_id: Optional[str] = None
    meta_adset_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    launched_at: Optional[datetime] = None
    
    # Computed fields
    days_running: int = 0
    creative_count: int = 0
    metrics: Optional[CampaignMetricsSummary] = None
    
    class Config:
        from_attributes = True


class CampaignList(BaseModel):
    """Schema for list of campaigns"""
    campaigns: List[CampaignResponse]
    total: int
    
    class Config:
        from_attributes = True


class CampaignLaunchResponse(BaseModel):
    """Response after launching campaign to Meta"""
    success: bool
    campaign_id: UUID
    meta_campaign_id: Optional[str] = None
    meta_adset_id: Optional[str] = None
    message: str
    launched_at: Optional[datetime] = None


