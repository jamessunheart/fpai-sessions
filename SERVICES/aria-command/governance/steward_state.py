"""
STEWARD STATE - James's Coherence Tracking
==========================================

The steward (James) is the coherent node at the center of Apprentice OS.
This module tracks his state: coherence, stress, decision quality, and capacity.

When the steward's coherence drops below baseline, the system pauses expansion.
When stress is high, no new complexity is added.

The system exists to serve the steward's flourishing, not the other way around.
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

logger = logging.getLogger("aria.governance.steward_state")


@dataclass
class StewardMetrics:
    """Current metrics for the steward (James)."""
    
    # Core metrics (0-100 scale)
    coherence_score: float = 70.0      # Clarity, regulation, sustainable pace
    stress_level: float = 40.0         # Current pressure/tension
    decision_quality: float = 0.75     # Recent decision outcomes (0-1)
    energy_level: float = 70.0         # Available capacity
    
    # Baselines (personalized to James)
    coherence_baseline: float = 65.0   # Personal baseline coherence
    stress_baseline: float = 35.0      # Personal baseline stress
    
    # Trends
    coherence_trend: str = "stable"    # increasing, stable, decreasing
    stress_trend: str = "stable"       # increasing, stable, decreasing
    
    # Capacity indicators
    available_capacity: float = 0.6    # 0-1, how much room for new things
    complexity_tolerance: float = 0.5  # 0-1, ability to handle complexity now
    
    # Timestamps
    last_updated: datetime = field(default_factory=datetime.now)
    last_check_in: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["last_updated"] = self.last_updated.isoformat()
        if self.last_check_in:
            d["last_check_in"] = self.last_check_in.isoformat()
        return d
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StewardMetrics":
        if "last_updated" in d and isinstance(d["last_updated"], str):
            d["last_updated"] = datetime.fromisoformat(d["last_updated"])
        if "last_check_in" in d and isinstance(d["last_check_in"], str):
            d["last_check_in"] = datetime.fromisoformat(d["last_check_in"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
    
    @property
    def is_coherent(self) -> bool:
        """Is coherence at or above baseline?"""
        return self.coherence_score >= self.coherence_baseline
    
    @property
    def is_stressed(self) -> bool:
        """Is stress significantly above baseline?"""
        return self.stress_level > self.stress_baseline + 20
    
    @property
    def can_take_complexity(self) -> bool:
        """Is there capacity for new complexity?"""
        return (
            self.is_coherent and 
            not self.is_stressed and 
            self.available_capacity > 0.3 and
            self.complexity_tolerance > 0.3
        )
    
    @property
    def needs_pause(self) -> bool:
        """Should expansion be paused?"""
        return (
            not self.is_coherent or 
            self.stress_level > 70 or
            self.coherence_trend == "decreasing"
        )


class StewardState:
    """
    Manager for the steward's state.
    
    Tracks James's coherence, stress, and capacity over time.
    Provides the data needed for governance decisions.
    """
    
    def __init__(self, state_dir: str = None):
        """Initialize the steward state tracker."""
        if state_dir is None:
            state_dir = os.environ.get(
                "ARIA_STATE_DIR", 
                "/opt/fpai/aria-command/state"
            )
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.state_dir / "steward_state.json"
        self.db_path = self.state_dir / "steward_history.db"
        
        self._init_db()
        self.metrics = self._load_state()
    
    def _init_db(self):
        """Initialize the history database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS steward_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    coherence_score REAL,
                    stress_level REAL,
                    decision_quality REAL,
                    energy_level REAL,
                    coherence_trend TEXT,
                    stress_trend TEXT,
                    notes TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS steward_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT,
                    impact_coherence REAL,
                    impact_stress REAL
                )
            """)
            conn.commit()
    
    def _load_state(self) -> StewardMetrics:
        """Load the current state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                return StewardMetrics.from_dict(data)
            except Exception as e:
                logger.error(f"Error loading steward state: {e}")
        return StewardMetrics()
    
    def _save_state(self):
        """Save the current state to disk."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.metrics.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving steward state: {e}")
    
    def _record_history(self, notes: str = None):
        """Record current state to history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO steward_history (
                        timestamp, coherence_score, stress_level,
                        decision_quality, energy_level, coherence_trend,
                        stress_trend, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    self.metrics.coherence_score,
                    self.metrics.stress_level,
                    self.metrics.decision_quality,
                    self.metrics.energy_level,
                    self.metrics.coherence_trend,
                    self.metrics.stress_trend,
                    notes
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error recording steward history: {e}")
    
    def get_metrics(self) -> StewardMetrics:
        """Get current steward metrics."""
        return self.metrics
    
    def update_coherence(self, score: float, reason: str = None):
        """
        Update coherence score.
        
        Should be called when:
        - Steward reports feeling clear/unclear
        - Decision quality indicators change
        - Significant life events affect clarity
        """
        old_score = self.metrics.coherence_score
        self.metrics.coherence_score = max(0, min(100, score))
        
        # Update trend
        if score > old_score + 5:
            self.metrics.coherence_trend = "increasing"
        elif score < old_score - 5:
            self.metrics.coherence_trend = "decreasing"
        else:
            self.metrics.coherence_trend = "stable"
        
        # Update capacity based on coherence
        self.metrics.available_capacity = max(0, (score - 40) / 60)
        
        self.metrics.last_updated = datetime.now()
        self._save_state()
        self._record_history(f"Coherence updated: {reason}" if reason else None)
        
        logger.info(f"Steward coherence updated: {old_score:.1f} → {score:.1f} ({reason})")
        
        # Check if we need to pause
        if self.metrics.needs_pause:
            logger.warning("STEWARD NEEDS PAUSE - coherence below baseline or declining")
    
    def update_stress(self, level: float, reason: str = None):
        """
        Update stress level.
        
        Should be called when:
        - Steward reports stress
        - System detects stress indicators
        - Significant pressure events occur
        """
        old_level = self.metrics.stress_level
        self.metrics.stress_level = max(0, min(100, level))
        
        # Update trend
        if level > old_level + 10:
            self.metrics.stress_trend = "increasing"
        elif level < old_level - 10:
            self.metrics.stress_trend = "decreasing"
        else:
            self.metrics.stress_trend = "stable"
        
        # Update complexity tolerance based on stress
        self.metrics.complexity_tolerance = max(0, (80 - level) / 60)
        
        self.metrics.last_updated = datetime.now()
        self._save_state()
        self._record_history(f"Stress updated: {reason}" if reason else None)
        
        logger.info(f"Steward stress updated: {old_level:.1f} → {level:.1f} ({reason})")
        
        # Alert if high stress
        if level > 70:
            logger.warning(f"HIGH STEWARD STRESS ({level}) - blocking new complexity")
    
    def update_decision_quality(self, quality: float, decision_desc: str = None):
        """Update decision quality indicator."""
        # Weighted average with recent decisions
        old_quality = self.metrics.decision_quality
        self.metrics.decision_quality = (old_quality * 0.7 + quality * 0.3)
        self.metrics.last_updated = datetime.now()
        self._save_state()
        
        if decision_desc:
            self._record_history(f"Decision quality: {quality:.2f} for '{decision_desc}'")
    
    def check_in(
        self,
        coherence: float = None,
        stress: float = None,
        energy: float = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        Full check-in from the steward.
        
        This is for James to report his current state directly.
        Returns system recommendations based on the check-in.
        """
        if coherence is not None:
            self.update_coherence(coherence, notes)
        if stress is not None:
            self.update_stress(stress, notes)
        if energy is not None:
            self.metrics.energy_level = max(0, min(100, energy))
        
        self.metrics.last_check_in = datetime.now()
        self._save_state()
        self._record_history(f"Check-in: {notes}" if notes else "Routine check-in")
        
        # Generate recommendations
        recommendations = []
        
        if self.metrics.needs_pause:
            recommendations.append({
                "type": "pause",
                "priority": "high",
                "message": "Consider pausing expansion. Coherence needs attention."
            })
        
        if self.metrics.is_stressed:
            recommendations.append({
                "type": "reduce_load",
                "priority": "high",
                "message": f"Stress ({self.metrics.stress_level:.0f}) is elevated. No new complexity recommended."
            })
        
        if not self.metrics.can_take_complexity:
            recommendations.append({
                "type": "hold_complexity",
                "priority": "medium",
                "message": "Current capacity doesn't support new complexity."
            })
        
        if self.metrics.coherence_trend == "increasing":
            recommendations.append({
                "type": "opportunity",
                "priority": "low",
                "message": "Coherence improving. Good time for strategic decisions."
            })
        
        return {
            "metrics": self.metrics.to_dict(),
            "can_expand": self.metrics.is_coherent and not self.metrics.needs_pause,
            "can_take_complexity": self.metrics.can_take_complexity,
            "recommendations": recommendations
        }
    
    def get_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get steward history for the past N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM steward_history
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (cutoff,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching steward history: {e}")
            return []
    
    def record_event(
        self,
        event_type: str,
        description: str,
        impact_coherence: float = 0,
        impact_stress: float = 0
    ):
        """Record an event that affects the steward."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO steward_events (
                        timestamp, event_type, description,
                        impact_coherence, impact_stress
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    event_type,
                    description,
                    impact_coherence,
                    impact_stress
                ))
                conn.commit()
            
            # Auto-update metrics based on event impact
            if impact_coherence != 0:
                new_coherence = self.metrics.coherence_score + impact_coherence
                self.update_coherence(new_coherence, f"Event: {event_type}")
            
            if impact_stress != 0:
                new_stress = self.metrics.stress_level + impact_stress
                self.update_stress(new_stress, f"Event: {event_type}")
                
        except Exception as e:
            logger.error(f"Error recording steward event: {e}")


# Singleton instance
_steward_state: Optional[StewardState] = None


def get_steward_state() -> StewardState:
    """Get the singleton StewardState instance."""
    global _steward_state
    if _steward_state is None:
        _steward_state = StewardState()
    return _steward_state


def update_steward_state(**kwargs) -> Dict[str, Any]:
    """
    Convenience function to update and check steward state.
    
    Usage:
        result = update_steward_state(
            coherence=75,
            stress=45,
            notes="After morning meditation"
        )
        if result["can_expand"]:
            print("Good to proceed with new initiatives")
    """
    return get_steward_state().check_in(**kwargs)


