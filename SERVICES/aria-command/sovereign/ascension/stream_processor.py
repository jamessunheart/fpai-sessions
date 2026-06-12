#!/usr/bin/env python3
"""
ARIA ASCENSION - STREAM PROCESSOR
=================================

Real-time learning from every interaction:
- Hook into every message in/out
- Extract features: intent, sentiment, response time, success
- Publish to learning pipeline
- Target: < 100ms processing latency
"""

import os
import json
import asyncio
import logging
import sqlite3
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.ascension.stream")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")


class Intent(str, Enum):
    """Detected user intent."""
    TRADING = "trading"
    STATUS = "status"
    BUILD = "build"
    QUESTION = "question"
    COMMAND = "command"
    FEEDBACK = "feedback"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class Sentiment(str, Enum):
    """Detected sentiment."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    URGENT = "urgent"
    FRUSTRATED = "frustrated"


@dataclass
class InteractionFeatures:
    """Extracted features from an interaction."""
    # Basic
    interaction_id: str
    timestamp: datetime
    
    # Message features
    message_length: int
    word_count: int
    has_question: bool
    has_command: bool
    has_emoji: bool
    punctuation_density: float  # !?. per word
    
    # Intent & Sentiment
    intent: Intent
    sentiment: Sentiment
    urgency_score: float  # 0-1
    
    # Context
    time_of_day: str  # morning/afternoon/evening/night
    day_of_week: int
    is_weekend: bool
    minutes_since_last: float
    
    # Response features (if response exists)
    response_length: int = 0
    response_time_ms: float = 0
    tools_used: List[str] = field(default_factory=list)
    success: bool = True
    
    # Follow-up signal
    followed_by_question: bool = False
    followed_by_correction: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "interaction_id": self.interaction_id,
            "timestamp": self.timestamp.isoformat(),
            "message_length": self.message_length,
            "word_count": self.word_count,
            "has_question": self.has_question,
            "has_command": self.has_command,
            "has_emoji": self.has_emoji,
            "punctuation_density": self.punctuation_density,
            "intent": self.intent.value,
            "sentiment": self.sentiment.value,
            "urgency_score": self.urgency_score,
            "time_of_day": self.time_of_day,
            "day_of_week": self.day_of_week,
            "is_weekend": self.is_weekend,
            "minutes_since_last": self.minutes_since_last,
            "response_length": self.response_length,
            "response_time_ms": self.response_time_ms,
            "tools_used": self.tools_used,
            "success": self.success,
            "followed_by_question": self.followed_by_question,
            "followed_by_correction": self.followed_by_correction
        }


STREAM_SCHEMA = """
CREATE TABLE IF NOT EXISTS interaction_stream (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interaction_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    user_message TEXT,
    response TEXT,
    features TEXT,
    processed INTEGER DEFAULT 0,
    learning_applied INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS feature_vectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interaction_id TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    interaction_id TEXT,
    data TEXT,
    applied INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_is_timestamp ON interaction_stream(timestamp);
CREATE INDEX IF NOT EXISTS idx_is_processed ON interaction_stream(processed);
CREATE INDEX IF NOT EXISTS idx_fv_interaction ON feature_vectors(interaction_id);
CREATE INDEX IF NOT EXISTS idx_le_type ON learning_events(event_type);
"""


# ============================================================================
# FEATURE EXTRACTOR
# ============================================================================

class FeatureExtractor:
    """
    Extracts features from messages in real-time.
    Optimized for speed - no AI calls, pure heuristics.
    """
    
    # Intent patterns
    TRADING_PATTERNS = [
        r'\b(sol|btc|eth|xrp|signal|trade|position|long|short|buy|sell)\b',
        r'\b(market|price|profit|loss|pnl)\b'
    ]
    
    STATUS_PATTERNS = [
        r'\b(status|health|server|service|memory|disk)\b',
        r'\?$'
    ]
    
    BUILD_PATTERNS = [
        r'\b(build|create|implement|add|fix|update|deploy)\b',
        r'\b(code|file|function|class|feature)\b'
    ]
    
    COMMAND_PATTERNS = [
        r'^/',
        r'\b(run|execute|restart|stop|start)\b'
    ]
    
    FEEDBACK_PATTERNS = [
        r'\b(good|great|thanks|perfect|awesome|love)\b',
        r'\b(bad|wrong|no|not|incorrect|broken)\b'
    ]
    
    # Sentiment patterns
    NEGATIVE_PATTERNS = [
        r'\b(no|not|wrong|bad|broken|fail|error|issue|problem)\b',
        r'(?:\?\s*){2,}',  # Multiple question marks
        r'(?:!\s*){2,}'   # Multiple exclamation marks
    ]
    
    FRUSTRATED_PATTERNS = [
        r'\b(again|still|yet|why|wtf|ugh)\b',
        r'(?:\?\s*){3,}'  # Many question marks = frustration
    ]
    
    URGENT_PATTERNS = [
        r'\b(urgent|asap|now|immediately|emergency|critical)\b',
        r'(?:!\s*){2,}'
    ]
    
    def __init__(self):
        self.last_interaction_time: Dict[int, datetime] = {}  # chat_id -> last time
    
    def extract(
        self,
        interaction_id: str,
        user_message: str,
        response: str = None,
        response_time_ms: float = 0,
        tools_used: List[str] = None,
        success: bool = True,
        chat_id: int = 0
    ) -> InteractionFeatures:
        """
        Extract features from an interaction.
        Target: < 10ms execution time.
        """
        now = datetime.now()
        msg_lower = user_message.lower()
        
        # Basic text features
        words = user_message.split()
        word_count = len(words)
        punctuation = sum(1 for c in user_message if c in '!?.')
        
        # Time features
        hour = now.hour
        if hour < 6:
            time_of_day = "night"
        elif hour < 12:
            time_of_day = "morning"
        elif hour < 18:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"
        
        # Minutes since last
        last_time = self.last_interaction_time.get(chat_id)
        if last_time:
            minutes_since = (now - last_time).total_seconds() / 60
        else:
            minutes_since = 999
        self.last_interaction_time[chat_id] = now
        
        # Intent detection
        intent = self._detect_intent(msg_lower)
        
        # Sentiment detection
        sentiment, urgency = self._detect_sentiment(msg_lower)
        
        features = InteractionFeatures(
            interaction_id=interaction_id,
            timestamp=now,
            message_length=len(user_message),
            word_count=word_count,
            has_question='?' in user_message,
            has_command=user_message.startswith('/'),
            has_emoji=bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]', user_message)),
            punctuation_density=punctuation / max(word_count, 1),
            intent=intent,
            sentiment=sentiment,
            urgency_score=urgency,
            time_of_day=time_of_day,
            day_of_week=now.weekday(),
            is_weekend=now.weekday() >= 5,
            minutes_since_last=minutes_since,
            response_length=len(response) if response else 0,
            response_time_ms=response_time_ms,
            tools_used=tools_used or [],
            success=success
        )
        
        return features
    
    def _detect_intent(self, text: str) -> Intent:
        """Fast intent detection using patterns."""
        # Check patterns in priority order
        for pattern in self.COMMAND_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return Intent.COMMAND
        
        for pattern in self.TRADING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return Intent.TRADING
        
        for pattern in self.BUILD_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return Intent.BUILD
        
        for pattern in self.STATUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return Intent.STATUS
        
        for pattern in self.FEEDBACK_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return Intent.FEEDBACK
        
        if '?' in text or text.lower().startswith(('what', 'how', 'why', 'when', 'where', 'who')):
            return Intent.QUESTION
        
        if text.lower() in ['hi', 'hello', 'hey', 'good morning', 'good evening']:
            return Intent.GREETING
        
        return Intent.UNKNOWN
    
    def _detect_sentiment(self, text: str) -> tuple[Sentiment, float]:
        """Fast sentiment detection. Returns (sentiment, urgency_score)."""
        urgency = 0.0
        
        # Check frustrated first (subset of negative)
        for pattern in self.FRUSTRATED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return Sentiment.FRUSTRATED, 0.8
        
        # Check urgent
        for pattern in self.URGENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                urgency = 0.9
                return Sentiment.URGENT, urgency
        
        # Check negative
        for pattern in self.NEGATIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return Sentiment.NEGATIVE, 0.3
        
        # Check positive
        positive_words = ['good', 'great', 'thanks', 'perfect', 'awesome', 'love', 'nice']
        if any(w in text for w in positive_words):
            return Sentiment.POSITIVE, 0.1
        
        return Sentiment.NEUTRAL, 0.2


# ============================================================================
# STREAM PROCESSOR
# ============================================================================

class StreamProcessor:
    """
    Main stream processor that handles real-time learning.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self.extractor = FeatureExtractor()
        self._callbacks: List[Callable[[InteractionFeatures], None]] = []
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
            cursor.executescript(STREAM_SCHEMA)
        
        logger.info(f"Stream processor initialized: {self.db_path}")
    
    def register_callback(self, callback: Callable[[InteractionFeatures], None]):
        """Register callback for new interactions."""
        self._callbacks.append(callback)
    
    async def process(
        self,
        interaction_id: str,
        user_message: str,
        response: str = None,
        response_time_ms: float = 0,
        tools_used: List[str] = None,
        success: bool = True,
        chat_id: int = 0
    ) -> InteractionFeatures:
        """
        Process an interaction and extract features.
        This should be called after EVERY interaction.
        """
        import time
        start = time.time()
        
        # Extract features
        features = self.extractor.extract(
            interaction_id=interaction_id,
            user_message=user_message,
            response=response,
            response_time_ms=response_time_ms,
            tools_used=tools_used,
            success=success,
            chat_id=chat_id
        )
        
        # Store in database
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO interaction_stream
                (interaction_id, timestamp, user_message, response, features)
                VALUES (?, ?, ?, ?, ?)
            """, (
                interaction_id,
                features.timestamp.isoformat(),
                user_message,
                response,
                json.dumps(features.to_dict())
            ))
            
            # Store individual feature vectors for analysis
            for name, value in [
                ("message_length", features.message_length),
                ("word_count", features.word_count),
                ("punctuation_density", features.punctuation_density),
                ("urgency_score", features.urgency_score),
                ("response_time_ms", features.response_time_ms),
                ("response_length", features.response_length),
            ]:
                cursor.execute("""
                    INSERT INTO feature_vectors (interaction_id, feature_name, feature_value, created_at)
                    VALUES (?, ?, ?, ?)
                """, (interaction_id, name, value, datetime.now().isoformat()))
        
        # Check for follow-up patterns in previous interaction
        await self._check_followup_signals(features)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(features)
            except Exception as e:
                logger.error(f"Stream callback error: {e}")
        
        processing_time = (time.time() - start) * 1000
        logger.debug(f"Stream processed in {processing_time:.1f}ms: {features.intent.value}/{features.sentiment.value}")
        
        return features
    
    async def _check_followup_signals(self, features: InteractionFeatures):
        """Check if this interaction is a follow-up signal for the previous one."""
        with self._cursor() as cursor:
            # Get previous interaction
            cursor.execute("""
                SELECT interaction_id, features FROM interaction_stream
                WHERE timestamp < ?
                ORDER BY timestamp DESC LIMIT 1
            """, (features.timestamp.isoformat(),))
            
            prev = cursor.fetchone()
            if not prev:
                return
            
            # Check if this is a correction or question follow-up
            is_correction = features.sentiment in [Sentiment.NEGATIVE, Sentiment.FRUSTRATED]
            is_question = features.has_question or features.intent == Intent.QUESTION
            
            if is_correction or is_question:
                # Update previous interaction's follow-up flags
                prev_features = json.loads(prev["features"])
                prev_features["followed_by_correction"] = is_correction
                prev_features["followed_by_question"] = is_question
                
                cursor.execute("""
                    UPDATE interaction_stream SET features = ? WHERE interaction_id = ?
                """, (json.dumps(prev_features), prev["interaction_id"]))
                
                # Log learning event
                cursor.execute("""
                    INSERT INTO learning_events (timestamp, event_type, interaction_id, data)
                    VALUES (?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    "followup_signal",
                    prev["interaction_id"],
                    json.dumps({"correction": is_correction, "question": is_question})
                ))
    
    def get_recent_features(self, limit: int = 50) -> List[Dict]:
        """Get recent interaction features."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT features FROM interaction_stream
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            
            return [json.loads(row["features"]) for row in cursor.fetchall()]
    
    def get_intent_distribution(self, hours: int = 24) -> Dict[str, int]:
        """Get intent distribution for recent period."""
        since = datetime.now().isoformat()[:11] + "00:00:00"  # Simplified
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT features FROM interaction_stream
                WHERE timestamp > ?
            """, (since,))
            
            distribution = {}
            for row in cursor.fetchall():
                features = json.loads(row["features"])
                intent = features.get("intent", "unknown")
                distribution[intent] = distribution.get(intent, 0) + 1
            
            return distribution
    
    def get_sentiment_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get sentiment trends."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT features FROM interaction_stream
                ORDER BY timestamp DESC LIMIT 100
            """)
            
            sentiments = []
            urgencies = []
            for row in cursor.fetchall():
                features = json.loads(row["features"])
                sentiments.append(features.get("sentiment", "neutral"))
                urgencies.append(features.get("urgency_score", 0))
            
            return {
                "negative_rate": sentiments.count("negative") / max(len(sentiments), 1),
                "frustrated_rate": sentiments.count("frustrated") / max(len(sentiments), 1),
                "avg_urgency": sum(urgencies) / max(len(urgencies), 1),
                "total_interactions": len(sentiments)
            }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_processor: Optional[StreamProcessor] = None


def get_stream_processor() -> StreamProcessor:
    """Get global stream processor."""
    global _processor
    if _processor is None:
        _processor = StreamProcessor()
    return _processor


async def process_interaction(
    interaction_id: str,
    user_message: str,
    response: str = None,
    response_time_ms: float = 0,
    tools_used: List[str] = None,
    success: bool = True,
    chat_id: int = 0
) -> InteractionFeatures:
    """Process an interaction through the stream."""
    return await get_stream_processor().process(
        interaction_id, user_message, response,
        response_time_ms, tools_used, success, chat_id
    )


def get_recent_features(limit: int = 50) -> List[Dict]:
    """Get recent features."""
    return get_stream_processor().get_recent_features(limit)


