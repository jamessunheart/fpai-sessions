#!/usr/bin/env python3
"""
ARIA ASCENSION - RHYTHM DETECTOR
================================

Detect user behavior patterns:
- Time-of-day patterns
- Day-of-week patterns
- Context triggers (e.g., "after market close")

Used to anticipate needs before the user asks.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
from collections import defaultdict

logger = logging.getLogger("aria.ascension.rhythm")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")


@dataclass
class TimeSlot:
    """A time slot for pattern detection."""
    hour: int
    day_of_week: int  # 0=Monday, 6=Sunday
    
    @property
    def is_weekend(self) -> bool:
        return self.day_of_week >= 5
    
    @property
    def period(self) -> str:
        if self.hour < 6:
            return "night"
        elif self.hour < 12:
            return "morning"
        elif self.hour < 18:
            return "afternoon"
        else:
            return "evening"
    
    @property
    def slot_key(self) -> str:
        return f"{self.day_of_week}:{self.hour}"


@dataclass 
class RhythmPattern:
    """A detected rhythm pattern."""
    pattern_type: str  # hourly, daily, weekly
    slot_key: str
    primary_intent: str
    confidence: float
    occurrence_count: int
    last_seen: datetime
    
    def to_dict(self) -> Dict:
        return {
            "pattern_type": self.pattern_type,
            "slot_key": self.slot_key,
            "primary_intent": self.primary_intent,
            "confidence": self.confidence,
            "occurrence_count": self.occurrence_count,
            "last_seen": self.last_seen.isoformat()
        }


@dataclass
class PredictedNeed:
    """A predicted user need."""
    intent: str
    topic: str
    confidence: float
    reason: str
    suggested_action: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "intent": self.intent,
            "topic": self.topic,
            "confidence": self.confidence,
            "reason": self.reason,
            "suggested_action": self.suggested_action
        }


RHYTHM_SCHEMA = """
CREATE TABLE IF NOT EXISTS hourly_patterns (
    hour INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    intent TEXT NOT NULL,
    topic TEXT,
    occurrence_count INTEGER DEFAULT 1,
    last_seen TEXT,
    PRIMARY KEY (hour, day_of_week, intent)
);

CREATE TABLE IF NOT EXISTS sequence_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_event TEXT NOT NULL,
    following_intent TEXT NOT NULL,
    avg_delay_minutes REAL,
    occurrence_count INTEGER DEFAULT 1,
    confidence REAL DEFAULT 0.5,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS user_rhythm_profile (
    id INTEGER PRIMARY KEY,
    typical_start_hour INTEGER,
    typical_end_hour INTEGER,
    most_active_day INTEGER,
    preferred_response_style TEXT,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_hp_hour ON hourly_patterns(hour);
CREATE INDEX IF NOT EXISTS idx_sp_trigger ON sequence_patterns(trigger_event);
"""


# ============================================================================
# RHYTHM DETECTOR
# ============================================================================

class RhythmDetector:
    """
    Detects user behavior rhythms and patterns.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
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
            cursor.executescript(RHYTHM_SCHEMA)
            
            # Ensure profile exists
            cursor.execute("SELECT COUNT(*) FROM user_rhythm_profile")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO user_rhythm_profile 
                    (id, typical_start_hour, typical_end_hour, most_active_day, preferred_response_style, updated_at)
                    VALUES (1, 8, 22, 1, 'balanced', ?)
                """, (datetime.now().isoformat(),))
        
        logger.info(f"Rhythm detector initialized: {self.db_path}")
    
    # ========================================================================
    # RECORDING
    # ========================================================================
    
    def record_activity(
        self,
        intent: str,
        topic: str = None,
        timestamp: datetime = None
    ):
        """Record an activity for rhythm learning."""
        if timestamp is None:
            timestamp = datetime.now()
        
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        with self._cursor() as cursor:
            # Update hourly pattern
            cursor.execute("""
                INSERT INTO hourly_patterns (hour, day_of_week, intent, topic, occurrence_count, last_seen)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(hour, day_of_week, intent) DO UPDATE SET
                    occurrence_count = occurrence_count + 1,
                    last_seen = ?
            """, (hour, day_of_week, intent, topic, timestamp.isoformat(), timestamp.isoformat()))
    
    def record_sequence(
        self,
        trigger_event: str,
        following_intent: str,
        delay_minutes: float
    ):
        """Record a sequence pattern (A followed by B)."""
        with self._cursor() as cursor:
            # Check if pattern exists
            cursor.execute("""
                SELECT id, avg_delay_minutes, occurrence_count FROM sequence_patterns
                WHERE trigger_event = ? AND following_intent = ?
            """, (trigger_event, following_intent))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing
                new_count = row["occurrence_count"] + 1
                new_avg = (row["avg_delay_minutes"] * row["occurrence_count"] + delay_minutes) / new_count
                new_confidence = min(0.95, 0.5 + (new_count * 0.05))
                
                cursor.execute("""
                    UPDATE sequence_patterns
                    SET avg_delay_minutes = ?, occurrence_count = ?, confidence = ?, last_seen = ?
                    WHERE id = ?
                """, (new_avg, new_count, new_confidence, datetime.now().isoformat(), row["id"]))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO sequence_patterns (trigger_event, following_intent, avg_delay_minutes, occurrence_count, last_seen)
                    VALUES (?, ?, ?, 1, ?)
                """, (trigger_event, following_intent, delay_minutes, datetime.now().isoformat()))
    
    # ========================================================================
    # PREDICTION
    # ========================================================================
    
    def predict_current_need(self) -> Optional[PredictedNeed]:
        """
        Predict what the user likely needs RIGHT NOW based on:
        - Current time patterns
        - Recent activity sequences
        """
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        
        with self._cursor() as cursor:
            # Get patterns for current time slot
            cursor.execute("""
                SELECT intent, topic, occurrence_count
                FROM hourly_patterns
                WHERE hour = ? AND day_of_week = ?
                ORDER BY occurrence_count DESC
                LIMIT 5
            """, (hour, day_of_week))
            
            time_patterns = cursor.fetchall()
            
            if not time_patterns:
                # Try same hour, any day
                cursor.execute("""
                    SELECT intent, topic, SUM(occurrence_count) as total
                    FROM hourly_patterns
                    WHERE hour = ?
                    GROUP BY intent
                    ORDER BY total DESC
                    LIMIT 3
                """, (hour,))
                time_patterns = cursor.fetchall()
        
        if not time_patterns:
            return None
        
        top = time_patterns[0]
        total = sum(p["occurrence_count"] if "occurrence_count" in p.keys() else p["total"] for p in time_patterns)
        count = top["occurrence_count"] if "occurrence_count" in top.keys() else top["total"]
        confidence = count / max(total, 1)
        
        return PredictedNeed(
            intent=top["intent"],
            topic=top["topic"] or "",
            confidence=min(0.9, confidence),
            reason=f"Usually active at {hour}:00 on {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][day_of_week]}",
            suggested_action=self._get_suggested_action(top["intent"], top["topic"])
        )
    
    def predict_after_event(self, trigger_event: str) -> Optional[PredictedNeed]:
        """Predict what user needs after a specific event."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT following_intent, avg_delay_minutes, confidence
                FROM sequence_patterns
                WHERE trigger_event = ?
                ORDER BY confidence DESC
                LIMIT 1
            """, (trigger_event,))
            
            row = cursor.fetchone()
            
            if not row or row["confidence"] < 0.6:
                return None
            
            return PredictedNeed(
                intent=row["following_intent"],
                topic="",
                confidence=row["confidence"],
                reason=f"Usually follows {trigger_event}",
                suggested_action=self._get_suggested_action(row["following_intent"], "")
            )
    
    def _get_suggested_action(self, intent: str, topic: str) -> str:
        """Get suggested proactive action for an intent."""
        suggestions = {
            "trading": f"Prepare trading signals{' for ' + topic if topic else ''}",
            "status": "Prepare system status summary",
            "build": "Check for pending build tasks",
            "question": "Be ready with context",
        }
        return suggestions.get(intent, "")
    
    # ========================================================================
    # PROFILE
    # ========================================================================
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get user's rhythm profile."""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM user_rhythm_profile WHERE id = 1")
            row = cursor.fetchone()
            
            if not row:
                return {}
            
            return {
                "typical_start_hour": row["typical_start_hour"],
                "typical_end_hour": row["typical_end_hour"],
                "most_active_day": row["most_active_day"],
                "preferred_response_style": row["preferred_response_style"]
            }
    
    def update_profile(self):
        """Update user profile based on collected data."""
        with self._cursor() as cursor:
            # Find typical active hours
            cursor.execute("""
                SELECT hour, SUM(occurrence_count) as total
                FROM hourly_patterns
                GROUP BY hour
                ORDER BY total DESC
            """)
            hours = cursor.fetchall()
            
            if hours:
                active_hours = [h["hour"] for h in hours[:8]]  # Top 8 hours
                start_hour = min(active_hours)
                end_hour = max(active_hours)
                
                cursor.execute("""
                    UPDATE user_rhythm_profile
                    SET typical_start_hour = ?, typical_end_hour = ?, updated_at = ?
                    WHERE id = 1
                """, (start_hour, end_hour, datetime.now().isoformat()))
            
            # Find most active day
            cursor.execute("""
                SELECT day_of_week, SUM(occurrence_count) as total
                FROM hourly_patterns
                GROUP BY day_of_week
                ORDER BY total DESC
                LIMIT 1
            """)
            day_row = cursor.fetchone()
            
            if day_row:
                cursor.execute("""
                    UPDATE user_rhythm_profile
                    SET most_active_day = ?, updated_at = ?
                    WHERE id = 1
                """, (day_row["day_of_week"], datetime.now().isoformat()))
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_activity_heatmap(self) -> Dict[str, Dict[int, int]]:
        """Get activity heatmap by hour and day."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT hour, day_of_week, SUM(occurrence_count) as total
                FROM hourly_patterns
                GROUP BY hour, day_of_week
            """)
            
            heatmap = defaultdict(lambda: defaultdict(int))
            for row in cursor.fetchall():
                day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][row["day_of_week"]]
                heatmap[day_name][row["hour"]] = row["total"]
            
            return dict(heatmap)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rhythm detection statistics."""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM hourly_patterns")
            pattern_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM sequence_patterns")
            sequence_count = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT intent, SUM(occurrence_count) as total
                FROM hourly_patterns
                GROUP BY intent
                ORDER BY total DESC
                LIMIT 5
            """)
            top_intents = {row["intent"]: row["total"] for row in cursor.fetchall()}
        
        return {
            "total_patterns": pattern_count,
            "sequence_patterns": sequence_count,
            "top_intents": top_intents,
            "profile": self.get_user_profile()
        }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_detector: Optional[RhythmDetector] = None


def get_rhythm_detector() -> RhythmDetector:
    """Get global rhythm detector."""
    global _detector
    if _detector is None:
        _detector = RhythmDetector()
    return _detector


def record_activity(intent: str, topic: str = None):
    """Record activity for rhythm learning."""
    get_rhythm_detector().record_activity(intent, topic)


def predict_current_need() -> Optional[PredictedNeed]:
    """Predict current user need."""
    return get_rhythm_detector().predict_current_need()


