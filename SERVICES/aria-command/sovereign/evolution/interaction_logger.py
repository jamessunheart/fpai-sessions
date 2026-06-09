#!/usr/bin/env python3
"""
ARIA INTERACTION LOGGER
========================

Comprehensive logging of all Aria interactions with rich metadata
for evolution analysis.

Features:
- Full interaction capture (message, response, tools, timing)
- User satisfaction signals (implicit and explicit)
- Session continuity tracking
- Intent classification
- Correction detection
"""

import os
import json
import sqlite3
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import contextmanager
import threading
import hashlib

logger = logging.getLogger("aria.evolution.interaction")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")

class SatisfactionSignal(str, Enum):
    """Detected user satisfaction level."""
    POSITIVE = "positive"       # Thanks, great, perfect
    NEUTRAL = "neutral"         # No clear signal
    NEGATIVE = "negative"       # No, wrong, incorrect
    CORRECTION = "correction"   # "I meant...", "actually..."
    ABANDONMENT = "abandonment" # User stopped responding
    RETRY = "retry"             # User repeated similar request


class IntentCategory(str, Enum):
    """High-level intent classification."""
    QUESTION = "question"           # Information seeking
    COMMAND = "command"             # Execute action
    CONVERSATION = "conversation"   # General chat
    FEEDBACK = "feedback"           # About Aria herself
    TRADING = "trading"             # Trading related
    SERVER = "server"               # Server/infrastructure
    BUILD = "build"                 # Code/development
    UNKNOWN = "unknown"


@dataclass
class Interaction:
    """A complete interaction record."""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # User context
    user_id: str = ""
    session_id: str = ""
    message_id: Optional[str] = None
    
    # Input
    user_message: str = ""
    message_length: int = 0
    intent: IntentCategory = IntentCategory.UNKNOWN
    
    # Processing
    model_used: str = ""
    tools_called: List[str] = field(default_factory=list)
    tool_count: int = 0
    thinking_time_ms: float = 0
    
    # Output
    response: str = ""
    response_length: int = 0
    total_time_ms: float = 0
    
    # Quality signals
    success: bool = True
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    
    # Satisfaction (detected later)
    satisfaction: SatisfactionSignal = SatisfactionSignal.NEUTRAL
    was_correction: bool = False
    follow_up_count: int = 0
    
    # Costs
    tokens_used: int = 0
    cost_usd: float = 0.0


# ============================================================================
# DATABASE SCHEMA EXTENSION
# ============================================================================

INTERACTION_SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT,
    message_id TEXT,
    user_message TEXT,
    message_length INTEGER,
    intent TEXT,
    model_used TEXT,
    tools_called TEXT,
    tool_count INTEGER,
    thinking_time_ms REAL,
    response TEXT,
    response_length INTEGER,
    total_time_ms REAL,
    success INTEGER DEFAULT 1,
    error_type TEXT,
    error_message TEXT,
    satisfaction TEXT DEFAULT 'neutral',
    was_correction INTEGER DEFAULT 0,
    follow_up_count INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    message_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_int_timestamp ON interactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_int_user ON interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_int_session ON interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_int_intent ON interactions(intent);
CREATE INDEX IF NOT EXISTS idx_int_satisfaction ON interactions(satisfaction);
CREATE INDEX IF NOT EXISTS idx_int_success ON interactions(success);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    last_activity TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    avg_satisfaction REAL DEFAULT 0.5,
    topics TEXT
);

CREATE INDEX IF NOT EXISTS idx_sess_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sess_last ON sessions(last_activity);

CREATE TABLE IF NOT EXISTS user_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    pattern_data TEXT,
    occurrence_count INTEGER DEFAULT 1,
    last_seen TEXT,
    learned_preference TEXT,
    UNIQUE(user_id, pattern_type)
);

CREATE INDEX IF NOT EXISTS idx_pattern_user ON user_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_type ON user_patterns(pattern_type);
"""


# ============================================================================
# SATISFACTION DETECTION
# ============================================================================

POSITIVE_SIGNALS = [
    r'\bthanks?\b', r'\bthank you\b', r'\bperfect\b', r'\bgreat\b',
    r'\bexcellent\b', r'\bawesome\b', r'\bnice\b', r'\bgood\b',
    r'\blove it\b', r'\bworks?\b', r'👍', r'✅', r'🙏'
]

NEGATIVE_SIGNALS = [
    r'\bno\b', r'\bwrong\b', r'\bincorrect\b', r'\bthat\'s not\b',
    r'\bdoesn\'t work\b', r'\bnot what\b', r'\bbroke\b', r'\bfailed\b',
    r'\bstill not\b', r'👎', r'❌'
]

CORRECTION_SIGNALS = [
    r'\bi meant\b', r'\bactually\b', r'\bno,?\s+i\b', r'\bwhat i wanted\b',
    r'\blet me rephrase\b', r'\bto clarify\b', r'\binstead\b',
    r'\bnot that\b', r'\bthe other\b'
]


def detect_satisfaction(
    user_message: str,
    prev_response: Optional[str] = None,
    time_since_last: Optional[float] = None
) -> Tuple[SatisfactionSignal, bool]:
    """
    Detect user satisfaction from their message.
    
    Returns:
        Tuple of (satisfaction_signal, is_correction)
    """
    msg_lower = user_message.lower()
    
    # Check for correction signals first
    for pattern in CORRECTION_SIGNALS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return SatisfactionSignal.CORRECTION, True
    
    # Check positive signals
    for pattern in POSITIVE_SIGNALS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return SatisfactionSignal.POSITIVE, False
    
    # Check negative signals
    for pattern in NEGATIVE_SIGNALS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return SatisfactionSignal.NEGATIVE, False
    
    # Check for abandonment (if too long since last message)
    if time_since_last and time_since_last > 3600:  # 1 hour
        return SatisfactionSignal.ABANDONMENT, False
    
    return SatisfactionSignal.NEUTRAL, False


def classify_intent(message: str) -> IntentCategory:
    """Classify the user's intent from their message."""
    msg_lower = message.lower()
    
    # Check for questions
    if any(q in msg_lower for q in ['?', 'what', 'how', 'why', 'when', 'where', 'who']):
        # But check for specific domains first
        if any(t in msg_lower for t in ['trade', 'position', 'signal', 'btc', 'eth', 'sol']):
            return IntentCategory.TRADING
        if any(s in msg_lower for s in ['server', 'service', 'memory', 'cpu', 'restart']):
            return IntentCategory.SERVER
        if any(b in msg_lower for b in ['build', 'code', 'file', 'function', 'implement']):
            return IntentCategory.BUILD
        return IntentCategory.QUESTION
    
    # Check for commands (slash commands)
    if message.startswith('/'):
        return IntentCategory.COMMAND
    
    # Check for feedback about Aria
    if any(a in msg_lower for a in ['aria', 'yourself', 'your code', 'improve']):
        return IntentCategory.FEEDBACK
    
    # Domain-specific
    if any(t in msg_lower for t in ['trade', 'buy', 'sell', 'long', 'short', 'position']):
        return IntentCategory.TRADING
    
    if any(s in msg_lower for s in ['restart', 'deploy', 'server', 'docker', 'service']):
        return IntentCategory.SERVER
    
    if any(b in msg_lower for b in ['create', 'edit', 'delete', 'file', 'build', 'implement']):
        return IntentCategory.BUILD
    
    return IntentCategory.CONVERSATION


# ============================================================================
# INTERACTION LOGGER
# ============================================================================

class InteractionLogger:
    """
    Comprehensive interaction logging for evolution learning.
    
    Tracks:
    - All messages and responses
    - Timing and performance
    - User satisfaction signals
    - Session continuity
    - Usage patterns
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
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
            cursor.executescript(INTERACTION_SCHEMA)
        logger.info(f"Interaction logger initialized: {self.db_path}")
    
    def _get_message_hash(self, message: str) -> str:
        """Generate hash for deduplication."""
        return hashlib.md5(message.encode()).hexdigest()[:16]
    
    def log_interaction(
        self,
        user_id: str,
        user_message: str,
        response: str,
        model_used: str = "unknown",
        tools_called: List[str] = None,
        thinking_time_ms: float = 0,
        total_time_ms: float = 0,
        success: bool = True,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        session_id: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> int:
        """
        Log a complete interaction.
        
        Returns:
            The interaction ID.
        """
        tools = tools_called or []
        intent = classify_intent(user_message)
        
        # Get previous interaction for satisfaction detection
        prev = self._get_last_interaction(user_id)
        prev_response = prev["response"] if prev else None
        time_since = None
        if prev:
            prev_time = datetime.fromisoformat(prev["timestamp"])
            time_since = (datetime.now() - prev_time).total_seconds()
        
        satisfaction, was_correction = detect_satisfaction(
            user_message, prev_response, time_since
        )
        
        # If this is a correction, update the previous interaction
        if was_correction and prev:
            self._mark_as_corrected(prev["id"])
        
        # Generate session ID if not provided
        if not session_id:
            session_id = self._get_or_create_session(user_id)
        
        # Log the interaction
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO interactions (
                    timestamp, user_id, session_id, message_id,
                    user_message, message_length, intent,
                    model_used, tools_called, tool_count, thinking_time_ms,
                    response, response_length, total_time_ms,
                    success, error_type, error_message,
                    satisfaction, was_correction,
                    tokens_used, cost_usd, message_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                user_id,
                session_id,
                message_id,
                user_message[:5000],  # Truncate
                len(user_message),
                intent.value,
                model_used,
                json.dumps(tools),
                len(tools),
                thinking_time_ms,
                response[:10000],  # Truncate
                len(response),
                total_time_ms,
                1 if success else 0,
                error_type,
                error_message,
                satisfaction.value,
                1 if was_correction else 0,
                tokens_used,
                cost_usd,
                self._get_message_hash(user_message)
            ))
            interaction_id = cursor.lastrowid
        
        # Update session
        self._update_session(session_id, success)
        
        # Learn patterns
        self._learn_pattern(user_id, intent, user_message, tools)
        
        return interaction_id
    
    def _get_last_interaction(self, user_id: str) -> Optional[Dict]:
        """Get the most recent interaction for a user."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM interactions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def _mark_as_corrected(self, interaction_id: int):
        """Mark an interaction as having been corrected."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE interactions
                SET satisfaction = 'correction', was_correction = 1
                WHERE id = ?
            """, (interaction_id,))
    
    def _get_or_create_session(self, user_id: str) -> str:
        """Get current session or create new one."""
        # Session expires after 2 hours of inactivity
        cutoff = (datetime.now() - timedelta(hours=2)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE user_id = ? AND last_activity >= ?
                ORDER BY last_activity DESC
                LIMIT 1
            """, (user_id, cutoff))
            
            row = cursor.fetchone()
            if row:
                return row["session_id"]
            
            # Create new session
            session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            cursor.execute("""
                INSERT INTO sessions (session_id, user_id, started_at, last_activity)
                VALUES (?, ?, ?, ?)
            """, (session_id, user_id, datetime.now().isoformat(), datetime.now().isoformat()))
            
            return session_id
    
    def _update_session(self, session_id: str, success: bool):
        """Update session statistics."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE sessions
                SET 
                    last_activity = ?,
                    message_count = message_count + 1,
                    success_rate = (success_rate * message_count + ?) / (message_count + 1)
                WHERE session_id = ?
            """, (
                datetime.now().isoformat(),
                1.0 if success else 0.0,
                session_id
            ))
    
    def _learn_pattern(
        self,
        user_id: str,
        intent: IntentCategory,
        message: str,
        tools: List[str]
    ):
        """Learn user patterns for proactive suggestions."""
        # Extract hour of day
        hour = datetime.now().hour
        
        patterns_to_record = [
            (f"intent_{intent.value}", json.dumps({"intent": intent.value})),
            (f"hour_{hour}", json.dumps({"hour": hour})),
        ]
        
        # Record tool preferences
        for tool in tools:
            patterns_to_record.append(
                (f"tool_{tool}", json.dumps({"tool": tool}))
            )
        
        with self._cursor() as cursor:
            for pattern_type, pattern_data in patterns_to_record:
                cursor.execute("""
                    INSERT INTO user_patterns (user_id, pattern_type, pattern_data, last_seen)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, pattern_type) DO UPDATE SET
                        occurrence_count = occurrence_count + 1,
                        last_seen = excluded.last_seen
                """, (user_id, pattern_type, pattern_data, datetime.now().isoformat()))
    
    # ========================================================================
    # QUERY METHODS FOR EVOLUTION
    # ========================================================================
    
    def get_recent_interactions(
        self,
        hours: int = 24,
        user_id: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict]:
        """Get recent interactions for analysis."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        query = "SELECT * FROM interactions WHERE timestamp >= ?"
        params = [since]
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self._cursor() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_corrections(self, hours: int = 24) -> List[Dict]:
        """Get interactions that were corrections (user had to clarify)."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM interactions
                WHERE timestamp >= ? AND (
                    satisfaction = 'correction' OR was_correction = 1
                )
                ORDER BY timestamp DESC
            """, (since,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_failed_interactions(self, hours: int = 24) -> List[Dict]:
        """Get interactions that failed or had errors."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM interactions
                WHERE timestamp >= ? AND (
                    success = 0 OR satisfaction IN ('negative', 'correction')
                )
                ORDER BY timestamp DESC
            """, (since,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_successful_interactions(self, hours: int = 24) -> List[Dict]:
        """Get interactions that were successful."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM interactions
                WHERE timestamp >= ? AND success = 1 AND satisfaction IN ('positive', 'neutral')
                ORDER BY timestamp DESC
            """, (since,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_intent_distribution(self, hours: int = 24) -> Dict[str, int]:
        """Get distribution of intents."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT intent, COUNT(*) as count
                FROM interactions
                WHERE timestamp >= ?
                GROUP BY intent
                ORDER BY count DESC
            """, (since,))
            return {row["intent"]: row["count"] for row in cursor.fetchall()}
    
    def get_satisfaction_distribution(self, hours: int = 24) -> Dict[str, int]:
        """Get distribution of satisfaction signals."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT satisfaction, COUNT(*) as count
                FROM interactions
                WHERE timestamp >= ?
                GROUP BY satisfaction
                ORDER BY count DESC
            """, (since,))
            return {row["satisfaction"]: row["count"] for row in cursor.fetchall()}
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for evolution analysis."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                    AVG(total_time_ms) as avg_response_time,
                    AVG(tokens_used) as avg_tokens,
                    SUM(cost_usd) as total_cost
                FROM interactions
                WHERE timestamp >= ?
            """, (since,))
            overall = dict(cursor.fetchone())
            
            # Satisfaction breakdown
            cursor.execute("""
                SELECT satisfaction, COUNT(*) as count
                FROM interactions
                WHERE timestamp >= ?
                GROUP BY satisfaction
            """, (since,))
            satisfaction = {row["satisfaction"]: row["count"] for row in cursor.fetchall()}
            
            # Intent breakdown
            cursor.execute("""
                SELECT intent, 
                       COUNT(*) as count,
                       AVG(total_time_ms) as avg_time
                FROM interactions
                WHERE timestamp >= ?
                GROUP BY intent
            """, (since,))
            intents = {row["intent"]: {
                "count": row["count"],
                "avg_time": row["avg_time"]
            } for row in cursor.fetchall()}
            
            # Correction rate
            correction_rate = (
                satisfaction.get("correction", 0) / overall["total"] * 100
                if overall["total"] > 0 else 0
            )
            
            # Success rate
            success_rate = (
                overall["successes"] / overall["total"] * 100
                if overall["total"] > 0 else 0
            )
        
        return {
            "period_hours": hours,
            "total_interactions": overall["total"],
            "success_rate": success_rate,
            "correction_rate": correction_rate,
            "avg_response_time_ms": overall["avg_response_time"],
            "avg_tokens": overall["avg_tokens"],
            "total_cost_usd": overall["total_cost"] or 0,
            "satisfaction_distribution": satisfaction,
            "intent_breakdown": intents
        }
    
    def get_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Get learned patterns for a user."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT pattern_type, pattern_data, occurrence_count, last_seen
                FROM user_patterns
                WHERE user_id = ?
                ORDER BY occurrence_count DESC
            """, (user_id,))
            
            patterns = {}
            for row in cursor.fetchall():
                patterns[row["pattern_type"]] = {
                    "data": json.loads(row["pattern_data"]),
                    "count": row["occurrence_count"],
                    "last_seen": row["last_seen"]
                }
            
            return patterns
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_logger: Optional[InteractionLogger] = None


def get_interaction_logger() -> InteractionLogger:
    """Get or create global interaction logger."""
    global _logger
    if _logger is None:
        _logger = InteractionLogger()
    return _logger


def log_interaction(
    user_id: str,
    user_message: str,
    response: str,
    **kwargs
) -> int:
    """Log an interaction."""
    return get_interaction_logger().log_interaction(
        user_id, user_message, response, **kwargs
    )


def get_evolution_data(hours: int = 24) -> Dict[str, Any]:
    """Get data for evolution analysis."""
    il = get_interaction_logger()
    return {
        "summary": il.get_performance_summary(hours),
        "corrections": il.get_corrections(hours),
        "failures": il.get_failed_interactions(hours),
        "successes": il.get_successful_interactions(hours)[:50],  # Sample
        "intents": il.get_intent_distribution(hours),
        "satisfaction": il.get_satisfaction_distribution(hours)
    }


# ============================================================================
# MEM0 CLOUD SYNC
# ============================================================================

async def sync_learning_to_mem0(
    action: str,
    outcome: str,
    insight: str
) -> bool:
    """
    Sync a learning to Mem0 cloud for persistent memory.
    
    This is called when Aria learns something important that should
    persist across sessions and be recallable later.
    """
    try:
        from memory.mem0_sync import get_mem0_sync
        
        sync = get_mem0_sync()
        if not sync.enabled:
            return False
        
        return await sync.sync_learning(action, outcome, insight)
    except Exception as e:
        logger.error(f"Failed to sync learning to Mem0: {e}")
        return False


async def search_mem0_context(query: str, limit: int = 5) -> list:
    """
    Search Mem0 for relevant context/memories.
    
    Use this before responding to enrich Aria's context with past learnings.
    """
    try:
        from memory.mem0_sync import get_mem0_sync
        
        sync = get_mem0_sync()
        if not sync.enabled:
            return []
        
        return await sync.search_cloud(query, limit=limit)
    except Exception as e:
        logger.error(f"Failed to search Mem0: {e}")
        return []


async def get_mem0_status() -> dict:
    """Get Mem0 sync status."""
    try:
        from memory.mem0_sync import get_mem0_sync
        return await get_mem0_sync().get_status()
    except Exception as e:
        return {"enabled": False, "error": str(e)}

