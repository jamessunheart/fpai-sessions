#!/usr/bin/env python3
"""
JAI AUTOMATION ENGINE
=====================
What JAI does 24/7 without being asked.

Core principle: Restraint is the intelligence.
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
FCF_API = "http://127.0.0.1:8780"


async def send_ping(message: str):
    """Send a minimal ping to James."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Cannot ping (no telegram config)")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            r = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json=payload
            )
            return r.status_code == 200
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        return False


class JAIAutomation:
    """
    JAI Automation - Runs continuously with restraint.
    
    Principles:
    - Decide when to speak (not always)
    - Offer one option (not ten)
    - Accept silence as feedback
    - Triggers are opportunities
    """
    
    def __init__(self):
        self.running = False
        self.last_health_check = None
        self.last_fcf_check = None
        self.last_trade_check = None
        self.last_ping_time = None
        self.pings_this_hour = 0
        self.hour_start = datetime.now()
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.silence_count = 0
        self.load_config()
    
    def load_config(self):
        self.config = {
            # Trading
            "trading_enabled": True,
            "max_drawdown_pct": 15,
            
            # Timing
            "health_check_interval": 300,
            "trade_check_interval": 60,
            "fcf_check_interval": 1800,
            
            # Restraint
            "max_pings_per_hour": 2,
            "min_ping_gap_minutes": 15,
            "silence_threshold": 3,
            
            # FCF
            "proactive_fcf_enabled": True,
        }
    
    async def run(self):
        """Main automation loop."""
        self.running = True
        logger.info("JAI Automation Engine started")
        logger.info("Principles: Precision. Restraint. Learning.")
        
        await send_ping("JAI online. Watching quietly.")
        
        while self.running:
            try:
                await self.check_cycle()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Automation error: {e}")
                await asyncio.sleep(60)
    
    async def check_cycle(self):
        """One automation cycle."""
        now = datetime.now()
        
        if (now - self.hour_start).seconds > 3600:
            self.hour_start = now
            self.pings_this_hour = 0
        
        if not self.last_health_check or (now - self.last_health_check).seconds > self.config["health_check_interval"]:
            await self.auto_health_check()
            self.last_health_check = now
        
        if self.config["trading_enabled"]:
            if not self.last_trade_check or (now - self.last_trade_check).seconds > self.config["trade_check_interval"]:
                await self.auto_trade_check()
                self.last_trade_check = now
        
        if self.config["proactive_fcf_enabled"]:
            if not self.last_fcf_check or (now - self.last_fcf_check).seconds > self.config["fcf_check_interval"]:
                await self.auto_fcf_check()
                self.last_fcf_check = now
    
    def can_ping(self) -> bool:
        """Check if we should ping (restraint logic)."""
        now = datetime.now()
        
        if self.pings_this_hour >= self.config["max_pings_per_hour"]:
            return False
        
        if self.last_ping_time:
            minutes_since = (now - self.last_ping_time).seconds / 60
            min_gap = self.config["min_ping_gap_minutes"]
            
            if self.silence_count >= self.config["silence_threshold"]:
                min_gap = min_gap * 2
            
            if minutes_since < min_gap:
                return False
        
        return True
    
    async def do_ping(self, message: str, ping_type: str = "general"):
        """Send a ping with tracking."""
        if not self.can_ping():
            logger.info(f"Ping suppressed (restraint): {ping_type}")
            return False
        
        success = await send_ping(message)
        if success:
            self.pings_this_hour += 1
            self.last_ping_time = datetime.now()
            logger.info(f"Ping sent: {ping_type}")
        return success
    
    async def auto_health_check(self):
        """Check services - only alert if something breaks."""
        services = [
            ("WhaleTrack", "http://127.0.0.1:8600/health"),
            ("Trading", "http://127.0.0.1:8601/health"),
            ("FCF", "http://127.0.0.1:8780/health"),
        ]
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in services:
                try:
                    r = await client.get(url)
                    if r.status_code != 200:
                        await self.handle_service_issue(name, f"Status {r.status_code}")
                except Exception as e:
                    await self.handle_service_issue(name, str(e)[:50])
    
    async def handle_service_issue(self, service: str, error: str):
        """Handle unhealthy service - fix silently."""
        key = f"svc:{service}"
        now = datetime.now()
        
        if key in self.alert_cooldowns:
            if (now - self.alert_cooldowns[key]).seconds < 1800:
                return
        
        service_map = {
            "WhaleTrack": "fpai-whaletrack-magnet",
            "Trading": "fpai-whaletrack-live",
            "FCF": "fpai-fcf",
        }
        
        if service in service_map:
            os.system(f"systemctl restart {service_map[service]}")
            logger.info(f"Auto-restarted {service}")
            self.alert_cooldowns[key] = now
    
    async def auto_trade_check(self):
        """Monitor trading - alert on significant moves only."""
        try:
            with open("/opt/fpai/hyperliquid_credentials.json") as f:
                creds = json.load(f)
            
            r = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": creds["main_account"]}, 
                timeout=10)
            acct = r.json()
            account_value = float(acct.get("marginSummary", {}).get("accountValue", 0))
            
            for p in acct.get("assetPositions", []):
                pos = p.get("position", {})
                pnl = float(pos.get("unrealizedPnl", 0))
                sz = float(pos.get("szi", 0))
                
                if sz != 0:
                    coin = pos.get("coin")
                    pnl_pct = (pnl / account_value) * 100 if account_value > 0 else 0
                    
                    if pnl_pct < -self.config["max_drawdown_pct"]:
                        key = f"dd:{coin}"
                        if key not in self.alert_cooldowns or \
                           (datetime.now() - self.alert_cooldowns[key]).seconds > 3600:
                            msg = f"Warning: {coin} down {abs(pnl_pct):.0f}% (${pnl:.0f}). Close or hold?"
                            await self.do_ping(msg, "drawdown")
                            self.alert_cooldowns[key] = datetime.now()
                    
                    if pnl_pct > 10:
                        key = f"tp:{coin}"
                        if key not in self.alert_cooldowns or \
                           (datetime.now() - self.alert_cooldowns[key]).seconds > 3600:
                            msg = f"Profit: {coin} up {pnl_pct:.0f}% (${pnl:.0f}). Take profit?"
                            await self.do_ping(msg, "take_profit")
                            self.alert_cooldowns[key] = datetime.now()
                            
        except Exception as e:
            logger.error(f"Trade check error: {e}")
    
    async def auto_fcf_check(self):
        """
        Proactive state support - the core intelligence.
        
        - Check if conditions suggest support might help
        - Offer ONE tiny action
        - Learn from response (or silence)
        """
        try:
            hour = datetime.now().hour
            trigger_context = None
            
            # Late night (11pm-1am)
            if 23 <= hour or hour <= 1:
                trigger_context = "night"
            # Monday morning
            elif datetime.now().weekday() == 0 and 6 <= hour <= 9:
                trigger_context = "monday"
            # Afternoon slump
            elif 14 <= hour <= 16:
                trigger_context = "afternoon"
            
            if not trigger_context:
                return
            
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{FCF_API}/popups", params={"user_id": TELEGRAM_CHAT_ID})
                data = r.json()
                
                if data.get("should_show"):
                    action = data.get("action", {})
                    popup_msg = data.get("message", "Quick reset?")
                    title = action.get("title", "Pause")
                    duration = action.get("duration_sec", 20)
                    instructions = action.get("instructions", "Take a breath.")
                    
                    msg = f"{popup_msg}\n\n*{title}* ({duration}s)\n{instructions}\n\nReply 'done' after, or ignore."
                    await self.do_ping(msg, "fcf_proactive")
                    
                elif trigger_context == "night" and self.can_ping():
                    msg = "Winding down?\n\n*Do Nothing* (20s)\nStop. Just be still for 20 seconds.\n\nReply 'done' or ignore."
                    await self.do_ping(msg, "night_checkin")
                        
        except Exception as e:
            logger.error(f"FCF check error: {e}")
    
    def stop(self):
        self.running = False


_automation = None

def get_automation() -> JAIAutomation:
    global _automation
    if _automation is None:
        _automation = JAIAutomation()
    return _automation


async def start_automation():
    auto = get_automation()
    await auto.run()


if __name__ == "__main__":
    asyncio.run(start_automation())








