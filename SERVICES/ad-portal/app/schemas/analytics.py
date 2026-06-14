"""
Analytics Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


class AnalyticsOverview(BaseModel):
    """Dashboard overview statistics"""
    # Totals
    total_spend: Decimal = Decimal("0.00")
    total_revenue: Decimal = Decimal("0.00")
    total_profit: Decimal = Decimal("0.00")
    total_conversions: int = 0
    
    # Rates
    overall_roas: float = 0.0
    avg_cpa: Decimal = Decimal("0.00")
    avg_ctr: float = 0.0
    
    # Counts
    active_campaigns: int = 0
    active_offers: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    
    # Period
    period_start: date
    period_end: date
    
    # Trends (vs previous period)
    spend_trend: float = 0.0  # % change
    revenue_trend: float = 0.0
    profit_trend: float = 0.0
    roas_trend: float = 0.0


class CampaignPerformance(BaseModel):
    """Performance metrics for a single campaign"""
    campaign_id: UUID
    campaign_name: str
    offer_name: str
    status: str
    
    # Metrics
    spend: Decimal = Decimal("0.00")
    revenue: Decimal = Decimal("0.00")
    profit: Decimal = Decimal("0.00")
    conversions: int = 0
    impressions: int = 0
    clicks: int = 0
    
    # Rates
    roas: float = 0.0
    ctr: float = 0.0
    cpc: Decimal = Decimal("0.00")
    cpa: Decimal = Decimal("0.00")
    
    # Time
    days_running: int = 0
    last_conversion: Optional[datetime] = None


class CampaignPerformanceList(BaseModel):
    """List of campaign performance metrics"""
    campaigns: List[CampaignPerformance]
    total: int
    sort_by: str = "profit"
    
    # Aggregates
    total_spend: Decimal = Decimal("0.00")
    total_revenue: Decimal = Decimal("0.00")
    total_profit: Decimal = Decimal("0.00")


class DailyMetrics(BaseModel):
    """Metrics for a single day"""
    date: date
    spend: Decimal = Decimal("0.00")
    revenue: Decimal = Decimal("0.00")
    profit: Decimal = Decimal("0.00")
    conversions: int = 0
    impressions: int = 0
    clicks: int = 0
    roas: float = 0.0
    cpa: Decimal = Decimal("0.00")


class DailyMetricsList(BaseModel):
    """List of daily metrics"""
    metrics: List[DailyMetrics]
    period_start: date
    period_end: date
    
    # Period totals
    total_spend: Decimal = Decimal("0.00")
    total_revenue: Decimal = Decimal("0.00")
    total_profit: Decimal = Decimal("0.00")
    avg_daily_spend: Decimal = Decimal("0.00")
    avg_daily_revenue: Decimal = Decimal("0.00")


class HourlyMetrics(BaseModel):
    """Metrics for a single hour"""
    hour: int  # 0-23
    spend: Decimal = Decimal("0.00")
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: Decimal = Decimal("0.00")


class HourlyMetricsList(BaseModel):
    """Hourly breakdown for a specific date"""
    date: date
    metrics: List[HourlyMetrics]
    peak_hour: int = 0
    peak_conversions: int = 0


class CreativePerformance(BaseModel):
    """A/B test performance for creatives"""
    creative_id: UUID
    campaign_id: UUID
    variation: str
    headline: str
    
    # Metrics
    impressions: int = 0
    clicks: int = 0
    spend: Decimal = Decimal("0.00")
    conversions: int = 0
    revenue: Decimal = Decimal("0.00")
    
    # Rates
    ctr: float = 0.0
    conversion_rate: float = 0.0
    cpa: Decimal = Decimal("0.00")
    roas: float = 0.0
    
    # Ranking
    is_winner: bool = False
    confidence: float = 0.0  # Statistical confidence


class CreativePerformanceList(BaseModel):
    """List of creative performance for A/B comparison"""
    campaign_id: UUID
    campaign_name: str
    creatives: List[CreativePerformance]
    winner: Optional[str] = None  # Variation letter
    test_status: str = "running"  # running, conclusive, needs_data
    recommendation: Optional[str] = None


class OptimizationRecommendation(BaseModel):
    """AI-generated optimization recommendation"""
    campaign_id: UUID
    campaign_name: str
    recommendation_type: str  # scale, pause, adjust_budget, change_creative, adjust_targeting
    action: str
    reason: str
    expected_impact: str
    confidence: float
    priority: str  # high, medium, low
    created_at: datetime


class OptimizationRecommendationList(BaseModel):
    """List of optimization recommendations"""
    recommendations: List[OptimizationRecommendation]
    generated_at: datetime


