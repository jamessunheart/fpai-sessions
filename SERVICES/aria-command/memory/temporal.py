"""
ARIA TEMPORAL MEMORY
=====================

Understands time-based patterns in memory.

Humans remember WHEN things happened:
- "Last Tuesday we fixed that bug"
- "Every morning James checks trading"
- "This usually happens after deployments"

This module:
1. Tracks temporal patterns (time of day, day of week, sequences)
2. Predicts what's likely to happen based on time
3. Surfaces time-relevant memories
4. Detects recurring issues
"""

import os
import sqlite3
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager
from collections import defaultdict
from enum import Enum

logger = logging.getLogger("aria.memory.temporal")

# Configuration
TEMPORAL_DB_PATH = Path(os.getenv("ARIA_TEMPORAL_DB", "/opt/fpai/aria-command/state/temporal.db"))


class TimeWindow(str, Enum):
    """Time windows for pattern detection."""
    MORNING = "morning"      # 5am - 12pm
    AFTERNOON = "afternoon"  # 12pm - 5pm
    EVENING = "evening"      # 5pm - 9pm
    NIGHT = "night"          # 9pm - 5am
    WEEKDAY = "weekday"
    WEEKEND = "weekend"


class EventType(str, Enum):
    """Types of temporal events."""
    QUERY = "query"           # James asked something
    ERROR = "error"           # Something broke
    FIX = "fix"               # Something was fixed
    DEPLOY = "deploy"         # Deployment happened
    CHECK = "check"           # Status check
    TRADE = "trade"           # Trading activity
    BUILD = "build"           # Building activity


@dataclass
class TemporalEvent:
    """An event with temporal context."""
    id: str
    event_type: EventType
    description: str
    timestamp: datetime
    time_window: TimeWindow
    day_of_week: int  # 0=Monday, 6=Sunday
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.event_type.value,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "time_window": self.time_window.value,
            "day_of_week": self.day_of_week,
            "day_name": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][self.day_of_week],
            "metadata": self.metadata
        }


@dataclass
class TemporalPattern:
    """A detected temporal pattern."""
    id: str
    pattern_type: str  # recurring, sequence, correlation
    description: str
    frequency: str     # daily, weekly, after_X
    confidence: float
    occurrences: int
    last_occurred: datetime
    next_expected: Optional[datetime]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.pattern_type,
            "description": self.description,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "last_occurred": self.last_occurred.isoformat(),
            "next_expected": self.next_expected.isoformat() if self.next_expected else None
        }


class TemporalMemory:
    """
    Time-aware memory that understands patterns over time.
    
    Features:
    - Track when events happen
    - Detect recurring patterns
    - Predict upcoming events
    - Surface time-relevant context
    """
    
    def __init__(self):
        self._ensure_db()
        logger.info("⏰ Temporal memory initialized")
    
    def _ensure_db(self):
        """Create database and tables."""
        TEMPORAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    time_window TEXT NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    hour INTEGER NOT NULL,
                    metadata TEXT DEFAULT '{}'
                );
                
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    occurrences INTEGER DEFAULT 0,
                    last_occurred TEXT,
                    next_expected TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_events_window ON events(time_window);
                CREATE INDEX IF NOT EXISTS idx_events_dow ON events(day_of_week);
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(str(TEMPORAL_DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _get_time_window(self, dt: datetime) -> TimeWindow:
        """Determine time window from datetime."""
        hour = dt.hour
        if 5 <= hour < 12:
            return TimeWindow.MORNING
        elif 12 <= hour < 17:
            return TimeWindow.AFTERNOON
        elif 17 <= hour < 21:
            return TimeWindow.EVENING
        else:
            return TimeWindow.NIGHT
    
    def record_event(
        self,
        event_type: EventType,
        description: str,
        metadata: Dict = None,
        timestamp: datetime = None
    ) -> TemporalEvent:
        """
        Record a temporal event.
        """
        ts = timestamp or datetime.now(timezone.utc)
        event_id = f"evt_{ts.timestamp()}"
        
        event = TemporalEvent(
            id=event_id,
            event_type=event_type,
            description=description[:500],
            timestamp=ts,
            time_window=self._get_time_window(ts),
            day_of_week=ts.weekday(),
            metadata=metadata or {}
        )
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO events 
                (id, event_type, description, timestamp, time_window, day_of_week, hour, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.id,
                event.event_type.value,
                event.description,
                ts.isoformat(),
                event.time_window.value,
                event.day_of_week,
                ts.hour,
                json.dumps(event.metadata)
            ))
        
        # Try to detect patterns
        self._detect_patterns(event)
        
        return event
    
    def _detect_patterns(self, new_event: TemporalEvent):
        """
        Detect temporal patterns based on new event.
        """
        with self._get_connection() as conn:
            # Look for recurring events at same time
            similar = conn.execute("""
                SELECT time_window, day_of_week, COUNT(*) as count
                FROM events
                WHERE event_type = ?
                GROUP BY time_window, day_of_week
                HAVING count >= 3
            """, (new_event.event_type.value,)).fetchall()
            
            for row in similar:
                pattern_id = f"pat_{new_event.event_type.value}_{row['time_window']}_{row['day_of_week']}"
                
                # Check if pattern exists
                existing = conn.execute(
                    "SELECT * FROM patterns WHERE id = ?", (pattern_id,)
                ).fetchone()
                
                if existing:
                    # Update existing pattern
                    conn.execute("""
                        UPDATE patterns
                        SET occurrences = occurrences + 1,
                            last_occurred = ?,
                            confidence = MIN(0.95, confidence + 0.05)
                        WHERE id = ?
                    """, (new_event.timestamp.isoformat(), pattern_id))
                else:
                    # Create new pattern
                    day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][row['day_of_week']]
                    description = f"{new_event.event_type.value.title()} events often occur on {day_name} {row['time_window']}"
                    
                    conn.execute("""
                        INSERT INTO patterns
                        (id, pattern_type, description, frequency, confidence, occurrences, last_occurred)
                        VALUES (?, 'recurring', ?, 'weekly', 0.5, ?, ?)
                    """, (pattern_id, description, row['count'], new_event.timestamp.isoformat()))
    
    def get_relevant_now(self) -> List[TemporalPattern]:
        """
        Get patterns relevant to the current time.
        """
        now = datetime.now(timezone.utc)
        current_window = self._get_time_window(now)
        current_dow = now.weekday()
        
        with self._get_connection() as conn:
            # Get patterns that match current time context
            rows = conn.execute("""
                SELECT * FROM patterns
                WHERE description LIKE ? OR description LIKE ?
                ORDER BY confidence DESC
                LIMIT 5
            """, (f"%{current_window.value}%", f"%{['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][current_dow]}%")).fetchall()
            
            return [self._row_to_pattern(row) for row in rows]
    
    def get_events_in_range(
        self,
        start: datetime,
        end: datetime = None,
        event_type: EventType = None
    ) -> List[TemporalEvent]:
        """
        Get events within a time range.
        """
        end = end or datetime.now(timezone.utc)
        
        with self._get_connection() as conn:
            if event_type:
                rows = conn.execute("""
                    SELECT * FROM events
                    WHERE timestamp >= ? AND timestamp <= ? AND event_type = ?
                    ORDER BY timestamp DESC
                """, (start.isoformat(), end.isoformat(), event_type.value)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM events
                    WHERE timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp DESC
                """, (start.isoformat(), end.isoformat())).fetchall()
            
            return [self._row_to_event(row) for row in rows]
    
    def get_events_today(self, event_type: EventType = None) -> List[TemporalEvent]:
        """Get all events from today."""
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return self.get_events_in_range(start_of_day, now, event_type)
    
    def predict_upcoming(self, hours: int = 4) -> List[Dict]:
        """
        Predict what might happen in the next N hours based on patterns.
        """
        now = datetime.now(timezone.utc)
        predictions = []
        
        # Get patterns with high confidence
        with self._get_connection() as conn:
            patterns = conn.execute("""
                SELECT * FROM patterns
                WHERE confidence > 0.5
                ORDER BY confidence DESC
            """).fetchall()
            
            for row in patterns:
                pattern = self._row_to_pattern(row)
                
                # Check if pattern is likely in next N hours
                if pattern.next_expected:
                    if now <= pattern.next_expected <= now + timedelta(hours=hours):
                        predictions.append({
                            "pattern": pattern.description,
                            "expected_at": pattern.next_expected.isoformat(),
                            "confidence": pattern.confidence
                        })
        
        return predictions
    
    def get_context_prompt(self) -> str:
        """
        Get temporal context for prompt injection.
        """
        now = datetime.now(timezone.utc)
        window = self._get_time_window(now)
        day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][now.weekday()]
        
        lines = [f"\n## ⏰ Temporal Context\n"]
        lines.append(f"*Current time: {day_name} {window.value} ({now.strftime('%H:%M UTC')})*\n")
        
        # Relevant patterns
        patterns = self.get_relevant_now()
        if patterns:
            lines.append("**Typical at this time:**")
            for p in patterns[:3]:
                lines.append(f"- {p.description} (confidence: {p.confidence:.0%})")
        
        # Today's events
        events_today = self.get_events_today()
        if events_today:
            lines.append(f"\n**Today's activity:** {len(events_today)} events logged")
        
        # Predictions
        predictions = self.predict_upcoming(hours=2)
        if predictions:
            lines.append("\n**Upcoming predictions:**")
            for pred in predictions[:2]:
                lines.append(f"- {pred['pattern']} (expected soon)")
        
        if len(lines) > 2:
            lines.append("\n---\n")
            return "\n".join(lines)
        
        return ""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get temporal memory statistics."""
        with self._get_connection() as conn:
            event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            pattern_count = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]
            
            by_type = dict(conn.execute(
                "SELECT event_type, COUNT(*) FROM events GROUP BY event_type"
            ).fetchall())
            
            by_window = dict(conn.execute(
                "SELECT time_window, COUNT(*) FROM events GROUP BY time_window"
            ).fetchall())
            
            high_confidence = conn.execute(
                "SELECT COUNT(*) FROM patterns WHERE confidence > 0.7"
            ).fetchone()[0]
            
            return {
                "total_events": event_count,
                "total_patterns": pattern_count,
                "events_by_type": by_type,
                "events_by_window": by_window,
                "high_confidence_patterns": high_confidence,
                "db_path": str(TEMPORAL_DB_PATH)
            }
    
    def _row_to_event(self, row: sqlite3.Row) -> TemporalEvent:
        """Convert row to TemporalEvent."""
        return TemporalEvent(
            id=row["id"],
            event_type=EventType(row["event_type"]),
            description=row["description"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            time_window=TimeWindow(row["time_window"]),
            day_of_week=row["day_of_week"],
            metadata=json.loads(row["metadata"])
        )
    
    def _row_to_pattern(self, row: sqlite3.Row) -> TemporalPattern:
        """Convert row to TemporalPattern."""
        return TemporalPattern(
            id=row["id"],
            pattern_type=row["pattern_type"],
            description=row["description"],
            frequency=row["frequency"],
            confidence=row["confidence"],
            occurrences=row["occurrences"],
            last_occurred=datetime.fromisoformat(row["last_occurred"]) if row["last_occurred"] else datetime.now(timezone.utc),
            next_expected=datetime.fromisoformat(row["next_expected"]) if row["next_expected"] else None
        )


# ============================================================================
# SINGLETON
# ============================================================================

_temporal: Optional[TemporalMemory] = None


def get_temporal_memory() -> TemporalMemory:
    """Get or create temporal memory instance."""
    global _temporal
    if _temporal is None:
        _temporal = TemporalMemory()
    return _temporal









