#!/usr/bin/env python3
"""
ALIGNMENT ECONOMICS - RULES ENGINE
====================================

Decision hierarchy:
1. System coherence
2. Circulation health  
3. Long-term resilience
4. Yield

Forgiveness by design, not charity.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from enum import Enum

from models.core import (
    Position, PositionType,
    Debt, DebtClassification, DebtStatus,
    Flow, FlowPurpose,
    SystemHealth
)
from ledger.storage import (
    PositionStore, DebtStore, FlowStore,
    calculate_health
)


# ============================================================================
# CONFIGURATION
# ============================================================================

class RoutingConfig:
    """System routing configuration."""
    
    # Capital must be routed within this window
    MAX_IDLE_DAYS = 7
    
    # Priority order for deployment
    DEPLOYMENT_PRIORITY = [
        FlowPurpose.RELIEF,
        FlowPurpose.PRODUCTIVE,
        FlowPurpose.TRUST_BUILDING,
        FlowPurpose.INSTITUTIONAL,
    ]
    
    # Minimum allocations (as ratio of total capital)
    MIN_ALLOCATIONS = {
        FlowPurpose.RELIEF: Decimal("0.20"),        # 20% to debt relief
        FlowPurpose.PRODUCTIVE: Decimal("0.30"),    # 30% to productive
        FlowPurpose.RESERVE: Decimal("0.10"),       # 10% liquidity buffer
    }
    
    # Maximum autonomous decision (requires human approval above this)
    MAX_AUTONOMOUS_AMOUNT = Decimal("10000")


class ForgivenessConfig:
    """Forgiveness trigger configuration."""
    
    # Time-based forgiveness (days active)
    TIME_TRIGGERS = {
        DebtClassification.PRODUCTIVE: 365,     # 1 year
        DebtClassification.TRANSITIONAL: 180,   # 6 months
        DebtClassification.EXTRACTIVE: None,    # Must be explicitly handled
    }
    
    # Participation score required
    PARTICIPATION_REQUIRED = {
        DebtClassification.PRODUCTIVE: 0.8,
        DebtClassification.TRANSITIONAL: 0.6,
        DebtClassification.EXTRACTIVE: 1.0,
    }
    
    # Yield coverage threshold (yield >= principal)
    YIELD_THRESHOLD = Decimal("1.0")
    
    # Health-based acceleration
    HEALTH_ACCELERATION = {
        "stress_below": 0.3,
        "velocity_above": 0.5,
        "acceleration_factor": 2.0,
    }


# ============================================================================
# ROUTING ENGINE
# ============================================================================

@dataclass
class RoutingRecommendation:
    """A recommendation for routing capital."""
    from_position: Position
    to_target: str  # Description of target
    amount: Decimal
    purpose: FlowPurpose
    priority: int  # 1 = highest
    reasoning: str
    requires_approval: bool
    urgency: str  # "immediate", "soon", "when_ready"


class RoutingEngine:
    """
    Recommends how to route idle capital.
    
    Follows the hierarchy:
    1. System coherence first
    2. Then circulation health
    3. Then resilience
    4. Then yield
    """
    
    def __init__(self):
        self.config = RoutingConfig()
    
    def get_recommendations(self) -> List[RoutingRecommendation]:
        """Get routing recommendations for idle capital."""
        recommendations = []
        
        # Get system state
        health = calculate_health()
        idle_positions = PositionStore.get_idle()
        active_debts = DebtStore.list_active()
        
        for position in idle_positions:
            if position.value <= 0:
                continue
            
            # Get best recommendation for this position
            rec = self._recommend_for_position(position, health, active_debts)
            if rec:
                recommendations.append(rec)
        
        # Sort by priority
        recommendations.sort(key=lambda r: r.priority)
        
        return recommendations
    
    def _recommend_for_position(
        self,
        position: Position,
        health: SystemHealth,
        debts: List[Debt]
    ) -> Optional[RoutingRecommendation]:
        """Get recommendation for a single position."""
        
        amount = position.value
        
        # Priority 1: If stress is high, focus on relief
        if health.stress_index > 0.6:
            extractive = [d for d in debts if d.classification == DebtClassification.EXTRACTIVE]
            if extractive:
                target = extractive[0]
                return RoutingRecommendation(
                    from_position=position,
                    to_target=f"Debt relief: {target.name or target.lender}",
                    amount=min(amount, target.remaining),
                    purpose=FlowPurpose.RELIEF,
                    priority=1,
                    reasoning=f"High stress ({health.stress_index:.1%}). Prioritizing extractive debt relief.",
                    requires_approval=amount > self.config.MAX_AUTONOMOUS_AMOUNT,
                    urgency="immediate"
                )
        
        # Priority 2: Liquidity buffer if low
        if health.liquidity_ratio < float(self.config.MIN_ALLOCATIONS[FlowPurpose.RESERVE]):
            needed = health.total_capital * self.config.MIN_ALLOCATIONS[FlowPurpose.RESERVE]
            cash_positions = PositionStore.get_by_type(PositionType.CASH)
            current_cash = sum(p.value for p in cash_positions)
            gap = needed - current_cash
            
            if gap > 0:
                return RoutingRecommendation(
                    from_position=position,
                    to_target="Liquidity reserve",
                    amount=min(amount, gap),
                    purpose=FlowPurpose.RESERVE,
                    priority=2,
                    reasoning=f"Liquidity ratio ({health.liquidity_ratio:.1%}) below minimum (10%).",
                    requires_approval=False,  # Auto-approve reserve building
                    urgency="soon"
                )
        
        # Priority 3: Productive debt reduction
        productive = [d for d in debts if d.classification == DebtClassification.PRODUCTIVE]
        if productive:
            target = productive[0]
            return RoutingRecommendation(
                from_position=position,
                to_target=f"Productive debt: {target.name or target.lender}",
                amount=min(amount, target.remaining),
                purpose=FlowPurpose.PRODUCTIVE,
                priority=3,
                reasoning="Reducing productive debt to increase yield accumulation.",
                requires_approval=amount > self.config.MAX_AUTONOMOUS_AMOUNT,
                urgency="when_ready"
            )
        
        # Priority 4: Trust building (if all else is healthy)
        if health.is_healthy:
            return RoutingRecommendation(
                from_position=position,
                to_target="Trust-building deployment",
                amount=amount,
                purpose=FlowPurpose.TRUST_BUILDING,
                priority=4,
                reasoning="System healthy. Capital available for relationship building.",
                requires_approval=True,  # Always approve trust-building
                urgency="when_ready"
            )
        
        return None
    
    def check_routing_health(self) -> Dict:
        """Check if current routing follows rules."""
        health = calculate_health()
        recent_flows = FlowStore.list_recent(30)
        
        # Calculate allocation ratios
        total_flowed = sum(f.amount for f in recent_flows)
        allocation_by_purpose = {}
        
        for purpose in FlowPurpose:
            purpose_flows = [f for f in recent_flows if f.purpose == purpose]
            purpose_total = sum(f.amount for f in purpose_flows)
            allocation_by_purpose[purpose.value] = {
                "amount": str(purpose_total),
                "ratio": float(purpose_total / total_flowed) if total_flowed > 0 else 0
            }
        
        # Check minimums
        violations = []
        for purpose, min_ratio in self.config.MIN_ALLOCATIONS.items():
            actual = allocation_by_purpose.get(purpose.value, {}).get("ratio", 0)
            if actual < float(min_ratio):
                violations.append({
                    "purpose": purpose.value,
                    "required": float(min_ratio),
                    "actual": actual
                })
        
        return {
            "healthy": len(violations) == 0,
            "allocations": allocation_by_purpose,
            "violations": violations,
            "idle_capital": [p.to_dict() for p in PositionStore.get_idle()],
            "stress_index": health.stress_index
        }


# ============================================================================
# FORGIVENESS ENGINE
# ============================================================================

@dataclass
class ForgivenessRecommendation:
    """A recommendation to forgive a debt."""
    debt: Debt
    trigger: str  # What triggered this
    ready: bool
    reasoning: str
    requires_approval: bool


class ForgivenessEngine:
    """
    Determines when debts are ready for forgiveness.
    
    Forgiveness is mechanical, not charity.
    """
    
    def __init__(self):
        self.config = ForgivenessConfig()
    
    def check_all(self) -> List[ForgivenessRecommendation]:
        """Check all active debts for forgiveness readiness."""
        recommendations = []
        debts = DebtStore.list_active()
        health = calculate_health()
        
        for debt in debts:
            rec = self._check_debt(debt, health)
            recommendations.append(rec)
        
        return [r for r in recommendations if r.ready]
    
    def _check_debt(self, debt: Debt, health: SystemHealth) -> ForgivenessRecommendation:
        """Check if a single debt is ready for forgiveness."""
        
        # Get acceleration factor
        acceleration = 1.0
        if (health.stress_index < self.config.HEALTH_ACCELERATION["stress_below"] and
            health.capital_velocity > self.config.HEALTH_ACCELERATION["velocity_above"]):
            acceleration = self.config.HEALTH_ACCELERATION["acceleration_factor"]
        
        # Check yield coverage
        if debt.yield_accumulated >= debt.principal * self.config.YIELD_THRESHOLD:
            return ForgivenessRecommendation(
                debt=debt,
                trigger="yield_coverage",
                ready=True,
                reasoning=f"Yield ({debt.yield_coverage:.1%}) exceeds principal. Debt has paid for itself.",
                requires_approval=False  # Auto-forgive when yield covered
            )
        
        # Check time + participation
        time_threshold = self.config.TIME_TRIGGERS.get(debt.classification)
        if time_threshold:
            adjusted_threshold = time_threshold / acceleration
            participation_required = self.config.PARTICIPATION_REQUIRED.get(debt.classification, 1.0)
            
            if (debt.days_active >= adjusted_threshold and 
                debt.participation_score >= participation_required):
                return ForgivenessRecommendation(
                    debt=debt,
                    trigger="time_participation",
                    ready=True,
                    reasoning=(
                        f"Active {debt.days_active} days (threshold: {adjusted_threshold:.0f}), "
                        f"participation {debt.participation_score:.0%} (required: {participation_required:.0%})"
                    ),
                    requires_approval=debt.classification == DebtClassification.EXTRACTIVE
                )
        
        # Not ready yet
        return ForgivenessRecommendation(
            debt=debt,
            trigger="",
            ready=False,
            reasoning=self._explain_not_ready(debt, health),
            requires_approval=True
        )
    
    def _explain_not_ready(self, debt: Debt, health: SystemHealth) -> str:
        """Explain why debt isn't ready for forgiveness."""
        parts = []
        
        # Yield progress
        if debt.yield_coverage < 1.0:
            parts.append(f"Yield coverage: {debt.yield_coverage:.0%} of principal")
        
        # Time progress
        time_threshold = self.config.TIME_TRIGGERS.get(debt.classification)
        if time_threshold:
            progress = min(1.0, debt.days_active / time_threshold)
            parts.append(f"Time: {debt.days_active} / {time_threshold} days ({progress:.0%})")
        
        # Participation
        required = self.config.PARTICIPATION_REQUIRED.get(debt.classification, 1.0)
        if debt.participation_score < required:
            parts.append(f"Participation: {debt.participation_score:.0%} / {required:.0%}")
        
        return " | ".join(parts) if parts else "Needs more time or activity"
    
    def execute_forgiveness(self, debt_id: str, approved_by: str = "steward") -> Debt:
        """Execute forgiveness on a debt."""
        debt = DebtStore.get(debt_id)
        if not debt:
            raise ValueError(f"Debt {debt_id} not found")
        
        ready, trigger = debt.check_forgiveness_ready()
        if not ready:
            raise ValueError(f"Debt {debt_id} is not ready for forgiveness")
        
        # Record the forgiveness
        debt = DebtStore.forgive(debt, f"Trigger: {trigger}, Approved by: {approved_by}")
        
        # Create a flow record
        flow = Flow(
            from_position=debt.lender,
            to_position="forgiven",
            amount=debt.remaining,
            purpose=FlowPurpose.RELIEF,
            description=f"Debt forgiveness: {debt.name}",
            approved_by=approved_by,
            auto_approved=True
        )
        FlowStore.create(flow)
        
        return debt


# ============================================================================
# DAILY CHECKLIST
# ============================================================================

def generate_daily_checklist() -> Dict:
    """Generate the daily circulation checklist."""
    health = calculate_health()
    idle = PositionStore.get_idle()
    forgiveness_ready = ForgivenessEngine().check_all()
    routing_recs = RoutingEngine().get_recommendations()
    
    checklist = {
        "date": datetime.now().isoformat(),
        "health_summary": {
            "stress_index": health.stress_index,
            "capital_velocity": health.capital_velocity,
            "liquidity_ratio": health.liquidity_ratio,
            "is_healthy": health.is_healthy,
            "total_capital": str(health.total_capital),
            "total_debt": str(health.total_debt),
            "net_position": str(health.net_position),
        },
        "morning_checks": [
            {"item": "Review overnight positions", "status": "pending"},
            {"item": f"Idle capital check: {len(idle)} positions", "status": "alert" if idle else "ok"},
            {"item": f"Liquidity buffer: {health.liquidity_ratio:.1%}", "status": "ok" if health.liquidity_ratio >= 0.1 else "alert"},
            {"item": f"Stress level: {health.stress_index:.1%}", "status": "ok" if health.stress_index < 0.6 else "alert"},
        ],
        "actions_needed": [
            {
                "priority": r.priority,
                "action": f"Route {r.amount} from {r.from_position.name} → {r.to_target}",
                "purpose": r.purpose.value,
                "urgency": r.urgency,
                "requires_approval": r.requires_approval,
                "reasoning": r.reasoning
            }
            for r in routing_recs[:5]
        ],
        "forgiveness_ready": [
            {
                "debt_id": r.debt.id,
                "debt_name": r.debt.name,
                "amount": str(r.debt.remaining),
                "trigger": r.trigger,
                "reasoning": r.reasoning,
                "requires_approval": r.requires_approval
            }
            for r in forgiveness_ready
        ],
        "evening_log": [
            {"item": "Record day's flows", "status": "pending"},
            {"item": "Update participation scores", "status": "pending"},
            {"item": "Note stress signals", "status": "pending"},
        ]
    }
    
    return checklist


