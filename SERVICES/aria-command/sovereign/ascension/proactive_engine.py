#!/usr/bin/env python3
"""
ARIA ASCENSION - PROACTIVE ENGINE
=================================

Generate proactive actions based on predictions:
- Score potential proactive actions
- Threshold: Only act if confidence > 80%
- Anti-spam: Max 3 proactive messages/hour

Makes Aria anticipate needs before asking.
"""

import os
import json
import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.ascension.proactive")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")

# Proactive limits
MAX_PROACTIVE_PER_HOUR = int(os.getenv("MAX_PROACTIVE_PER_HOUR", "3"))
MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_PROACTIVE_CONFIDENCE", "0.8"))
COOLDOWN_MINUTES = int(os.getenv("PROACTIVE_COOLDOWN_MINUTES", "15"))


class ActionType(str, Enum):
    """Types of proactive actions."""
    ALERT = "alert"           # Important notification
    SUGGESTION = "suggestion"  # Helpful suggestion
    BRIEFING = "briefing"     # Daily/morning brief
    REMINDER = "reminder"     # Scheduled reminder
    INSIGHT = "insight"       # Pattern-based insight
    OFFER = "offer"           # Offer to help


class ActionPriority(str, Enum):
    """Priority levels for proactive actions."""
    CRITICAL = "critical"  # Send immediately
    HIGH = "high"          # Send soon
    NORMAL = "normal"      # Send when convenient
    LOW = "low"            # Can wait


@dataclass
class ProactiveAction:
    """A potential proactive action."""
    id: str
    action_type: ActionType
    priority: ActionPriority
    message: str
    confidence: float
    reason: str
    trigger: str
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = None
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "priority": self.priority.value,
            "message": self.message,
            "confidence": self.confidence,
            "reason": self.reason,
            "trigger": self.trigger,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "data": self.data
        }


PROACTIVE_SCHEMA = """
CREATE TABLE IF NOT EXISTS proactive_queue (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    message TEXT NOT NULL,
    confidence REAL,
    reason TEXT,
    trigger TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    data TEXT,
    sent INTEGER DEFAULT 0,
    sent_at TEXT
);

CREATE TABLE IF NOT EXISTS proactive_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    user_response TEXT,
    was_helpful INTEGER
);

CREATE TABLE IF NOT EXISTS proactive_limits (
    id INTEGER PRIMARY KEY,
    hourly_count INTEGER DEFAULT 0,
    last_reset TEXT,
    last_sent TEXT
);

CREATE INDEX IF NOT EXISTS idx_pq_priority ON proactive_queue(priority);
CREATE INDEX IF NOT EXISTS idx_pq_sent ON proactive_queue(sent);
CREATE INDEX IF NOT EXISTS idx_ph_type ON proactive_history(action_type);
"""


# ============================================================================
# PROACTIVE ENGINE
# ============================================================================

class ProactiveEngine:
    """
    Engine for generating and managing proactive actions.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._action_generators: List[Callable] = []
        self._send_callback: Optional[Callable] = None
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_db(self):
        """Initialize database."""
        from pathlib import Path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with self._cursor() as cursor:
            cursor.executescript(PROACTIVE_SCHEMA)
            
            # Ensure limits row exists
            cursor.execute("SELECT COUNT(*) FROM proactive_limits")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO proactive_limits (id, hourly_count, last_reset)
                    VALUES (1, 0, ?)
                """, (datetime.now().isoformat(),))
        
        logger.info(f"Proactive engine initialized: {self.db_path}")
    
    def set_send_callback(self, callback: Callable[[ProactiveAction], None]):
        """Set callback for sending proactive messages."""
        self._send_callback = callback
    
    def register_generator(self, generator: Callable[[], List[ProactiveAction]]):
        """Register an action generator."""
        self._action_generators.append(generator)
    
    # ========================================================================
    # ACTION MANAGEMENT
    # ========================================================================
    
    def queue_action(self, action: ProactiveAction):
        """Queue a proactive action."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO proactive_queue
                (id, action_type, priority, message, confidence, reason, trigger, created_at, expires_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action.id, action.action_type.value, action.priority.value,
                action.message, action.confidence, action.reason, action.trigger,
                action.created_at.isoformat(),
                action.expires_at.isoformat() if action.expires_at else None,
                json.dumps(action.data)
            ))
        
        logger.debug(f"Queued proactive action: {action.id} ({action.action_type.value})")
    
    def get_pending_actions(self) -> List[ProactiveAction]:
        """Get all pending (unsent) actions."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM proactive_queue
                WHERE sent = 0 AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY 
                    CASE priority 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'normal' THEN 3 
                        ELSE 4 
                    END,
                    created_at ASC
            """, (datetime.now().isoformat(),))
            
            return [self._row_to_action(row) for row in cursor.fetchall()]
    
    def _row_to_action(self, row) -> ProactiveAction:
        """Convert database row to ProactiveAction."""
        return ProactiveAction(
            id=row["id"],
            action_type=ActionType(row["action_type"]),
            priority=ActionPriority(row["priority"]),
            message=row["message"],
            confidence=row["confidence"],
            reason=row["reason"],
            trigger=row["trigger"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            data=json.loads(row["data"] or "{}")
        )
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    
    def _check_rate_limit(self) -> bool:
        """Check if we can send another proactive message."""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM proactive_limits WHERE id = 1")
            row = cursor.fetchone()
            
            if not row:
                return True
            
            # Reset hourly count if needed
            last_reset = datetime.fromisoformat(row["last_reset"])
            if datetime.now() - last_reset > timedelta(hours=1):
                cursor.execute("""
                    UPDATE proactive_limits SET hourly_count = 0, last_reset = ? WHERE id = 1
                """, (datetime.now().isoformat(),))
                return True
            
            # Check hourly limit
            if row["hourly_count"] >= MAX_PROACTIVE_PER_HOUR:
                return False
            
            # Check cooldown
            if row["last_sent"]:
                last_sent = datetime.fromisoformat(row["last_sent"])
                if datetime.now() - last_sent < timedelta(minutes=COOLDOWN_MINUTES):
                    return False
            
            return True
    
    def _record_sent(self, action: ProactiveAction):
        """Record that an action was sent."""
        with self._cursor() as cursor:
            # Update queue
            cursor.execute("""
                UPDATE proactive_queue SET sent = 1, sent_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), action.id))
            
            # Update limits
            cursor.execute("""
                UPDATE proactive_limits 
                SET hourly_count = hourly_count + 1, last_sent = ?
                WHERE id = 1
            """, (datetime.now().isoformat(),))
            
            # Add to history
            cursor.execute("""
                INSERT INTO proactive_history (action_id, action_type, sent_at)
                VALUES (?, ?, ?)
            """, (action.id, action.action_type.value, datetime.now().isoformat()))
    
    # ========================================================================
    # SENDING
    # ========================================================================
    
    async def process_queue(self) -> Optional[ProactiveAction]:
        """
        Process the queue and send the next appropriate action.
        Returns the sent action or None if nothing was sent.
        """
        # Check rate limit
        if not self._check_rate_limit():
            logger.debug("Rate limit reached, skipping proactive")
            return None
        
        # Get pending actions
        actions = self.get_pending_actions()
        
        for action in actions:
            # Check confidence threshold (critical bypasses)
            if action.priority != ActionPriority.CRITICAL:
                if action.confidence < MIN_CONFIDENCE_THRESHOLD:
                    continue
            
            # Send if we have a callback
            if self._send_callback:
                try:
                    await self._send_callback(action)
                    self._record_sent(action)
                    logger.info(f"Sent proactive: {action.action_type.value} - {action.message[:50]}...")
                    return action
                except Exception as e:
                    logger.error(f"Failed to send proactive: {e}")
            else:
                # No callback, just record as sent
                self._record_sent(action)
                return action
        
        return None
    
    async def send_now(self, action: ProactiveAction) -> bool:
        """Send an action immediately (bypasses queue)."""
        # Critical actions bypass rate limit
        if action.priority != ActionPriority.CRITICAL:
            if not self._check_rate_limit():
                return False
        
        if self._send_callback:
            try:
                await self._send_callback(action)
                self._record_sent(action)
                return True
            except Exception as e:
                logger.error(f"Failed to send: {e}")
                return False
        
        return False
    
    # ========================================================================
    # GENERATION
    # ========================================================================
    
    def generate_actions(self) -> List[ProactiveAction]:
        """Generate new proactive actions from all generators."""
        all_actions = []
        
        for generator in self._action_generators:
            try:
                actions = generator()
                all_actions.extend(actions)
            except Exception as e:
                logger.error(f"Generator error: {e}")
        
        # Queue all generated actions
        for action in all_actions:
            self.queue_action(action)
        
        return all_actions
    
    # ========================================================================
    # FEEDBACK
    # ========================================================================
    
    def record_feedback(self, action_id: str, was_helpful: bool, response: str = None):
        """Record user feedback on a proactive action."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE proactive_history
                SET was_helpful = ?, user_response = ?
                WHERE action_id = ?
            """, (1 if was_helpful else 0, response, action_id))
    
    # ========================================================================
    # BUILT-IN GENERATORS
    # ========================================================================
    
    def generate_time_based_actions(self) -> List[ProactiveAction]:
        """Generate actions based on time of day."""
        now = datetime.now()
        actions = []
        
        # Morning brief (6-8 AM on weekdays)
        if now.weekday() < 5 and 6 <= now.hour < 8:
            actions.append(ProactiveAction(
                id=f"morning-brief-{now.strftime('%Y%m%d')}",
                action_type=ActionType.BRIEFING,
                priority=ActionPriority.NORMAL,
                message="☀️ Good morning! Would you like your daily brief? (Trading signals, server status, pending tasks)",
                confidence=0.85,
                reason="Morning routine time",
                trigger="time:morning_weekday"
            ))
        
        # Market close reminder (4 PM on weekdays)
        if now.weekday() < 5 and now.hour == 16:
            actions.append(ProactiveAction(
                id=f"market-close-{now.strftime('%Y%m%d')}",
                action_type=ActionType.REMINDER,
                priority=ActionPriority.NORMAL,
                message="📊 Market is closing soon. Want to review your positions?",
                confidence=0.75,
                reason="Market hours",
                trigger="time:market_close"
            ))
        
        return actions
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proactive engine statistics."""
        with self._cursor() as cursor:
            # Queue stats
            cursor.execute("""
                SELECT COUNT(*) as pending FROM proactive_queue WHERE sent = 0
            """)
            pending = cursor.fetchone()["pending"]
            
            # History stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN was_helpful = 1 THEN 1 ELSE 0 END) as helpful,
                    SUM(CASE WHEN was_helpful = 0 THEN 1 ELSE 0 END) as not_helpful
                FROM proactive_history
                WHERE sent_at > ?
            """, ((datetime.now() - timedelta(days=7)).isoformat(),))
            history = cursor.fetchone()
            
            # Rate limit status
            cursor.execute("SELECT * FROM proactive_limits WHERE id = 1")
            limits = cursor.fetchone()
        
        return {
            "pending_actions": pending,
            "sent_last_7_days": history["total"] or 0,
            "helpful_rate": (history["helpful"] or 0) / max(history["total"] or 1, 1),
            "hourly_remaining": MAX_PROACTIVE_PER_HOUR - (limits["hourly_count"] or 0) if limits else MAX_PROACTIVE_PER_HOUR,
            "can_send_now": self._check_rate_limit()
        }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_engine: Optional[ProactiveEngine] = None


def get_proactive_engine() -> ProactiveEngine:
    """Get global proactive engine."""
    global _engine
    if _engine is None:
        _engine = ProactiveEngine()
    return _engine


def queue_proactive(action: ProactiveAction):
    """Queue a proactive action."""
    get_proactive_engine().queue_action(action)


async def process_proactive_queue() -> Optional[ProactiveAction]:
    """Process proactive queue."""
    return await get_proactive_engine().process_queue()


def create_proactive(
    action_type: ActionType,
    message: str,
    priority: ActionPriority = ActionPriority.NORMAL,
    confidence: float = 0.8,
    reason: str = "",
    trigger: str = ""
) -> ProactiveAction:
    """Create a proactive action."""
    import uuid
    return ProactiveAction(
        id=str(uuid.uuid4())[:8],
        action_type=action_type,
        priority=priority,
        message=message,
        confidence=confidence,
        reason=reason,
        trigger=trigger
    )


