"""
Campaign Optimizer

AI-powered optimization recommendations for ad campaigns.
"""
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.config import settings
from app.models import Campaign, AdMetrics, Conversion, ProfitReport
from app.schemas.analytics import OptimizationRecommendation


class CampaignOptimizer:
    """
    Generate AI-powered optimization recommendations
    """
    
    # Thresholds for recommendations
    SCALE_ROAS_THRESHOLD = 2.0  # Scale campaigns with ROAS > 2x
    PAUSE_ROAS_THRESHOLD = 0.5  # Consider pausing ROAS < 0.5x
    MIN_DATA_DAYS = 3  # Minimum days of data before recommendations
    MIN_SPEND_FOR_DECISION = 50  # Minimum spend before making decisions
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.brain_url = settings.AI_BRAIN_URL
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def analyze_campaign(
        self,
        campaign_id: UUID,
        days: int = 7
    ) -> Optional[OptimizationRecommendation]:
        """
        Analyze a single campaign and generate recommendation
        
        Args:
            campaign_id: Campaign to analyze
            days: Days of data to consider
            
        Returns:
            OptimizationRecommendation or None if not enough data
        """
        # Get campaign
        campaign_result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        
        if not campaign or campaign.status == "archived":
            return None
        
        # Check if enough days running
        if campaign.days_running < self.MIN_DATA_DAYS:
            return None
        
        # Get metrics
        start_date = date.today() - timedelta(days=days)
        
        metrics_result = await self.db.execute(
            select(
                func.coalesce(func.sum(AdMetrics.spend), 0).label('spend'),
                func.coalesce(func.sum(AdMetrics.impressions), 0).label('impressions'),
                func.coalesce(func.sum(AdMetrics.clicks), 0).label('clicks')
            ).where(
                and_(
                    AdMetrics.campaign_id == campaign_id,
                    AdMetrics.date >= start_date
                )
            )
        )
        metrics = metrics_result.first()
        
        conv_result = await self.db.execute(
            select(
                func.count(Conversion.id).label('count'),
                func.coalesce(func.sum(Conversion.amount), 0).label('revenue')
            ).where(
                and_(
                    Conversion.campaign_id == campaign_id,
                    func.date(Conversion.converted_at) >= start_date
                )
            )
        )
        conv = conv_result.first()
        
        spend = float(metrics.spend or 0)
        revenue = float(conv.revenue or 0)
        conversions = conv.count or 0
        impressions = metrics.impressions or 0
        clicks = metrics.clicks or 0
        
        # Not enough spend for decision
        if spend < self.MIN_SPEND_FOR_DECISION:
            return None
        
        # Calculate metrics
        roas = revenue / spend if spend > 0 else 0
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cpa = spend / conversions if conversions > 0 else float('inf')
        
        # Generate recommendation
        return self._generate_recommendation(
            campaign=campaign,
            spend=spend,
            revenue=revenue,
            conversions=conversions,
            roas=roas,
            ctr=ctr,
            cpa=cpa
        )
    
    def _generate_recommendation(
        self,
        campaign: Campaign,
        spend: float,
        revenue: float,
        conversions: int,
        roas: float,
        ctr: float,
        cpa: float
    ) -> OptimizationRecommendation:
        """Generate recommendation based on metrics"""
        
        # Determine recommendation type
        if roas >= self.SCALE_ROAS_THRESHOLD:
            # Scale winner
            return OptimizationRecommendation(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                recommendation_type="scale",
                action=f"Increase daily budget by 50% (${float(campaign.daily_budget) * 1.5:.2f}/day)",
                reason=f"Campaign is profitable with {roas:.1f}x ROAS. ${conversions} conversions at ${cpa:.2f} CPA.",
                expected_impact=f"Estimated +{int(conversions * 0.5)} conversions/week",
                confidence=min(0.95, 0.5 + (roas / 10)),
                priority="high",
                created_at=datetime.utcnow()
            )
        
        elif roas < self.PAUSE_ROAS_THRESHOLD and spend > 100:
            # Consider pausing
            return OptimizationRecommendation(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                recommendation_type="pause",
                action="Pause campaign and review targeting/creative",
                reason=f"Campaign is unprofitable with {roas:.2f}x ROAS. Spent ${spend:.2f} with only ${revenue:.2f} revenue.",
                expected_impact=f"Save ${float(campaign.daily_budget):.2f}/day in ad spend",
                confidence=0.8,
                priority="high",
                created_at=datetime.utcnow()
            )
        
        elif ctr < 1.0:
            # Low CTR - creative issue
            return OptimizationRecommendation(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                recommendation_type="change_creative",
                action="Test new ad creatives - current CTR is below benchmark",
                reason=f"CTR is only {ctr:.2f}% (benchmark: 1-2%). Ads aren't capturing attention.",
                expected_impact="Potential 2-3x improvement in CTR",
                confidence=0.7,
                priority="medium",
                created_at=datetime.utcnow()
            )
        
        elif roas >= 1.0 and roas < self.SCALE_ROAS_THRESHOLD:
            # Profitable but could improve
            return OptimizationRecommendation(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                recommendation_type="adjust_budget",
                action="Maintain current budget, focus on improving conversion rate",
                reason=f"Campaign is breakeven to slightly profitable ({roas:.2f}x ROAS). Room for optimization.",
                expected_impact="Potential to reach 2x ROAS with optimization",
                confidence=0.6,
                priority="medium",
                created_at=datetime.utcnow()
            )
        
        else:
            # Monitor
            return OptimizationRecommendation(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                recommendation_type="monitor",
                action="Continue monitoring - gathering more data",
                reason=f"Current ROAS: {roas:.2f}x. Need more data for confident recommendations.",
                expected_impact="N/A",
                confidence=0.4,
                priority="low",
                created_at=datetime.utcnow()
            )
    
    async def get_all_recommendations(self, days: int = 7) -> List[OptimizationRecommendation]:
        """
        Get recommendations for all active campaigns
        
        Returns list sorted by priority
        """
        # Get active campaigns
        campaigns_result = await self.db.execute(
            select(Campaign).where(Campaign.status.in_(['active', 'paused']))
        )
        campaigns = campaigns_result.scalars().all()
        
        recommendations = []
        for campaign in campaigns:
            rec = await self.analyze_campaign(campaign.id, days)
            if rec:
                recommendations.append(rec)
        
        # Sort by priority and confidence
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(
            key=lambda r: (priority_order.get(r.priority, 3), -r.confidence)
        )
        
        return recommendations
    
    async def get_ai_analysis(self, campaign_id: UUID) -> Optional[str]:
        """
        Get AI-generated detailed analysis of campaign
        
        Uses AI Brain for deeper insights
        """
        rec = await self.analyze_campaign(campaign_id)
        if not rec:
            return None
        
        # Get campaign details
        campaign_result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        
        prompt = f"""Analyze this Facebook ad campaign and provide actionable recommendations:

CAMPAIGN: {campaign.name}
STATUS: {campaign.status}
DAILY BUDGET: ${float(campaign.daily_budget):.2f}
DAYS RUNNING: {campaign.days_running}

CURRENT RECOMMENDATION: {rec.action}
REASON: {rec.reason}

Please provide:
1. A brief summary of the campaign performance
2. 2-3 specific actions to improve results
3. What metrics to watch over the next week

Keep response under 200 words."""

        try:
            response = await self.client.post(
                f"{self.brain_url}/api/generate",
                json={"prompt": prompt, "max_tokens": 400}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("content", "")
        except:
            return None
    
    async def auto_optimize(self, dry_run: bool = True) -> List[Dict]:
        """
        Automatically apply optimizations
        
        Args:
            dry_run: If True, only report what would be done
            
        Returns:
            List of actions taken or proposed
        """
        recommendations = await self.get_all_recommendations()
        actions = []
        
        for rec in recommendations:
            if rec.priority == "high" and rec.confidence >= 0.8:
                action = {
                    "campaign_id": str(rec.campaign_id),
                    "campaign_name": rec.campaign_name,
                    "action": rec.action,
                    "type": rec.recommendation_type,
                    "applied": False
                }
                
                if not dry_run:
                    # Apply the optimization
                    if rec.recommendation_type == "pause":
                        # Pause campaign
                        campaign = await self.db.get(Campaign, rec.campaign_id)
                        if campaign:
                            campaign.status = "paused"
                            await self.db.flush()
                            action["applied"] = True
                    
                    elif rec.recommendation_type == "scale":
                        # Increase budget
                        campaign = await self.db.get(Campaign, rec.campaign_id)
                        if campaign:
                            campaign.daily_budget = campaign.daily_budget * Decimal("1.5")
                            await self.db.flush()
                            action["applied"] = True
                
                actions.append(action)
        
        return actions


