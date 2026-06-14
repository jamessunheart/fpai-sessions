#!/usr/bin/env python3
"""
ARIA REFLECTION TRIGGER SYSTEM
==============================

Triggers reflection cycles based on:
1. Scheduled time (daily at 6 AM, weekly deep review on Sundays)
2. Interaction threshold (every 50 interactions)
3. High-severity pattern detection
4. Manual command (/reflect now)
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.reflection.trigger")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("REFLECTION_DB", "/opt/fpai/aria-command/state/reflection.db")
EVOLUTION_DB = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")

# Trigger thresholds
INTERACTION_THRESHOLD = int(os.getenv("REFLECTION_INTERACTION_THRESHOLD", "50"))
DAILY_HOUR = int(os.getenv("REFLECTION_DAILY_HOUR", "6"))  # 6 AM
WEEKLY_DAY = int(os.getenv("REFLECTION_WEEKLY_DAY", "6"))  # Sunday = 6

# Cost limits
DAILY_COST_CAP = float(os.getenv("REFLECTION_DAILY_COST_CAP", "1.0"))


class TriggerType(str, Enum):
    SCHEDULED_DAILY = "scheduled_daily"
    SCHEDULED_WEEKLY = "scheduled_weekly"
    THRESHOLD = "threshold"
    PATTERN = "pattern"
    MANUAL = "manual"


@dataclass
class TriggerEvent:
    """A trigger event that initiates a reflection cycle."""
    trigger_type: TriggerType
    triggered_at: datetime = field(default_factory=datetime.now)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "trigger_type": self.trigger_type.value,
            "triggered_at": self.triggered_at.isoformat(),
            "reason": self.reason,
            "metadata": self.metadata
        }


TRIGGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS trigger_state (
    id INTEGER PRIMARY KEY,
    last_daily_trigger TEXT,
    last_weekly_trigger TEXT,
    last_threshold_trigger TEXT,
    interactions_since_last INTEGER DEFAULT 0,
    daily_cost_spent REAL DEFAULT 0.0,
    daily_cost_reset_date TEXT,
    paused INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trigger_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_type TEXT NOT NULL,
    triggered_at TEXT NOT NULL,
    reason TEXT,
    metadata TEXT,
    cycle_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_th_type ON trigger_history(trigger_type);
CREATE INDEX IF NOT EXISTS idx_th_date ON trigger_history(triggered_at);
"""


# ============================================================================
# REFLECTION TRIGGER
# ============================================================================

class ReflectionTrigger:
    """
    Manages triggers for reflection cycles.
    
    Monitors:
    - Time-based schedules (daily, weekly)
    - Interaction count thresholds
    - Pattern detection signals
    - Manual triggers
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._callbacks: List[Callable[[TriggerEvent], None]] = []
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
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
            cursor.executescript(TRIGGER_SCHEMA)
            
            # Ensure state row exists
            cursor.execute("SELECT COUNT(*) FROM trigger_state")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO trigger_state (id, daily_cost_reset_date)
                    VALUES (1, ?)
                """, (datetime.now().date().isoformat(),))
        
        logger.info(f"Reflection trigger initialized: {self.db_path}")
    
    def register_callback(self, callback: Callable[[TriggerEvent], None]):
        """Register a callback to be called when trigger fires."""
        self._callbacks.append(callback)
    
    def _fire_trigger(self, event: TriggerEvent):
        """Fire trigger and notify callbacks."""
        # Record in history
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO trigger_history (trigger_type, triggered_at, reason, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                event.trigger_type.value,
                event.triggered_at.isoformat(),
                event.reason,
                json.dumps(event.metadata)
            ))
        
        logger.info(f"Trigger fired: {event.trigger_type.value} - {event.reason}")
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Trigger callback error: {e}")
    
    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================
    
    def _get_state(self) -> Dict[str, Any]:
        """Get current trigger state."""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM trigger_state WHERE id = 1")
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def _update_state(self, **kwargs):
        """Update trigger state."""
        if not kwargs:
            return
        
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values())
        
        with self._cursor() as cursor:
            cursor.execute(f"UPDATE trigger_state SET {set_clause} WHERE id = 1", values)
    
    def is_paused(self) -> bool:
        """Check if reflection is paused."""
        state = self._get_state()
        return bool(state.get("paused", 0))
    
    def pause(self):
        """Pause reflection triggers."""
        self._update_state(paused=1)
        logger.info("Reflection triggers paused")
    
    def resume(self):
        """Resume reflection triggers."""
        self._update_state(paused=0)
        logger.info("Reflection triggers resumed")
    
    # ========================================================================
    # COST TRACKING
    # ========================================================================
    
    def _check_cost_cap(self) -> bool:
        """Check if daily cost cap allows more spending."""
        state = self._get_state()
        
        # Reset if new day
        today = datetime.now().date().isoformat()
        if state.get("daily_cost_reset_date") != today:
            self._update_state(daily_cost_spent=0.0, daily_cost_reset_date=today)
            return True
        
        return state.get("daily_cost_spent", 0) < DAILY_COST_CAP
    
    def record_cost(self, cost: float):
        """Record cost spent on reflection."""
        state = self._get_state()
        new_cost = state.get("daily_cost_spent", 0) + cost
        self._update_state(daily_cost_spent=new_cost)
    
    def get_daily_cost(self) -> float:
        """Get cost spent today."""
        state = self._get_state()
        today = datetime.now().date().isoformat()
        
        if state.get("daily_cost_reset_date") != today:
            return 0.0
        
        return state.get("daily_cost_spent", 0)
    
    # ========================================================================
    # TRIGGER CHECKS
    # ========================================================================
    
    def check_scheduled_daily(self) -> Optional[TriggerEvent]:
        """Check if daily scheduled trigger should fire."""
        state = self._get_state()
        now = datetime.now()
        
        # Check if it's the right hour
        if now.hour != DAILY_HOUR:
            return None
        
        # Check if already triggered today
        last_trigger = state.get("last_daily_trigger")
        if last_trigger:
            last_dt = datetime.fromisoformat(last_trigger)
            if last_dt.date() == now.date():
                return None
        
        # Fire trigger
        self._update_state(last_daily_trigger=now.isoformat())
        
        return TriggerEvent(
            trigger_type=TriggerType.SCHEDULED_DAILY,
            reason=f"Daily scheduled reflection at {DAILY_HOUR}:00",
            metadata={"scheduled_hour": DAILY_HOUR}
        )
    
    def check_scheduled_weekly(self) -> Optional[TriggerEvent]:
        """Check if weekly scheduled trigger should fire."""
        state = self._get_state()
        now = datetime.now()
        
        # Check if it's the right day and hour
        if now.weekday() != WEEKLY_DAY or now.hour != DAILY_HOUR:
            return None
        
        # Check if already triggered this week
        last_trigger = state.get("last_weekly_trigger")
        if last_trigger:
            last_dt = datetime.fromisoformat(last_trigger)
            # Same week check
            if (now - last_dt).days < 7:
                return None
        
        # Fire trigger
        self._update_state(last_weekly_trigger=now.isoformat())
        
        return TriggerEvent(
            trigger_type=TriggerType.SCHEDULED_WEEKLY,
            reason="Weekly deep reflection cycle",
            metadata={"is_deep_review": True}
        )
    
    def check_threshold(self) -> Optional[TriggerEvent]:
        """Check if interaction threshold trigger should fire."""
        state = self._get_state()
        interactions = state.get("interactions_since_last", 0)
        
        if interactions < INTERACTION_THRESHOLD:
            return None
        
        # Reset counter and fire
        self._update_state(
            interactions_since_last=0,
            last_threshold_trigger=datetime.now().isoformat()
        )
        
        return TriggerEvent(
            trigger_type=TriggerType.THRESHOLD,
            reason=f"Reached {INTERACTION_THRESHOLD} interactions",
            metadata={"interaction_count": interactions}
        )
    
    def increment_interactions(self, count: int = 1):
        """Increment interaction counter."""
        state = self._get_state()
        new_count = state.get("interactions_since_last", 0) + count
        self._update_state(interactions_since_last=new_count)
    
    def check_patterns(self) -> Optional[TriggerEvent]:
        """Check if high-severity patterns should trigger reflection."""
        try:
            # Connect to evolution DB to check patterns
            conn = sqlite3.connect(EVOLUTION_DB)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check for recent high-severity patterns
            since = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) as count FROM detected_patterns
                WHERE detected_at > ? AND severity = 'high' AND addressed = 0
            """, (since,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result["count"] >= 2:
                return TriggerEvent(
                    trigger_type=TriggerType.PATTERN,
                    reason=f"Detected {result['count']} high-severity patterns",
                    metadata={"pattern_count": result["count"]}
                )
            
        except Exception as e:
            logger.debug(f"Pattern check failed: {e}")
        
        return None
    
    def trigger_manual(self, reason: str = "Manual trigger") -> TriggerEvent:
        """Manually trigger a reflection cycle."""
        event = TriggerEvent(
            trigger_type=TriggerType.MANUAL,
            reason=reason,
            metadata={"triggered_by": "user"}
        )
        
        self._fire_trigger(event)
        return event
    
    # ========================================================================
    # MAIN CHECK LOOP
    # ========================================================================
    
    def check_all(self) -> Optional[TriggerEvent]:
        """Check all triggers and return first that fires."""
        if self.is_paused():
            return None
        
        if not self._check_cost_cap():
            logger.debug("Daily cost cap reached, skipping triggers")
            return None
        
        # Check in priority order
        checks = [
            self.check_patterns,      # Highest priority
            self.check_scheduled_weekly,
            self.check_scheduled_daily,
            self.check_threshold,
        ]
        
        for check in checks:
            event = check()
            if event:
                self._fire_trigger(event)
                return event
        
        return None
    
    async def start(self):
        """Start the trigger monitoring loop."""
        if self._running:
            return
        
        self._running = True
        logger.info("Reflection trigger monitor started")
        
        while self._running:
            try:
                event = self.check_all()
                if event:
                    logger.info(f"Trigger check found: {event.trigger_type.value}")
            except Exception as e:
                logger.error(f"Trigger check error: {e}")
            
            # Check every minute
            await asyncio.sleep(60)
    
    def stop(self):
        """Stop the trigger monitoring loop."""
        self._running = False
        logger.info("Reflection trigger monitor stopped")
    
    # ========================================================================
    # STATUS
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get trigger system status."""
        state = self._get_state()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT trigger_type, COUNT(*) as count, MAX(triggered_at) as last
                FROM trigger_history
                GROUP BY trigger_type
            """)
            history_summary = {row["trigger_type"]: {"count": row["count"], "last": row["last"]} 
                            for row in cursor.fetchall()}
        
        return {
            "paused": bool(state.get("paused", 0)),
            "interactions_since_last": state.get("interactions_since_last", 0),
            "interaction_threshold": INTERACTION_THRESHOLD,
            "daily_cost_spent": state.get("daily_cost_spent", 0),
            "daily_cost_cap": DAILY_COST_CAP,
            "last_daily_trigger": state.get("last_daily_trigger"),
            "last_weekly_trigger": state.get("last_weekly_trigger"),
            "history_summary": history_summary
        }
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get recent trigger history."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT trigger_type, triggered_at, reason, metadata
                FROM trigger_history
                ORDER BY triggered_at DESC
                LIMIT ?
            """, (limit,))
            
            return [
                {
                    "trigger_type": row["trigger_type"],
                    "triggered_at": row["triggered_at"],
                    "reason": row["reason"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                }
                for row in cursor.fetchall()
            ]


# ============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ============================================================================

_trigger: Optional[ReflectionTrigger] = None


def get_trigger() -> ReflectionTrigger:
    """Get global trigger instance."""
    global _trigger
    if _trigger is None:
        _trigger = ReflectionTrigger()
    return _trigger


def trigger_manual(reason: str = "Manual trigger") -> TriggerEvent:
    """Manually trigger reflection."""
    return get_trigger().trigger_manual(reason)


def increment_interactions(count: int = 1):
    """Increment interaction counter."""
    get_trigger().increment_interactions(count)


def get_trigger_status() -> Dict[str, Any]:
    """Get trigger status."""
    return get_trigger().get_status()


def pause_triggers():
    """Pause all triggers."""
    get_trigger().pause()


def resume_triggers():
    """Resume triggers."""
    get_trigger().resume()

