#!/usr/bin/env python3
"""
ARIA ASCENSION - MICRO LEARNER
==============================

Instant micro-adjustments based on recent patterns:
- Response quality predictor
- Adjust response length/detail based on recent feedback
- No AI call needed - statistical model

Target: Adjust behavior in real-time without any API calls
"""

import os
import json
import sqlite3
import logging
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.ascension.micro")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")

# Learning rates
RESPONSE_LENGTH_DECAY = 0.95  # How fast old data loses influence
MIN_SAMPLES = 5  # Minimum samples before adjusting


@dataclass
class ResponseConfig:
    """Current response configuration based on learning."""
    # Length adjustments
    target_length_multiplier: float = 1.0  # 0.5 = half length, 2.0 = double
    detail_level: float = 0.5  # 0 = minimal, 1 = maximum detail
    
    # Speed adjustments
    urgency_threshold: float = 0.3  # When to switch to brief mode
    
    # Style adjustments
    emoji_density: float = 0.3  # How many emojis to use
    formality: float = 0.5  # 0 = casual, 1 = formal
    
    def to_dict(self) -> Dict:
        return {
            "target_length_multiplier": self.target_length_multiplier,
            "detail_level": self.detail_level,
            "urgency_threshold": self.urgency_threshold,
            "emoji_density": self.emoji_density,
            "formality": self.formality
        }


@dataclass
class FeedbackSignal:
    """A feedback signal from an interaction."""
    timestamp: datetime
    signal_type: str  # positive, negative, correction, question
    response_length: int
    response_time_ms: float
    context: Dict[str, Any] = field(default_factory=dict)


MICRO_SCHEMA = """
CREATE TABLE IF NOT EXISTS micro_config (
    id INTEGER PRIMARY KEY,
    config TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    response_length INTEGER,
    response_time_ms REAL,
    context TEXT
);

CREATE TABLE IF NOT EXISTS adjustment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    adjustment_type TEXT NOT NULL,
    old_value REAL,
    new_value REAL,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_fs_timestamp ON feedback_signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_fs_type ON feedback_signals(signal_type);
"""


# ============================================================================
# MICRO LEARNER
# ============================================================================

class MicroLearner:
    """
    Real-time micro-adjustment system.
    
    Learns patterns like:
    - User prefers shorter responses at night
    - After corrections, reduce detail level
    - Urgent queries need brief responses
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._config: Optional[ResponseConfig] = None
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
            cursor.executescript(MICRO_SCHEMA)
            
            # Ensure config exists
            cursor.execute("SELECT COUNT(*) FROM micro_config")
            if cursor.fetchone()[0] == 0:
                default_config = ResponseConfig()
                cursor.execute("""
                    INSERT INTO micro_config (id, config, updated_at)
                    VALUES (1, ?, ?)
                """, (json.dumps(default_config.to_dict()), datetime.now().isoformat()))
        
        logger.info(f"Micro learner initialized: {self.db_path}")
    
    # ========================================================================
    # CONFIG MANAGEMENT
    # ========================================================================
    
    def get_config(self) -> ResponseConfig:
        """Get current response configuration."""
        if self._config:
            return self._config
        
        with self._cursor() as cursor:
            cursor.execute("SELECT config FROM micro_config WHERE id = 1")
            row = cursor.fetchone()
            
            if row:
                data = json.loads(row["config"])
                self._config = ResponseConfig(**data)
            else:
                self._config = ResponseConfig()
        
        return self._config
    
    def _save_config(self):
        """Save current config to database."""
        if not self._config:
            return
        
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE micro_config SET config = ?, updated_at = ? WHERE id = 1
            """, (json.dumps(self._config.to_dict()), datetime.now().isoformat()))
    
    # ========================================================================
    # FEEDBACK RECORDING
    # ========================================================================
    
    def record_feedback(
        self,
        signal_type: str,
        response_length: int = 0,
        response_time_ms: float = 0,
        context: Dict = None
    ):
        """
        Record a feedback signal.
        
        Signal types:
        - positive: User expressed satisfaction
        - negative: User expressed dissatisfaction
        - correction: User had to correct/repeat
        - question: User followed up with question
        - quick_followup: User sent another message very fast
        """
        signal = FeedbackSignal(
            timestamp=datetime.now(),
            signal_type=signal_type,
            response_length=response_length,
            response_time_ms=response_time_ms,
            context=context or {}
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO feedback_signals (timestamp, signal_type, response_length, response_time_ms, context)
                VALUES (?, ?, ?, ?, ?)
            """, (
                signal.timestamp.isoformat(),
                signal.signal_type,
                signal.response_length,
                signal.response_time_ms,
                json.dumps(signal.context)
            ))
        
        # Trigger micro-adjustment
        self._maybe_adjust()
    
    # ========================================================================
    # LEARNING & ADJUSTMENT
    # ========================================================================
    
    def _maybe_adjust(self):
        """Check if adjustments are needed based on recent feedback."""
        # Get recent signals
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT signal_type, response_length, response_time_ms, context
                FROM feedback_signals
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, ((datetime.now() - timedelta(hours=6)).isoformat(),))
            
            signals = [
                FeedbackSignal(
                    timestamp=datetime.now(),
                    signal_type=row["signal_type"],
                    response_length=row["response_length"],
                    response_time_ms=row["response_time_ms"],
                    context=json.loads(row["context"] or "{}")
                )
                for row in cursor.fetchall()
            ]
        
        if len(signals) < MIN_SAMPLES:
            return
        
        config = self.get_config()
        old_config = config.to_dict()
        adjusted = False
        
        # Calculate signal ratios
        negative_count = sum(1 for s in signals if s.signal_type in ["negative", "correction"])
        positive_count = sum(1 for s in signals if s.signal_type == "positive")
        question_count = sum(1 for s in signals if s.signal_type == "question")
        
        negative_ratio = negative_count / len(signals)
        positive_ratio = positive_count / len(signals)
        question_ratio = question_count / len(signals)
        
        # Adjust length multiplier based on feedback
        if negative_ratio > 0.3:
            # Too many negative signals - responses might be too long/verbose
            avg_length = sum(s.response_length for s in signals) / len(signals)
            if avg_length > 500:
                # Reduce length
                config.target_length_multiplier = max(0.5, config.target_length_multiplier * 0.9)
                adjusted = True
                self._log_adjustment("length_multiplier", old_config["target_length_multiplier"], 
                                    config.target_length_multiplier, "High negative ratio with long responses")
        
        elif positive_ratio > 0.5:
            # Lots of positive feedback - maintain current settings
            pass
        
        # Adjust detail level based on follow-up questions
        if question_ratio > 0.4:
            # Many follow-up questions - might need more detail
            config.detail_level = min(1.0, config.detail_level + 0.1)
            adjusted = True
            self._log_adjustment("detail_level", old_config["detail_level"],
                                config.detail_level, "High follow-up question ratio")
        elif question_ratio < 0.1 and negative_ratio < 0.1:
            # Few questions and few negatives - detail level is good or could be reduced
            if config.detail_level > 0.5:
                config.detail_level = config.detail_level * 0.95
                adjusted = True
                self._log_adjustment("detail_level", old_config["detail_level"],
                                    config.detail_level, "Low question/negative ratio")
        
        # Adjust based on response times
        avg_time = sum(s.response_time_ms for s in signals) / len(signals)
        if avg_time > 10000:  # > 10 seconds average
            # Responses are slow - reduce detail to speed up
            config.detail_level = max(0.2, config.detail_level * 0.9)
            adjusted = True
            self._log_adjustment("detail_level", old_config["detail_level"],
                                config.detail_level, f"Slow responses: {avg_time:.0f}ms avg")
        
        if adjusted:
            self._config = config
            self._save_config()
            logger.info(f"Micro-adjustment applied: {config.to_dict()}")
    
    def _log_adjustment(self, adj_type: str, old_val: float, new_val: float, reason: str):
        """Log an adjustment for auditing."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO adjustment_history (timestamp, adjustment_type, old_value, new_value, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), adj_type, old_val, new_val, reason))
    
    # ========================================================================
    # RESPONSE RECOMMENDATIONS
    # ========================================================================
    
    def get_response_recommendations(
        self,
        urgency_score: float = 0.0,
        time_of_day: str = None,
        is_followup: bool = False
    ) -> Dict[str, Any]:
        """
        Get recommendations for the current response.
        
        Returns settings the response generator should use.
        """
        config = self.get_config()
        
        # Base recommendations
        recommendations = {
            "max_length": int(500 * config.target_length_multiplier),
            "include_details": config.detail_level > 0.5,
            "use_bullet_points": config.detail_level > 0.3,
            "add_emoji": config.emoji_density > 0.3,
            "be_brief": False
        }
        
        # Adjust for urgency
        if urgency_score > config.urgency_threshold:
            recommendations["max_length"] = 200
            recommendations["include_details"] = False
            recommendations["be_brief"] = True
        
        # Adjust for time of day
        if time_of_day in ["night", "evening"]:
            recommendations["max_length"] = int(recommendations["max_length"] * 0.7)
        
        # Adjust for follow-up
        if is_followup:
            recommendations["include_details"] = True  # They want more info
        
        return recommendations
    
    def get_optimal_response_length(
        self,
        intent: str,
        urgency: float = 0.0
    ) -> int:
        """Get optimal response length for given intent and urgency."""
        config = self.get_config()
        
        # Base lengths by intent
        base_lengths = {
            "trading": 300,
            "status": 200,
            "build": 500,
            "question": 400,
            "command": 100,
            "feedback": 100,
            "greeting": 50,
            "unknown": 200
        }
        
        base = base_lengths.get(intent, 200)
        
        # Apply multiplier
        length = int(base * config.target_length_multiplier)
        
        # Apply urgency reduction
        if urgency > 0.5:
            length = int(length * (1 - urgency * 0.5))
        
        return max(50, length)  # Minimum 50 chars
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        with self._cursor() as cursor:
            # Signal counts
            cursor.execute("""
                SELECT signal_type, COUNT(*) as count
                FROM feedback_signals
                WHERE timestamp > ?
                GROUP BY signal_type
            """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
            signals_24h = {row["signal_type"]: row["count"] for row in cursor.fetchall()}
            
            # Recent adjustments
            cursor.execute("""
                SELECT adjustment_type, old_value, new_value, reason, timestamp
                FROM adjustment_history
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            recent_adjustments = [dict(row) for row in cursor.fetchall()]
        
        config = self.get_config()
        
        return {
            "current_config": config.to_dict(),
            "signals_24h": signals_24h,
            "recent_adjustments": recent_adjustments
        }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_learner: Optional[MicroLearner] = None


def get_micro_learner() -> MicroLearner:
    """Get global micro learner."""
    global _learner
    if _learner is None:
        _learner = MicroLearner()
    return _learner


def record_feedback(signal_type: str, **kwargs):
    """Record feedback signal."""
    get_micro_learner().record_feedback(signal_type, **kwargs)


def get_response_recommendations(**kwargs) -> Dict[str, Any]:
    """Get response recommendations."""
    return get_micro_learner().get_response_recommendations(**kwargs)


def get_optimal_length(intent: str, urgency: float = 0.0) -> int:
    """Get optimal response length."""
    return get_micro_learner().get_optimal_response_length(intent, urgency)


