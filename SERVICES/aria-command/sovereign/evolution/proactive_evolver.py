#!/usr/bin/env python3
"""
ARIA PROACTIVITY EVOLVER
=========================

Learns when and how to initiate proactive actions based on:
- Time patterns (James always checks X in morning)
- Event triggers (After deployment, James checks logs)
- Correlations (When metric X drops, action Y needed)

Features:
- Time-based pattern detection
- Event-action correlation
- Proactive suggestion generation
- Anti-spam safeguards
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import defaultdict
import threading

from .interaction_logger import get_interaction_logger, IntentCategory

logger = logging.getLogger("aria.evolution.proactive")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")
MIN_PATTERN_CONFIDENCE = 0.7  # Minimum confidence to suggest proactively
MAX_PROACTIVE_PER_HOUR = 3    # Anti-spam limit


@dataclass
class ProactivePattern:
    """A learned proactive pattern."""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Trigger
    trigger_type: str = ""  # time, event, metric
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    
    # Action
    action_type: str = ""  # message, check, alert
    action_data: Dict[str, Any] = field(default_factory=dict)
    
    # Learning
    occurrence_count: int = 0
    confidence: float = 0.0
    last_triggered: Optional[datetime] = None
    success_count: int = 0
    ignore_count: int = 0  # User ignored the proactive message
    
    # Status
    is_active: bool = True


PROACTIVE_SCHEMA = """
CREATE TABLE IF NOT EXISTS proactive_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_data TEXT,
    action_type TEXT,
    action_data TEXT,
    occurrence_count INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0,
    last_triggered TEXT,
    success_count INTEGER DEFAULT 0,
    ignore_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_pp_trigger ON proactive_patterns(trigger_type);
CREATE INDEX IF NOT EXISTS idx_pp_confidence ON proactive_patterns(confidence);
CREATE INDEX IF NOT EXISTS idx_pp_active ON proactive_patterns(is_active);

CREATE TABLE IF NOT EXISTS proactive_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER,
    triggered_at TEXT NOT NULL,
    trigger_reason TEXT,
    action_taken TEXT,
    user_response TEXT,
    was_helpful INTEGER
);

CREATE INDEX IF NOT EXISTS idx_ph_pattern ON proactive_history(pattern_id);
CREATE INDEX IF NOT EXISTS idx_ph_time ON proactive_history(triggered_at);

CREATE TABLE IF NOT EXISTS time_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    hour INTEGER NOT NULL,
    day_of_week INTEGER,
    intent TEXT,
    occurrence_count INTEGER DEFAULT 1,
    last_seen TEXT
);

CREATE INDEX IF NOT EXISTS idx_tp_user ON time_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_tp_hour ON time_patterns(hour);
"""


# ============================================================================
# PROACTIVITY EVOLVER
# ============================================================================

class ProactiveEvolver:
    """
    Learns proactive behavior patterns.
    
    Process:
    1. Track interaction times and contexts
    2. Detect recurring patterns
    3. Generate proactive suggestions
    4. Track effectiveness
    5. Refine patterns
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        self._last_proactive: Dict[str, datetime] = {}  # Anti-spam tracking
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Get cursor with auto-commit."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def _init_db(self):
        """Initialize database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._cursor() as cursor:
            cursor.executescript(PROACTIVE_SCHEMA)
        logger.info(f"Proactive evolver initialized: {self.db_path}")
    
    def learn_from_interaction(
        self,
        user_id: str,
        intent: str,
        message: str,
        tools_used: List[str] = None
    ):
        """Learn time patterns from an interaction."""
        now = datetime.now()
        hour = now.hour
        day = now.weekday()
        
        with self._cursor() as cursor:
            # Update or insert time pattern
            # First try to update existing
            cursor.execute("""
                UPDATE time_patterns 
                SET occurrence_count = occurrence_count + 1, last_seen = ?
                WHERE user_id = ? AND hour = ? AND intent = ?
            """, (now.isoformat(), user_id, hour, intent))
            
            if cursor.rowcount == 0:
                # Insert new
                cursor.execute("""
                    INSERT INTO time_patterns (user_id, hour, day_of_week, intent, occurrence_count, last_seen)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (user_id, hour, day, intent, now.isoformat()))
            
            # Check if we have enough data to create a proactive pattern
            self._check_for_pattern(user_id, hour, intent)
    
    def _check_for_pattern(self, user_id: str, hour: int, intent: str, threshold: int = 5):
        """Check if we should create a proactive pattern."""
        with self._cursor() as cursor:
            # Check if this hour/intent combo happens frequently
            cursor.execute("""
                SELECT SUM(occurrence_count) as total
                FROM time_patterns
                WHERE user_id = ? AND hour = ? AND intent = ?
            """, (user_id, hour, intent))
            
            total = cursor.fetchone()["total"] or 0
            
            if total >= threshold:
                # Check if we already have this pattern
                cursor.execute("""
                    SELECT id FROM proactive_patterns
                    WHERE trigger_type = 'time'
                    AND json_extract(trigger_data, '$.hour') = ?
                    AND json_extract(action_data, '$.intent') = ?
                """, (hour, intent))
                
                if not cursor.fetchone():
                    # Create new pattern
                    self._create_time_pattern(user_id, hour, intent, total)
    
    def _create_time_pattern(self, user_id: str, hour: int, intent: str, count: int):
        """Create a time-based proactive pattern."""
        # Map intent to action
        action_map = {
            "trading": {"message": "Good morning! Want me to check market conditions?", "check": "market_status"},
            "server": {"message": "Want me to check server health?", "check": "server_status"},
            "question": {"message": "I'm here if you need anything!", "check": None}
        }
        
        action = action_map.get(intent, {"message": "Ready to help!", "check": None})
        
        pattern = ProactivePattern(
            trigger_type="time",
            trigger_data={"hour": hour, "user_id": user_id},
            action_type="message",
            action_data={"intent": intent, **action},
            occurrence_count=count,
            confidence=min(0.9, count / 20)  # Caps at 0.9
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO proactive_patterns (
                    created_at, trigger_type, trigger_data, action_type,
                    action_data, occurrence_count, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                pattern.trigger_type,
                json.dumps(pattern.trigger_data),
                pattern.action_type,
                json.dumps(pattern.action_data),
                pattern.occurrence_count,
                pattern.confidence
            ))
        
        logger.info(f"Created time pattern: hour={hour}, intent={intent}")
    
    def get_due_actions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get proactive actions that are due now."""
        now = datetime.now()
        hour = now.hour
        
        # Anti-spam check
        last = self._last_proactive.get(user_id)
        if last and (now - last).total_seconds() < 3600 / MAX_PROACTIVE_PER_HOUR:
            return []
        
        actions = []
        
        with self._cursor() as cursor:
            # Get time-based patterns
            cursor.execute("""
                SELECT * FROM proactive_patterns
                WHERE trigger_type = 'time'
                AND is_active = 1
                AND confidence >= ?
                AND (
                    json_extract(trigger_data, '$.user_id') = ?
                    OR json_extract(trigger_data, '$.user_id') IS NULL
                )
                AND json_extract(trigger_data, '$.hour') = ?
            """, (MIN_PATTERN_CONFIDENCE, user_id, hour))
            
            for row in cursor.fetchall():
                # Check if already triggered today
                last_triggered = row["last_triggered"]
                if last_triggered:
                    last_dt = datetime.fromisoformat(last_triggered)
                    if last_dt.date() == now.date():
                        continue  # Already triggered today
                
                action_data = json.loads(row["action_data"]) if row["action_data"] else {}
                
                actions.append({
                    "pattern_id": row["id"],
                    "type": row["action_type"],
                    "message": action_data.get("message", ""),
                    "check": action_data.get("check"),
                    "confidence": row["confidence"]
                })
        
        return actions
    
    def record_trigger(self, pattern_id: int, action: str, user_response: str = None, was_helpful: bool = None):
        """Record that a pattern was triggered."""
        now = datetime.now()
        
        with self._cursor() as cursor:
            # Update pattern
            cursor.execute("""
                UPDATE proactive_patterns
                SET last_triggered = ?,
                    success_count = success_count + ?,
                    ignore_count = ignore_count + ?
                WHERE id = ?
            """, (
                now.isoformat(),
                1 if was_helpful else 0,
                1 if was_helpful is False else 0,
                pattern_id
            ))
            
            # Log history
            cursor.execute("""
                INSERT INTO proactive_history (
                    pattern_id, triggered_at, action_taken, user_response, was_helpful
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                pattern_id,
                now.isoformat(),
                action,
                user_response,
                1 if was_helpful else (0 if was_helpful is False else None)
            ))
            
            # Update confidence based on feedback
            if was_helpful is not None:
                self._update_confidence(pattern_id)
    
    def _update_confidence(self, pattern_id: int):
        """Update pattern confidence based on performance."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT success_count, ignore_count, occurrence_count
                FROM proactive_patterns
                WHERE id = ?
            """, (pattern_id,))
            
            row = cursor.fetchone()
            if not row:
                return
            
            total_feedback = row["success_count"] + row["ignore_count"]
            if total_feedback == 0:
                return
            
            # Calculate new confidence
            base_confidence = row["success_count"] / total_feedback
            # Blend with occurrence-based confidence
            occurrence_confidence = min(0.9, row["occurrence_count"] / 20)
            new_confidence = (base_confidence * 0.7) + (occurrence_confidence * 0.3)
            
            cursor.execute("""
                UPDATE proactive_patterns
                SET confidence = ?
                WHERE id = ?
            """, (new_confidence, pattern_id))
            
            # Disable if confidence drops too low
            if new_confidence < 0.3:
                cursor.execute("""
                    UPDATE proactive_patterns
                    SET is_active = 0
                    WHERE id = ?
                """, (pattern_id,))
                logger.info(f"Disabled low-confidence pattern {pattern_id}")
    
    def learn_from_event(self, event_type: str, event_data: Dict[str, Any], subsequent_action: str):
        """
        Learn event-action correlations.
        
        Example: After 'deployment' event, user often runs 'check_logs'.
        """
        with self._cursor() as cursor:
            # Check for existing pattern
            cursor.execute("""
                SELECT id, occurrence_count FROM proactive_patterns
                WHERE trigger_type = 'event'
                AND json_extract(trigger_data, '$.event_type') = ?
                AND json_extract(action_data, '$.subsequent_action') = ?
            """, (event_type, subsequent_action))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing
                new_count = row["occurrence_count"] + 1
                cursor.execute("""
                    UPDATE proactive_patterns
                    SET occurrence_count = ?,
                        confidence = ?
                    WHERE id = ?
                """, (new_count, min(0.9, new_count / 10), row["id"]))
            else:
                # Create new
                cursor.execute("""
                    INSERT INTO proactive_patterns (
                        created_at, trigger_type, trigger_data,
                        action_type, action_data, occurrence_count, confidence
                    ) VALUES (?, 'event', ?, 'suggest', ?, 1, 0.3)
                """, (
                    datetime.now().isoformat(),
                    json.dumps({"event_type": event_type, **event_data}),
                    json.dumps({"subsequent_action": subsequent_action})
                ))
    
    def get_suggestion_for_event(self, event_type: str) -> Optional[Dict[str, Any]]:
        """Get a proactive suggestion based on an event."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM proactive_patterns
                WHERE trigger_type = 'event'
                AND is_active = 1
                AND confidence >= ?
                AND json_extract(trigger_data, '$.event_type') = ?
                ORDER BY confidence DESC
                LIMIT 1
            """, (MIN_PATTERN_CONFIDENCE, event_type))
            
            row = cursor.fetchone()
            if row:
                action_data = json.loads(row["action_data"]) if row["action_data"] else {}
                return {
                    "pattern_id": row["id"],
                    "action": action_data.get("subsequent_action"),
                    "confidence": row["confidence"]
                }
        
        return None
    
    def get_patterns_summary(self) -> Dict[str, Any]:
        """Get summary of proactive patterns."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT trigger_type, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM proactive_patterns
                WHERE is_active = 1
                GROUP BY trigger_type
            """)
            by_type = {
                row["trigger_type"]: {
                    "count": row["count"],
                    "avg_confidence": row["avg_confidence"]
                }
                for row in cursor.fetchall()
            }
            
            cursor.execute("""
                SELECT SUM(success_count) as successes, SUM(ignore_count) as ignores
                FROM proactive_patterns
            """)
            totals = cursor.fetchone()
            
            total_feedback = (totals["successes"] or 0) + (totals["ignores"] or 0)
            success_rate = totals["successes"] / total_feedback if total_feedback > 0 else 0
        
        return {
            "by_trigger_type": by_type,
            "total_success_rate": success_rate,
            "total_triggers": total_feedback
        }
    
    def get_high_confidence_patterns(self) -> List[ProactivePattern]:
        """Get high-confidence active patterns."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM proactive_patterns
                WHERE is_active = 1 AND confidence >= ?
                ORDER BY confidence DESC
            """, (MIN_PATTERN_CONFIDENCE,))
            
            return [
                ProactivePattern(
                    id=row["id"],
                    trigger_type=row["trigger_type"],
                    trigger_data=json.loads(row["trigger_data"]) if row["trigger_data"] else {},
                    action_type=row["action_type"],
                    action_data=json.loads(row["action_data"]) if row["action_data"] else {},
                    occurrence_count=row["occurrence_count"],
                    confidence=row["confidence"],
                    is_active=True
                )
                for row in cursor.fetchall()
            ]
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_evolver: Optional[ProactiveEvolver] = None


def get_proactive_evolver() -> ProactiveEvolver:
    """Get or create global proactive evolver."""
    global _evolver
    if _evolver is None:
        _evolver = ProactiveEvolver()
    return _evolver


def learn_proactive_pattern(user_id: str, intent: str, message: str, tools: List[str] = None):
    """Learn from an interaction for proactive patterns."""
    get_proactive_evolver().learn_from_interaction(user_id, intent, message, tools)


def get_proactive_actions(user_id: str) -> List[Dict[str, Any]]:
    """Get proactive actions due for a user."""
    return get_proactive_evolver().get_due_actions(user_id)

