"""
DECISION ENGINE - Rule Evaluation System
========================================

The decision engine evaluates every significant action against governance rules.
It integrates:
- Priority Stack (PRINCIPLES)
- Three Nevers (inviolable constraints)
- Shadow Costs (hidden cost calculation)
- Steward State (James's current metrics)
- Rules from rules.yaml

The engine returns: APPROVE, FLAG, or BLOCK with reasoning.
"""

import os
import yaml
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from .principles import PriorityStack, Priority, PriorityStackResult, get_priority_stack
from .three_nevers import ThreeNevers, NeverCheckResult, get_never_checker
from .shadow_costs import ShadowCostTracker, ShadowCostResult, get_shadow_cost_tracker
from .steward_state import StewardState, StewardMetrics, get_steward_state

logger = logging.getLogger("aria.governance.decision_engine")


class DecisionType(Enum):
    """Types of decisions from the engine."""
    APPROVE = auto()      # Action is allowed
    FLAG = auto()         # Action needs explicit review
    BLOCK = auto()        # Action is blocked
    RECOMMEND = auto()    # Recommendation only, not binding


class RuleActionType(Enum):
    """Types of rule actions."""
    PAUSE = "pause"
    BLOCK = "block"
    FLAG = "flag"
    RECOMMEND = "recommend"
    ROUTE = "route"
    ALERT = "alert"
    CHECK = "check"


@dataclass
class RuleEvaluation:
    """Result of evaluating a single rule."""
    rule_id: str
    rule_name: str
    layer: int
    triggered: bool
    action_type: Optional[RuleActionType]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    """The final decision from the engine."""
    decision_type: DecisionType
    action: str                           # The action being evaluated
    reasoning: str                        # Human-readable reasoning
    
    # Component results
    priority_result: Optional[PriorityStackResult] = None
    never_result: Optional[NeverCheckResult] = None
    shadow_cost_result: Optional[ShadowCostResult] = None
    
    # Rule evaluations
    triggered_rules: List[RuleEvaluation] = field(default_factory=list)
    blocking_rules: List[RuleEvaluation] = field(default_factory=list)
    
    # Context
    steward_metrics: Optional[StewardMetrics] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Override info
    can_override: bool = False
    override_requires: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_type": self.decision_type.name,
            "action": self.action,
            "reasoning": self.reasoning,
            "triggered_rules": [
                {"id": r.rule_id, "name": r.rule_name, "message": r.message}
                for r in self.triggered_rules
            ],
            "blocking_rules": [
                {"id": r.rule_id, "name": r.rule_name, "message": r.message}
                for r in self.blocking_rules
            ],
            "can_override": self.can_override,
            "override_requires": self.override_requires,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_summary(self) -> str:
        """Get a human-readable summary for Aria to use."""
        lines = [f"**{self.decision_type.name}**: {self.reasoning}"]
        
        if self.blocking_rules:
            lines.append("\nBlocking rules:")
            for r in self.blocking_rules:
                lines.append(f"  - [{r.rule_id}] {r.message}")
        
        if self.triggered_rules and self.decision_type != DecisionType.BLOCK:
            lines.append("\nTriggered rules:")
            for r in self.triggered_rules[:3]:  # Limit to top 3
                lines.append(f"  - [{r.rule_id}] {r.message}")
        
        if self.can_override:
            lines.append(f"\n*Can override with: {', '.join(self.override_requires)}*")
        
        return "\n".join(lines)


class DecisionEngine:
    """
    The governance decision engine for Apprentice OS.
    
    Evaluates every significant action against:
    1. Three Nevers (inviolable constraints)
    2. Priority Stack (coherence > circulation > resilience > yield)
    3. Shadow Costs (hidden costs)
    4. Rules from rules.yaml
    5. Current steward state
    """
    
    def __init__(self, rules_path: str = None):
        """Initialize the decision engine."""
        if rules_path is None:
            rules_path = os.path.join(
                os.path.dirname(__file__),
                "rules.yaml"
            )
        
        self.rules_path = rules_path
        self.rules = self._load_rules()
        
        # Get component instances
        self.priority_stack = get_priority_stack()
        self.never_checker = get_never_checker()
        self.shadow_tracker = get_shadow_cost_tracker()
        self.steward_state = get_steward_state()
        
        # Decision history
        self.history: List[Decision] = []
        self.override_log: List[Tuple[datetime, str, str]] = []
    
    def _load_rules(self) -> Dict[str, Any]:
        """Load rules from YAML file."""
        try:
            with open(self.rules_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading rules: {e}")
            return {"rules": [], "meta": {}}
    
    def reload_rules(self):
        """Reload rules from disk."""
        self.rules = self._load_rules()
        logger.info("Rules reloaded")
    
    def evaluate(
        self,
        action: str,
        context: Dict[str, Any] = None,
        expected_benefit: float = 1.0
    ) -> Decision:
        """
        Evaluate an action against all governance rules.
        
        This is the main entry point. Every significant action should pass through here.
        
        Args:
            action: Description of the proposed action
            context: Current context including:
                - Any metrics relevant to rules
                - Expected impacts on coherence/circulation/resilience
                - Trading context if applicable
            expected_benefit: Expected benefit (for shadow cost ratio)
        
        Returns:
            Decision with APPROVE, FLAG, or BLOCK
        """
        if context is None:
            context = {}
        
        # Add steward state to context
        steward_metrics = self.steward_state.get_metrics()
        context.setdefault("steward_stress", steward_metrics.stress_level)
        context.setdefault("steward_coherence", steward_metrics.coherence_score)
        context.setdefault("coherence_baseline", steward_metrics.coherence_baseline)
        context.setdefault("coherence_trend", steward_metrics.coherence_trend)
        context.setdefault("decision_quality", steward_metrics.decision_quality)
        
        triggered_rules = []
        blocking_rules = []
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Check THREE NEVERS (Inviolable - checked first)
        # ═══════════════════════════════════════════════════════════════
        never_result = self.never_checker.check_all(action, context)
        
        if not never_result.action_allowed:
            # Three Nevers violation - BLOCK immediately, cannot override
            decision = Decision(
                decision_type=DecisionType.BLOCK,
                action=action,
                reasoning=f"THREE NEVERS VIOLATED: {never_result.reasoning}",
                never_result=never_result,
                steward_metrics=steward_metrics,
                can_override=False
            )
            self.history.append(decision)
            logger.warning(f"Action blocked by THREE NEVERS: {action}")
            return decision
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Check Priority Stack
        # ═══════════════════════════════════════════════════════════════
        priority_result = self.priority_stack.evaluate(action, context)
        
        if not priority_result.overall_approved:
            # Priority stack blocked - may be overridable depending on which priority
            can_override = priority_result.blocking_priority not in [Priority.COHERENCE]
            override_requires = []
            if can_override:
                override_requires = ["explicit_acknowledgment", "steward_confirmation"]
            
            decision = Decision(
                decision_type=DecisionType.BLOCK if priority_result.blocking_priority == Priority.COHERENCE else DecisionType.FLAG,
                action=action,
                reasoning=priority_result.reasoning,
                priority_result=priority_result,
                never_result=never_result,
                steward_metrics=steward_metrics,
                can_override=can_override,
                override_requires=override_requires
            )
            self.history.append(decision)
            logger.info(f"Action flagged by priority stack: {action}")
            return decision
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Calculate Shadow Costs
        # ═══════════════════════════════════════════════════════════════
        shadow_result = self.shadow_tracker.calculate(action, context, expected_benefit)
        
        if shadow_result.exceeds_benefit:
            decision = Decision(
                decision_type=DecisionType.FLAG,
                action=action,
                reasoning=f"Shadow costs exceed benefit (ratio: {shadow_result.shadow_cost_ratio:.2f}). {shadow_result.recommendation}",
                priority_result=priority_result,
                never_result=never_result,
                shadow_cost_result=shadow_result,
                steward_metrics=steward_metrics,
                can_override=True,
                override_requires=["explicit_review", "shadow_cost_acknowledgment"]
            )
            self.history.append(decision)
            logger.info(f"Action flagged by shadow costs: {action}")
            return decision
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Evaluate YAML Rules (by layer)
        # ═══════════════════════════════════════════════════════════════
        rules = self.rules.get("rules", [])
        rules_by_layer = {}
        for rule in rules:
            layer = rule.get("layer", 5)
            if layer not in rules_by_layer:
                rules_by_layer[layer] = []
            rules_by_layer[layer].append(rule)
        
        # Evaluate rules in layer order (1 = highest priority)
        for layer in sorted(rules_by_layer.keys()):
            for rule in rules_by_layer[layer]:
                eval_result = self._evaluate_rule(rule, context)
                
                if eval_result.triggered:
                    triggered_rules.append(eval_result)
                    
                    if eval_result.action_type in [RuleActionType.BLOCK]:
                        blocking_rules.append(eval_result)
                        
                        # Check if override is allowed
                        rule_override = rule.get("override", {})
                        can_override = rule_override.get("allowed", True)
                        
                        decision = Decision(
                            decision_type=DecisionType.BLOCK,
                            action=action,
                            reasoning=f"Rule [{rule['id']}] blocked action: {eval_result.message}",
                            priority_result=priority_result,
                            never_result=never_result,
                            shadow_cost_result=shadow_result,
                            triggered_rules=triggered_rules,
                            blocking_rules=blocking_rules,
                            steward_metrics=steward_metrics,
                            can_override=can_override,
                            override_requires=["steward_confirmation"] if can_override else []
                        )
                        self.history.append(decision)
                        return decision
                    
                    elif eval_result.action_type == RuleActionType.FLAG:
                        # Continue evaluation but note the flag
                        pass
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Determine Final Decision
        # ═══════════════════════════════════════════════════════════════
        
        # Check for any flagged rules
        flagged = [r for r in triggered_rules if r.action_type == RuleActionType.FLAG]
        
        if flagged:
            decision = Decision(
                decision_type=DecisionType.FLAG,
                action=action,
                reasoning=f"Action flagged by {len(flagged)} rule(s): {flagged[0].message}",
                priority_result=priority_result,
                never_result=never_result,
                shadow_cost_result=shadow_result,
                triggered_rules=triggered_rules,
                steward_metrics=steward_metrics,
                can_override=True,
                override_requires=["explicit_acknowledgment"]
            )
        elif shadow_result.has_warnings:
            decision = Decision(
                decision_type=DecisionType.APPROVE,
                action=action,
                reasoning=f"Approved with caution. Shadow cost warnings: {shadow_result.recommendation}",
                priority_result=priority_result,
                never_result=never_result,
                shadow_cost_result=shadow_result,
                triggered_rules=triggered_rules,
                steward_metrics=steward_metrics
            )
        else:
            decision = Decision(
                decision_type=DecisionType.APPROVE,
                action=action,
                reasoning="All governance checks passed. Action approved.",
                priority_result=priority_result,
                never_result=never_result,
                shadow_cost_result=shadow_result,
                triggered_rules=triggered_rules,
                steward_metrics=steward_metrics
            )
        
        self.history.append(decision)
        return decision
    
    def _evaluate_rule(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any]
    ) -> RuleEvaluation:
        """Evaluate a single rule against the context."""
        rule_id = rule.get("id", "unknown")
        rule_name = rule.get("name", "Unknown Rule")
        layer = rule.get("layer", 5)
        condition = rule.get("condition", {})
        action = rule.get("action", {})
        
        triggered = False
        action_type = None
        message = ""
        details = {}
        
        # Evaluate condition
        if "metric" in condition:
            metric_name = condition["metric"]
            operator = condition.get("operator", "eq")
            threshold = condition.get("threshold")
            
            # Handle special threshold values
            if threshold == "baseline":
                threshold = context.get("coherence_baseline", 65)
            
            # Get metric value from context
            metric_value = context.get(metric_name)
            
            if metric_value is not None and threshold is not None:
                triggered = self._compare(metric_value, operator, threshold)
                details["metric"] = metric_name
                details["value"] = metric_value
                details["threshold"] = threshold
        
        elif "type" in condition:
            # Special condition types
            cond_type = condition["type"]
            if cond_type == "trading_action":
                triggered = context.get("is_trading_action", False)
            elif cond_type == "speculation_detected":
                triggered = context.get("speculation_detected", False)
            elif cond_type == "phase_criteria_met":
                triggered = context.get("phase_criteria_met", False)
        
        elif "any" in condition:
            # Any of multiple conditions
            for sub_cond in condition["any"]:
                if "metric" in sub_cond:
                    metric_value = context.get(sub_cond["metric"])
                    if metric_value is not None:
                        if self._compare(metric_value, sub_cond.get("operator", "eq"), sub_cond.get("threshold")):
                            triggered = True
                            break
        
        # Get action info if triggered
        if triggered:
            action_type_str = action.get("type", "recommend")
            try:
                action_type = RuleActionType(action_type_str)
            except ValueError:
                action_type = RuleActionType.RECOMMEND
            
            message = action.get("message", f"Rule {rule_id} triggered")
        
        return RuleEvaluation(
            rule_id=rule_id,
            rule_name=rule_name,
            layer=layer,
            triggered=triggered,
            action_type=action_type,
            message=message,
            details=details
        )
    
    def _compare(self, value: float, operator: str, threshold: float) -> bool:
        """Compare a value against a threshold."""
        if operator == "lt":
            return value < threshold
        elif operator == "gt":
            return value > threshold
        elif operator == "lte":
            return value <= threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "eq":
            return value == threshold
        elif operator == "ne":
            return value != threshold
        return False
    
    def quick_check(self, action: str) -> Tuple[bool, str]:
        """
        Quick check if an action is likely to be approved.
        
        Returns (is_likely_approved, reason)
        """
        steward = self.steward_state.get_metrics()
        
        # Quick checks
        if not steward.is_coherent:
            return (False, "Steward coherence below baseline")
        
        if steward.is_stressed:
            return (False, "Steward stress is elevated")
        
        if steward.needs_pause:
            return (False, "System needs pause")
        
        return (True, "Quick checks passed")
    
    def get_steward_summary(self) -> Dict[str, Any]:
        """Get current steward state summary for Aria."""
        metrics = self.steward_state.get_metrics()
        return {
            "coherence": metrics.coherence_score,
            "stress": metrics.stress_level,
            "is_coherent": metrics.is_coherent,
            "can_expand": not metrics.needs_pause,
            "can_take_complexity": metrics.can_take_complexity,
            "recommendations": self.steward_state.check_in().get("recommendations", [])
        }
    
    def get_history(self, limit: int = 10) -> List[Decision]:
        """Get recent decision history."""
        return self.history[-limit:]


# Singleton instance
_decision_engine: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    """Get the singleton DecisionEngine."""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionEngine()
    return _decision_engine


def evaluate_action(
    action: str,
    context: Dict[str, Any] = None,
    expected_benefit: float = 1.0
) -> Decision:
    """
    Convenience function to evaluate an action.
    
    Usage:
        decision = evaluate_action(
            "Deploy new trading strategy",
            {"is_trading_action": True, "expected_revenue": 500}
        )
        
        if decision.decision_type == DecisionType.APPROVE:
            # Proceed
            pass
        elif decision.decision_type == DecisionType.FLAG:
            # Ask for confirmation
            print(decision.reasoning)
        else:
            # Blocked
            print(f"Cannot proceed: {decision.reasoning}")
    """
    return get_decision_engine().evaluate(action, context, expected_benefit)


