#!/usr/bin/env python3
"""
CIS Learning Daemon
===================
Runs the learning cycle automatically.

Schedule:
- Every 6 hours: Quick analysis (last 7 days)
- Every 24 hours: Deep analysis (last 30 days)
"""
import asyncio
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s | LEARN | %(message)s")
logger = logging.getLogger("cis.learning.daemon")


async def run_learning_daemon():
    """Main learning daemon loop."""
    from cis.learning import run_learning_cycle
    
    logger.info("Learning daemon started")
    
    last_quick_run = None
    last_deep_run = None
    
    while True:
        try:
            now = datetime.now()
            
            # Quick analysis every 6 hours
            if not last_quick_run or (now - last_quick_run).seconds > 21600:
                logger.info("Running quick learning cycle (7 days)")
                report = run_learning_cycle(days=7)
                logger.info(f"Quick cycle: {report.interventions_analyzed} interventions, "
                           f"{len(report.patterns_detected)} patterns")
                for rec in report.recommendations[:3]:
                    logger.info(f"  Recommendation: {rec}")
                last_quick_run = now
            
            # Deep analysis every 24 hours
            if not last_deep_run or (now - last_deep_run).seconds > 86400:
                logger.info("Running deep learning cycle (30 days)")
                report = run_learning_cycle(days=30)
                logger.info(f"Deep cycle: {report.interventions_analyzed} interventions, "
                           f"{len(report.patterns_detected)} patterns")
                for rec in report.recommendations:
                    logger.info(f"  Recommendation: {rec}")
                last_deep_run = now
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Learning daemon error: {e}")
            await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(run_learning_daemon())








