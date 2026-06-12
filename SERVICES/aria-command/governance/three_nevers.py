"""
THREE NEVERS - Inviolable Constraints
=====================================

These constraints CANNOT be overridden. They are hardcoded and enforced at multiple layers.

1. NEVER optimize for yield at the expense of coherence or circulation.
2. NEVER introduce complexity faster than the steward can remain regulated.
3. NEVER treat debt as permanent.

The purpose is not to prevent all risk-taking. It is to ensure that risk-taking
NEVER compromises the foundation on which everything else is built.

If you find yourself wanting to override a Never, that is signal. Pause. Ask why.
The constraint is pointing at something.
"""

import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger("aria.governance.three_nevers")


class NeverType(Enum):
    """The three inviolable constraints."""
    YIELD_OVER_COHERENCE = 1  # Never optimize yield at expense of coherence/circulation
    COMPLEXITY_OVER_REGULATION = 2  # Never add complexity faster than steward can handle
    PERMANENT_DEBT = 3  # Never treat debt as permanent


@dataclass
class NeverViolation:
    """A detected violation of a Never constraint."""
    never_type: NeverType
    severity: float  # 0.0 to 1.0 (1.0 = critical violation)
    description: str
    evidence: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    action_blocked: str = ""
    
    @property
    def is_critical(self) -> bool:
        return self.severity >= 0.8
    
    @property
    def is_warning(self) -> bool:
        return 0.5 <= self.severity < 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "never_type": self.never_type.name,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
            "action_blocked": self.action_blocked,
            "is_critical": self.is_critical,
        }


@dataclass 
class NeverCheckResult:
    """Result of checking all Never constraints."""
    violations: List[NeverViolation]
    action_allowed: bool
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0
    
    @property
    def critical_violations(self) -> List[NeverViolation]:
        return [v for v in self.violations if v.is_critical]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "violations": [v.to_dict() for v in self.violations],
            "action_allowed": self.action_allowed,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
        }


class ThreeNevers:
    """
    The inviolable constraint checker for Apprentice OS.
    
    These constraints are structural, not cultural. They are enforced by:
    1. Decision Engine Rules - Actions that violate are blocked
    2. This checker - Runtime validation of all significant actions
    3. Aria's Core - Will not suggest violating actions
    4. Audit Trail - Any violation attempt is permanently logged
    """
    
    # Thresholds for Never 1: Yield vs Coherence
    YIELD_COHERENCE_RATIO_THRESHOLD = 1.0  # Shadow cost ratio where yield benefit is blocked
    
    # Thresholds for Never 2: Complexity vs Regulation
    COMPLEXITY_COHERENCE_DELTA_THRESHOLD = 0.2  # Max complexity increase while coherence decreasing
    STRESS_THRESHOLD_FOR_COMPLEXITY = 60  # Above this stress, no new complexity allowed
    
    # Thresholds for Never 3: Debt Permanence
    DEBT_WARNING_DAYS = 60
    DEBT_CRITICAL_DAYS = 90
    
    def __init__(self):
        self.violation_log: List[NeverViolation] = []
        self.override_attempts: List[Tuple[datetime, NeverType, str]] = []
    
    def check_all(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> NeverCheckResult:
        """
        Check an action against ALL THREE NEVERS.
        
        This is the primary entry point. Every significant action should pass through here.
        
        Args:
            action: Description of the proposed action
            context: Current system state including:
                - yield_benefit: Expected yield improvement
                - coherence_impact: Impact on coherence (-1 to 1)
                - circulation_impact: Impact on circulation (-1 to 1)
                - complexity_delta: Change in system complexity
                - steward_stress: Current stress level (0-100)
                - steward_coherence: Current coherence score
                - debt_entries: List of {amount, days_old, has_resolution_path}
        
        Returns:
            NeverCheckResult with any violations and whether action is allowed
        """
        violations = []
        
        # Check Never 1: Yield over Coherence/Circulation
        v1 = self._check_never_1_yield_over_coherence(action, context)
        if v1:
            violations.append(v1)
        
        # Check Never 2: Complexity over Regulation
        v2 = self._check_never_2_complexity_over_regulation(action, context)
        if v2:
            violations.append(v2)
        
        # Check Never 3: Permanent Debt
        v3 = self._check_never_3_permanent_debt(action, context)
        if v3:
            violations.append(v3)
        
        # Log all violations
        for v in violations:
            v.action_blocked = action
            self.violation_log.append(v)
            logger.warning(f"NEVER VIOLATION: {v.never_type.name} - {v.description}")
        
        # Determine if action is allowed
        # ANY Never violation blocks the action - these are INVIOLABLE
        action_allowed = len(violations) == 0
        
        if violations:
            reasoning = "ACTION BLOCKED - Never constraint violated: " + "; ".join(
                [f"{v.never_type.name}: {v.description}" for v in violations]
            )
        else:
            reasoning = "All Never constraints satisfied"
        
        return NeverCheckResult(
            violations=violations,
            action_allowed=action_allowed,
            reasoning=reasoning
        )
    
    def _check_never_1_yield_over_coherence(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> Optional[NeverViolation]:
        """
        Never 1: Never optimize for yield at the expense of coherence or circulation.
        
        If a decision improves financial returns but increases steward stress → reject
        If a decision accelerates output but reduces value flow to builders → reject
        If a decision hits a metric target but breaks relationship health → reject
        """
        yield_benefit = context.get("yield_benefit", 0)
        coherence_impact = context.get("coherence_impact", 0)
        circulation_impact = context.get("circulation_impact", 0)
        
        evidence = []
        
        # Check if yield is positive but coherence is negative
        if yield_benefit > 0 and coherence_impact < 0:
            severity = min(1.0, abs(coherence_impact) * 0.8 + yield_benefit * 0.2)
            evidence.append(f"Yield benefit (+{yield_benefit}) while harming coherence ({coherence_impact})")
            
            return NeverViolation(
                never_type=NeverType.YIELD_OVER_COHERENCE,
                severity=severity,
                description="Action improves yield but damages coherence",
                evidence=evidence
            )
        
        # Check if yield is positive but circulation is negative
        if yield_benefit > 0 and circulation_impact < -0.2:
            severity = min(1.0, abs(circulation_impact) * 0.7 + yield_benefit * 0.3)
            evidence.append(f"Yield benefit (+{yield_benefit}) while harming circulation ({circulation_impact})")
            
            return NeverViolation(
                never_type=NeverType.YIELD_OVER_COHERENCE,
                severity=severity,
                description="Action improves yield but damages circulation",
                evidence=evidence
            )
        
        # Check shadow cost ratio
        shadow_cost_ratio = context.get("shadow_cost_ratio", 0)
        if shadow_cost_ratio > self.YIELD_COHERENCE_RATIO_THRESHOLD and yield_benefit > 0:
            evidence.append(f"Shadow cost ratio ({shadow_cost_ratio:.2f}) exceeds threshold")
            evidence.append("Hidden costs outweigh visible yield benefits")
            
            return NeverViolation(
                never_type=NeverType.YIELD_OVER_COHERENCE,
                severity=min(1.0, shadow_cost_ratio * 0.5),
                description="Shadow costs exceed yield benefits",
                evidence=evidence
            )
        
        return None
    
    def _check_never_2_complexity_over_regulation(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> Optional[NeverViolation]:
        """
        Never 2: Never introduce complexity faster than the steward can remain regulated.
        
        Adding new apprentices, modules, projects, or connections must not outpace coherence.
        If the steward is already at capacity, no new complexity enters.
        Growth happens at the pace of integration, not the pace of opportunity.
        """
        complexity_delta = context.get("complexity_delta", 0)
        steward_stress = context.get("steward_stress", 50)
        steward_coherence = context.get("steward_coherence", 70)
        coherence_trend = context.get("coherence_trend", "stable")  # increasing, stable, decreasing
        
        evidence = []
        
        # Check: Adding complexity while stress is high
        if complexity_delta > 0 and steward_stress > self.STRESS_THRESHOLD_FOR_COMPLEXITY:
            severity = min(1.0, (steward_stress - self.STRESS_THRESHOLD_FOR_COMPLEXITY) / 40 + complexity_delta * 0.3)
            evidence.append(f"Adding complexity (+{complexity_delta}) while stress is high ({steward_stress})")
            evidence.append(f"Stress threshold: {self.STRESS_THRESHOLD_FOR_COMPLEXITY}")
            
            return NeverViolation(
                never_type=NeverType.COMPLEXITY_OVER_REGULATION,
                severity=severity,
                description="Cannot add complexity while steward is stressed",
                evidence=evidence
            )
        
        # Check: Adding complexity while coherence is decreasing
        if complexity_delta > self.COMPLEXITY_COHERENCE_DELTA_THRESHOLD and coherence_trend == "decreasing":
            evidence.append(f"Adding significant complexity (+{complexity_delta}) while coherence is decreasing")
            evidence.append("Must restore coherence baseline before adding new complexity")
            
            return NeverViolation(
                never_type=NeverType.COMPLEXITY_OVER_REGULATION,
                severity=0.8,
                description="Cannot add complexity while coherence is declining",
                evidence=evidence
            )
        
        # Check: Adding complexity when coherence is below baseline
        coherence_baseline = context.get("coherence_baseline", 60)
        if complexity_delta > 0 and steward_coherence < coherence_baseline:
            evidence.append(f"Adding complexity while coherence ({steward_coherence}) is below baseline ({coherence_baseline})")
            
            return NeverViolation(
                never_type=NeverType.COMPLEXITY_OVER_REGULATION,
                severity=0.7,
                description="Cannot add complexity when coherence is below baseline",
                evidence=evidence
            )
        
        return None
    
    def _check_never_3_permanent_debt(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> Optional[NeverViolation]:
        """
        Never 3: Never treat debt as permanent.
        
        All debt (financial, relational, technical, energetic) has a resolution path.
        No debt entry exists without a target resolution date.
        Debt that persists beyond 90 days without progress triggers escalation.
        """
        # Check if action creates debt without resolution path
        creates_debt = context.get("creates_debt", False)
        has_resolution_path = context.get("has_resolution_path", True)
        
        evidence = []
        
        if creates_debt and not has_resolution_path:
            evidence.append("Action creates debt without a resolution path")
            evidence.append("All debt must have a target resolution date")
            
            return NeverViolation(
                never_type=NeverType.PERMANENT_DEBT,
                severity=0.9,
                description="Cannot create debt without resolution path",
                evidence=evidence
            )
        
        # Check existing debt entries
        debt_entries = context.get("debt_entries", [])
        critical_debts = []
        warning_debts = []
        
        for debt in debt_entries:
            days_old = debt.get("days_old", 0)
            has_path = debt.get("has_resolution_path", True)
            debt_name = debt.get("name", "unnamed debt")
            
            if days_old > self.DEBT_CRITICAL_DAYS and not has_path:
                critical_debts.append(f"{debt_name} ({days_old} days old, no resolution)")
            elif days_old > self.DEBT_WARNING_DAYS:
                warning_debts.append(f"{debt_name} ({days_old} days old)")
        
        if critical_debts:
            evidence.append(f"Critical debts without resolution: {', '.join(critical_debts)}")
            evidence.append(f"Debts > {self.DEBT_CRITICAL_DAYS} days must have active resolution")
            
            # Block adding NEW debt while critical debt exists
            if creates_debt:
                return NeverViolation(
                    never_type=NeverType.PERMANENT_DEBT,
                    severity=0.95,
                    description="Cannot add new debt while critical unresolved debt exists",
                    evidence=evidence
                )
        
        return None
    
    def attempt_override(
        self,
        never_type: NeverType,
        reason: str
    ) -> Tuple[bool, str]:
        """
        Attempt to override a Never constraint.
        
        Spoiler: This always fails. The Nevers cannot be overridden.
        But we log the attempt for analysis.
        """
        self.override_attempts.append((datetime.now(), never_type, reason))
        logger.warning(f"OVERRIDE ATTEMPT (DENIED): {never_type.name} - {reason}")
        
        return (
            False,
            f"The THREE NEVERS cannot be overridden. {never_type.name} is inviolable. "
            f"Your attempt has been logged. If you're trying to override, ask why the constraint is blocking you. "
            f"The constraint is pointing at something important."
        )
    
    def get_violation_log(self, limit: int = 20) -> List[NeverViolation]:
        """Get recent violations."""
        return self.violation_log[-limit:]
    
    def get_override_attempts(self) -> List[Tuple[datetime, NeverType, str]]:
        """Get all override attempts (for audit)."""
        return self.override_attempts


# Singleton instance
_three_nevers: Optional[ThreeNevers] = None


def get_never_checker() -> ThreeNevers:
    """Get the singleton ThreeNevers checker."""
    global _three_nevers
    if _three_nevers is None:
        _three_nevers = ThreeNevers()
    return _three_nevers


def check_never_constraints(
    action: str,
    context: Dict[str, Any]
) -> NeverCheckResult:
    """
    Convenience function to check an action against the Three Nevers.
    
    Usage:
        result = check_never_constraints(
            "Deploy high-risk trading bot",
            {
                "yield_benefit": 0.5,
                "coherence_impact": -0.3,
                "steward_stress": 75
            }
        )
        if not result.action_allowed:
            print(f"BLOCKED: {result.reasoning}")
    """
    return get_never_checker().check_all(action, context)


