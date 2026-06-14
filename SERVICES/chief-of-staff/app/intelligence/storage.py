"""
Signal storage and retrieval
"""
import asyncio
from collections import deque
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging

from app.models import Signal, SignalCategory, UserAction
from app.config import settings

logger = logging.getLogger(__name__)


class SignalStorage:
    """In-memory signal storage with time-based retention"""

    def __init__(self):
        self.signals: Dict[str, Signal] = {}
        self.signal_history: deque = deque(maxlen=settings.MAX_SIGNALS_HISTORY)
        self._lock = asyncio.Lock()

    async def store(self, signal: Signal) -> None:
        """Store a signal"""
        async with self._lock:
            self.signals[signal.signal_id] = signal
            self.signal_history.append(signal)
            logger.info(f"Stored signal {signal.signal_id} ({signal.category.value})")

    async def get(self, signal_id: str) -> Optional[Signal]:
        """Get a signal by ID"""
        async with self._lock:
            return self.signals.get(signal_id)

    async def get_by_category(
        self, category: SignalCategory, limit: int = 100
    ) -> List[Signal]:
        """Get signals by category"""
        async with self._lock:
            signals = [
                s for s in self.signal_history
                if s.category == category
            ]
            return list(reversed(signals))[:limit]

    async def get_urgent(self) -> List[Signal]:
        """Get current urgent signals"""
        return await self.get_by_category(SignalCategory.URGENT, limit=50)

    async def get_important(self, hours: int = 24) -> List[Signal]:
        """Get important signals from last N hours"""
        async with self._lock:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            signals = [
                s for s in self.signal_history
                if s.category == SignalCategory.IMPORTANT
                and s.timestamp >= cutoff
            ]
            return list(reversed(signals))

    async def get_auto_handled(self, hours: int = 24) -> List[Signal]:
        """Get auto-handled signals from last N hours"""
        async with self._lock:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            signals = [
                s for s in self.signal_history
                if s.category == SignalCategory.AUTO
                and s.timestamp >= cutoff
            ]
            return list(reversed(signals))

    async def update_user_response(
        self, signal_id: str, action: UserAction
    ) -> bool:
        """Update signal with user response"""
        async with self._lock:
            if signal_id in self.signals:
                signal = self.signals[signal_id]
                signal.user_response = action
                signal.responded_at = datetime.utcnow()
                logger.info(f"Updated signal {signal_id} with user action: {action.value}")
                return True
            return False

    async def get_stats(self) -> Dict:
        """Get storage statistics"""
        async with self._lock:
            total = len(self.signal_history)
            by_category = {}
            for category in SignalCategory:
                count = sum(1 for s in self.signal_history if s.category == category)
                by_category[category.value] = count

            return {
                "total_signals": total,
                "by_category": by_category,
                "oldest": self.signal_history[0].timestamp if self.signal_history else None,
                "newest": self.signal_history[-1].timestamp if self.signal_history else None,
            }

    async def cleanup_old_signals(self) -> int:
        """Remove signals older than retention period"""
        async with self._lock:
            cutoff = datetime.utcnow() - timedelta(days=settings.SIGNAL_RETENTION_DAYS)
            before_count = len(self.signals)

            # Remove from dict
            expired_ids = [
                sid for sid, signal in self.signals.items()
                if signal.timestamp < cutoff
            ]
            for sid in expired_ids:
                del self.signals[sid]

            removed = before_count - len(self.signals)
            if removed > 0:
                logger.info(f"Cleaned up {removed} old signals")

            return removed


# Global storage instance
signal_storage = SignalStorage()
