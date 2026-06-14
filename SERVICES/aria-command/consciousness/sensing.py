"""
ARIA SENSING LAYER
===================

Gap 6 Solution: Emotional and coherence detection.

The governance rules say things like:
- "If James seems stressed, pause expansion"
- Track coherence (James's stress state)
- Consider shadow costs

But there was no actual SENSING. This module adds it:
1. Detect emotion in messages
2. Track coherence over time  
3. Adjust behavior based on sensed state

Now Aria can FEEL, not just THINK.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger("aria.consciousness.sensing")

# State persistence
STATE_FILE = Path("/opt/fpai/aria-command/state/coherence.json")


class EmotionalState(str, Enum):
    """Detected emotional states."""
    CALM = "calm"
    HAPPY = "happy"
    STRESSED = "stressed"
    FRUSTRATED = "frustrated"
    ANXIOUS = "anxious"
    EXCITED = "excited"
    TIRED = "tired"
    UNCERTAIN = "uncertain"
    NEUTRAL = "neutral"


class CoherenceLevel(str, Enum):
    """James's coherence (mental/emotional) levels."""
    HIGH = "high"         # Calm, focused, making good decisions
    MODERATE = "moderate" # Normal operating state
    LOW = "low"          # Some stress, needs care
    CRITICAL = "critical" # High stress, pause non-essential actions


@dataclass
class EmotionReading:
    """A single emotion reading from a message."""
    primary_emotion: EmotionalState
    confidence: float  # 0-1
    secondary_emotions: List[EmotionalState] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)  # What triggered this reading
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "primary_emotion": self.primary_emotion.value,
            "confidence": self.confidence,
            "secondary_emotions": [e.value for e in self.secondary_emotions],
            "triggers": self.triggers,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class CoherenceState:
    """James's overall coherence state."""
    level: CoherenceLevel = CoherenceLevel.MODERATE
    stress_score: float = 0.3  # 0=calm, 1=max stress
    energy_level: float = 0.7  # 0=exhausted, 1=high energy
    recent_emotions: List[EmotionReading] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    trend: str = "stable"  # improving, stable, declining
    
    def to_dict(self) -> Dict:
        return {
            "level": self.level.value,
            "stress_score": self.stress_score,
            "energy_level": self.energy_level,
            "recent_emotions": [e.to_dict() for e in self.recent_emotions[-10:]],
            "last_updated": self.last_updated.isoformat(),
            "trend": self.trend
        }


# ============================================================================
# EMOTION PATTERNS
# ============================================================================

EMOTION_PATTERNS = {
    EmotionalState.STRESSED: {
        "keywords": ["stressed", "overwhelmed", "too much", "can't handle", "struggling", 
                     "swamped", "drowning", "burning out", "exhausted", "crazy day"],
        "patterns": [r"i['\"]?m\s+(so\s+)?stressed", r"too\s+much\s+(to\s+do|going\s+on)"],
        "weight": 0.8
    },
    EmotionalState.FRUSTRATED: {
        "keywords": ["frustrated", "annoying", "annoyed", "ugh", "dammit", "damn",
                     "fucking", "shit", "wtf", "seriously?", "come on"],
        "patterns": [r"(why\s+)?won['\"]?t\s+(it|this)\s+work", r"not\s+working"],
        "weight": 0.7
    },
    EmotionalState.ANXIOUS: {
        "keywords": ["worried", "anxious", "nervous", "concerned", "afraid", "scared",
                     "what if", "uncertain", "risky"],
        "patterns": [r"i['\"]?m\s+worried\s+about", r"what\s+if\s+.+\s+goes\s+wrong"],
        "weight": 0.6
    },
    EmotionalState.TIRED: {
        "keywords": ["tired", "exhausted", "drained", "worn out", "sleepy", 
                     "need a break", "wiped", "running on empty"],
        "patterns": [r"(so|really)\s+tired", r"need\s+(some\s+)?sleep"],
        "weight": 0.5
    },
    EmotionalState.HAPPY: {
        "keywords": ["happy", "great", "awesome", "amazing", "fantastic", "excited",
                     "love it", "perfect", "excellent", "wonderful"],
        "patterns": [r"(this|that)\s+is\s+(so\s+)?(great|awesome|amazing)"],
        "weight": 0.4
    },
    EmotionalState.EXCITED: {
        "keywords": ["excited", "can't wait", "pumped", "stoked", "hyped",
                     "looking forward", "!!", "🚀", "🔥"],
        "patterns": [r"(so|really)\s+excited", r"can['\"]?t\s+wait"],
        "weight": 0.5
    },
    EmotionalState.UNCERTAIN: {
        "keywords": ["not sure", "maybe", "i think", "possibly", "dunno", 
                     "idk", "hmm", "unclear"],
        "patterns": [r"i['\"]?m\s+not\s+sure", r"what\s+do\s+you\s+think"],
        "weight": 0.3
    }
}


class EmotionSensor:
    """
    Detects emotional state from messages.
    """
    
    def __init__(self):
        self.patterns = EMOTION_PATTERNS
        logger.info("Emotion sensor initialized")
    
    def sense(self, message: str) -> EmotionReading:
        """
        Sense emotion from a message.
        
        Args:
            message: The message to analyze
        
        Returns:
            EmotionReading with detected emotion
        """
        message_lower = message.lower()
        
        scores: Dict[EmotionalState, float] = {}
        triggers: Dict[EmotionalState, List[str]] = {}
        
        for emotion, config in self.patterns.items():
            score = 0.0
            emotion_triggers = []
            
            # Check keywords
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    score += config["weight"] * 0.5
                    emotion_triggers.append(f"keyword:{keyword}")
            
            # Check patterns
            for pattern in config.get("patterns", []):
                if re.search(pattern, message_lower, re.IGNORECASE):
                    score += config["weight"]
                    emotion_triggers.append(f"pattern:{pattern[:20]}")
            
            if score > 0:
                scores[emotion] = score
                triggers[emotion] = emotion_triggers
        
        # Determine primary emotion
        if not scores:
            return EmotionReading(
                primary_emotion=EmotionalState.NEUTRAL,
                confidence=0.5,
                triggers=[]
            )
        
        primary_emotion = max(scores, key=scores.get)
        confidence = min(1.0, scores[primary_emotion])
        
        # Get secondary emotions
        secondary = sorted(
            [e for e in scores if e != primary_emotion],
            key=lambda e: scores[e],
            reverse=True
        )[:2]
        
        return EmotionReading(
            primary_emotion=primary_emotion,
            confidence=confidence,
            secondary_emotions=secondary,
            triggers=triggers.get(primary_emotion, [])
        )


class CoherenceTracker:
    """
    Tracks James's coherence over time.
    
    Coherence = mental/emotional state that enables good decisions.
    High coherence = calm, focused, clear.
    Low coherence = stressed, reactive, scattered.
    """
    
    def __init__(self):
        self.state = CoherenceState()
        self.sensor = EmotionSensor()
        self._load_state()
        logger.info("Coherence tracker initialized")
    
    def _load_state(self):
        """Load state from file."""
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text())
                self.state.level = CoherenceLevel(data.get("level", "moderate"))
                self.state.stress_score = data.get("stress_score", 0.3)
                self.state.energy_level = data.get("energy_level", 0.7)
                self.state.trend = data.get("trend", "stable")
                logger.info(f"Coherence state loaded: {self.state.level.value}")
        except Exception as e:
            logger.warning(f"Could not load coherence state: {e}")
    
    def _save_state(self):
        """Save state to file."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.state.last_updated = datetime.now()
            STATE_FILE.write_text(json.dumps(self.state.to_dict(), indent=2))
        except Exception as e:
            logger.warning(f"Could not save coherence state: {e}")
    
    def process_message(self, message: str, user_id: str = None) -> Dict[str, Any]:
        """
        Process a message and update coherence state.
        
        Args:
            message: The message to process
            user_id: Optional user ID (only track James specifically)
        
        Returns:
            Dict with sensing results
        """
        # Sense emotion
        emotion = self.sensor.sense(message)
        
        # Add to recent emotions (keep last 20)
        self.state.recent_emotions.append(emotion)
        self.state.recent_emotions = self.state.recent_emotions[-20:]
        
        # Update stress score based on emotion
        stress_delta = {
            EmotionalState.STRESSED: 0.2,
            EmotionalState.FRUSTRATED: 0.15,
            EmotionalState.ANXIOUS: 0.1,
            EmotionalState.TIRED: 0.1,
            EmotionalState.HAPPY: -0.1,
            EmotionalState.EXCITED: -0.05,
            EmotionalState.CALM: -0.15,
            EmotionalState.NEUTRAL: -0.02,
        }.get(emotion.primary_emotion, 0)
        
        # Apply delta with emotion confidence
        self.state.stress_score += stress_delta * emotion.confidence
        self.state.stress_score = max(0, min(1, self.state.stress_score))
        
        # Natural decay of stress over time (calm down gradually)
        time_since_update = (datetime.now() - self.state.last_updated).total_seconds() / 3600
        decay = min(0.1, time_since_update * 0.05)
        self.state.stress_score = max(0, self.state.stress_score - decay)
        
        # Determine coherence level from stress score
        if self.state.stress_score < 0.2:
            self.state.level = CoherenceLevel.HIGH
        elif self.state.stress_score < 0.5:
            self.state.level = CoherenceLevel.MODERATE
        elif self.state.stress_score < 0.7:
            self.state.level = CoherenceLevel.LOW
        else:
            self.state.level = CoherenceLevel.CRITICAL
        
        # Determine trend from recent emotions
        recent_stress = [e for e in self.state.recent_emotions[-5:] 
                         if e.primary_emotion in [EmotionalState.STRESSED, 
                                                   EmotionalState.FRUSTRATED,
                                                   EmotionalState.ANXIOUS]]
        if len(recent_stress) >= 3:
            self.state.trend = "declining"
        elif len(recent_stress) == 0:
            self.state.trend = "improving"
        else:
            self.state.trend = "stable"
        
        self._save_state()
        
        return {
            "emotion_detected": emotion.to_dict(),
            "coherence_level": self.state.level.value,
            "stress_score": self.state.stress_score,
            "trend": self.state.trend,
            "should_pause_expansion": self.state.level == CoherenceLevel.CRITICAL
        }
    
    def get_coherence_context(self) -> str:
        """
        Get coherence context for system prompt.
        
        Returns context about James's state to guide Aria's behavior.
        """
        if self.state.level == CoherenceLevel.HIGH:
            return ""  # No special handling needed
        
        lines = ["\n## 💫 COHERENCE AWARENESS\n"]
        
        if self.state.level == CoherenceLevel.MODERATE:
            lines.append("James appears to be in a normal state. Proceed normally but stay attentive.")
        
        elif self.state.level == CoherenceLevel.LOW:
            lines.append("⚠️ **James may be experiencing some stress.**")
            lines.append("- Be extra supportive and concise")
            lines.append("- Avoid overwhelming with options")
            lines.append("- Consider suggesting breaks if appropriate")
            lines.append(f"- Recent trend: {self.state.trend}")
        
        elif self.state.level == CoherenceLevel.CRITICAL:
            lines.append("🚨 **HIGH STRESS DETECTED**")
            lines.append("- Pause any expansion or non-essential actions")
            lines.append("- Be calm, reassuring, and supportive")
            lines.append("- Keep responses brief and clear")
            lines.append("- Prioritize James's wellbeing over tasks")
            lines.append("- Consider suggesting self-care")
        
        return "\n".join(lines)
    
    def get_state(self) -> CoherenceState:
        """Get current coherence state."""
        return self.state
    
    def get_recent_emotions(self, limit: int = 5) -> List[Dict]:
        """Get recent emotion readings."""
        return [e.to_dict() for e in self.state.recent_emotions[-limit:]]
    
    def reset_to_calm(self):
        """Reset state to calm (e.g., after explicit "I'm fine" signal)."""
        self.state.stress_score = 0.2
        self.state.level = CoherenceLevel.HIGH
        self.state.trend = "improving"
        self._save_state()


# ============================================================================
# SINGLETON
# ============================================================================

_tracker: Optional[CoherenceTracker] = None


def get_coherence_tracker() -> CoherenceTracker:
    """Get or create coherence tracker."""
    global _tracker
    if _tracker is None:
        _tracker = CoherenceTracker()
    return _tracker


def sense_emotion(message: str) -> EmotionReading:
    """Sense emotion from a message."""
    return get_coherence_tracker().sensor.sense(message)


def process_for_coherence(message: str, user_id: str = None) -> Dict[str, Any]:
    """Process a message and update coherence state."""
    return get_coherence_tracker().process_message(message, user_id)


def get_coherence_context() -> str:
    """Get coherence context for system prompt."""
    return get_coherence_tracker().get_coherence_context()









