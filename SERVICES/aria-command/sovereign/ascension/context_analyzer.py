#!/usr/bin/env python3
"""
ARIA ASCENSION - CONTEXT ANALYZER
=================================

Analyze context and emotional state:
- Message brevity → urgency level
- Time of day → attention level
- Repeated queries → dissatisfaction signal
- Emoji/punctuation → emotional state

Enables emotionally intelligent responses.
"""

import os
import json
import re
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.ascension.context")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")


class EmotionalState(str, Enum):
    """Detected emotional state."""
    CALM = "calm"
    FOCUSED = "focused"
    HURRIED = "hurried"
    FRUSTRATED = "frustrated"
    EXCITED = "excited"
    TIRED = "tired"
    CURIOUS = "curious"


class AttentionLevel(str, Enum):
    """User's likely attention level."""
    HIGH = "high"        # Fully engaged, wants detail
    MEDIUM = "medium"    # Normal, balanced responses
    LOW = "low"          # Distracted, wants quick answers
    MINIMAL = "minimal"  # Very limited, ultra-brief only


@dataclass
class ContextAnalysis:
    """Complete context analysis for current interaction."""
    # Emotional state
    emotional_state: EmotionalState
    emotional_confidence: float
    
    # Attention
    attention_level: AttentionLevel
    
    # Urgency
    urgency_score: float  # 0-1
    
    # Dissatisfaction
    dissatisfaction_score: float  # 0-1, based on repeated queries
    
    # Recommended response style
    recommended_verbosity: str  # minimal, brief, normal, detailed
    recommended_tone: str  # casual, professional, urgent, supportive
    
    # Context hints
    recent_topics: List[str] = field(default_factory=list)
    repeated_queries: int = 0
    time_context: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "emotional_state": self.emotional_state.value,
            "emotional_confidence": self.emotional_confidence,
            "attention_level": self.attention_level.value,
            "urgency_score": self.urgency_score,
            "dissatisfaction_score": self.dissatisfaction_score,
            "recommended_verbosity": self.recommended_verbosity,
            "recommended_tone": self.recommended_tone,
            "recent_topics": self.recent_topics,
            "repeated_queries": self.repeated_queries,
            "time_context": self.time_context
        }


CONTEXT_SCHEMA = """
CREATE TABLE IF NOT EXISTS context_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    message_hash TEXT,
    emotional_state TEXT,
    attention_level TEXT,
    urgency_score REAL,
    analysis TEXT
);

CREATE TABLE IF NOT EXISTS query_repetitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_pattern TEXT NOT NULL,
    first_seen TEXT,
    last_seen TEXT,
    repetition_count INTEGER DEFAULT 1,
    UNIQUE(query_pattern)
);

CREATE INDEX IF NOT EXISTS idx_ch_timestamp ON context_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_qr_pattern ON query_repetitions(query_pattern);
"""


# ============================================================================
# CONTEXT ANALYZER
# ============================================================================

class ContextAnalyzer:
    """
    Analyzes user context for emotionally intelligent responses.
    """
    
    # Emotional indicators
    FRUSTRATED_INDICATORS = [
        r'(?:\?\s*){3,}',        # ??? 
        r'(?:!\s*){3,}',         # !!!
        r'\b(again|still|yet|wtf|ugh|sigh)\b',
        r'\b(not working|broken|fail|wrong)\b',
        r'^no[,.]?\s*$',         # Just "no"
    ]
    
    EXCITED_INDICATORS = [
        r'(?:!\s*){2,}',
        r'\b(wow|awesome|amazing|great|love|perfect)\b',
        r'🎉|🚀|💪|🔥',
    ]
    
    HURRIED_INDICATORS = [
        r'^[\?\w]{1,3}$',        # Very short messages
        r'\b(quick|fast|asap|now|hurry)\b',
        r'\b(brb|gtg)\b',
    ]
    
    TIRED_INDICATORS = [
        r'\b(tired|sleepy|exhausted|late)\b',
        r'😴|🥱',
    ]
    
    CURIOUS_INDICATORS = [
        r'^(what|how|why|when|where|who|can you|could you)\b',
        r'\b(curious|wonder|interesting|explain)\b',
        r'🤔|💭',
    ]
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._recent_messages: List[str] = []  # Last N messages for repetition detection
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
            cursor.executescript(CONTEXT_SCHEMA)
        
        logger.info(f"Context analyzer initialized: {self.db_path}")
    
    # ========================================================================
    # ANALYSIS
    # ========================================================================
    
    def analyze(
        self,
        message: str,
        timestamp: datetime = None,
        recent_messages: List[str] = None
    ) -> ContextAnalysis:
        """
        Perform complete context analysis on a message.
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Update recent messages
        if recent_messages:
            self._recent_messages = recent_messages[-10:]
        else:
            self._recent_messages.append(message)
            self._recent_messages = self._recent_messages[-10:]
        
        # Detect emotional state
        emotional_state, confidence = self._detect_emotional_state(message)
        
        # Determine attention level
        attention_level = self._determine_attention_level(message, timestamp)
        
        # Calculate urgency
        urgency = self._calculate_urgency(message, timestamp)
        
        # Check for dissatisfaction (repeated queries)
        dissatisfaction, repetitions = self._check_dissatisfaction(message)
        
        # Determine response style
        verbosity = self._recommend_verbosity(
            emotional_state, attention_level, urgency, len(message)
        )
        tone = self._recommend_tone(emotional_state, urgency)
        
        # Get time context
        time_context = self._get_time_context(timestamp)
        
        # Get recent topics
        recent_topics = self._extract_recent_topics()
        
        analysis = ContextAnalysis(
            emotional_state=emotional_state,
            emotional_confidence=confidence,
            attention_level=attention_level,
            urgency_score=urgency,
            dissatisfaction_score=dissatisfaction,
            recommended_verbosity=verbosity,
            recommended_tone=tone,
            recent_topics=recent_topics,
            repeated_queries=repetitions,
            time_context=time_context
        )
        
        # Store analysis
        self._store_analysis(message, analysis)
        
        return analysis
    
    def _detect_emotional_state(self, message: str) -> tuple[EmotionalState, float]:
        """Detect emotional state from message."""
        msg_lower = message.lower()
        
        scores = {
            EmotionalState.FRUSTRATED: 0,
            EmotionalState.EXCITED: 0,
            EmotionalState.HURRIED: 0,
            EmotionalState.TIRED: 0,
            EmotionalState.CURIOUS: 0,
        }
        
        # Check indicators
        for pattern in self.FRUSTRATED_INDICATORS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                scores[EmotionalState.FRUSTRATED] += 1
        
        for pattern in self.EXCITED_INDICATORS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                scores[EmotionalState.EXCITED] += 1
        
        for pattern in self.HURRIED_INDICATORS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                scores[EmotionalState.HURRIED] += 1
        
        for pattern in self.TIRED_INDICATORS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                scores[EmotionalState.TIRED] += 1
        
        for pattern in self.CURIOUS_INDICATORS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                scores[EmotionalState.CURIOUS] += 1
        
        # Find highest score
        max_score = max(scores.values())
        
        if max_score == 0:
            # Default states based on other signals
            if len(message) > 100:
                return EmotionalState.FOCUSED, 0.5
            else:
                return EmotionalState.CALM, 0.5
        
        # Get state with highest score
        for state, score in scores.items():
            if score == max_score:
                confidence = min(0.9, 0.5 + (score * 0.15))
                return state, confidence
        
        return EmotionalState.CALM, 0.5
    
    def _determine_attention_level(self, message: str, timestamp: datetime) -> AttentionLevel:
        """Determine user's attention level."""
        hour = timestamp.hour
        msg_length = len(message)
        
        # Night time = likely lower attention
        if hour < 6 or hour > 23:
            return AttentionLevel.MINIMAL
        
        # Very short messages = low attention
        if msg_length < 5:
            return AttentionLevel.LOW
        
        # Detailed messages = high attention
        if msg_length > 200:
            return AttentionLevel.HIGH
        
        # Questions often indicate engaged attention
        if '?' in message and msg_length > 20:
            return AttentionLevel.HIGH
        
        return AttentionLevel.MEDIUM
    
    def _calculate_urgency(self, message: str, timestamp: datetime) -> float:
        """Calculate urgency score (0-1)."""
        urgency = 0.0
        msg_lower = message.lower()
        
        # Urgent words
        urgent_words = ['urgent', 'asap', 'now', 'immediately', 'emergency', 'critical', 'help']
        for word in urgent_words:
            if word in msg_lower:
                urgency += 0.3
        
        # Short messages with question marks
        if len(message) < 10 and '?' in message:
            urgency += 0.2
        
        # Multiple punctuation
        if re.search(r'[!?]{2,}', message):
            urgency += 0.2
        
        # Time of day factor
        hour = timestamp.hour
        if hour < 6 or hour > 22:  # Late night = probably urgent if messaging
            urgency += 0.1
        
        return min(1.0, urgency)
    
    def _check_dissatisfaction(self, message: str) -> tuple[float, int]:
        """Check for dissatisfaction based on repeated queries."""
        # Normalize message for comparison
        normalized = re.sub(r'[^\w\s]', '', message.lower()).strip()
        if not normalized:
            return 0.0, 0
        
        # Check against recent messages
        similar_count = 0
        for prev in self._recent_messages[:-1]:  # Exclude current
            prev_normalized = re.sub(r'[^\w\s]', '', prev.lower()).strip()
            # Check for similarity
            if normalized == prev_normalized:
                similar_count += 1
            elif normalized in prev_normalized or prev_normalized in normalized:
                similar_count += 0.5
        
        # Record repetition
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO query_repetitions (query_pattern, first_seen, last_seen)
                VALUES (?, ?, ?)
                ON CONFLICT(query_pattern) DO UPDATE SET
                    repetition_count = repetition_count + 1,
                    last_seen = ?
            """, (normalized[:100], datetime.now().isoformat(), 
                  datetime.now().isoformat(), datetime.now().isoformat()))
            
            cursor.execute("""
                SELECT repetition_count FROM query_repetitions WHERE query_pattern = ?
            """, (normalized[:100],))
            row = cursor.fetchone()
            repetitions = row["repetition_count"] if row else 1
        
        # Calculate dissatisfaction score
        dissatisfaction = min(1.0, similar_count * 0.3 + (repetitions - 1) * 0.2)
        
        return dissatisfaction, int(similar_count)
    
    def _recommend_verbosity(
        self,
        emotional_state: EmotionalState,
        attention_level: AttentionLevel,
        urgency: float,
        message_length: int
    ) -> str:
        """Recommend response verbosity level."""
        # Start with baseline based on attention
        verbosity_map = {
            AttentionLevel.HIGH: "detailed",
            AttentionLevel.MEDIUM: "normal",
            AttentionLevel.LOW: "brief",
            AttentionLevel.MINIMAL: "minimal"
        }
        base = verbosity_map[attention_level]
        
        # Adjust for emotional state
        if emotional_state == EmotionalState.HURRIED:
            return "minimal"
        if emotional_state == EmotionalState.FRUSTRATED:
            return "brief"  # Don't overwhelm
        if emotional_state == EmotionalState.CURIOUS:
            return "detailed"  # They want to learn
        
        # Adjust for urgency
        if urgency > 0.7:
            return "minimal"
        if urgency > 0.4:
            return "brief"
        
        # Adjust for message length (mirror user)
        if message_length < 10:
            if base in ["detailed", "normal"]:
                return "brief"
        
        return base
    
    def _recommend_tone(self, emotional_state: EmotionalState, urgency: float) -> str:
        """Recommend response tone."""
        if urgency > 0.7:
            return "urgent"
        
        if emotional_state == EmotionalState.FRUSTRATED:
            return "supportive"
        if emotional_state == EmotionalState.EXCITED:
            return "enthusiastic"
        if emotional_state == EmotionalState.TIRED:
            return "gentle"
        if emotional_state == EmotionalState.HURRIED:
            return "efficient"
        
        return "professional"
    
    def _get_time_context(self, timestamp: datetime) -> str:
        """Get time-based context."""
        hour = timestamp.hour
        day = timestamp.weekday()
        
        if day >= 5:
            day_context = "weekend"
        else:
            day_context = "weekday"
        
        if hour < 6:
            time_context = "late_night"
        elif hour < 9:
            time_context = "early_morning"
        elif hour < 12:
            time_context = "morning"
        elif hour < 14:
            time_context = "lunch"
        elif hour < 18:
            time_context = "afternoon"
        elif hour < 21:
            time_context = "evening"
        else:
            time_context = "night"
        
        return f"{day_context}_{time_context}"
    
    def _extract_recent_topics(self) -> List[str]:
        """Extract topics from recent messages."""
        topics = []
        topic_patterns = {
            "trading": r'\b(sol|btc|eth|xrp|trade|signal|long|short)\b',
            "servers": r'\b(server|service|status|memory|disk)\b',
            "code": r'\b(code|file|function|build|deploy)\b',
        }
        
        for msg in self._recent_messages[-5:]:
            msg_lower = msg.lower()
            for topic, pattern in topic_patterns.items():
                if re.search(pattern, msg_lower):
                    if topic not in topics:
                        topics.append(topic)
        
        return topics
    
    def _store_analysis(self, message: str, analysis: ContextAnalysis):
        """Store analysis for learning."""
        import hashlib
        msg_hash = hashlib.md5(message.encode()).hexdigest()[:16]
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO context_history 
                (timestamp, message_hash, emotional_state, attention_level, urgency_score, analysis)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                msg_hash,
                analysis.emotional_state.value,
                analysis.attention_level.value,
                analysis.urgency_score,
                json.dumps(analysis.to_dict())
            ))
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context analysis statistics."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT emotional_state, COUNT(*) as count
                FROM context_history
                WHERE timestamp > ?
                GROUP BY emotional_state
            """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
            emotional_dist = {row["emotional_state"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("""
                SELECT AVG(urgency_score) as avg_urgency
                FROM context_history
                WHERE timestamp > ?
            """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
            row = cursor.fetchone()
            avg_urgency = row["avg_urgency"] or 0
        
        return {
            "emotional_distribution_24h": emotional_dist,
            "average_urgency_24h": avg_urgency
        }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_analyzer: Optional[ContextAnalyzer] = None


def get_context_analyzer() -> ContextAnalyzer:
    """Get global context analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ContextAnalyzer()
    return _analyzer


def analyze_context(message: str, **kwargs) -> ContextAnalysis:
    """Analyze message context."""
    return get_context_analyzer().analyze(message, **kwargs)


