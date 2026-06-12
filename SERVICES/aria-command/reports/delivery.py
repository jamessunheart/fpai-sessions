#!/usr/bin/env python3
"""
Report Delivery
===============
Sends reports via Telegram (primary channel).

Features:
- State-aware delivery (adjusts based on user state)
- Rate limiting
- Delivery confirmation
"""
import os
import httpx
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("reports.delivery")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


async def send_telegram(message: str) -> bool:
    """Send message via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Report delivered via Telegram")
                return True
            else:
                logger.error(f"Telegram error: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Delivery error: {e}")
        return False


def send_telegram_sync(message: str) -> bool:
    """Synchronous version of send_telegram."""
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(send_telegram(message))


class ReportDelivery:
    """
    Handles report delivery with state awareness.
    """
    
    def __init__(self):
        self.last_delivery = None
    
    def get_user_state(self) -> tuple:
        """Get current user state from CIS."""
        try:
            from cis.sensors import sense_all
            aggregated = sense_all()
            return aggregated.state, aggregated.intensity
        except:
            return "calm", 2
    
    def should_deliver(self, report_type: str, priority: int = 3) -> tuple:
        """
        Check if we should deliver this report now.
        
        Returns: (should_deliver, adjusted_content_level)
        """
        state, intensity = self.get_user_state()
        
        # Priority 0 (critical) always delivers
        if priority == 0:
            return True, "full"
        
        # State-based adjustments
        if state == "overloaded":
            if priority > 1:
                return False, None  # Skip non-essential
            return True, "minimal"  # Essential only
        
        elif state == "stuck":
            if report_type in ["progress", "status"]:
                return True, "brief"  # Brief updates only
            return True, "full"
        
        elif state == "busy":
            return True, "brief"
        
        elif state in ["calm", "open"]:
            return True, "full"
        
        return True, "full"
    
    async def deliver(self, message: str, report_type: str, priority: int = 3) -> bool:
        """
        Deliver a report.
        
        Args:
            message: The formatted report content
            report_type: Type of report (for logging)
            priority: 0=critical, 4=low
        
        Returns:
            True if delivered successfully
        """
        from .scheduler import get_scheduler
        
        # Check if we can deliver
        scheduler = get_scheduler()
        can_send, reason = scheduler.can_send_report(priority)
        
        if not can_send:
            logger.info(f"Report delivery blocked: {reason}")
            return False
        
        # Check state-based delivery
        should, content_level = self.should_deliver(report_type, priority)
        
        if not should:
            logger.info(f"Report delivery skipped due to user state")
            return False
        
        # Deliver
        success = await send_telegram(message)
        
        if success:
            # Record delivery
            state, intensity = self.get_user_state()
            scheduler.record_report_sent(report_type, message, state, intensity)
            self.last_delivery = datetime.now()
        
        return success
    
    def deliver_sync(self, message: str, report_type: str, priority: int = 3) -> bool:
        """Synchronous version of deliver."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.deliver(message, report_type, priority))


# Singleton
_delivery: Optional[ReportDelivery] = None

def get_delivery() -> ReportDelivery:
    global _delivery
    if _delivery is None:
        _delivery = ReportDelivery()
    return _delivery


async def deliver_report(message: str, report_type: str, priority: int = 3) -> bool:
    """Deliver a report."""
    return await get_delivery().deliver(message, report_type, priority)


def deliver_report_sync(message: str, report_type: str, priority: int = 3) -> bool:
    """Deliver a report (sync)."""
    return get_delivery().deliver_sync(message, report_type, priority)








