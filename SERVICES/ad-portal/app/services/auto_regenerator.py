"""
Auto-Regenerator Service

Automatically regenerates underperforming creatives using AI.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Dict
from datetime import date, timedelta
from uuid import UUID

from app.models import Creative, Campaign, AdMetrics, Conversion
from app.services.creative_ai import CreativeAIGenerator
from app.schemas.creative import CreativeCreate

logger = logging.getLogger(__name__)


class AutoRegenerator:
    """
    Automatically regenerate underperforming creatives
    """
    
    # Performance thresholds
    MIN_CTR_THRESHOLD = 1.0  # Regenerate if CTR < 1%
    MAX_CPA_THRESHOLD = 50.0  # Regenerate if CPA > $50
    MIN_IMPRESSIONS = 1000  # Need at least 1000 impressions to judge
    MIN_DAYS_RUNNING = 3  # Creative must run for at least 3 days
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.generator = CreativeAIGenerator()
    
    async def find_underperformers(self) -> List[Creative]:
        """
        Find creatives that are underperforming
        
        Criteria:
        - CTR < 1% AND impressions > 1000
        - OR CPA > $50 AND conversions > 0
        - Active creatives only
        - Running for at least 3 days
        """
        cutoff_date = date.today() - timedelta(days=self.MIN_DAYS_RUNNING)
        
        # Get all active creatives with metrics
        result = await self.db.execute(
            select(Creative)
            .join(Campaign)
            .where(
                Creative.active == True,
                Campaign.status == 'active',
                Creative.created_at <= cutoff_date
            )
        )
        creatives = result.scalars().all()
        
        underperformers = []
        
        for creative in creatives:
            # Get metrics for this creative
            metrics_result = await self.db.execute(
                select(
                    func.coalesce(func.sum(AdMetrics.impressions), 0).label('impressions'),
                    func.coalesce(func.sum(AdMetrics.clicks), 0).label('clicks'),
                    func.coalesce(func.sum(AdMetrics.spend), 0).label('spend')
                ).where(AdMetrics.creative_id == creative.id)
            )
            metrics = metrics_result.first()
            
            # Get conversions
            conv_result = await self.db.execute(
                select(
                    func.count(Conversion.id).label('count'),
                    func.coalesce(func.sum(Conversion.amount), 0).label('revenue')
                ).where(Conversion.campaign_id == creative.campaign_id)
            )
            conv = conv_result.first()
            
            impressions = metrics.impressions or 0
            clicks = metrics.clicks or 0
            spend = float(metrics.spend or 0)
            conversions = conv.count or 0
            
            # Skip if not enough data
            if impressions < self.MIN_IMPRESSIONS:
                continue
            
            # Calculate metrics
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            cpa = spend / conversions if conversions > 0 else float('inf')
            
            # Check if underperforming
            is_underperforming = False
            reason = ""
            
            if ctr < self.MIN_CTR_THRESHOLD:
                is_underperforming = True
                reason = f"Low CTR: {ctr:.2f}% (threshold: {self.MIN_CTR_THRESHOLD}%)"
            
            if conversions > 0 and cpa > self.MAX_CPA_THRESHOLD:
                is_underperforming = True
                reason = f"High CPA: ${cpa:.2f} (threshold: ${self.MAX_CPA_THRESHOLD})"
            
            if is_underperforming:
                creative._regeneration_reason = reason
                creative._metrics = {
                    'ctr': ctr,
                    'cpa': cpa,
                    'impressions': impressions,
                    'clicks': clicks,
                    'spend': spend,
                    'conversions': conversions
                }
                underperformers.append(creative)
        
        return underperformers
    
    async def regenerate_creative(self, creative: Creative) -> Creative:
        """
        Regenerate an underperforming creative
        
        Returns:
            New Creative instance (not yet saved)
        """
        # Get campaign and offer
        from app.models import Offer
        
        campaign_result = await self.db.execute(
            select(Campaign).where(Campaign.id == creative.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        
        if not campaign:
            raise ValueError(f"Campaign {creative.campaign_id} not found")
        
        offer_result = await self.db.execute(
            select(Offer).where(Offer.id == campaign.offer_id)
        )
        offer = offer_result.scalar_one_or_none()
        
        if not offer:
            raise ValueError(f"Offer for campaign {campaign.id} not found")
        
        # Get metrics
        metrics = getattr(creative, '_metrics', {})
        reason = getattr(creative, '_regeneration_reason', 'Underperforming')
        
        # Determine optimization focus
        if metrics.get('ctr', 0) < self.MIN_CTR_THRESHOLD:
            suggestion_type = "ctr"
        else:
            suggestion_type = "cpa"
        
        # Generate improved creative
        logger.info(
            f"Regenerating creative {creative.id} ({reason}). "
            f"Current CTR: {metrics.get('ctr', 0):.2f}%, CPA: ${metrics.get('cpa', 0):.2f}"
        )
        
        improved = await self.generator.improve_creative(
            creative=creative,
            metrics=metrics,
            suggestion_type=suggestion_type
        )
        
        # Create new creative from improved version
        # Find next variation letter
        existing_variations = await self.db.execute(
            select(Creative.variation)
            .where(Creative.campaign_id == campaign.id)
        )
        used_variations = {v[0] for v in existing_variations.all()}
        
        # Find next available letter
        next_variation = "A"
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in used_variations:
                next_variation = letter
                break
        
        # Create new creative
        new_creative = Creative(
            campaign_id=campaign.id,
            name=f"{campaign.name} - Improved {next_variation}",
            headline=improved.headline,
            primary_text=improved.primary_text,
            description=improved.description or creative.description,
            call_to_action=creative.call_to_action,
            image_url=creative.image_url,  # Keep same image for now
            variation=next_variation,
            active=True
        )
        
        return new_creative
    
    async def regenerate_all_underperformers(self, max_per_run: int = 5) -> List[Dict]:
        """
        Find and regenerate all underperforming creatives
        
        Args:
            max_per_run: Maximum number of creatives to regenerate per run
            
        Returns:
            List of regeneration results
        """
        underperformers = await self.find_underperformers()
        
        if not underperformers:
            logger.info("No underperforming creatives found")
            return []
        
        # Limit to max_per_run
        underperformers = underperformers[:max_per_run]
        
        results = []
        
        for creative in underperformers:
            try:
                # Generate improved version
                new_creative = await self.regenerate_creative(creative)
                
                # Pause old creative
                creative.active = False
                
                # Save new creative
                self.db.add(new_creative)
                await self.db.flush()
                
                # Get campaign name
                campaign_result = await self.db.execute(
                    select(Campaign).where(Campaign.id == creative.campaign_id)
                )
                campaign = campaign_result.scalar_one_or_none()
                campaign_name = campaign.name if campaign else "Unknown"
                
                results.append({
                    "old_creative_id": str(creative.id),
                    "new_creative_id": str(new_creative.id),
                    "campaign_id": str(creative.campaign_id),
                    "campaign_name": campaign_name,
                    "reason": getattr(creative, '_regeneration_reason', 'Underperforming'),
                    "old_headline": creative.headline,
                    "new_headline": new_creative.headline,
                    "status": "success"
                })
                
                logger.info(
                    f"✅ Regenerated creative {creative.id} → {new_creative.id} "
                    f"for campaign {campaign_name}"
                )
                
            except Exception as e:
                logger.error(f"Failed to regenerate creative {creative.id}: {e}")
                
                # Get campaign name
                campaign_result = await self.db.execute(
                    select(Campaign).where(Campaign.id == creative.campaign_id)
                )
                campaign = campaign_result.scalar_one_or_none()
                campaign_name = campaign.name if campaign else "Unknown"
                
                results.append({
                    "old_creative_id": str(creative.id),
                    "campaign_id": str(creative.campaign_id),
                    "campaign_name": campaign_name,
                    "reason": getattr(creative, '_regeneration_reason', 'Underperforming'),
                    "status": "failed",
                    "error": str(e)
                })
        
        await self.db.commit()
        
        return results

