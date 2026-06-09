#!/usr/bin/env python3
"""
JAI AUTOMATION ENGINE - LEARNING-AWARE
=======================================
Proactive continuity support that learns and adapts.

SOUL: Automate the holding of the thread, not the steering of the life.

Upgrades:
- Uses real sentiment analysis (Claude)
- Uses learned timing preferences
- Uses learned action weights
- Runs learning cycles automatically
"""
import os
import json
import asyncio
import logging
import httpx
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s | JAI | %(message)s")
logger = logging.getLogger("jai.auto")

# Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# CIS imports
try:
    from cis.sensors import sense_all, sense_silence
    from cis.threads import get_active_threads
    from cis.learning import run_learning_cycle, get_timing_preference
    from cis.decisions import decide as learning_decide
    from cis import get_cis
    CIS_AVAILABLE = True
except ImportError as e:
    CIS_AVAILABLE = False
    logger.warning(f"CIS not available: {e}")


async def send_ping(message: str) -> bool:
    """Send a minimal ping to James."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Cannot ping (no telegram config)")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            }
            r = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json=payload
            )
            return r.status_code == 200
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        return False


class LearningAwareAutomation:
    """
    Learning-aware automation engine.
    
    Uses learned patterns to:
    - Know best times to intervene
    - Know which actions work best
    - Adapt restraint based on outcomes
    """
    
    def __init__(self):
        self.running = False
        self.user_id = "james"
        
        # Timing
        self.last_sensor_check = None
        self.last_intervention = None
        self.last_health_check = None
        self.last_learning_run = None
        
        # Restraint tracking
        self.pings_this_hour = 0
        self.hour_start = datetime.now()
        self.silence_count = 0
        self.no_response_count = 0
        
        # Config
        self.config = {
            "sensor_interval_seconds": 1800,  # 30 minutes
            "health_interval_seconds": 300,   # 5 minutes
            "learning_interval_seconds": 21600,  # 6 hours
            
            # Restraint
            "max_pings_per_hour": 2,
            "min_ping_gap_minutes": 20,
            "timing_threshold": 0.3,  # Don't ping if timing score below this
        }
    
    def reset_hourly(self):
        """Reset hourly counters."""
        now = datetime.now()
        if (now - self.hour_start).seconds > 3600:
            self.hour_start = now
            self.pings_this_hour = 0
    
    def can_ping(self) -> tuple:
        """Check if we should ping (restraint logic with learning)."""
        self.reset_hourly()
        
        # Hard limit
        if self.pings_this_hour >= self.config["max_pings_per_hour"]:
            return False, "rate_limit"
        
        # Learned timing check
        if CIS_AVAILABLE:
            hour = datetime.now().hour
            timing_score = get_timing_preference(hour, self.user_id)
            if timing_score < self.config["timing_threshold"]:
                return False, f"bad_timing_{timing_score:.2f}"
        
        # Time since last ping
        if self.last_intervention:
            minutes_since = (datetime.now() - self.last_intervention).seconds / 60
            min_gap = self.config["min_ping_gap_minutes"]
            
            if self.silence_count > 0:
                min_gap = min_gap * 2
            
            if minutes_since < min_gap:
                return False, "too_soon"
        
        return True, "ok"
    
    def record_ping(self):
        """Record that we sent a ping."""
        self.pings_this_hour += 1
        self.last_intervention = datetime.now()
        self.silence_count += 1
    
    async def run(self):
        """Main automation loop."""
        self.running = True
        logger.info("Learning-Aware Automation Engine started")
        logger.info("SOUL: Automate the holding of the thread, not the steering of the life.")
        
        while self.running:
            try:
                await self.check_cycle()
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Automation error: {e}")
                await asyncio.sleep(120)
    
    async def check_cycle(self):
        """One automation cycle."""
        now = datetime.now()
        
        # Silent health check
        if not self.last_health_check or (now - self.last_health_check).seconds > self.config["health_interval_seconds"]:
            await self.silent_health_check()
            self.last_health_check = now
        
        # Learning cycle
        if CIS_AVAILABLE:
            if not self.last_learning_run or (now - self.last_learning_run).seconds > self.config["learning_interval_seconds"]:
                await self.run_learning()
                self.last_learning_run = now
        
        # Sensor-based check
        if not self.last_sensor_check or (now - self.last_sensor_check).seconds > self.config["sensor_interval_seconds"]:
            await self.sensor_based_check()
            self.last_sensor_check = now
    
    async def silent_health_check(self):
        """Check and fix services silently."""
        services = [
            ("fpai-aria", "http://127.0.0.1:8710/health"),
            ("fpai-level10-trader", "http://127.0.0.1:8601/health"),
        ]
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for service_name, url in services:
                try:
                    r = await client.get(url)
                    if r.status_code != 200:
                        logger.info(f"Restarting {service_name}")
                        os.system(f"systemctl restart {service_name}")
                except:
                    logger.info(f"Restarting {service_name}")
                    os.system(f"systemctl restart {service_name}")
    
    async def run_learning(self):
        """Run a learning cycle."""
        try:
            logger.info("Running learning cycle...")
            report = run_learning_cycle(days=7)
            logger.info(f"Learning: {report.interventions_analyzed} interventions, "
                       f"{len(report.patterns_detected)} patterns")
            
            if report.timing_insights:
                logger.info(f"Timing insights: {report.timing_insights}")
            
            for rec in report.recommendations[:2]:
                logger.info(f"Recommendation: {rec}")
                
        except Exception as e:
            logger.error(f"Learning error: {e}")
    
    async def sensor_based_check(self):
        """Use sensors and learning to decide on intervention."""
        if not CIS_AVAILABLE:
            return
        
        try:
            # Aggregate all sensors
            aggregated = sense_all()
            
            logger.info(f"Sensor: {aggregated.state} ({aggregated.intensity}/5, {aggregated.confidence})")
            
            # Use learning-aware decision engine
            decision = learning_decide(
                state=aggregated.state,
                intensity=aggregated.intensity,
                confidence=aggregated.confidence,
                trigger_type=aggregated.intervention_reason or "sensed",
                user_id=self.user_id
            )
            
            logger.info(f"Decision: {decision.type} (timing={decision.timing_score:.2f}, action={decision.action_score:.2f})")
            
            if decision.type == "silence":
                logger.info(f"Staying silent: {decision.reason}")
                return
            
            # Check restraint
            can_ping, reason = self.can_ping()
            if not can_ping:
                logger.info(f"Ping suppressed: {reason}")
                return
            
            # Get action details and send intervention
            await self.send_intervention(decision, aggregated)
            
        except Exception as e:
            logger.error(f"Sensor check error: {e}")
    
    async def send_intervention(self, decision, aggregated):
        """Send the actual intervention."""
        try:
            # Get action details
            cis = get_cis()
            actions = cis.db.get_actions()
            action = next((a for a in actions if a.id == decision.action_id), None)
            
            if not action:
                logger.warning(f"Action not found: {decision.action_id}")
                return
            
            # Build message
            mirrors = {
                "overloaded": "Load is high",
                "stuck": "Pattern stuck",
                "busy": "Moving fast"
            }
            mirror = mirrors.get(aggregated.state, "Checking in")
            
            # Thread context
            thread_ctx = ""
            try:
                threads = get_active_threads(self.user_id)
                if threads:
                    thread_ctx = f"\n(Thread: {threads[0].description})"
            except:
                pass
            
            message = f"{mirror}.{thread_ctx}\n\n{action.instruction}\n\nReply: helped / same / no"
            
            if await send_ping(message):
                self.record_ping()
                
                # Log intervention
                cis.db.log_intervention(
                    user_id=self.user_id,
                    action_id=action.id,
                    trigger_type="sensed",
                    state=aggregated.state,
                    intensity=aggregated.intensity,
                    confidence=aggregated.confidence,
                    decision_type=decision.type,
                    decision_confidence=decision.confidence,
                    channel="telegram",
                    message=message
                )
                
                logger.info(f"Intervention sent: {action.action_key}")
            
        except Exception as e:
            logger.error(f"Send intervention error: {e}")
    
    def stop(self):
        self.running = False


# Singleton
_automation: Optional[LearningAwareAutomation] = None

def get_automation() -> LearningAwareAutomation:
    global _automation
    if _automation is None:
        _automation = LearningAwareAutomation()
    return _automation


async def start_automation():
    auto = get_automation()
    await auto.run()


if __name__ == "__main__":
    asyncio.run(start_automation())








