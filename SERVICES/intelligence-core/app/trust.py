"""
Trust Scoring System - Graduated Autonomy
==========================================

Trust is earned, not given. This module tracks system performance
and gates autonomy based on proven track record.

Trust Levels:
- suggest_only: Default - recommend only, human approves
- small_auto: 60%+ accuracy, 50+ suggestions - auto up to $100
- medium_auto: 70%+ accuracy, 200+ suggestions - auto up to $1000  
- full_auto: 80%+ accuracy, 500+ suggestions - full autonomy with kill switch

Safety Features:
- Automatic pause on 3 consecutive failures
- Kill switch for emergency stop
- All autonomous actions logged
- DAILY COST CAP - Maximum spend per day
- ROLLBACK REQUIRED - Only act if backup exists
"""

import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger("intelligence.trust")

# Persistence path
TRUST_DATA_PATH = os.getenv("TRUST_DATA_PATH", "/opt/fpai/data/trust_state.json")

# Safety Configuration
DEFAULT_DAILY_CAP = float(os.getenv("DAILY_COST_CAP", "50.0"))  # $50/day default
REQUIRE_ROLLBACK = os.getenv("REQUIRE_ROLLBACK", "true").lower() == "true"


class AutonomyLevel(str, Enum):
    SUGGEST_ONLY = "suggest_only"  # Default, human approves everything
    SMALL_AUTO = "small_auto"      # Can auto-execute up to $100 value
    MEDIUM_AUTO = "medium_auto"    # Can auto-execute up to $1000 value
    FULL_AUTO = "full_auto"        # Full autonomy with kill switch


@dataclass
class AutonomyTierRequirements:
    """Requirements to reach each autonomy tier."""
    min_accuracy: float
    min_suggestions: int
    max_value: float  # Maximum value of autonomous action
    description: str


TIER_REQUIREMENTS = {
    AutonomyLevel.SUGGEST_ONLY: AutonomyTierRequirements(
        min_accuracy=0.0,
        min_suggestions=0,
        max_value=0.0,
        description="Recommend only, human approves all actions"
    ),
    AutonomyLevel.SMALL_AUTO: AutonomyTierRequirements(
        min_accuracy=0.6,
        min_suggestions=50,
        max_value=100.0,
        description="Auto-execute actions valued up to $100"
    ),
    AutonomyLevel.MEDIUM_AUTO: AutonomyTierRequirements(
        min_accuracy=0.7,
        min_suggestions=200,
        max_value=1000.0,
        description="Auto-execute actions valued up to $1,000"
    ),
    AutonomyLevel.FULL_AUTO: AutonomyTierRequirements(
        min_accuracy=0.8,
        min_suggestions=500,
        max_value=float('inf'),
        description="Full autonomy with emergency kill switch"
    ),
}


@dataclass
class ActionRecord:
    """Record of an autonomous action taken."""
    action_id: str
    action_type: str
    description: str
    value_usd: float
    confidence: float
    executed_at: str
    outcome: Optional[str] = None  # positive, negative, neutral, pending
    outcome_recorded_at: Optional[str] = None


@dataclass
class TrustState:
    """Current state of the trust system."""
    # Core metrics
    suggestions_made: int = 0
    suggestions_accepted: int = 0
    outcomes_positive: int = 0
    outcomes_negative: int = 0
    outcomes_neutral: int = 0
    
    # Autonomous actions
    auto_actions_taken: int = 0
    auto_actions_successful: int = 0
    auto_actions_failed: int = 0
    
    # Safety state
    consecutive_failures: int = 0
    is_paused: bool = False
    pause_reason: Optional[str] = None
    paused_at: Optional[str] = None
    
    # Manual overrides
    manual_trust_adjustment: float = 0.0  # -1 to +1, applied as modifier
    last_manual_adjustment_at: Optional[str] = None
    manual_autonomy_override: Optional[str] = None  # If set, use this level instead of calculated
    
    # DAILY COST CAP - Safety guardrail
    daily_cost_cap: float = DEFAULT_DAILY_CAP  # Max spend per day
    daily_spend_today: float = 0.0  # Spent so far today
    daily_spend_reset_date: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    
    # ROLLBACK REQUIREMENT - Only act if backup exists
    require_rollback: bool = REQUIRE_ROLLBACK
    
    # History
    action_history: List[Dict] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def total_outcomes(self) -> int:
        return self.outcomes_positive + self.outcomes_negative + self.outcomes_neutral
    
    @property
    def accuracy(self) -> float:
        """What % of accepted suggestions had positive outcomes."""
        total = self.outcomes_positive + self.outcomes_negative
        if total == 0:
            return 0.5  # Default assumption
        return self.outcomes_positive / total
    
    @property
    def acceptance_rate(self) -> float:
        """What % of suggestions were accepted."""
        if self.suggestions_made == 0:
            return 0.0
        return self.suggestions_accepted / self.suggestions_made
    
    @property
    def auto_success_rate(self) -> float:
        """Success rate of autonomous actions."""
        total = self.auto_actions_successful + self.auto_actions_failed
        if total == 0:
            return 0.0
        return self.auto_actions_successful / total
    
    @property
    def trust_score(self) -> float:
        """
        Overall trust score 0-1.
        
        Composite of:
        - Accuracy (60% weight)
        - Volume of data (20% weight)
        - Auto success rate (20% weight)
        - Manual adjustment
        """
        # Accuracy component (0-1)
        accuracy_component = self.accuracy * 0.6
        
        # Volume component - more data = more trust (log scale)
        import math
        volume = min(1.0, math.log10(max(1, self.suggestions_made)) / 3)  # 1000 suggestions = 1.0
        volume_component = volume * 0.2
        
        # Auto success component
        auto_component = self.auto_success_rate * 0.2 if self.auto_actions_taken > 0 else 0.1
        
        base_score = accuracy_component + volume_component + auto_component
        
        # Apply manual adjustment (clamped)
        adjusted = base_score + self.manual_trust_adjustment * 0.2
        
        return max(0.0, min(1.0, adjusted))
    
    @property
    def autonomy_level(self) -> AutonomyLevel:
        """Current autonomy level based on metrics or manual override."""
        if self.is_paused:
            return AutonomyLevel.SUGGEST_ONLY
        
        # Check for manual override
        if self.manual_autonomy_override:
            try:
                return AutonomyLevel(self.manual_autonomy_override)
            except ValueError:
                pass  # Invalid override, use calculated
        
        accuracy = self.accuracy
        suggestions = self.suggestions_made
        
        # Check tiers from highest to lowest
        if accuracy >= 0.8 and suggestions >= 500:
            return AutonomyLevel.FULL_AUTO
        elif accuracy >= 0.7 and suggestions >= 200:
            return AutonomyLevel.MEDIUM_AUTO
        elif accuracy >= 0.6 and suggestions >= 50:
            return AutonomyLevel.SMALL_AUTO
        else:
            return AutonomyLevel.SUGGEST_ONLY
    
    def can_auto_execute(self, action_value: float, has_rollback: bool = False) -> tuple:
        """
        Check if an action can be auto-executed given current trust level and safety limits.
        
        Returns: (can_execute: bool, reason: str)
        """
        # Check if paused
        if self.is_paused:
            return False, "System is paused"
        
        # Check autonomy level
        level = self.autonomy_level
        requirements = TIER_REQUIREMENTS[level]
        
        if action_value > requirements.max_value:
            return False, f"Action value ${action_value} exceeds tier limit ${requirements.max_value}"
        
        # Check daily cost cap
        self._reset_daily_spend_if_needed()
        if self.daily_spend_today + action_value > self.daily_cost_cap:
            remaining = self.daily_cost_cap - self.daily_spend_today
            return False, f"Would exceed daily cap. Remaining: ${remaining:.2f}"
        
        # Check rollback requirement
        if self.require_rollback and not has_rollback:
            return False, "Action requires backup/rollback capability"
        
        return True, "OK"
    
    def _reset_daily_spend_if_needed(self):
        """Reset daily spend counter if it's a new day."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.daily_spend_reset_date != today:
            self.daily_spend_today = 0.0
            self.daily_spend_reset_date = today
    
    def record_spend(self, amount: float):
        """Record spending against daily cap."""
        self._reset_daily_spend_if_needed()
        self.daily_spend_today += amount
    
    def get_daily_budget_status(self) -> Dict[str, Any]:
        """Get current daily budget status."""
        self._reset_daily_spend_if_needed()
        return {
            "daily_cap": self.daily_cost_cap,
            "spent_today": self.daily_spend_today,
            "remaining": max(0, self.daily_cost_cap - self.daily_spend_today),
            "reset_date": self.daily_spend_reset_date,
            "percent_used": (self.daily_spend_today / self.daily_cost_cap * 100) if self.daily_cost_cap > 0 else 0
        }
    
    def get_next_tier_progress(self) -> Dict[str, Any]:
        """Get progress towards next autonomy tier."""
        current = self.autonomy_level
        
        # Determine next tier
        tier_order = [
            AutonomyLevel.SUGGEST_ONLY,
            AutonomyLevel.SMALL_AUTO,
            AutonomyLevel.MEDIUM_AUTO,
            AutonomyLevel.FULL_AUTO
        ]
        
        current_idx = tier_order.index(current)
        if current_idx >= len(tier_order) - 1:
            return {
                "current_tier": current.value,
                "next_tier": None,
                "at_max_tier": True
            }
        
        next_tier = tier_order[current_idx + 1]
        requirements = TIER_REQUIREMENTS[next_tier]
        
        accuracy_progress = min(1.0, self.accuracy / requirements.min_accuracy)
        volume_progress = min(1.0, self.suggestions_made / requirements.min_suggestions)
        
        return {
            "current_tier": current.value,
            "next_tier": next_tier.value,
            "accuracy_required": requirements.min_accuracy,
            "accuracy_current": self.accuracy,
            "accuracy_progress": accuracy_progress,
            "suggestions_required": requirements.min_suggestions,
            "suggestions_current": self.suggestions_made,
            "volume_progress": volume_progress,
            "overall_progress": (accuracy_progress + volume_progress) / 2,
            "at_max_tier": False
        }


class TrustManager:
    """
    Manages trust state, autonomy levels, and safety mechanisms.
    """
    
    def __init__(self):
        self.state = TrustState()
        self._load_state()
    
    def _load_state(self):
        """Load trust state from disk."""
        try:
            path = Path(TRUST_DATA_PATH)
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    self.state = TrustState(
                        suggestions_made=data.get("suggestions_made", 0),
                        suggestions_accepted=data.get("suggestions_accepted", 0),
                        outcomes_positive=data.get("outcomes_positive", 0),
                        outcomes_negative=data.get("outcomes_negative", 0),
                        outcomes_neutral=data.get("outcomes_neutral", 0),
                        auto_actions_taken=data.get("auto_actions_taken", 0),
                        auto_actions_successful=data.get("auto_actions_successful", 0),
                        auto_actions_failed=data.get("auto_actions_failed", 0),
                        consecutive_failures=data.get("consecutive_failures", 0),
                        is_paused=data.get("is_paused", False),
                        pause_reason=data.get("pause_reason"),
                        paused_at=data.get("paused_at"),
                        manual_trust_adjustment=data.get("manual_trust_adjustment", 0.0),
                        last_manual_adjustment_at=data.get("last_manual_adjustment_at"),
                        daily_cost_cap=data.get("daily_cost_cap", DEFAULT_DAILY_CAP),
                        daily_spend_today=data.get("daily_spend_today", 0.0),
                        daily_spend_reset_date=data.get("daily_spend_reset_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                        require_rollback=data.get("require_rollback", REQUIRE_ROLLBACK),
                        action_history=data.get("action_history", [])[-100:],  # Keep last 100
                        last_updated=data.get("last_updated", datetime.now(timezone.utc).isoformat())
                    )
                    logger.info(f"Loaded trust state: {self.state.autonomy_level.value}")
                    logger.info(f"Daily cap: ${self.state.daily_cost_cap}, Require rollback: {self.state.require_rollback}")
        except Exception as e:
            logger.warning(f"Failed to load trust state: {e}, starting fresh")
    
    def _save_state(self):
        """Persist trust state to disk."""
        try:
            path = Path(TRUST_DATA_PATH)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            self.state.last_updated = datetime.now(timezone.utc).isoformat()
            
            with open(path, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save trust state: {e}")
    
    def record_suggestion(self, accepted: bool):
        """Record that a suggestion was made and whether it was accepted."""
        self.state.suggestions_made += 1
        if accepted:
            self.state.suggestions_accepted += 1
        self._save_state()
    
    def record_outcome(self, outcome: str):
        """Record the outcome of an accepted suggestion."""
        if outcome == "positive":
            self.state.outcomes_positive += 1
            self.state.consecutive_failures = 0
        elif outcome == "negative":
            self.state.outcomes_negative += 1
            self.state.consecutive_failures += 1
            self._check_auto_pause()
        else:
            self.state.outcomes_neutral += 1
        
        self._save_state()
    
    def record_auto_action(
        self,
        action_id: str,
        action_type: str,
        description: str,
        value_usd: float,
        confidence: float,
        has_rollback: bool = False
    ) -> tuple:
        """
        Record an autonomous action attempt.
        Returns (allowed: bool, reason: str)
        """
        # Check all safety conditions
        can_execute, reason = self.state.can_auto_execute(value_usd, has_rollback)
        
        if not can_execute:
            logger.warning(f"Auto action blocked: {reason}")
            return False, reason
        
        action = ActionRecord(
            action_id=action_id,
            action_type=action_type,
            description=description,
            value_usd=value_usd,
            confidence=confidence,
            executed_at=datetime.now(timezone.utc).isoformat()
        )
        
        self.state.auto_actions_taken += 1
        self.state.action_history.append(asdict(action))
        
        # Record spend against daily cap
        self.state.record_spend(value_usd)
        
        # Keep only last 100 actions
        if len(self.state.action_history) > 100:
            self.state.action_history = self.state.action_history[-100:]
        
        self._save_state()
        logger.info(f"Auto action recorded: {action_id} (${value_usd})")
        
        return True, "OK"
    
    def record_auto_action_outcome(self, action_id: str, outcome: str):
        """Record the outcome of an autonomous action."""
        # Find and update the action
        for action in reversed(self.state.action_history):
            if action.get("action_id") == action_id:
                action["outcome"] = outcome
                action["outcome_recorded_at"] = datetime.now(timezone.utc).isoformat()
                break
        
        if outcome == "positive":
            self.state.auto_actions_successful += 1
            self.state.consecutive_failures = 0
        elif outcome == "negative":
            self.state.auto_actions_failed += 1
            self.state.consecutive_failures += 1
            self._check_auto_pause()
        
        self._save_state()
    
    def _check_auto_pause(self):
        """Check if system should auto-pause due to consecutive failures."""
        if self.state.consecutive_failures >= 3:
            self.pause("Automatic pause: 3 consecutive negative outcomes")
    
    def pause(self, reason: str = "Manual pause"):
        """Pause all autonomous actions."""
        self.state.is_paused = True
        self.state.pause_reason = reason
        self.state.paused_at = datetime.now(timezone.utc).isoformat()
        self._save_state()
        logger.warning(f"System PAUSED: {reason}")
    
    def resume(self):
        """Resume autonomous actions."""
        self.state.is_paused = False
        self.state.pause_reason = None
        self.state.paused_at = None
        self.state.consecutive_failures = 0  # Reset failure counter
        self._save_state()
        logger.info("System RESUMED")
    
    def adjust_trust(self, adjustment: float, reason: str = None):
        """
        Manually adjust trust score.
        
        adjustment: -1 to +1 (negative = demote, positive = promote)
        """
        self.state.manual_trust_adjustment = max(-1.0, min(1.0, adjustment))
        self.state.last_manual_adjustment_at = datetime.now(timezone.utc).isoformat()
        self._save_state()
        logger.info(f"Trust manually adjusted by {adjustment}: {reason}")
    
    def set_daily_cap(self, cap: float):
        """Set the daily cost cap for autonomous actions."""
        self.state.daily_cost_cap = max(0, cap)
        self._save_state()
        logger.info(f"Daily cap set to ${cap}")
    
    def set_require_rollback(self, require: bool):
        """Set whether rollback is required for autonomous actions."""
        self.state.require_rollback = require
        self._save_state()
        logger.info(f"Require rollback set to {require}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get complete trust status for dashboard."""
        # Reset daily spend if needed
        self.state._reset_daily_spend_if_needed()
        
        return {
            "trust_score": round(self.state.trust_score, 3),
            "autonomy_level": self.state.autonomy_level.value,
            "tier_description": TIER_REQUIREMENTS[self.state.autonomy_level].description,
            "max_auto_value": TIER_REQUIREMENTS[self.state.autonomy_level].max_value,
            
            "metrics": {
                "suggestions_made": self.state.suggestions_made,
                "suggestions_accepted": self.state.suggestions_accepted,
                "acceptance_rate": round(self.state.acceptance_rate, 3),
                "accuracy": round(self.state.accuracy, 3),
                "outcomes": {
                    "positive": self.state.outcomes_positive,
                    "negative": self.state.outcomes_negative,
                    "neutral": self.state.outcomes_neutral
                }
            },
            
            "autonomous_actions": {
                "total": self.state.auto_actions_taken,
                "successful": self.state.auto_actions_successful,
                "failed": self.state.auto_actions_failed,
                "success_rate": round(self.state.auto_success_rate, 3)
            },
            
            "safety": {
                "is_paused": self.state.is_paused,
                "pause_reason": self.state.pause_reason,
                "paused_at": self.state.paused_at,
                "consecutive_failures": self.state.consecutive_failures
            },
            
            # Daily cost cap settings
            "daily_budget": {
                "daily_cap": self.state.daily_cost_cap,
                "spent_today": round(self.state.daily_spend_today, 2),
                "remaining": round(max(0, self.state.daily_cost_cap - self.state.daily_spend_today), 2),
                "percent_used": round((self.state.daily_spend_today / self.state.daily_cost_cap * 100) if self.state.daily_cost_cap > 0 else 0, 1),
                "reset_date": self.state.daily_spend_reset_date
            },
            
            # Rollback requirement
            "require_rollback": self.state.require_rollback,
            
            "next_tier": self.state.get_next_tier_progress(),
            "recent_actions": self.state.action_history[-10:],
            "last_updated": self.state.last_updated
        }


# Singleton instance
_trust_manager: Optional[TrustManager] = None


def get_trust_manager() -> TrustManager:
    """Get singleton trust manager instance."""
    global _trust_manager
    if _trust_manager is None:
        _trust_manager = TrustManager()
    return _trust_manager

