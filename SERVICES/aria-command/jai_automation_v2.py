#!/usr/bin/env python3
"""
JAI AUTOMATION ENGINE - CIS-AWARE
=================================
Proactive continuity support that finds you through sensing.

SOUL: Automate the holding of the thread, not the steering of the life.

Principles:
- Sense before speaking
- Silence is the default
- One action only
- Learn from proof
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
    from cis.sensors import sense_all, sense_silence, sense_external
    from cis.threads import get_active_threads
    from cis import get_cis
    CIS_AVAILABLE = True
except ImportError:
    CIS_AVAILABLE = False
    logger.warning("CIS not available - running in limited mode")


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


class CISAwareAutomation:
    """
    CIS-Aware Automation - Finds you through sensing.
    
    Components:
    1. Sensor Aggregation - combines all signal sources
    2. Finder Loop - decides when to intervene
    3. Restraint Engine - prevents over-intervention
    4. Micro-Action - delivers one small thing
    5. Proof Loop - learns from outcomes
    """
    
    def __init__(self):
        self.running = False
        self.user_id = "james"
        
        # Timing
        self.last_sensor_check = None
        self.last_intervention = None
        self.last_health_check = None
        
        # Restraint tracking
        self.pings_this_hour = 0
        self.hour_start = datetime.now()
        self.silence_count = 0
        self.no_response_count = 0
        
        # Cooldowns
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        # Config
        self.config = {
            "sensor_interval_seconds": 1800,  # 30 minutes
            "health_interval_seconds": 300,   # 5 minutes
            
            # Restraint
            "max_pings_per_hour": 2,
            "min_ping_gap_minutes": 20,
            "silence_multiplier": 2,  # Double gap after ignored pings
            "max_no_response_streak": 2,  # Stop pinging after 2 ignored
            
            # State thresholds
            "intervention_intensity_threshold": 4,  # Only intervene at 4+
            "silence_hours_threshold": 48,  # Check in after 48h silence
        }
    
    def reset_hourly(self):
        """Reset hourly counters."""
        now = datetime.now()
        if (now - self.hour_start).seconds > 3600:
            self.hour_start = now
            self.pings_this_hour = 0
    
    def can_ping(self) -> bool:
        """Check if we should ping (restraint logic)."""
        self.reset_hourly()
        
        # Hard limit
        if self.pings_this_hour >= self.config["max_pings_per_hour"]:
            return False
        
        # No response streak - back off
        if self.no_response_count >= self.config["max_no_response_streak"]:
            logger.info("Backing off - no responses")
            return False
        
        # Time since last ping
        if self.last_intervention:
            minutes_since = (datetime.now() - self.last_intervention).seconds / 60
            min_gap = self.config["min_ping_gap_minutes"]
            
            # Increase gap if being ignored
            if self.silence_count > 0:
                min_gap = min_gap * self.config["silence_multiplier"]
            
            if minutes_since < min_gap:
                return False
        
        return True
    
    def record_ping(self):
        """Record that we sent a ping."""
        self.pings_this_hour += 1
        self.last_intervention = datetime.now()
        self.silence_count += 1  # Assume ignored until proven otherwise
    
    def record_response(self, helped: bool):
        """Record that we got a response."""
        self.silence_count = 0
        self.no_response_count = 0
        
        if not helped:
            # They responded but it didn't help - still learn
            logger.info("Response received: didn't help")
    
    async def run(self):
        """Main automation loop."""
        self.running = True
        logger.info("CIS-Aware Automation Engine started")
        logger.info("SOUL: Automate the holding of the thread, not the steering of the life.")
        
        while self.running:
            try:
                await self.check_cycle()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Automation error: {e}")
                await asyncio.sleep(120)
    
    async def check_cycle(self):
        """One automation cycle."""
        now = datetime.now()
        
        # Health check (silent - fix issues without pinging)
        if not self.last_health_check or (now - self.last_health_check).seconds > self.config["health_interval_seconds"]:
            await self.silent_health_check()
            self.last_health_check = now
        
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
                        logger.info(f"Restarting {service_name} (status {r.status_code})")
                        os.system(f"systemctl restart {service_name}")
                except Exception as e:
                    logger.info(f"Restarting {service_name} (error: {str(e)[:30]})")
                    os.system(f"systemctl restart {service_name}")
    
    async def sensor_based_check(self):
        """
        The Finder Loop - uses CIS sensors to decide if intervention is needed.
        """
        if not CIS_AVAILABLE:
            logger.debug("CIS not available, skipping sensor check")
            return
        
        try:
            # Aggregate all sensors
            aggregated = sense_all()
            
            logger.info(f"Sensor check: {aggregated.state} ({aggregated.intensity}/5, {aggregated.confidence})")
            
            # Check if intervention is warranted
            if aggregated.should_intervene:
                await self.handle_intervention(aggregated)
            
            # Check silence drift
            silence = sense_silence()
            if silence.should_check_in and self.can_ping():
                await self.handle_drift_check(silence)
            
        except Exception as e:
            logger.error(f"Sensor check error: {e}")
    
    async def handle_intervention(self, aggregated):
        """
        Handle a detected intervention opportunity.
        Uses CIS decision engine if available.
        """
        if not self.can_ping():
            logger.info(f"Intervention suppressed (restraint): {aggregated.intervention_reason}")
            return
        
        try:
            cis = get_cis()
            
            # Get best action for current state
            from cis.engine import UserState
            current = UserState(
                state=aggregated.state,
                intensity=aggregated.intensity,
                confidence=aggregated.confidence,
                source="sensed",
                captured_at=datetime.now().isoformat()
            )
            
            decision = cis.decisions.decide(self.user_id, current, aggregated.intervention_reason or "sensed")
            
            if decision.type == "silence":
                logger.info("CIS decision: silence")
                return
            
            # Get the action
            if decision.action_id:
                actions = cis.db.get_actions()
                action = next((a for a in actions if a.id == decision.action_id), None)
                
                if action:
                    # Build message
                    message = self.build_intervention_message(aggregated, action)
                    
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
            logger.error(f"Intervention error: {e}")
    
    def build_intervention_message(self, aggregated, action) -> str:
        """Build a minimal intervention message."""
        # Status mirror based on state
        mirrors = {
            "overloaded": "Load is high",
            "stuck": "Pattern stuck",
            "busy": "Moving fast"
        }
        
        mirror = mirrors.get(aggregated.state, "Checking in")
        
        # Include thread context if available
        thread_context = ""
        try:
            threads = get_active_threads(self.user_id)
            if threads:
                thread_context = f"\n(Thread: {threads[0].description})"
        except:
            pass
        
        return f"{mirror}.{thread_context}\n\n{action.instruction}\n\nReply: helped / same / no"
    
    async def handle_drift_check(self, silence):
        """Handle drift detection - gentle check-in."""
        if not self.can_ping():
            return
        
        hours = int(silence.hours_silent)
        
        if silence.last_state in ["overloaded", "stuck"]:
            message = f"Still there? ({hours}h quiet)\n\nReply with how you're feeling (e.g., 'calm 2', 'busy 3')"
        else:
            message = f"Checking in. ({hours}h since last signal)\n\nReply with state if you want, or ignore."
        
        if await send_ping(message):
            self.record_ping()
            logger.info(f"Drift check sent ({hours}h)")
    
    def stop(self):
        self.running = False


# Singleton
_automation: Optional[CISAwareAutomation] = None

def get_automation() -> CISAwareAutomation:
    global _automation
    if _automation is None:
        _automation = CISAwareAutomation()
    return _automation


async def start_automation():
    auto = get_automation()
    await auto.run()


if __name__ == "__main__":
    asyncio.run(start_automation())








