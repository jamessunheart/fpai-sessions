#!/usr/bin/env python3
"""
Message Pattern Sensor
======================
Senses state from message patterns without explicit input.

Signals:
- Message frequency = activity level
- Message length = cognitive load
- Response time = availability
- Tone keywords = emotional state
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("cis.sensors.messages")

@dataclass
class MessageSignal:
    state: str  # calm, busy, overloaded, stuck
    intensity: int  # 1-5
    confidence: str  # low, medium, high
    signals: Dict  # what triggered the inference
    source: str = "message"


# Tone detection keywords
FRUSTRATION_WORDS = [
    "frustrated", "annoying", "broken", "stuck", "can't", "won't work",
    "failing", "error", "bug", "issue", "problem", "wrong", "hate",
    "ugh", "argh", "damn", "wtf", "why won't", "doesn't work"
]

OVERWHELM_WORDS = [
    "overwhelmed", "too much", "drowning", "buried", "swamped",
    "exhausted", "tired", "burnt out", "can't keep up", "behind"
]

CALM_WORDS = [
    "good", "great", "nice", "working", "done", "finished", "complete",
    "thanks", "perfect", "excellent", "smooth", "easy", "handled"
]

BUSY_WORDS = [
    "quick", "fast", "busy", "rushing", "hurry", "asap", "urgent",
    "deadline", "need to", "have to", "gotta"
]

STUCK_WORDS = [
    "stuck", "blocked", "can't figure", "don't know", "confused",
    "lost", "no idea", "help", "unsure", "unclear"
]


class MessageSensor:
    """Senses state from message patterns."""
    
    def __init__(self, db_path: str = "/opt/fpai/aria/cis.db"):
        self.db_path = db_path
    
    def _get_recent_messages(self, hours: int = 24) -> List[Dict]:
        """Get recent messages from conversation history."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if we have a messages table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_log'")
            if not cursor.fetchone():
                conn.close()
                return []
            
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor.execute("""
                SELECT content, timestamp, word_count, response_time_seconds
                FROM message_log
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {"content": r[0], "timestamp": r[1], "word_count": r[2], "response_time": r[3]}
                for r in rows
            ]
        except Exception as e:
            logger.debug(f"Could not get message history: {e}")
            return []
    
    def analyze_message(self, message: str) -> MessageSignal:
        """Analyze a single message for state signals."""
        msg_lower = message.lower()
        signals = {}
        
        # Word count
        word_count = len(message.split())
        signals["word_count"] = word_count
        
        # Tone detection
        frustration_count = sum(1 for w in FRUSTRATION_WORDS if w in msg_lower)
        overwhelm_count = sum(1 for w in OVERWHELM_WORDS if w in msg_lower)
        calm_count = sum(1 for w in CALM_WORDS if w in msg_lower)
        busy_count = sum(1 for w in BUSY_WORDS if w in msg_lower)
        stuck_count = sum(1 for w in STUCK_WORDS if w in msg_lower)
        
        signals["frustration_words"] = frustration_count
        signals["overwhelm_words"] = overwhelm_count
        signals["calm_words"] = calm_count
        signals["busy_words"] = busy_count
        signals["stuck_words"] = stuck_count
        
        # Punctuation analysis
        exclamation_count = message.count("!")
        question_count = message.count("?")
        signals["exclamations"] = exclamation_count
        signals["questions"] = question_count
        
        # Infer state
        state = "calm"
        intensity = 2
        confidence = "low"
        
        # Short messages (< 10 words) with busy words = busy
        if word_count < 10 and busy_count > 0:
            state = "busy"
            intensity = 3
            confidence = "medium"
        
        # Frustration or overwhelm words = overloaded
        if frustration_count >= 2 or overwhelm_count >= 1:
            state = "overloaded"
            intensity = 4
            confidence = "high" if overwhelm_count >= 1 else "medium"
        
        # Stuck words = stuck
        if stuck_count >= 1:
            state = "stuck"
            intensity = 3
            confidence = "medium"
            if frustration_count > 0:
                intensity = 4
        
        # Calm words dominate = calm
        if calm_count >= 2 and frustration_count == 0 and overwhelm_count == 0:
            state = "calm"
            intensity = 2
            confidence = "medium"
        
        # Very short message = could be busy
        if word_count <= 3:
            if state == "calm":
                state = "busy"
                intensity = 2
            confidence = "low"  # Hard to tell from short messages
        
        # Multiple exclamations = heightened state
        if exclamation_count >= 2:
            intensity = min(5, intensity + 1)
        
        return MessageSignal(
            state=state,
            intensity=intensity,
            confidence=confidence,
            signals=signals
        )
    
    def sense(self) -> Optional[MessageSignal]:
        """Sense current state from recent message patterns."""
        messages = self._get_recent_messages(24)
        
        if not messages:
            return None
        
        # Aggregate signals
        total_words = sum(m.get("word_count", 0) for m in messages)
        avg_words = total_words / len(messages) if messages else 0
        
        # Analyze most recent message for tone
        if messages and messages[0].get("content"):
            return self.analyze_message(messages[0]["content"])
        
        return None


# Singleton
_sensor: Optional[MessageSensor] = None

def get_message_sensor() -> MessageSensor:
    global _sensor
    if _sensor is None:
        _sensor = MessageSensor()
    return _sensor

def sense_message(message: str) -> MessageSignal:
    """Analyze a message for state signals."""
    return get_message_sensor().analyze_message(message)

def sense_from_history() -> Optional[MessageSignal]:
    """Sense from message history."""
    return get_message_sensor().sense()








