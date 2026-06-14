#!/usr/bin/env python3
"""
ARIA REAL-TIME LEARNER (TIER 1)
================================

Learns from every interaction in real-time with < 100ms latency.

Features:
- Immediate correction detection and application
- Success reinforcement caching
- Real-time metrics updates
- Pattern-based response optimization

This is the first line of learning - happens synchronously with every message.
"""

import os
import json
import sqlite3
import hashlib
import logging
import re
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.evolution.realtime")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")

# Learning signals
CORRECTION_SIGNALS = [
    r'\bno,?\s+i\s+meant\b', r'\bactually\b', r'\bi\s+meant\b',
    r'\bwhat\s+i\s+wanted\b', r'\blet\s+me\s+rephrase\b', r'\bto\s+clarify\b',
    r'\binstead\b', r'\bnot\s+that\b', r'\bthe\s+other\b', r'\bwrong\b',
    r'\bincorrect\b', r'\bthat\'s\s+not\s+(what|right)\b'
]

SUCCESS_SIGNALS = [
    r'\bthanks?\b', r'\bthank\s+you\b', r'\bperfect\b', r'\bgreat\b',
    r'\bexcellent\b', r'\bawesome\b', r'\bnice\b', r'\bgood\s+job\b',
    r'\bworks?\b', r'\blove\s+it\b', r'👍', r'✅', r'🙏', r'💯'
]


@dataclass
class CorrectionPair:
    """A correction learned from user feedback."""
    id: Optional[int] = None
    query_pattern: str = ""  # What the user asked
    wrong_interpretation: str = ""  # What Aria thought they meant
    correct_interpretation: str = ""  # What they actually meant
    occurrence_count: int = 1
    last_seen: datetime = field(default_factory=datetime.now)
    confidence: float = 0.5  # Increases with more occurrences


@dataclass
class SuccessPattern:
    """A successful response pattern to reinforce."""
    id: Optional[int] = None
    query_hash: str = ""
    query_pattern: str = ""
    successful_approach: str = ""  # How we handled it
    response_summary: str = ""
    reinforcement_count: int = 1
    last_used: datetime = field(default_factory=datetime.now)
    avg_response_time_ms: float = 0


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

REALTIME_SCHEMA = """
-- Corrections table: What Aria learned from user corrections
CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_pattern TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    wrong_interpretation TEXT,
    correct_interpretation TEXT NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    last_seen TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    user_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_corr_hash ON corrections(query_hash);
CREATE INDEX IF NOT EXISTS idx_corr_confidence ON corrections(confidence DESC);

-- Success patterns: Approaches that worked well
CREATE TABLE IF NOT EXISTS success_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL,
    query_pattern TEXT NOT NULL,
    successful_approach TEXT NOT NULL,
    response_summary TEXT,
    reinforcement_count INTEGER DEFAULT 1,
    last_used TEXT NOT NULL,
    avg_response_time_ms REAL DEFAULT 0,
    user_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_success_hash ON success_patterns(query_hash);
CREATE INDEX IF NOT EXISTS idx_success_count ON success_patterns(reinforcement_count DESC);

-- Real-time metrics (rolling windows)
CREATE TABLE IF NOT EXISTS realtime_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_type TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    value REAL NOT NULL,
    sample_count INTEGER DEFAULT 1,
    UNIQUE(metric_type, window_start)
);

CREATE INDEX IF NOT EXISTS idx_metrics_type ON realtime_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_time ON realtime_metrics(window_end DESC);

-- Immediate learnings: Quick rules learned from single interactions
CREATE TABLE IF NOT EXISTS immediate_learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learning_type TEXT NOT NULL,
    trigger_pattern TEXT NOT NULL,
    learned_rule TEXT NOT NULL,
    confidence REAL DEFAULT 0.6,
    applied_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_learning_type ON immediate_learnings(learning_type);
CREATE INDEX IF NOT EXISTS idx_learning_confidence ON immediate_learnings(confidence DESC);
"""


# ============================================================================
# REAL-TIME LEARNER
# ============================================================================

class RealtimeLearner:
    """
    Learns from interactions in real-time.
    
    Called synchronously after every Aria response to:
    1. Detect if previous response was corrected
    2. Reinforce successful patterns
    3. Update rolling metrics
    4. Apply immediate learnings
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        
        # In-memory caches for speed
        self._correction_cache: Dict[str, CorrectionPair] = {}
        self._success_cache: Dict[str, SuccessPattern] = {}
        self._last_interaction: Dict[str, Dict] = {}  # Per user
        
        self._load_caches()
    
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
            cursor.executescript(REALTIME_SCHEMA)
        logger.info("Realtime learner initialized")
    
    def _load_caches(self):
        """Load recent corrections and success patterns into memory."""
        try:
            with self._cursor() as cursor:
                # Load top corrections (high confidence)
                cursor.execute("""
                    SELECT * FROM corrections
                    WHERE confidence >= 0.5
                    ORDER BY occurrence_count DESC
                    LIMIT 100
                """)
                for row in cursor.fetchall():
                    self._correction_cache[row["query_hash"]] = CorrectionPair(
                        id=row["id"],
                        query_pattern=row["query_pattern"],
                        wrong_interpretation=row["wrong_interpretation"],
                        correct_interpretation=row["correct_interpretation"],
                        occurrence_count=row["occurrence_count"],
                        confidence=row["confidence"]
                    )
                
                # Load success patterns
                cursor.execute("""
                    SELECT * FROM success_patterns
                    ORDER BY reinforcement_count DESC
                    LIMIT 200
                """)
                for row in cursor.fetchall():
                    self._success_cache[row["query_hash"]] = SuccessPattern(
                        id=row["id"],
                        query_hash=row["query_hash"],
                        query_pattern=row["query_pattern"],
                        successful_approach=row["successful_approach"],
                        response_summary=row["response_summary"],
                        reinforcement_count=row["reinforcement_count"]
                    )
                
                logger.info(f"Loaded {len(self._correction_cache)} corrections, {len(self._success_cache)} success patterns")
                
        except Exception as e:
            logger.warning(f"Cache load error (may be first run): {e}")
    
    def _hash_query(self, query: str) -> str:
        """Generate a hash for query matching."""
        # Normalize: lowercase, remove extra spaces, remove punctuation
        normalized = re.sub(r'[^\w\s]', '', query.lower())
        normalized = ' '.join(normalized.split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    # ========================================================================
    # CORE LEARNING METHODS
    # ========================================================================
    
    def process_interaction(
        self,
        user_id: str,
        user_message: str,
        aria_response: str,
        response_time_ms: float,
        tools_used: List[str] = None,
        success: bool = True
    ) -> Dict[str, Any]:
        """
        Process an interaction for real-time learning.
        
        This should be called after every Aria response.
        Returns insights about what was learned.
        
        Args:
            user_id: The user's ID
            user_message: What the user said
            aria_response: Aria's response
            response_time_ms: How long it took
            tools_used: Which tools were called
            success: Whether the interaction succeeded technically
            
        Returns:
            Dict with learning insights
        """
        insights = {
            "correction_detected": False,
            "correction_applied": None,
            "success_reinforced": False,
            "pattern_matched": None,
            "metrics_updated": []
        }
        
        # Get the previous interaction for this user
        prev = self._last_interaction.get(user_id)
        
        # 1. Check if this message is correcting the previous response
        if prev and self._is_correction(user_message):
            correction = self._learn_correction(
                user_id=user_id,
                original_query=prev["message"],
                wrong_response=prev["response"],
                correction_message=user_message
            )
            insights["correction_detected"] = True
            insights["correction_applied"] = {
                "original": prev["message"][:50],
                "learned": correction.correct_interpretation[:50]
            }
            logger.info(f"Learned correction: {correction.query_pattern[:30]} -> {correction.correct_interpretation[:30]}")
        
        # 2. Check for success signals in this message (about previous response)
        elif prev and self._is_success_signal(user_message):
            pattern = self._reinforce_success(
                user_id=user_id,
                query=prev["message"],
                response=prev["response"],
                response_time_ms=prev.get("time_ms", 0),
                tools_used=prev.get("tools", [])
            )
            insights["success_reinforced"] = True
            insights["pattern_matched"] = pattern.query_pattern[:50] if pattern else None
            logger.info(f"Reinforced success pattern for: {prev['message'][:30]}")
        
        # 3. Check if this query matches a known correction
        query_hash = self._hash_query(user_message)
        if query_hash in self._correction_cache:
            correction = self._correction_cache[query_hash]
            insights["pattern_matched"] = f"CORRECTION: {correction.correct_interpretation}"
        
        # 4. Check if this query matches a success pattern
        elif query_hash in self._success_cache:
            pattern = self._success_cache[query_hash]
            insights["pattern_matched"] = f"SUCCESS: {pattern.successful_approach}"
        
        # 5. Update rolling metrics
        self._update_metrics(response_time_ms, success, tools_used or [])
        insights["metrics_updated"] = ["response_time", "success_rate", "tool_usage"]
        
        # 6. Store this interaction for next comparison
        self._last_interaction[user_id] = {
            "message": user_message,
            "response": aria_response,
            "time_ms": response_time_ms,
            "tools": tools_used or [],
            "timestamp": datetime.now().isoformat()
        }
        
        return insights
    
    def _is_correction(self, message: str) -> bool:
        """Check if a message is correcting the previous response."""
        msg_lower = message.lower()
        for pattern in CORRECTION_SIGNALS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True
        return False
    
    def _is_success_signal(self, message: str) -> bool:
        """Check if a message indicates satisfaction with previous response."""
        msg_lower = message.lower()
        for pattern in SUCCESS_SIGNALS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True
        return False
    
    def _learn_correction(
        self,
        user_id: str,
        original_query: str,
        wrong_response: str,
        correction_message: str
    ) -> CorrectionPair:
        """
        Learn from a correction.
        
        Extracts what the user actually wanted and stores it for future reference.
        """
        query_hash = self._hash_query(original_query)
        
        # Extract the correct interpretation from the correction message
        # Try to find what comes after "I meant", "actually", etc.
        correct_interpretation = correction_message
        for pattern in [r'i meant\s+(.+)', r'actually\s+(.+)', r'what i wanted was\s+(.+)']:
            match = re.search(pattern, correction_message, re.IGNORECASE)
            if match:
                correct_interpretation = match.group(1).strip()
                break
        
        # Extract what we thought they meant (simplified from wrong response)
        wrong_interpretation = ""
        if "trading" in wrong_response.lower() or "position" in wrong_response.lower():
            wrong_interpretation = "trading query"
        elif "server" in wrong_response.lower() or "service" in wrong_response.lower():
            wrong_interpretation = "server query"
        else:
            wrong_interpretation = "unknown"
        
        # Check if we already have this correction
        if query_hash in self._correction_cache:
            existing = self._correction_cache[query_hash]
            existing.occurrence_count += 1
            existing.confidence = min(0.95, existing.confidence + 0.1)
            existing.last_seen = datetime.now()
            
            # Update in DB
            with self._cursor() as cursor:
                cursor.execute("""
                    UPDATE corrections SET
                        occurrence_count = occurrence_count + 1,
                        confidence = MIN(0.95, confidence + 0.1),
                        last_seen = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), existing.id))
            
            return existing
        
        # Create new correction
        correction = CorrectionPair(
            query_pattern=original_query[:500],
            wrong_interpretation=wrong_interpretation,
            correct_interpretation=correct_interpretation[:500],
            occurrence_count=1,
            confidence=0.6,
            last_seen=datetime.now()
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO corrections (
                    query_pattern, query_hash, wrong_interpretation,
                    correct_interpretation, occurrence_count, last_seen,
                    confidence, user_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                correction.query_pattern,
                query_hash,
                correction.wrong_interpretation,
                correction.correct_interpretation,
                1, datetime.now().isoformat(), 0.6,
                user_id, datetime.now().isoformat()
            ))
            correction.id = cursor.lastrowid
        
        # Cache it
        self._correction_cache[query_hash] = correction
        
        return correction
    
    def _reinforce_success(
        self,
        user_id: str,
        query: str,
        response: str,
        response_time_ms: float,
        tools_used: List[str]
    ) -> Optional[SuccessPattern]:
        """
        Reinforce a successful response pattern.
        """
        query_hash = self._hash_query(query)
        
        # Determine the successful approach
        if tools_used:
            approach = f"Used tools: {', '.join(tools_used[:3])}"
        else:
            approach = "Direct response without tools"
        
        # Check if we already have this pattern
        if query_hash in self._success_cache:
            existing = self._success_cache[query_hash]
            existing.reinforcement_count += 1
            existing.last_used = datetime.now()
            existing.avg_response_time_ms = (
                existing.avg_response_time_ms * (existing.reinforcement_count - 1) + response_time_ms
            ) / existing.reinforcement_count
            
            # Update in DB
            with self._cursor() as cursor:
                cursor.execute("""
                    UPDATE success_patterns SET
                        reinforcement_count = reinforcement_count + 1,
                        last_used = ?,
                        avg_response_time_ms = ?
                    WHERE id = ?
                """, (
                    datetime.now().isoformat(),
                    existing.avg_response_time_ms,
                    existing.id
                ))
            
            return existing
        
        # Create new success pattern
        pattern = SuccessPattern(
            query_hash=query_hash,
            query_pattern=query[:500],
            successful_approach=approach,
            response_summary=response[:200],
            reinforcement_count=1,
            last_used=datetime.now(),
            avg_response_time_ms=response_time_ms
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO success_patterns (
                    query_hash, query_pattern, successful_approach,
                    response_summary, reinforcement_count, last_used,
                    avg_response_time_ms, user_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.query_hash,
                pattern.query_pattern,
                pattern.successful_approach,
                pattern.response_summary,
                1, datetime.now().isoformat(),
                response_time_ms, user_id, datetime.now().isoformat()
            ))
            pattern.id = cursor.lastrowid
        
        # Cache it
        self._success_cache[query_hash] = pattern
        
        return pattern
    
    def _update_metrics(
        self,
        response_time_ms: float,
        success: bool,
        tools_used: List[str]
    ):
        """Update rolling window metrics."""
        now = datetime.now()
        window_start = now.replace(minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(hours=1)
        
        metrics = [
            ("response_time", response_time_ms),
            ("success_rate", 1.0 if success else 0.0),
            ("tool_count", len(tools_used))
        ]
        
        with self._cursor() as cursor:
            for metric_type, value in metrics:
                cursor.execute("""
                    INSERT INTO realtime_metrics (metric_type, window_start, window_end, value, sample_count)
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(metric_type, window_start) DO UPDATE SET
                        value = (value * sample_count + excluded.value) / (sample_count + 1),
                        sample_count = sample_count + 1
                """, (
                    metric_type,
                    window_start.isoformat(),
                    window_end.isoformat(),
                    value
                ))
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    def get_correction_for_query(self, query: str) -> Optional[CorrectionPair]:
        """
        Check if we have a learned correction for this query.
        
        Use this before processing to potentially redirect Aria's interpretation.
        """
        query_hash = self._hash_query(query)
        return self._correction_cache.get(query_hash)
    
    def get_success_pattern(self, query: str) -> Optional[SuccessPattern]:
        """
        Get the success pattern for a similar query.
        
        Use this to inform how Aria should approach the query.
        """
        query_hash = self._hash_query(query)
        return self._success_cache.get(query_hash)
    
    def get_recent_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """Get metrics for the recent period."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT metric_type, AVG(value) as avg_value, SUM(sample_count) as total_samples
                FROM realtime_metrics
                WHERE window_start >= ?
                GROUP BY metric_type
            """, (since,))
            
            metrics = {}
            for row in cursor.fetchall():
                metrics[row["metric_type"]] = {
                    "average": row["avg_value"],
                    "samples": row["total_samples"]
                }
            
            return metrics
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of what's been learned."""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM corrections")
            correction_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM success_patterns")
            success_count = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM corrections
                WHERE last_seen >= ?
            """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
            recent_corrections = cursor.fetchone()["count"]
        
        return {
            "total_corrections": correction_count,
            "total_success_patterns": success_count,
            "corrections_last_24h": recent_corrections,
            "cached_corrections": len(self._correction_cache),
            "cached_success_patterns": len(self._success_cache),
            "recent_metrics": self.get_recent_metrics(1)
        }
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_learner: Optional[RealtimeLearner] = None


def get_realtime_learner() -> RealtimeLearner:
    """Get or create global realtime learner."""
    global _learner
    if _learner is None:
        _learner = RealtimeLearner()
    return _learner


def process_interaction(
    user_id: str,
    user_message: str,
    aria_response: str,
    response_time_ms: float = 0,
    tools_used: List[str] = None,
    success: bool = True
) -> Dict[str, Any]:
    """Process an interaction for real-time learning."""
    return get_realtime_learner().process_interaction(
        user_id, user_message, aria_response,
        response_time_ms, tools_used, success
    )


def get_query_insights(query: str) -> Dict[str, Any]:
    """Get any learned insights for a query before processing."""
    learner = get_realtime_learner()
    
    correction = learner.get_correction_for_query(query)
    success_pattern = learner.get_success_pattern(query)
    
    return {
        "has_correction": correction is not None,
        "correction": {
            "correct_interpretation": correction.correct_interpretation,
            "confidence": correction.confidence
        } if correction else None,
        "has_success_pattern": success_pattern is not None,
        "success_pattern": {
            "approach": success_pattern.successful_approach,
            "reinforcement_count": success_pattern.reinforcement_count
        } if success_pattern else None
    }


