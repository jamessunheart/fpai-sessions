#!/usr/bin/env python3
"""
Silence Monitor
===============
Monitors silence patterns to detect drift risk.

Key insight: Silence after strain = concern
            Silence after calm = fine

Signals:
- Time since last interaction
- Last known state when silence began
- Pattern of silence (normal rhythm vs. unusual)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger("cis.sensors.silence")

@dataclass
class SilenceSignal:
    hours_silent: float
    last_state: Optional[str]
    last_intensity: Optional[int]
    drift_risk: str  # none, low, medium, high
    should_check_in: bool
    signals: Dict
    source: str = "silence"


class SilenceMonitor:
    """Monitors silence patterns for drift detection."""
    
    def __init__(self, db_path: str = "/opt/fpai/aria/cis.db"):
        self.db_path = db_path
        
        # Concerning states - silence after these is worrying
        self.concerning_states = ["overloaded", "stuck"]
        
        # Thresholds
        self.drift_threshold_hours = 48  # After this, check in if concerning
        self.normal_silence_hours = 24  # Less than this is normal
    
    def _get_last_interaction(self) -> Optional[Dict]:
        """Get the last interaction timestamp and state."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get last state from state_history
            cursor.execute("""
                SELECT state, intensity, confidence, captured_at
                FROM state_history
                ORDER BY captured_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "state": row[0],
                    "intensity": row[1],
                    "confidence": row[2],
                    "timestamp": row[3]
                }
            return None
        except Exception as e:
            logger.debug(f"Could not get last interaction: {e}")
            return None
    
    def _get_intervention_response_rate(self) -> float:
        """Get the rate at which interventions are responded to."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT outcome FROM interventions
                WHERE outcome IS NOT NULL
                ORDER BY delivered_at DESC
                LIMIT 10
            """)
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return 0.5  # Unknown, assume medium
            
            responded = sum(1 for r in rows if r[0] not in ["pending", "no_response"])
            return responded / len(rows)
        except Exception as e:
            logger.debug(f"Could not get response rate: {e}")
            return 0.5
    
    def sense(self) -> SilenceSignal:
        """Sense current silence state and drift risk."""
        signals = {}
        
        last = self._get_last_interaction()
        
        if not last:
            # No history at all
            return SilenceSignal(
                hours_silent=0,
                last_state=None,
                last_intensity=None,
                drift_risk="none",
                should_check_in=False,
                signals={"no_history": True}
            )
        
        # Calculate hours since last interaction
        try:
            last_time = datetime.fromisoformat(last["timestamp"])
            hours_silent = (datetime.now() - last_time).total_seconds() / 3600
        except:
            hours_silent = 0
        
        signals["hours_silent"] = round(hours_silent, 1)
        signals["last_state"] = last["state"]
        signals["last_intensity"] = last["intensity"]
        
        # Determine drift risk
        drift_risk = "none"
        should_check_in = False
        
        # Long silence after concerning state = high drift risk
        if hours_silent >= self.drift_threshold_hours:
            if last["state"] in self.concerning_states:
                drift_risk = "high"
                should_check_in = True
            elif last["intensity"] and last["intensity"] >= 4:
                drift_risk = "medium"
                should_check_in = True
            else:
                drift_risk = "low"
        elif hours_silent >= self.normal_silence_hours:
            if last["state"] in self.concerning_states:
                drift_risk = "medium"
            else:
                drift_risk = "low"
        
        # Check response rate - if they don't respond, don't check in
        response_rate = self._get_intervention_response_rate()
        signals["response_rate"] = response_rate
        
        if response_rate < 0.3:
            # They often don't respond - be more cautious
            should_check_in = False
            signals["reason"] = "low_response_rate"
        
        return SilenceSignal(
            hours_silent=hours_silent,
            last_state=last["state"],
            last_intensity=last["intensity"],
            drift_risk=drift_risk,
            should_check_in=should_check_in,
            signals=signals
        )


# Singleton
_monitor: Optional[SilenceMonitor] = None

def get_silence_monitor() -> SilenceMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SilenceMonitor()
    return _monitor

def sense_silence() -> SilenceSignal:
    """Sense current silence state."""
    return get_silence_monitor().sense()








