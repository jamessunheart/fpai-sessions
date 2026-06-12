"""
ARIA FEEDBACK LOOP
==================

Completes the dimensional cycle:
  Dream → Action → Result → Dream

Returns signal from manifestation back to vision.
Tracks what worked, what didn't, what patterns emerge.
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import sqlite3
from pathlib import Path

from dream_journal import get_dream_journal, Vision, VisionStatus

logger = logging.getLogger("aria.feedback")

# Database for feedback tracking
FEEDBACK_DB = Path("/opt/fpai/aria-bridge/feedback_loop.db")


class FeedbackType(str, Enum):
    """Types of feedback signals."""
    VISION_MATCHED = "vision_matched"       # Result matched the vision
    VISION_PARTIAL = "vision_partial"       # Partially matched
    VISION_MISSED = "vision_missed"         # Didn't match
    UNEXPECTED_GOOD = "unexpected_good"     # Surprise positive
    UNEXPECTED_BAD = "unexpected_bad"       # Surprise negative
    PATTERN_DETECTED = "pattern_detected"   # New pattern seen
    LEARNING = "learning"                   # Something learned


@dataclass
class FeedbackEntry:
    """A feedback entry in the loop."""
    id: str
    timestamp: str
    
    # What was attempted
    vision_id: Optional[str]
    action_taken: str
    
    # What happened
    result: str
    feedback_type: FeedbackType
    
    # Analysis
    matched_vision: bool
    deviation: Optional[str]  # How it differed from vision
    pattern: Optional[str]    # Pattern observed
    learning: Optional[str]   # What was learned
    
    # Next iteration
    next_action: Optional[str]
    refinement: Optional[str]
    
    # Metadata
    dimension_from: str
    dimension_to: str


@dataclass
class PatternInsight:
    """A pattern detected across feedback cycles."""
    id: str
    description: str
    first_seen: str
    occurrences: int
    confidence: float  # 0-1
    action_suggested: Optional[str]
    vision_ids: List[str]


class FeedbackLoop:
    """
    The feedback system that completes the dimensional cycle.
    
    Dream → Action → Result → Dream
    
    Tracks:
    - What visions led to what actions
    - What actions produced what results
    - How results compared to visions
    - What patterns are emerging
    - What refinements are needed
    """
    
    def __init__(self, db_path: Path = FEEDBACK_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.journal = get_dream_journal()
        self._init_db()
        logger.info(f"FeedbackLoop initialized: {self.db_path}")
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Feedback entries
        c.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                vision_id TEXT,
                action_taken TEXT NOT NULL,
                result TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                matched_vision INTEGER,
                deviation TEXT,
                pattern TEXT,
                learning TEXT,
                next_action TEXT,
                refinement TEXT,
                dimension_from TEXT,
                dimension_to TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Patterns detected
        c.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                occurrences INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                action_suggested TEXT,
                vision_ids TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Vision-action-result chains
        c.execute("""
            CREATE TABLE IF NOT EXISTS chains (
                id TEXT PRIMARY KEY,
                vision_id TEXT,
                action_ids TEXT NOT NULL,
                result_ids TEXT NOT NULL,
                cycle_complete INTEGER DEFAULT 0,
                outcome TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_vision ON feedback(vision_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_date ON feedback(timestamp)")
        
        conn.commit()
        conn.close()
    
    # ==================== RECORDING FEEDBACK ====================
    
    def record_feedback(
        self,
        action_taken: str,
        result: str,
        vision_id: Optional[str] = None,
        matched_vision: bool = False,
        deviation: Optional[str] = None,
        pattern: Optional[str] = None,
        learning: Optional[str] = None,
        next_action: Optional[str] = None,
        dimension_from: str = "digital",
        dimension_to: str = "dream_astral"
    ) -> FeedbackEntry:
        """
        Record feedback from a manifestation.
        
        This completes one cycle: Dream → Action → Result → Dream
        """
        feedback_id = f"feedback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        now = datetime.utcnow().isoformat()
        
        # Determine feedback type
        if matched_vision:
            feedback_type = FeedbackType.VISION_MATCHED
        elif deviation and "partial" in deviation.lower():
            feedback_type = FeedbackType.VISION_PARTIAL
        elif pattern:
            feedback_type = FeedbackType.PATTERN_DETECTED
        elif learning:
            feedback_type = FeedbackType.LEARNING
        else:
            feedback_type = FeedbackType.VISION_MISSED
        
        entry = FeedbackEntry(
            id=feedback_id,
            timestamp=now,
            vision_id=vision_id,
            action_taken=action_taken,
            result=result,
            feedback_type=feedback_type,
            matched_vision=matched_vision,
            deviation=deviation,
            pattern=pattern,
            learning=learning,
            next_action=next_action,
            refinement=deviation if not matched_vision else None,
            dimension_from=dimension_from,
            dimension_to=dimension_to
        )
        
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO feedback 
            (id, timestamp, vision_id, action_taken, result, feedback_type,
             matched_vision, deviation, pattern, learning, next_action, 
             refinement, dimension_from, dimension_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id, entry.timestamp, entry.vision_id, entry.action_taken,
            entry.result, entry.feedback_type.value, int(entry.matched_vision),
            entry.deviation, entry.pattern, entry.learning, entry.next_action,
            entry.refinement, entry.dimension_from, entry.dimension_to
        ))
        
        conn.commit()
        conn.close()
        
        # Update the vision in the journal if linked
        if vision_id:
            self.journal.record_feedback(
                vision_id=vision_id,
                matched_vision=matched_vision,
                feedback=f"{result}\n\nLearning: {learning}" if learning else result,
                from_dimension=dimension_from
            )
        
        # Check for patterns
        if pattern:
            self._update_pattern(pattern, vision_id)
        
        emoji = "✅" if matched_vision else "🔄"
        logger.info(f"{emoji} Feedback recorded: {feedback_id}")
        
        return entry
    
    def _update_pattern(self, pattern_description: str, vision_id: Optional[str] = None):
        """Update or create a pattern entry."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Look for similar pattern
        c.execute("""
            SELECT * FROM patterns WHERE description LIKE ?
        """, (f"%{pattern_description[:50]}%",))
        
        existing = c.fetchone()
        
        if existing:
            # Update existing
            vision_ids = json.loads(existing["vision_ids"]) if existing["vision_ids"] else []
            if vision_id and vision_id not in vision_ids:
                vision_ids.append(vision_id)
            
            new_occurrences = existing["occurrences"] + 1
            new_confidence = min(0.95, existing["confidence"] + 0.1)
            
            c.execute("""
                UPDATE patterns 
                SET occurrences = ?, confidence = ?, vision_ids = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (new_occurrences, new_confidence, json.dumps(vision_ids), existing["id"]))
        else:
            # Create new
            pattern_id = f"pattern_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            vision_ids = [vision_id] if vision_id else []
            
            c.execute("""
                INSERT INTO patterns (id, description, first_seen, occurrences, confidence, vision_ids)
                VALUES (?, ?, datetime('now'), 1, 0.3, ?)
            """, (pattern_id, pattern_description, json.dumps(vision_ids)))
        
        conn.commit()
        conn.close()
    
    # ==================== QUERYING ====================
    
    def get_recent_feedback(self, days: int = 7, limit: int = 20) -> List[FeedbackEntry]:
        """Get recent feedback entries."""
        conn = self._get_conn()
        c = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        c.execute("""
            SELECT * FROM feedback 
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (cutoff, limit))
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_feedback(row) for row in rows]
    
    def get_feedback_for_vision(self, vision_id: str) -> List[FeedbackEntry]:
        """Get all feedback linked to a vision."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT * FROM feedback WHERE vision_id = ? ORDER BY timestamp DESC
        """, (vision_id,))
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_feedback(row) for row in rows]
    
    def get_patterns(self, min_confidence: float = 0.5) -> List[PatternInsight]:
        """Get detected patterns above confidence threshold."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT * FROM patterns 
            WHERE confidence >= ?
            ORDER BY confidence DESC, occurrences DESC
        """, (min_confidence,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            PatternInsight(
                id=row["id"],
                description=row["description"],
                first_seen=row["first_seen"],
                occurrences=row["occurrences"],
                confidence=row["confidence"],
                action_suggested=row["action_suggested"],
                vision_ids=json.loads(row["vision_ids"]) if row["vision_ids"] else []
            )
            for row in rows
        ]
    
    def _row_to_feedback(self, row) -> FeedbackEntry:
        """Convert row to FeedbackEntry."""
        return FeedbackEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            vision_id=row["vision_id"],
            action_taken=row["action_taken"],
            result=row["result"],
            feedback_type=FeedbackType(row["feedback_type"]),
            matched_vision=bool(row["matched_vision"]),
            deviation=row["deviation"],
            pattern=row["pattern"],
            learning=row["learning"],
            next_action=row["next_action"],
            refinement=row["refinement"],
            dimension_from=row["dimension_from"],
            dimension_to=row["dimension_to"]
        )
    
    # ==================== ANALYSIS ====================
    
    def get_match_rate(self, days: int = 30) -> Dict:
        """Get vision match rate over time."""
        conn = self._get_conn()
        c = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        c.execute("""
            SELECT 
                SUM(CASE WHEN matched_vision = 1 THEN 1 ELSE 0 END) as matched,
                SUM(CASE WHEN matched_vision = 0 THEN 1 ELSE 0 END) as missed,
                COUNT(*) as total
            FROM feedback 
            WHERE timestamp > ?
        """, (cutoff,))
        
        row = c.fetchone()
        conn.close()
        
        total = row["total"] or 1
        return {
            "matched": row["matched"] or 0,
            "missed": row["missed"] or 0,
            "total": total,
            "match_rate": (row["matched"] or 0) / total,
            "days": days
        }
    
    def get_learnings(self, limit: int = 10) -> List[str]:
        """Get recent learnings."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT learning FROM feedback 
            WHERE learning IS NOT NULL AND learning != ''
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [row["learning"] for row in rows]
    
    def get_summary(self) -> Dict:
        """Get feedback loop summary."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Count by type
        c.execute("""
            SELECT feedback_type, COUNT(*) as count 
            FROM feedback 
            GROUP BY feedback_type
        """)
        by_type = {row["feedback_type"]: row["count"] for row in c.fetchall()}
        
        # Recent match rate
        match_rate = self.get_match_rate(7)
        
        # Pattern count
        c.execute("SELECT COUNT(*) as count FROM patterns WHERE confidence >= 0.5")
        patterns_count = c.fetchone()["count"]
        
        # Recent learnings
        learnings = self.get_learnings(5)
        
        conn.close()
        
        return {
            "total_feedback": sum(by_type.values()),
            "by_type": by_type,
            "match_rate_7d": match_rate["match_rate"],
            "patterns_detected": patterns_count,
            "recent_learnings": learnings
        }
    
    # ==================== FORMATTING ====================
    
    def format_feedback_summary(self) -> str:
        """Format feedback summary for display."""
        summary = self.get_summary()
        patterns = self.get_patterns(min_confidence=0.5)
        
        lines = ["**🔄 Feedback Loop Summary**\n"]
        
        # Match rate
        match_pct = summary["match_rate_7d"] * 100
        lines.append(f"**Vision Match Rate (7d):** {match_pct:.0f}%")
        lines.append(f"**Total Cycles:** {summary['total_feedback']}")
        lines.append(f"**Patterns Detected:** {summary['patterns_detected']}")
        
        # Patterns
        if patterns:
            lines.append("\n**🌀 Emerging Patterns:**")
            for p in patterns[:3]:
                lines.append(f"• {p.description[:60]}... ({p.confidence:.0%})")
        
        # Learnings
        if summary["recent_learnings"]:
            lines.append("\n**📚 Recent Learnings:**")
            for learning in summary["recent_learnings"][:3]:
                lines.append(f"• {learning[:80]}...")
        
        return "\n".join(lines)


# Singleton
_loop: Optional[FeedbackLoop] = None


def get_feedback_loop() -> FeedbackLoop:
    """Get or create feedback loop instance."""
    global _loop
    if _loop is None:
        _loop = FeedbackLoop()
    return _loop


