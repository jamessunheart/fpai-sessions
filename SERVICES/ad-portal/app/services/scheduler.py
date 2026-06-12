"""
Background Job Scheduler

Handles automated tasks:
- Syncing metrics from Meta
- Generating daily profit reports
- AI optimization recommendations
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, datetime, timedelta
import logging

from app.database import async_session
from app.models import Campaign
from app.integrations.meta import MetaAdsClient
from app.services.profit_calculator import ProfitCalculator
from app.services.optimizer import CampaignOptimizer
from app.services.auto_regenerator import AutoRegenerator

logger = logging.getLogger(__name__)


class AdPortalScheduler:
    """
    Background job scheduler for Ad Portal
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Configure scheduled jobs"""
        
        # Sync Meta metrics every hour at :05
        self.scheduler.add_job(
            self.sync_meta_metrics,
            CronTrigger(minute=5),
            id='sync_meta_metrics',
            replace_existing=True
        )
        
        # Generate daily profit reports at 12:30 AM
        self.scheduler.add_job(
            self.generate_daily_reports,
            CronTrigger(hour=0, minute=30),
            id='generate_profit_reports',
            replace_existing=True
        )
        
        # Generate AI recommendations at 8 AM
        self.scheduler.add_job(
            self.generate_recommendations,
            CronTrigger(hour=8, minute=0),
            id='generate_recommendations',
            replace_existing=True
        )
        
        # Auto-apply optimizations at 9 AM (after recommendations)
        self.scheduler.add_job(
            self.auto_apply_optimizations,
            CronTrigger(hour=9, minute=0),
            id='auto_apply_optimizations',
            replace_existing=True
        )
        
        # Auto-regenerate underperformers at 10 AM
        self.scheduler.add_job(
            self.auto_regenerate_underperformers,
            CronTrigger(hour=10, minute=0),
            id='auto_regenerate_creatives',
            replace_existing=True
        )
        
        logger.info("Scheduler jobs configured")
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Ad Portal scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Ad Portal scheduler stopped")
    
    async def sync_meta_metrics(self):
        """
        Pull latest metrics from Meta for all active campaigns
        """
        logger.info("Starting Meta metrics sync...")
        
        async with async_session() as db:
            try:
                from sqlalchemy import select
                from app.models import Campaign, AdMetrics
                
                # Get active campaigns with Meta IDs
                result = await db.execute(
                    select(Campaign).where(
                        Campaign.status == 'active',
                        Campaign.meta_campaign_id.isnot(None)
                    )
                )
                campaigns = result.scalars().all()
                
                meta_client = MetaAdsClient()
                
                for campaign in campaigns:
                    try:
                        metrics_list = await meta_client.sync_metrics(campaign)
                        
                        for m in metrics_list:
                            # Upsert metric record
                            existing = await db.execute(
                                select(AdMetrics).where(
                                    AdMetrics.campaign_id == campaign.id,
                                    AdMetrics.date == m['date'],
                                    AdMetrics.hour.is_(None)  # Daily rollup
                                )
                            )
                            metric = existing.scalar_one_or_none()
                            
                            if metric:
                                metric.impressions = m['impressions']
                                metric.reach = m['reach']
                                metric.clicks = m['clicks']
                                metric.spend = m['spend']
                                metric.calculate_derived_metrics()
                            else:
                                metric = AdMetrics(
                                    campaign_id=campaign.id,
                                    date=m['date'],
                                    impressions=m['impressions'],
                                    reach=m['reach'],
                                    clicks=m['clicks'],
                                    spend=m['spend']
                                )
                                metric.calculate_derived_metrics()
                                db.add(metric)
                        
                        logger.info(f"Synced metrics for campaign {campaign.name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to sync campaign {campaign.id}: {e}")
                
                await db.commit()
                logger.info(f"Meta metrics sync complete. {len(campaigns)} campaigns processed.")
                
            except Exception as e:
                logger.error(f"Meta metrics sync failed: {e}")
                await db.rollback()
    
    async def generate_daily_reports(self):
        """
        Generate profit reports for yesterday
        """
        logger.info("Generating daily profit reports...")
        
        async with async_session() as db:
            try:
                calculator = ProfitCalculator(db)
                yesterday = date.today() - timedelta(days=1)
                
                reports = await calculator.generate_daily_reports(yesterday)
                
                await db.commit()
                logger.info(f"Generated {len(reports)} profit reports for {yesterday}")
                
            except Exception as e:
                logger.error(f"Daily reports generation failed: {e}")
                await db.rollback()
    
    async def generate_recommendations(self):
        """
        Generate AI optimization recommendations
        """
        logger.info("Generating optimization recommendations...")
        
        async with async_session() as db:
            try:
                optimizer = CampaignOptimizer(db)
                recommendations = await optimizer.get_all_recommendations()
                
                # Log high priority recommendations
                high_priority = [r for r in recommendations if r.priority == "high"]
                
                for rec in high_priority:
                    logger.info(
                        f"HIGH PRIORITY: {rec.campaign_name} - {rec.recommendation_type}: {rec.action}"
                    )
                
                logger.info(
                    f"Generated {len(recommendations)} recommendations "
                    f"({len(high_priority)} high priority)"
                )
                
            except Exception as e:
                logger.error(f"Recommendations generation failed: {e}")
    
    async def auto_apply_optimizations(self):
        """
        Automatically apply high-confidence optimization recommendations
        """
        logger.info("Starting auto-optimization...")
        
        async with async_session() as db:
            try:
                optimizer = CampaignOptimizer(db)
                
                # Run auto-optimize with dry_run=False to actually apply changes
                actions = await optimizer.auto_optimize(dry_run=False)
                
                applied = [a for a in actions if a.get("applied")]
                proposed = [a for a in actions if not a.get("applied")]
                
                for action in applied:
                    logger.info(
                        f"✅ AUTO-APPLIED: {action['campaign_name']} - "
                        f"{action['type']}: {action['action']}"
                    )
                
                if proposed:
                    logger.info(
                        f"⚠️  {len(proposed)} recommendations found but not applied "
                        f"(low confidence or already applied)"
                    )
                
                logger.info(
                    f"Auto-optimization complete. {len(applied)} actions applied, "
                    f"{len(proposed)} proposed."
                )
                
            except Exception as e:
                logger.error(f"Auto-optimization failed: {e}")
    
    async def auto_regenerate_underperformers(self):
        """
        Automatically regenerate underperforming creatives
        """
        logger.info("Starting auto-regeneration of underperformers...")
        
        async with async_session() as db:
            try:
                regenerator = AutoRegenerator(db)
                
                # Regenerate up to 5 creatives per run
                results = await regenerator.regenerate_all_underperformers(max_per_run=5)
                
                successful = [r for r in results if r.get("status") == "success"]
                failed = [r for r in results if r.get("status") == "failed"]
                
                for result in successful:
                    logger.info(
                        f"✅ REGENERATED: {result['campaign_name']} - "
                        f"Old: {result['old_headline'][:40]}... → "
                        f"New: {result['new_headline'][:40]}... "
                        f"({result['reason']})"
                    )
                
                if failed:
                    for result in failed:
                        logger.warning(
                            f"❌ FAILED: {result['campaign_name']} - {result.get('error', 'Unknown error')}"
                        )
                
                logger.info(
                    f"Auto-regeneration complete. {len(successful)} regenerated, "
                    f"{len(failed)} failed."
                )
                
            except Exception as e:
                logger.error(f"Auto-regeneration failed: {e}")


# Global scheduler instance
scheduler = AdPortalScheduler()


