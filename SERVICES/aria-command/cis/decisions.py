#!/usr/bin/env python3
"""
CIS Decision Engine - Learning-Aware
=====================================
Makes intervention decisions using learned patterns.

Integrates:
- Action weights (learned from outcomes)
- Timing preferences (learned from response patterns)
- Restraint rules (adapted from behavior)
"""
import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger("cis.decisions")

@dataclass
class Decision:
    type: str  # silence, stabilize, disrupt, execute, ask
    action_id: Optional[str]
    action_key: Optional[str]
    confidence: float
    reason: str
    timing_score: float
    action_score: float


class LearningAwareDecisionEngine:
    """
    Decision engine that uses learned patterns.
    """
    
    def __init__(self, db_path: str = "/opt/fpai/aria/cis.db"):
        self.db_path = db_path
        
        # Base intrusion costs
        self.INTRUSION_COST = {
            "calm": 0.8,
            "busy": 0.5,
            "overloaded": 0.3,
            "stuck": 0.2,
            "open": 0.1
        }
    
    def get_timing_score(self, user_id: str = "james") -> float:
        """Get current timing score based on learned preferences."""
        try:
            from cis.learning import get_timing_preference
            hour = datetime.now().hour
            return get_timing_preference(hour, user_id)
        except Exception as e:
            logger.debug(f"Could not get timing preference: {e}")
            return 0.5  # Neutral
    
    def get_action_score(self, action_key: str, state: str, user_id: str = "james") -> float:
        """Get action score based on learned weights."""
        try:
            from cis.learning import get_action_weight
            return get_action_weight(action_key, state, user_id)
        except Exception as e:
            logger.debug(f"Could not get action weight: {e}")
            return 1.0  # Neutral
    
    def should_intervene(self, state: str, intensity: int, confidence: str, user_id: str = "james") -> tuple:
        """
        Decide if we should intervene at all.
        
        Returns: (should_intervene, reason)
        """
        # Get timing score
        timing_score = self.get_timing_score(user_id)
        
        # If learned timing is bad (<0.3), don't intervene
        if timing_score < 0.3:
            return False, f"Bad timing (score={timing_score:.2f})"
        
        # Base intrusion cost
        intrusion_cost = self.INTRUSION_COST.get(state, 0.5)
        
        # Adjust for intensity
        if intensity >= 4:
            intrusion_cost *= 0.7  # Lower bar for high intensity
        
        # Confidence multiplier
        conf_mult = {"low": 0.3, "medium": 0.6, "high": 1.0}.get(confidence, 0.5)
        
        # Calculate intervention score
        intervention_score = conf_mult * timing_score
        
        if intervention_score > intrusion_cost:
            return True, f"Score {intervention_score:.2f} > cost {intrusion_cost:.2f}"
        else:
            return False, f"Score {intervention_score:.2f} <= cost {intrusion_cost:.2f}"
    
    def choose_action(self, state: str, intensity: int, user_id: str = "james") -> Optional[dict]:
        """
        Choose the best action for current state using learned weights.
        """
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get eligible actions for this state
            cursor.execute("""
                SELECT id, action_key, category, instruction, effective_states
                FROM actions
                WHERE active = 1
            """)
            
            candidates = []
            for row in cursor.fetchall():
                action_id, action_key, category, instruction, effective_states = row
                
                # Check if action is effective for this state
                try:
                    states = eval(effective_states) if effective_states else []
                    if state not in states and states:
                        continue
                except:
                    pass
                
                # Get learned weight
                weight = self.get_action_score(action_key, state, user_id)
                
                candidates.append({
                    "id": action_id,
                    "key": action_key,
                    "category": category,
                    "instruction": instruction,
                    "score": weight
                })
            
            conn.close()
            
            if not candidates:
                return None
            
            # Sort by score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            # Return best
            return candidates[0]
            
        except Exception as e:
            logger.error(f"Action selection error: {e}")
            return None
    
    def decide(self, state: str, intensity: int, confidence: str, 
               trigger_type: str, user_id: str = "james") -> Decision:
        """
        Make a complete intervention decision.
        """
        timing_score = self.get_timing_score(user_id)
        
        # First, should we intervene at all?
        should, reason = self.should_intervene(state, intensity, confidence, user_id)
        
        if not should:
            return Decision(
                type="silence",
                action_id=None,
                action_key=None,
                confidence=0.0,
                reason=reason,
                timing_score=timing_score,
                action_score=0.0
            )
        
        # Choose action
        action = self.choose_action(state, intensity, user_id)
        
        if not action:
            return Decision(
                type="silence",
                action_id=None,
                action_key=None,
                confidence=0.0,
                reason="No suitable action found",
                timing_score=timing_score,
                action_score=0.0
            )
        
        return Decision(
            type=action["category"],
            action_id=action["id"],
            action_key=action["key"],
            confidence=action["score"] * timing_score,
            reason=f"Best action for {state}",
            timing_score=timing_score,
            action_score=action["score"]
        )


# Singleton
_engine: Optional[LearningAwareDecisionEngine] = None

def get_decision_engine() -> LearningAwareDecisionEngine:
    global _engine
    if _engine is None:
        _engine = LearningAwareDecisionEngine()
    return _engine

def decide(state: str, intensity: int, confidence: str, 
           trigger_type: str, user_id: str = "james") -> Decision:
    """Make an intervention decision."""
    return get_decision_engine().decide(state, intensity, confidence, trigger_type, user_id)








