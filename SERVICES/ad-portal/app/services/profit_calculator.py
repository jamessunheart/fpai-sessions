"""
Profit Calculator Service

Calculate ROAS, profit margins, and generate daily profit reports.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.models import Campaign, AdMetrics, Conversion, ProfitReport


class ProfitCalculator:
    """
    Calculate and track profit metrics across campaigns
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_campaign_profit(
        self,
        campaign_id: UUID,
        start_date: date = None,
        end_date: date = None
    ) -> Dict:
        """
        Calculate profit for a single campaign
        
        Args:
            campaign_id: Campaign to analyze
            start_date: Start of period (default: campaign launch)
            end_date: End of period (default: today)
            
        Returns:
            Dict with spend, revenue, profit, ROAS, CPA, margin
        """
        # Get campaign
        campaign_result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        
        if not campaign:
            return None
        
        # Default dates
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = campaign.launched_at.date() if campaign.launched_at else campaign.created_at.date()
        
        # Get total spend
        spend_result = await self.db.execute(
            select(func.coalesce(func.sum(AdMetrics.spend), 0))
            .where(
                and_(
                    AdMetrics.campaign_id == campaign_id,
                    AdMetrics.date >= start_date,
                    AdMetrics.date <= end_date
                )
            )
        )
        total_spend = Decimal(str(spend_result.scalar() or 0))
        
        # Get conversions and revenue
        conv_result = await self.db.execute(
            select(
                func.count(Conversion.id).label('count'),
                func.coalesce(func.sum(Conversion.amount), 0).label('revenue')
            ).where(
                and_(
                    Conversion.campaign_id == campaign_id,
                    func.date(Conversion.converted_at) >= start_date,
                    func.date(Conversion.converted_at) <= end_date
                )
            )
        )
        conv = conv_result.first()
        conversion_count = conv.count or 0
        total_revenue = Decimal(str(conv.revenue or 0))
        
        # Calculate metrics
        profit = total_revenue - total_spend
        roas = float(total_revenue / total_spend) if total_spend > 0 else 0
        cpa = float(total_spend / conversion_count) if conversion_count > 0 else 0
        margin_pct = float((profit / total_revenue) * 100) if total_revenue > 0 else 0
        
        return {
            "campaign_id": str(campaign_id),
            "campaign_name": campaign.name,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_spend": float(total_spend),
            "total_revenue": float(total_revenue),
            "profit": float(profit),
            "conversion_count": conversion_count,
            "roas": round(roas, 2),
            "cpa": round(cpa, 2),
            "margin_pct": round(margin_pct, 1),
            "is_profitable": profit > 0
        }
    
    async def calculate_daily_profit(
        self,
        campaign_id: UUID,
        target_date: date
    ) -> ProfitReport:
        """
        Calculate profit for a single day and save to profit_reports
        
        Args:
            campaign_id: Campaign to analyze
            target_date: Date to calculate
            
        Returns:
            ProfitReport model instance
        """
        # Get spend
        spend_result = await self.db.execute(
            select(func.coalesce(func.sum(AdMetrics.spend), 0))
            .where(
                and_(
                    AdMetrics.campaign_id == campaign_id,
                    AdMetrics.date == target_date
                )
            )
        )
        spend = Decimal(str(spend_result.scalar() or 0))
        
        # Get conversions
        conv_result = await self.db.execute(
            select(
                func.count(Conversion.id).label('count'),
                func.coalesce(func.sum(Conversion.amount), 0).label('revenue')
            ).where(
                and_(
                    Conversion.campaign_id == campaign_id,
                    func.date(Conversion.converted_at) == target_date
                )
            )
        )
        conv = conv_result.first()
        
        # Get campaign's offer_id
        campaign_result = await self.db.execute(
            select(Campaign.offer_id).where(Campaign.id == campaign_id)
        )
        offer_id = campaign_result.scalar()
        
        # Check for existing report
        existing = await self.db.execute(
            select(ProfitReport).where(
                and_(
                    ProfitReport.campaign_id == campaign_id,
                    ProfitReport.date == target_date
                )
            )
        )
        report = existing.scalar_one_or_none()
        
        if report:
            # Update existing
            report.total_spend = spend
            report.total_revenue = Decimal(str(conv.revenue or 0))
            report.conversion_count = conv.count or 0
        else:
            # Create new
            report = ProfitReport(
                date=target_date,
                campaign_id=campaign_id,
                offer_id=offer_id,
                total_spend=spend,
                total_revenue=Decimal(str(conv.revenue or 0)),
                conversion_count=conv.count or 0
            )
            self.db.add(report)
        
        await self.db.flush()
        return report
    
    async def generate_daily_reports(self, target_date: date = None) -> List[ProfitReport]:
        """
        Generate profit reports for all active campaigns for a date
        
        Args:
            target_date: Date to generate (default: yesterday)
            
        Returns:
            List of generated ProfitReport instances
        """
        if not target_date:
            target_date = date.today() - timedelta(days=1)
        
        # Get all campaigns that were active on target_date
        campaigns_result = await self.db.execute(
            select(Campaign).where(
                Campaign.status.in_(['active', 'paused', 'completed'])
            )
        )
        campaigns = campaigns_result.scalars().all()
        
        reports = []
        for campaign in campaigns:
            # Check if campaign was running on target_date
            if campaign.launched_at and campaign.launched_at.date() <= target_date:
                report = await self.calculate_daily_profit(campaign.id, target_date)
                reports.append(report)
        
        await self.db.flush()
        return reports
    
    async def get_profit_trend(
        self,
        campaign_id: UUID = None,
        days: int = 30
    ) -> List[Dict]:
        """
        Get daily profit trend for analysis
        
        Args:
            campaign_id: Optional filter by campaign
            days: Number of days to analyze
            
        Returns:
            List of daily profit data
        """
        start_date = date.today() - timedelta(days=days)
        
        query = select(ProfitReport).where(
            ProfitReport.date >= start_date
        ).order_by(ProfitReport.date)
        
        if campaign_id:
            query = query.where(ProfitReport.campaign_id == campaign_id)
        
        result = await self.db.execute(query)
        reports = result.scalars().all()
        
        return [
            {
                "date": r.date.isoformat(),
                "campaign_id": str(r.campaign_id),
                "spend": float(r.total_spend),
                "revenue": float(r.total_revenue),
                "profit": r.profit,
                "roas": r.roas,
                "conversions": r.conversion_count
            }
            for r in reports
        ]
    
    async def get_portfolio_summary(self, days: int = 30) -> Dict:
        """
        Get aggregate profit summary across all campaigns
        
        Returns:
            Portfolio-level metrics
        """
        start_date = date.today() - timedelta(days=days)
        
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(ProfitReport.total_spend), 0).label('spend'),
                func.coalesce(func.sum(ProfitReport.total_revenue), 0).label('revenue'),
                func.coalesce(func.sum(ProfitReport.conversion_count), 0).label('conversions')
            ).where(ProfitReport.date >= start_date)
        )
        summary = result.first()
        
        spend = Decimal(str(summary.spend or 0))
        revenue = Decimal(str(summary.revenue or 0))
        conversions = summary.conversions or 0
        
        profit = revenue - spend
        roas = float(revenue / spend) if spend > 0 else 0
        cpa = float(spend / conversions) if conversions > 0 else 0
        
        # Get campaign count
        campaign_count = await self.db.execute(
            select(func.count(func.distinct(ProfitReport.campaign_id)))
            .where(ProfitReport.date >= start_date)
        )
        
        return {
            "period_days": days,
            "total_spend": float(spend),
            "total_revenue": float(revenue),
            "total_profit": float(profit),
            "total_conversions": conversions,
            "avg_roas": round(roas, 2),
            "avg_cpa": round(cpa, 2),
            "campaign_count": campaign_count.scalar() or 0,
            "profitable": profit > 0,
            "daily_avg_spend": round(float(spend) / days, 2),
            "daily_avg_profit": round(float(profit) / days, 2)
        }


