"""
Confidence Engine - Calculates confidence scores for actions.

Combines agent consensus, historical success, risk level,
and user trust to determine action tiers.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("aria.core.confidence")


class ActionTier(Enum):
    """Action tiers based on confidence."""
    TIER_1 = 1  # Auto-execute (90%+)
    TIER_2 = 2  # Preview + Quick approve (70-89%)
    TIER_3 = 3  # Detailed review (50-69%)
    TIER_4 = 4  # Human required (<50%)


class RiskCategory(Enum):
    """Risk categories for operations."""
    TRIVIAL = "trivial"      # Comments, formatting
    LOW = "low"              # Logging, internal changes
    MEDIUM = "medium"        # New features, refactors
    HIGH = "high"            # API changes, deployments
    CRITICAL = "critical"    # Security, production, trading


@dataclass
class ConfidenceFactors:
    """Factors that contribute to confidence score."""
    agent_consensus: float = 0.0      # Agreement between agents
    historical_success: float = 0.0   # Past success rate
    risk_factor: float = 0.0          # Risk-adjusted score
    scope_factor: float = 0.0         # Based on change scope
    trust_factor: float = 0.0         # User trust level
    time_factor: float = 0.0          # Time-based adjustments


@dataclass
class ConfidenceResult:
    """Result of confidence calculation."""
    score: float
    tier: ActionTier
    factors: ConfidenceFactors
    reasoning: str
    can_auto_execute: bool
    requires_approval: bool
    approval_type: str  # "none", "quick", "detailed", "human"


class ConfidenceEngine:
    """
    Calculates confidence scores for actions.
    
    Combines multiple factors to determine whether an action
    can be auto-executed or requires human approval.
    """
    
    # Tier thresholds
    TIER_1_THRESHOLD = 0.90
    TIER_2_THRESHOLD = 0.70
    TIER_3_THRESHOLD = 0.50
    
    # Factor weights
    WEIGHTS = {
        "agent_consensus": 0.30,
        "historical_success": 0.20,
        "risk_factor": 0.25,
        "scope_factor": 0.10,
        "trust_factor": 0.10,
        "time_factor": 0.05
    }
    
    # Risk multipliers (reduce confidence for high-risk operations)
    RISK_MULTIPLIERS = {
        RiskCategory.TRIVIAL: 1.0,
        RiskCategory.LOW: 0.95,
        RiskCategory.MEDIUM: 0.85,
        RiskCategory.HIGH: 0.65,
        RiskCategory.CRITICAL: 0.40
    }
    
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self._success_cache: Dict[str, float] = {}
    
    def calculate(
        self,
        agent_opinions: List[Dict[str, Any]],
        task_type: str,
        scope: Dict[str, Any],
        trust_level: float = 0.5
    ) -> ConfidenceResult:
        """
        Calculate confidence score for an action.
        
        Args:
            agent_opinions: List of agent opinions with confidence and recommendation
            task_type: Type of task being evaluated
            scope: Scope of changes (files, lines, etc.)
            trust_level: User's trust level (0-1)
        
        Returns:
            ConfidenceResult with score, tier, and reasoning
        """
        factors = ConfidenceFactors()
        
        # 1. Agent Consensus
        factors.agent_consensus = self._calculate_consensus(agent_opinions)
        
        # 2. Historical Success
        factors.historical_success = self._get_historical_success(task_type)
        
        # 3. Risk Factor
        risk_category = self._categorize_risk(task_type, scope)
        factors.risk_factor = self.RISK_MULTIPLIERS[risk_category]
        
        # 4. Scope Factor
        factors.scope_factor = self._calculate_scope_factor(scope)
        
        # 5. Trust Factor
        factors.trust_factor = trust_level
        
        # 6. Time Factor
        factors.time_factor = self._calculate_time_factor()
        
        # Calculate weighted score
        raw_score = (
            factors.agent_consensus * self.WEIGHTS["agent_consensus"] +
            factors.historical_success * self.WEIGHTS["historical_success"] +
            factors.risk_factor * self.WEIGHTS["risk_factor"] +
            factors.scope_factor * self.WEIGHTS["scope_factor"] +
            factors.trust_factor * self.WEIGHTS["trust_factor"] +
            factors.time_factor * self.WEIGHTS["time_factor"]
        )
        
        # Apply risk multiplier
        final_score = raw_score * self.RISK_MULTIPLIERS[risk_category]
        final_score = max(0.0, min(1.0, final_score))
        
        # Determine tier
        tier = self._determine_tier(final_score, risk_category)
        
        # Build reasoning
        reasoning = self._build_reasoning(factors, final_score, tier, risk_category)
        
        return ConfidenceResult(
            score=final_score,
            tier=tier,
            factors=factors,
            reasoning=reasoning,
            can_auto_execute=tier == ActionTier.TIER_1,
            requires_approval=tier != ActionTier.TIER_1,
            approval_type=self._get_approval_type(tier)
        )
    
    def _calculate_consensus(self, opinions: List[Dict[str, Any]]) -> float:
        """Calculate agent consensus score."""
        if not opinions:
            return 0.5
        
        # Average confidence
        avg_confidence = sum(o.get("confidence", 0.5) for o in opinions) / len(opinions)
        
        # Agreement bonus (all agents agree)
        recommendations = [o.get("recommendation") for o in opinions]
        if len(set(recommendations)) == 1:
            avg_confidence *= 1.1  # 10% bonus for full agreement
        
        # Penalty for rejections
        rejections = sum(1 for r in recommendations if r == "reject")
        if rejections > 0:
            avg_confidence *= (1 - (rejections / len(opinions) * 0.5))
        
        return min(1.0, avg_confidence)
    
    def _get_historical_success(self, task_type: str) -> float:
        """Get historical success rate for task type."""
        if task_type in self._success_cache:
            return self._success_cache[task_type]
        
        # Calculate from history
        relevant = [h for h in self.history if h.get("task_type") == task_type]
        if not relevant:
            return 0.7  # Default for unknown task types
        
        successes = sum(1 for h in relevant if h.get("success", False))
        rate = successes / len(relevant)
        
        self._success_cache[task_type] = rate
        return rate
    
    def _categorize_risk(self, task_type: str, scope: Dict[str, Any]) -> RiskCategory:
        """Categorize the risk level of an operation."""
        # Task type risk mapping
        high_risk_types = {"deploy", "delete", "security", "production", "trade", "payment"}
        medium_risk_types = {"new_feature", "refactor", "api_change", "database"}
        low_risk_types = {"bug_fix", "config_change", "test"}
        trivial_types = {"comment", "format", "lint", "logging"}
        
        task_lower = task_type.lower()
        
        if any(t in task_lower for t in high_risk_types):
            return RiskCategory.CRITICAL if "production" in task_lower else RiskCategory.HIGH
        if any(t in task_lower for t in medium_risk_types):
            return RiskCategory.MEDIUM
        if any(t in task_lower for t in low_risk_types):
            return RiskCategory.LOW
        if any(t in task_lower for t in trivial_types):
            return RiskCategory.TRIVIAL
        
        # Check scope for additional risk indicators
        files_count = scope.get("files_count", 1)
        if files_count > 10:
            return RiskCategory.HIGH
        if files_count > 5:
            return RiskCategory.MEDIUM
        
        return RiskCategory.MEDIUM  # Default to medium
    
    def _calculate_scope_factor(self, scope: Dict[str, Any]) -> float:
        """Calculate confidence factor based on change scope."""
        files_count = scope.get("files_count", 1)
        lines_changed = scope.get("lines_changed", 0)
        
        # Smaller changes are safer
        file_factor = max(0.3, 1.0 - (files_count / 20))
        line_factor = max(0.3, 1.0 - (lines_changed / 500))
        
        return (file_factor + line_factor) / 2
    
    def _calculate_time_factor(self) -> float:
        """Calculate time-based confidence factor."""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()
        
        # Lower confidence during off-hours and weekends
        if weekday >= 5:  # Weekend
            return 0.7
        if hour < 6 or hour > 22:  # Night
            return 0.7
        if 9 <= hour <= 17:  # Business hours
            return 1.0
        
        return 0.85  # Early morning / evening
    
    def _determine_tier(self, score: float, risk: RiskCategory) -> ActionTier:
        """Determine action tier from score and risk."""
        # Critical risk always requires human
        if risk == RiskCategory.CRITICAL:
            return ActionTier.TIER_4
        
        # High risk caps at Tier 3
        if risk == RiskCategory.HIGH and score >= self.TIER_1_THRESHOLD:
            return ActionTier.TIER_2
        
        # Standard tier determination
        if score >= self.TIER_1_THRESHOLD:
            return ActionTier.TIER_1
        if score >= self.TIER_2_THRESHOLD:
            return ActionTier.TIER_2
        if score >= self.TIER_3_THRESHOLD:
            return ActionTier.TIER_3
        
        return ActionTier.TIER_4
    
    def _get_approval_type(self, tier: ActionTier) -> str:
        """Get approval type for tier."""
        mapping = {
            ActionTier.TIER_1: "none",
            ActionTier.TIER_2: "quick",
            ActionTier.TIER_3: "detailed",
            ActionTier.TIER_4: "human"
        }
        return mapping[tier]
    
    def _build_reasoning(
        self,
        factors: ConfidenceFactors,
        score: float,
        tier: ActionTier,
        risk: RiskCategory
    ) -> str:
        """Build human-readable reasoning."""
        parts = [f"Confidence: {score:.1%}"]
        
        if factors.agent_consensus < 0.7:
            parts.append(f"Low agent consensus ({factors.agent_consensus:.1%})")
        if risk in [RiskCategory.HIGH, RiskCategory.CRITICAL]:
            parts.append(f"High-risk operation ({risk.value})")
        if factors.historical_success < 0.7:
            parts.append(f"Below-average success rate ({factors.historical_success:.1%})")
        if factors.scope_factor < 0.5:
            parts.append("Large scope of changes")
        if factors.time_factor < 0.8:
            parts.append("Sub-optimal timing")
        
        tier_desc = {
            ActionTier.TIER_1: "Auto-execute",
            ActionTier.TIER_2: "Quick approval needed",
            ActionTier.TIER_3: "Detailed review needed",
            ActionTier.TIER_4: "Human approval required"
        }
        parts.append(f"Tier: {tier.value} ({tier_desc[tier]})")
        
        return " | ".join(parts)
    
    def record_outcome(self, task_type: str, success: bool, factors: Dict[str, Any]):
        """Record task outcome for learning."""
        self.history.append({
            "task_type": task_type,
            "success": success,
            "factors": factors,
            "timestamp": datetime.now().isoformat()
        })
        
        # Clear cache to force recalculation
        if task_type in self._success_cache:
            del self._success_cache[task_type]
        
        # Keep history manageable
        if len(self.history) > 1000:
            self.history = self.history[-500:]


# Singleton instance
_engine: Optional[ConfidenceEngine] = None

def get_confidence_engine() -> ConfidenceEngine:
    """Get or create confidence engine instance."""
    global _engine
    if _engine is None:
        _engine = ConfidenceEngine()
    return _engine

def get_confidence_status() -> Dict[str, Any]:
    """Get confidence engine status."""
    engine = get_confidence_engine()
    return {
        "history_size": len(engine.history),
        "cached_success_rates": engine._success_cache,
        "thresholds": {
            "tier_1": engine.TIER_1_THRESHOLD,
            "tier_2": engine.TIER_2_THRESHOLD,
            "tier_3": engine.TIER_3_THRESHOLD
        },
        "weights": engine.WEIGHTS
    }


