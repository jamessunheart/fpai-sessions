"""
PATTERN ENGINE
===============

Recognize recurring failure patterns and predict future failures.

Pattern types:
1. Temporal - "Fails every Monday" or "Fails around 3am"
2. Sequence - "When A fails, B usually fails next"
3. Config - "Port changes cause failures"
4. Correlation - "High memory + slow API = crash"

This enables PROACTIVE healing - fix problems BEFORE they happen.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from .intelligence_db import (
    IntelligenceDB, get_intelligence_db,
    PatternRecord, FailureRecord
)

logger = logging.getLogger("aria.intelligence.patterns")


class PatternType(str, Enum):
    """Types of patterns we can detect."""
    TEMPORAL = "temporal"       # Time-based patterns
    SEQUENCE = "sequence"       # A → B patterns
    CONFIG = "config"           # Config change patterns
    CORRELATION = "correlation" # Multi-factor patterns


@dataclass
class Pattern:
    """A detected failure pattern."""
    id: Optional[int] = None
    pattern_type: PatternType = PatternType.TEMPORAL
    description: str = ""
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    predicted_outcome: str = ""
    confidence: float = 0.0
    occurrence_count: int = 0
    preventive_action: str = ""
    last_triggered: Optional[str] = None
    
    def matches(self, current_state: Dict[str, Any]) -> bool:
        """Check if current state matches trigger conditions."""
        for key, expected in self.trigger_conditions.items():
            actual = current_state.get(key)
            
            if isinstance(expected, dict):
                # Complex condition (e.g., {"gt": 80})
                if "gt" in expected and actual <= expected["gt"]:
                    return False
                if "lt" in expected and actual >= expected["lt"]:
                    return False
                if "eq" in expected and actual != expected["eq"]:
                    return False
                if "contains" in expected and expected["contains"] not in str(actual):
                    return False
            else:
                # Simple equality
                if actual != expected:
                    return False
        
        return True
    
    @classmethod
    def from_record(cls, record: PatternRecord) -> "Pattern":
        return cls(
            id=record.id,
            pattern_type=PatternType(record.pattern_type),
            description=record.description,
            trigger_conditions=json.loads(record.trigger_conditions),
            predicted_outcome=record.predicted_outcome,
            confidence=record.confidence,
            occurrence_count=record.occurrence_count,
            preventive_action=record.preventive_action,
            last_triggered=record.last_triggered
        )


@dataclass
class Prediction:
    """A predicted failure."""
    service: str
    predicted_failure: str
    confidence: float
    pattern: Pattern
    recommended_action: str
    time_estimate: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PatternEngine:
    """
    Detects and uses patterns for prediction.
    
    Process:
    1. Analyze historical failures for patterns
    2. Store discovered patterns
    3. Match current state against patterns
    4. Generate predictions
    5. Recommend preventive actions
    """
    
    def __init__(self, db: IntelligenceDB = None):
        self.db = db or get_intelligence_db()
        self.patterns: List[Pattern] = []
        self._load_patterns()
        logger.info(f"PatternEngine initialized with {len(self.patterns)} patterns")
    
    def _load_patterns(self):
        """Load patterns from database."""
        records = self.db.get_patterns(min_confidence=0.3)
        self.patterns = [Pattern.from_record(r) for r in records]
    
    def detect_patterns(self, days: int = 30) -> List[Pattern]:
        """
        Analyze failure history and detect patterns.
        
        Returns newly discovered patterns.
        """
        failures = self.db.get_recent_failures(days=days)
        
        if len(failures) < 5:
            logger.debug("Not enough failures to detect patterns")
            return []
        
        new_patterns = []
        
        # 1. Detect temporal patterns
        temporal = self._find_temporal_patterns(failures)
        new_patterns.extend(temporal)
        
        # 2. Detect sequence patterns
        sequence = self._find_sequence_patterns(failures)
        new_patterns.extend(sequence)
        
        # 3. Detect config patterns
        config = self._find_config_patterns(failures)
        new_patterns.extend(config)
        
        # Store new patterns
        for pattern in new_patterns:
            record = PatternRecord(
                pattern_type=pattern.pattern_type.value,
                description=pattern.description,
                trigger_conditions=json.dumps(pattern.trigger_conditions),
                predicted_outcome=pattern.predicted_outcome,
                confidence=pattern.confidence,
                occurrence_count=pattern.occurrence_count,
                preventive_action=pattern.preventive_action
            )
            pattern.id = self.db.record_pattern(record)
        
        # Reload patterns
        self._load_patterns()
        
        logger.info(f"Detected {len(new_patterns)} new patterns")
        return new_patterns
    
    def _find_temporal_patterns(self, failures: List[FailureRecord]) -> List[Pattern]:
        """Find time-based patterns."""
        patterns = []
        
        # Group by hour of day
        by_hour = defaultdict(list)
        by_weekday = defaultdict(list)
        
        for f in failures:
            try:
                dt = datetime.fromisoformat(f.timestamp)
                by_hour[dt.hour].append(f)
                by_weekday[dt.weekday()].append(f)
            except Exception:
                continue
        
        # Check for hour patterns
        total = len(failures)
        for hour, hour_failures in by_hour.items():
            ratio = len(hour_failures) / total
            if ratio > 0.3:  # More than 30% happen at this hour
                patterns.append(Pattern(
                    pattern_type=PatternType.TEMPORAL,
                    description=f"Failures cluster around {hour}:00",
                    trigger_conditions={"hour": hour},
                    predicted_outcome=f"Higher failure probability at {hour}:00",
                    confidence=min(0.9, ratio + 0.2),
                    occurrence_count=len(hour_failures),
                    preventive_action=f"Schedule proactive health check at {hour}:00"
                ))
        
        # Check for weekday patterns
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                        "Friday", "Saturday", "Sunday"]
        for weekday, day_failures in by_weekday.items():
            ratio = len(day_failures) / total
            if ratio > 0.25:  # More than 25% on this day
                patterns.append(Pattern(
                    pattern_type=PatternType.TEMPORAL,
                    description=f"Failures more common on {weekday_names[weekday]}",
                    trigger_conditions={"weekday": weekday},
                    predicted_outcome=f"Higher failure probability on {weekday_names[weekday]}",
                    confidence=min(0.85, ratio + 0.15),
                    occurrence_count=len(day_failures),
                    preventive_action=f"Extra monitoring on {weekday_names[weekday]}"
                ))
        
        return patterns
    
    def _find_sequence_patterns(self, failures: List[FailureRecord]) -> List[Pattern]:
        """Find A → B patterns (one failure leads to another)."""
        patterns = []
        
        # Sort by timestamp
        sorted_failures = sorted(failures, key=lambda f: f.timestamp)
        
        # Look for sequences within 10 minutes
        sequences = defaultdict(int)
        
        for i, f1 in enumerate(sorted_failures[:-1]):
            for f2 in sorted_failures[i+1:i+5]:  # Check next 5 failures
                try:
                    t1 = datetime.fromisoformat(f1.timestamp)
                    t2 = datetime.fromisoformat(f2.timestamp)
                    
                    if (t2 - t1).total_seconds() < 600:  # Within 10 minutes
                        if f1.service != f2.service:
                            key = (f1.service, f2.service)
                            sequences[key] += 1
                except Exception:
                    continue
        
        # Find significant sequences
        for (s1, s2), count in sequences.items():
            if count >= 3:  # At least 3 occurrences
                patterns.append(Pattern(
                    pattern_type=PatternType.SEQUENCE,
                    description=f"{s1} failure often followed by {s2} failure",
                    trigger_conditions={"service_failed": s1},
                    predicted_outcome=f"{s2} likely to fail soon",
                    confidence=min(0.85, 0.5 + count * 0.1),
                    occurrence_count=count,
                    preventive_action=f"When {s1} fails, preemptively check {s2}"
                ))
        
        return patterns
    
    def _find_config_patterns(self, failures: List[FailureRecord]) -> List[Pattern]:
        """Find patterns related to configuration issues."""
        patterns = []
        
        # Look for config-related root causes
        config_failures = [f for f in failures if "config" in f.root_cause.lower()]
        
        if len(config_failures) >= 2:
            # Group by service
            by_service = defaultdict(list)
            for f in config_failures:
                by_service[f.service].append(f)
            
            for service, service_failures in by_service.items():
                if len(service_failures) >= 2:
                    patterns.append(Pattern(
                        pattern_type=PatternType.CONFIG,
                        description=f"{service} has recurring config issues",
                        trigger_conditions={"service": service, "category": "config"},
                        predicted_outcome=f"{service} config drift likely",
                        confidence=0.75,
                        occurrence_count=len(service_failures),
                        preventive_action=f"Add config validation for {service}"
                    ))
        
        return patterns
    
    def predict_failures(self, current_state: Dict[str, Any]) -> List[Prediction]:
        """
        Predict potential failures based on current state.
        
        Args:
            current_state: Current system state including:
                - hour: Current hour
                - weekday: Current day (0-6)
                - service_failed: Recently failed service
                - memory_percent: Memory usage
                - etc.
        
        Returns:
            List of predicted failures with recommendations
        """
        predictions = []
        
        # Add current time to state if not present
        now = datetime.now()
        if "hour" not in current_state:
            current_state["hour"] = now.hour
        if "weekday" not in current_state:
            current_state["weekday"] = now.weekday()
        
        for pattern in self.patterns:
            if pattern.matches(current_state):
                # Update pattern occurrence
                if pattern.id:
                    self.db.update_pattern_occurrence(pattern.id)
                
                predictions.append(Prediction(
                    service=pattern.predicted_outcome.split()[0] if pattern.predicted_outcome else "unknown",
                    predicted_failure=pattern.predicted_outcome,
                    confidence=pattern.confidence,
                    pattern=pattern,
                    recommended_action=pattern.preventive_action
                ))
        
        # Sort by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        if predictions:
            logger.info(f"Generated {len(predictions)} predictions")
        
        return predictions
    
    def get_high_confidence_patterns(self, min_confidence: float = 0.7) -> List[Pattern]:
        """Get patterns above a confidence threshold."""
        return [p for p in self.patterns if p.confidence >= min_confidence]
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get pattern statistics."""
        by_type = defaultdict(int)
        for p in self.patterns:
            by_type[p.pattern_type.value] += 1
        
        return {
            "total_patterns": len(self.patterns),
            "by_type": dict(by_type),
            "high_confidence": len([p for p in self.patterns if p.confidence > 0.7]),
            "avg_confidence": sum(p.confidence for p in self.patterns) / len(self.patterns) if self.patterns else 0,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[PatternEngine] = None


def get_pattern_engine() -> PatternEngine:
    """Get or create the pattern engine instance."""
    global _engine
    if _engine is None:
        _engine = PatternEngine()
    return _engine


def detect_patterns(days: int = 30) -> List[Pattern]:
    """Convenience function to detect patterns."""
    return get_pattern_engine().detect_patterns(days)


def predict_failures(current_state: Dict[str, Any]) -> List[Prediction]:
    """Convenience function to predict failures."""
    return get_pattern_engine().predict_failures(current_state)









