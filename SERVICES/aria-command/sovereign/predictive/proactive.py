#!/usr/bin/env python3
"""
ARIA ULTRA POWER - PROACTIVE ENGINE
=====================================

Proactive messaging system:
- Morning briefings
- Alert before problems occur
- Anticipatory updates
- Rate limiting to avoid spam
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.predictive.proactive")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


class MessagePriority(Enum):
    """Priority levels for proactive messages."""
    CRITICAL = "critical"  # Send immediately, break rate limit
    HIGH = "high"  # Send soon
    MEDIUM = "medium"  # Send when convenient
    LOW = "low"  # Can wait, batch with others


class MessageType(Enum):
    """Types of proactive messages."""
    MORNING_BRIEF = "morning_brief"
    ALERT = "alert"
    PREDICTION = "prediction"
    REMINDER = "reminder"
    UPDATE = "update"


@dataclass
class ProactiveMessage:
    """A proactive message to send."""
    message_type: MessageType
    priority: MessagePriority
    content: str
    target_user: str  # Chat ID
    scheduled_time: Optional[float] = None
    expires_at: Optional[float] = None
    voice: bool = False
    data: Dict = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class UserSettings:
    """User settings for proactive messages."""
    enabled: bool = True
    morning_brief_time: str = "09:00"
    max_messages_per_hour: int = 5
    min_interval_seconds: int = 300  # 5 minutes
    allowed_types: List[MessageType] = field(default_factory=lambda: list(MessageType))


class ProactiveEngine:
    """
    Engine for proactive messaging.
    
    Features:
    - Scheduled messages (morning brief)
    - Event-triggered messages (alerts)
    - Anticipation-based messages
    - Rate limiting and spam prevention
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._queue: List[ProactiveMessage] = []
        self._sent_history: Dict[str, List[float]] = {}  # user -> timestamps
        self._user_settings: Dict[str, UserSettings] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Default settings
        self._default_settings = UserSettings()
        
        # Brief generators
        self._brief_generators: List[Callable] = []
        
        logger.info("ProactiveEngine initialized")
    
    def register_brief_generator(self, generator: Callable):
        """Register a function that generates content for morning briefs."""
        self._brief_generators.append(generator)
    
    async def start(self):
        """Start the proactive engine."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("ProactiveEngine started")
    
    async def stop(self):
        """Stop the proactive engine."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ProactiveEngine stopped")
    
    async def _run_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                await self._process_scheduled()
                await self._process_queue()
            except Exception as e:
                logger.error(f"Proactive loop error: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _process_scheduled(self):
        """Process scheduled messages like morning briefs."""
        now = datetime.now()
        
        for user_id, settings in self._user_settings.items():
            if not settings.enabled:
                continue
            
            # Check morning brief
            if MessageType.MORNING_BRIEF in settings.allowed_types:
                brief_time = settings.morning_brief_time
                hour, minute = map(int, brief_time.split(":"))
                
                if now.hour == hour and now.minute == minute:
                    # Check if already sent today
                    history = self._sent_history.get(user_id, [])
                    today_start = datetime(now.year, now.month, now.day).timestamp()
                    today_briefs = [t for t in history if t > today_start]
                    
                    if not any(t > today_start for t in today_briefs):
                        await self._send_morning_brief(user_id)
    
    async def _process_queue(self):
        """Process queued messages."""
        now = time.time()
        
        # Sort by priority
        self._queue.sort(key=lambda m: (
            0 if m.priority == MessagePriority.CRITICAL else
            1 if m.priority == MessagePriority.HIGH else
            2 if m.priority == MessagePriority.MEDIUM else 3
        ))
        
        # Process messages
        sent = []
        for msg in self._queue:
            # Skip expired
            if msg.is_expired():
                sent.append(msg)
                continue
            
            # Skip if scheduled for later
            if msg.scheduled_time and msg.scheduled_time > now:
                continue
            
            # Check rate limit
            if not self._can_send(msg.target_user, msg.priority):
                continue
            
            # Send message
            success = await self._send_message(msg)
            if success:
                sent.append(msg)
                self._record_sent(msg.target_user)
        
        # Remove sent messages from queue
        for msg in sent:
            if msg in self._queue:
                self._queue.remove(msg)
    
    def _can_send(self, user_id: str, priority: MessagePriority) -> bool:
        """Check if we can send a message to this user."""
        # Critical always sends
        if priority == MessagePriority.CRITICAL:
            return True
        
        settings = self._user_settings.get(user_id, self._default_settings)
        history = self._sent_history.get(user_id, [])
        now = time.time()
        
        # Check hourly limit
        hour_ago = now - 3600
        recent_count = len([t for t in history if t > hour_ago])
        if recent_count >= settings.max_messages_per_hour:
            return False
        
        # Check minimum interval
        if history:
            last_sent = max(history)
            if now - last_sent < settings.min_interval_seconds:
                return False
        
        return True
    
    def _record_sent(self, user_id: str):
        """Record that a message was sent."""
        if user_id not in self._sent_history:
            self._sent_history[user_id] = []
        
        self._sent_history[user_id].append(time.time())
        
        # Cleanup old history (keep last 24 hours)
        cutoff = time.time() - 86400
        self._sent_history[user_id] = [
            t for t in self._sent_history[user_id] if t > cutoff
        ]
    
    async def _send_message(self, msg: ProactiveMessage) -> bool:
        """Send a proactive message via Telegram."""
        try:
            payload = {
                "chat_id": msg.target_user,
                "text": msg.content,
                "parse_mode": "Markdown"
            }
            
            response = await self.http.post(
                f"{TELEGRAM_API}/sendMessage",
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"Sent proactive {msg.message_type.value} to {msg.target_user}")
                return True
            else:
                logger.error(f"Failed to send proactive: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Proactive send error: {e}")
            return False
    
    async def _send_morning_brief(self, user_id: str):
        """Generate and send morning brief."""
        sections = []
        
        # Header
        now = datetime.now()
        sections.append(f"☀️ **Good morning, James!**")
        sections.append(f"_{now.strftime('%A, %B %d, %Y')}_\n")
        
        # Run registered generators
        for generator in self._brief_generators:
            try:
                content = await generator()
                if content:
                    sections.append(content)
            except Exception as e:
                logger.error(f"Brief generator error: {e}")
        
        # Default sections if no generators
        if len(sections) == 2:
            # Trading summary
            try:
                from sovereign.intel.sentiment import get_unified_sentiment
                us = get_unified_sentiment()
                
                for symbol in ["SOL", "BTC"]:
                    sentiment = await us.get_sentiment(symbol)
                    emoji = "🟢" if sentiment.score > 20 else "🔴" if sentiment.score < -20 else "⚪"
                    sections.append(f"{emoji} **{symbol}**: {sentiment.action} ({sentiment.score:+.0f})")
            except Exception as e:
                logger.error(f"Trading brief error: {e}")
            
            # Server status
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get("http://198.54.123.234:8600/health")
                    if resp.status_code == 200:
                        sections.append("\n🖥️ Servers: All healthy")
                    else:
                        sections.append("\n⚠️ Servers: Check status")
            except:
                sections.append("\n⚠️ Servers: Unable to check")
        
        # Combine and send
        content = "\n".join(sections)
        
        msg = ProactiveMessage(
            message_type=MessageType.MORNING_BRIEF,
            priority=MessagePriority.MEDIUM,
            content=content,
            target_user=user_id,
        )
        
        await self._send_message(msg)
    
    def schedule(
        self,
        user_id: str,
        content: str,
        message_type: MessageType = MessageType.UPDATE,
        priority: MessagePriority = MessagePriority.MEDIUM,
        delay_seconds: int = 0,
        expires_in_seconds: int = 3600,
    ):
        """Schedule a proactive message."""
        now = time.time()
        
        msg = ProactiveMessage(
            message_type=message_type,
            priority=priority,
            content=content,
            target_user=user_id,
            scheduled_time=now + delay_seconds if delay_seconds else None,
            expires_at=now + expires_in_seconds,
        )
        
        self._queue.append(msg)
        logger.info(f"Scheduled {message_type.value} for {user_id}")
    
    def alert(self, user_id: str, content: str, priority: MessagePriority = MessagePriority.HIGH):
        """Send an alert immediately."""
        self.schedule(
            user_id=user_id,
            content=f"🚨 **Alert**\n\n{content}",
            message_type=MessageType.ALERT,
            priority=priority,
        )
    
    def set_user_settings(self, user_id: str, settings: UserSettings):
        """Set user preferences for proactive messages."""
        self._user_settings[user_id] = settings
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self._queue)
    
    def get_stats(self, user_id: str = None) -> Dict:
        """Get proactive messaging stats."""
        if user_id:
            history = self._sent_history.get(user_id, [])
            return {
                "messages_sent_24h": len(history),
                "queue_size": len([m for m in self._queue if m.target_user == user_id]),
            }
        else:
            return {
                "total_queue": len(self._queue),
                "active_users": len(self._sent_history),
                "running": self._running,
            }


# Singleton instance
_engine: Optional[ProactiveEngine] = None


def get_proactive_engine() -> ProactiveEngine:
    """Get global ProactiveEngine instance."""
    global _engine
    if _engine is None:
        _engine = ProactiveEngine()
    return _engine


def schedule_proactive(
    user_id: str,
    content: str,
    message_type: MessageType = MessageType.UPDATE,
    priority: MessagePriority = MessagePriority.MEDIUM,
):
    """Convenience function to schedule a proactive message."""
    engine = get_proactive_engine()
    engine.schedule(user_id, content, message_type, priority)


