"""
ARIA NOTIFICATION SYSTEM
========================

Tiered notification system for proactive Aria.

Tiers:
- URGENT: Telegram immediately (trading signals, service failures)
- HIGH: Telegram soon (position risk, memory warnings)
- MEDIUM: Dashboard digest (build failures, revenue updates)
- LOW: Dashboard digest (routine updates)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
import httpx

logger = logging.getLogger("aria.notifications")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # James's chat ID
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Digest storage
DIGEST_FILE = Path("/opt/fpai/aria/digest_items.json")


@dataclass
class DigestItem:
    """An item for the daily digest."""
    title: str
    description: str
    category: str
    priority: str
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class NotificationSystem:
    """
    Tiered notification system.
    
    - Urgent/High: Send to Telegram immediately
    - Medium/Low: Queue for daily digest
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self.digest_items: List[DigestItem] = []
        self.last_urgent = {}  # Dedup urgent messages
        self._load_digest()
        logger.info("NotificationSystem initialized")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    def _load_digest(self):
        """Load pending digest items."""
        try:
            if DIGEST_FILE.exists():
                data = json.loads(DIGEST_FILE.read_text())
                self.digest_items = [DigestItem(**item) for item in data]
        except Exception as e:
            logger.warning(f"Failed to load digest: {e}")
    
    def _save_digest(self):
        """Save pending digest items."""
        try:
            DIGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(item) for item in self.digest_items]
            DIGEST_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save digest: {e}")
    
    async def send_urgent(self, message: str):
        """Send urgent notification via Telegram."""
        # Dedup check
        msg_hash = hash(message[:100])
        now = datetime.utcnow()
        
        if msg_hash in self.last_urgent:
            if now - self.last_urgent[msg_hash] < timedelta(minutes=5):
                logger.debug(f"Deduped urgent message: {message[:50]}...")
                return
        
        self.last_urgent[msg_hash] = now
        
        # Clean up old dedup entries
        cutoff = now - timedelta(hours=1)
        self.last_urgent = {k: v for k, v in self.last_urgent.items() if v > cutoff}
        
        # Send to Telegram
        await self._send_telegram(message)
    
    async def send_high(self, message: str):
        """Send high priority notification via Telegram (slightly less urgent)."""
        await self._send_telegram(f"📢 {message}")
    
    async def send_curiosity(self, message: str):
        """Send a curiosity insight."""
        await self._send_telegram(f"🤔 **Curiosity**\n\n{message}")
    
    async def send_digest(self, digest_content: str):
        """Send the daily digest."""
        await self._send_telegram(f"📬 **Morning Briefing**\n\n{digest_content}")
        
        # Clear digest items
        self.digest_items = []
        self._save_digest()
    
    async def add_to_digest(self, signal):
        """Add a signal to the daily digest."""
        item = DigestItem(
            title=signal.title,
            description=signal.description,
            category=signal.source,
            priority=signal.priority.value
        )
        self.digest_items.append(item)
        self._save_digest()
        logger.debug(f"Added to digest: {signal.title}")
    
    async def _send_telegram(self, message: str):
        """Send message to Telegram."""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured, message not sent")
            logger.info(f"Would send: {message[:100]}...")
            return
        
        try:
            await self.http.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
            logger.info(f"Sent Telegram: {message[:50]}...")
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
    
    def get_pending_digest_count(self) -> int:
        """Get number of items waiting for digest."""
        return len(self.digest_items)
    
    def format_digest_preview(self) -> str:
        """Format a preview of pending digest items."""
        if not self.digest_items:
            return "No items pending for digest."
        
        lines = [f"📋 {len(self.digest_items)} items pending:"]
        
        # Group by category
        by_category = {}
        for item in self.digest_items:
            cat = item.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)
        
        for cat, items in by_category.items():
            lines.append(f"\n**{cat.title()}** ({len(items)})")
            for item in items[:3]:
                lines.append(f"• {item.title}")
            if len(items) > 3:
                lines.append(f"• ... and {len(items) - 3} more")
        
        return "\n".join(lines)


# Singleton instance
_notifications: Optional[NotificationSystem] = None


def get_notifications() -> NotificationSystem:
    """Get or create the notification system."""
    global _notifications
    if _notifications is None:
        _notifications = NotificationSystem()
    return _notifications


