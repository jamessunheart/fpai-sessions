#!/usr/bin/env python3
"""
ARIA ULTRA POWER - PATTERN LEARNING
=====================================

Deep pattern learning for user behavior:
- Time-of-day patterns
- Context patterns (what follows what)
- Sequence learning
- Preference detection
"""

import sqlite3
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger("aria.predictive.patterns")

DEFAULT_DB_PATH = "/opt/fpai/aria-command/state/patterns.db"


@dataclass
class UserPattern:
    """A detected user behavior pattern."""
    pattern_type: str  # "time", "sequence", "preference", "context"
    description: str
    confidence: float  # 0-1
    frequency: int  # How often observed
    last_seen: float
    data: Dict = field(default_factory=dict)


@dataclass
class InteractionRecord:
    """Record of a user interaction."""
    timestamp: float
    hour: int
    day_of_week: int
    intent: str  # "trading", "server", "question", etc.
    topic: str  # "SOL", "memory", etc.
    message_preview: str
    response_type: str  # "quick", "detailed", "action"
    successful: bool


class PatternLearner:
    """
    Learn patterns from user interactions.
    
    Features:
    - Time-of-day patterns (when user typically asks for what)
    - Sequence patterns (what queries follow other queries)
    - Topic preferences
    - Response style preferences
    """
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        # In-memory pattern cache
        self._patterns: Dict[str, List[UserPattern]] = {}
        self._cache_time = 0
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("PatternLearner initialized")
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                hour INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL,
                intent TEXT,
                topic TEXT,
                message_preview TEXT,
                response_type TEXT,
                successful INTEGER DEFAULT 1
            )
        """)
        
        # Sequences table (for tracking A -> B patterns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                from_intent TEXT,
                from_topic TEXT,
                to_intent TEXT,
                to_topic TEXT,
                count INTEGER DEFAULT 1,
                last_seen REAL
            )
        """)
        
        # Learned patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                description TEXT,
                confidence REAL,
                frequency INTEGER,
                data TEXT,
                created_at REAL,
                updated_at REAL
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_time ON interactions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sequences_user ON sequences(user_id)")
        
        conn.commit()
        conn.close()
    
    def record_interaction(
        self,
        user_id: str,
        intent: str,
        topic: str,
        message: str,
        response_type: str = "quick",
        successful: bool = True
    ):
        """Record a user interaction for pattern learning."""
        now = datetime.now()
        timestamp = time.time()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert interaction
        cursor.execute("""
            INSERT INTO interactions 
            (user_id, timestamp, hour, day_of_week, intent, topic, message_preview, response_type, successful)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            timestamp,
            now.hour,
            now.weekday(),
            intent,
            topic,
            message[:100],
            response_type,
            1 if successful else 0
        ))
        
        # Get previous interaction for sequence tracking
        cursor.execute("""
            SELECT intent, topic FROM interactions 
            WHERE user_id = ? AND id != last_insert_rowid()
            ORDER BY timestamp DESC LIMIT 1
        """, (user_id,))
        
        prev = cursor.fetchone()
        if prev:
            prev_intent, prev_topic = prev
            
            # Update sequence
            cursor.execute("""
                INSERT INTO sequences (user_id, from_intent, from_topic, to_intent, to_topic, count, last_seen)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(user_id, from_intent, from_topic, to_intent, to_topic) 
                DO UPDATE SET count = count + 1, last_seen = ?
            """, (user_id, prev_intent, prev_topic, intent, topic, timestamp, timestamp))
        
        conn.commit()
        conn.close()
        
        # Invalidate cache
        self._cache_time = 0
    
    def get_patterns(self, user_id: str) -> List[UserPattern]:
        """Get learned patterns for a user."""
        # Check cache
        if user_id in self._patterns and time.time() - self._cache_time < self._cache_ttl:
            return self._patterns[user_id]
        
        patterns = []
        
        # Time patterns
        patterns.extend(self._analyze_time_patterns(user_id))
        
        # Sequence patterns
        patterns.extend(self._analyze_sequence_patterns(user_id))
        
        # Topic preferences
        patterns.extend(self._analyze_topic_preferences(user_id))
        
        self._patterns[user_id] = patterns
        self._cache_time = time.time()
        
        return patterns
    
    def _analyze_time_patterns(self, user_id: str) -> List[UserPattern]:
        """Analyze time-of-day patterns."""
        patterns = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Hour distribution by intent
        cursor.execute("""
            SELECT hour, intent, COUNT(*) as count
            FROM interactions
            WHERE user_id = ?
            GROUP BY hour, intent
            HAVING count >= 3
            ORDER BY count DESC
        """, (user_id,))
        
        hour_patterns = defaultdict(lambda: defaultdict(int))
        for hour, intent, count in cursor.fetchall():
            hour_patterns[hour][intent] = count
        
        # Find strong time patterns
        for hour, intents in hour_patterns.items():
            total = sum(intents.values())
            if total >= 5:
                top_intent = max(intents, key=intents.get)
                confidence = intents[top_intent] / total
                
                if confidence >= 0.5:
                    patterns.append(UserPattern(
                        pattern_type="time",
                        description=f"Usually asks about {top_intent} around {hour}:00",
                        confidence=confidence,
                        frequency=intents[top_intent],
                        last_seen=time.time(),
                        data={
                            "hour": hour,
                            "intent": top_intent,
                            "distribution": dict(intents),
                        }
                    ))
        
        # Day of week patterns
        cursor.execute("""
            SELECT day_of_week, intent, COUNT(*) as count
            FROM interactions
            WHERE user_id = ?
            GROUP BY day_of_week, intent
            HAVING count >= 3
        """, (user_id,))
        
        day_patterns = defaultdict(lambda: defaultdict(int))
        for day, intent, count in cursor.fetchall():
            day_patterns[day][intent] = count
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day, intents in day_patterns.items():
            total = sum(intents.values())
            if total >= 5:
                top_intent = max(intents, key=intents.get)
                confidence = intents[top_intent] / total
                
                if confidence >= 0.5:
                    patterns.append(UserPattern(
                        pattern_type="time",
                        description=f"On {day_names[day]}s, often asks about {top_intent}",
                        confidence=confidence,
                        frequency=intents[top_intent],
                        last_seen=time.time(),
                        data={
                            "day_of_week": day,
                            "day_name": day_names[day],
                            "intent": top_intent,
                        }
                    ))
        
        conn.close()
        return patterns
    
    def _analyze_sequence_patterns(self, user_id: str) -> List[UserPattern]:
        """Analyze query sequence patterns (A -> B)."""
        patterns = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get common sequences
        cursor.execute("""
            SELECT from_intent, from_topic, to_intent, to_topic, count, last_seen
            FROM sequences
            WHERE user_id = ? AND count >= 3
            ORDER BY count DESC
            LIMIT 10
        """, (user_id,))
        
        for from_intent, from_topic, to_intent, to_topic, count, last_seen in cursor.fetchall():
            # Calculate confidence based on how often this sequence occurs
            cursor.execute("""
                SELECT SUM(count) FROM sequences
                WHERE user_id = ? AND from_intent = ? AND from_topic = ?
            """, (user_id, from_intent, from_topic))
            total = cursor.fetchone()[0] or 1
            
            confidence = count / total
            
            if confidence >= 0.3:
                patterns.append(UserPattern(
                    pattern_type="sequence",
                    description=f"After {from_intent}/{from_topic}, often asks about {to_intent}/{to_topic}",
                    confidence=confidence,
                    frequency=count,
                    last_seen=last_seen,
                    data={
                        "from_intent": from_intent,
                        "from_topic": from_topic,
                        "to_intent": to_intent,
                        "to_topic": to_topic,
                    }
                ))
        
        conn.close()
        return patterns
    
    def _analyze_topic_preferences(self, user_id: str) -> List[UserPattern]:
        """Analyze topic preferences."""
        patterns = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get topic distribution
        cursor.execute("""
            SELECT topic, COUNT(*) as count
            FROM interactions
            WHERE user_id = ? AND topic IS NOT NULL
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 10
        """, (user_id,))
        
        topics = cursor.fetchall()
        total = sum(c for _, c in topics) or 1
        
        for topic, count in topics:
            if count >= 5:
                confidence = count / total
                patterns.append(UserPattern(
                    pattern_type="preference",
                    description=f"Frequently interested in {topic}",
                    confidence=confidence,
                    frequency=count,
                    last_seen=time.time(),
                    data={
                        "topic": topic,
                        "percentage": confidence * 100,
                    }
                ))
        
        conn.close()
        return patterns
    
    def predict_next(self, user_id: str, current_intent: str, current_topic: str) -> Optional[Dict]:
        """Predict what user might ask next based on patterns."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find most likely next query
        cursor.execute("""
            SELECT to_intent, to_topic, count
            FROM sequences
            WHERE user_id = ? AND from_intent = ? AND from_topic = ?
            ORDER BY count DESC
            LIMIT 1
        """, (user_id, current_intent, current_topic))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            to_intent, to_topic, count = result
            return {
                "intent": to_intent,
                "topic": to_topic,
                "confidence": min(1.0, count / 10),
            }
        
        return None
    
    def get_likely_needs_now(self, user_id: str) -> List[Dict]:
        """Get what user likely needs right now based on time patterns."""
        now = datetime.now()
        current_hour = now.hour
        current_day = now.weekday()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get historical intents for this time
        cursor.execute("""
            SELECT intent, topic, COUNT(*) as count
            FROM interactions
            WHERE user_id = ? 
            AND hour = ?
            AND day_of_week = ?
            GROUP BY intent, topic
            ORDER BY count DESC
            LIMIT 5
        """, (user_id, current_hour, current_day))
        
        results = cursor.fetchall()
        conn.close()
        
        total = sum(c for _, _, c in results) or 1
        
        needs = []
        for intent, topic, count in results:
            needs.append({
                "intent": intent,
                "topic": topic,
                "confidence": count / total,
                "historical_count": count,
            })
        
        return needs
    
    def get_stats(self, user_id: str) -> Dict:
        """Get pattern learning statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM interactions WHERE user_id = ?",
            (user_id,)
        )
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM sequences WHERE user_id = ?",
            (user_id,)
        )
        total_sequences = cursor.fetchone()[0]
        
        patterns = self.get_patterns(user_id)
        
        conn.close()
        
        return {
            "total_interactions": total_interactions,
            "total_sequences": total_sequences,
            "patterns_learned": len(patterns),
            "time_patterns": len([p for p in patterns if p.pattern_type == "time"]),
            "sequence_patterns": len([p for p in patterns if p.pattern_type == "sequence"]),
            "preferences": len([p for p in patterns if p.pattern_type == "preference"]),
        }


# Singleton instance
_learner: Optional[PatternLearner] = None


def get_pattern_learner() -> PatternLearner:
    """Get global PatternLearner instance."""
    global _learner
    if _learner is None:
        _learner = PatternLearner()
    return _learner


def record_interaction(
    user_id: str,
    intent: str,
    topic: str,
    message: str,
    response_type: str = "quick",
    successful: bool = True
):
    """Convenience function to record interaction."""
    learner = get_pattern_learner()
    learner.record_interaction(user_id, intent, topic, message, response_type, successful)


def get_user_patterns(user_id: str) -> List[UserPattern]:
    """Convenience function to get patterns."""
    learner = get_pattern_learner()
    return learner.get_patterns(user_id)


