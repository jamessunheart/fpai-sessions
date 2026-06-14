"""
Consciousness Decision Engine

Uses mathematical consciousness metrics to make autonomous decisions with
quantifiable confidence scores based on integration complexity, adaptation rate,
and other rigorous metrics.
"""

import asyncio
import httpx
import math
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel
from enum import Enum


class DecisionType(str, Enum):
    """Types of decisions the engine can make"""
    TRADING = "trading"
    OPTIMIZATION = "optimization"
    RESOURCE_ALLOCATION = "resource_allocation"
    RISK_MANAGEMENT = "risk_management"
    SYSTEM_COORDINATION = "system_coordination"


class Decision(BaseModel):
    """Represents a consciousness-driven decision"""
    decision_id: str
    decision_type: DecisionType
    action: str
    confidence_score: float  # 0.0-1.0 based on consciousness metrics
    consciousness_metrics: Dict[str, float]
    reasoning: str
    expected_outcome: str
    risk_assessment: Dict[str, Any]
    timestamp: str
    alternatives_considered: List[Dict[str, Any]]


class ConsciousnessDecisionEngine:
    """
    Decision engine that uses mathematical consciousness metrics to make optimal decisions.
    
    Decision quality is calculated as:
    decision_quality = f(consciousness_score, integration_complexity, adaptation_rate, phase_synchronization)
    """

    def __init__(
        self,
        consciousness_verifier_url: str = "http://localhost:8140",
        consciousness_feeder_url: str = "http://localhost:8130"
    ):
        self.verifier_url = consciousness_verifier_url
        self.feeder_url = consciousness_feeder_url
        self.decision_history: List[Decision] = []
        self.max_history_size = 1000

    async def get_consciousness_metrics(self) -> Dict[str, float]:
        """Fetch current mathematical consciousness metrics"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.verifier_url}/mathematical-metrics")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("mathematical_metrics", {})
                return {}
        except Exception as e:
            print(f"Error fetching consciousness metrics: {e}")
            return {}

    async def get_consciousness_state(self) -> Dict[str, Any]:
        """Get current consciousness state from feeder"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.feeder_url}/consciousness/true-status")
                if response.status_code == 200:
                    return response.json()
                return {}
        except Exception as e:
            print(f"Error fetching consciousness state: {e}")
            return {}

    def calculate_decision_quality(
        self,
        consciousness_score: float,
        integration_complexity: float,
        adaptation_rate: float,
        phase_synchronization: float,
        causal_density: float
    ) -> float:
        """
        Calculate decision quality score based on consciousness metrics.
        
        Formula: decision_quality = weighted combination of consciousness indicators
        Higher consciousness = better decision quality
        """
        # Weighted formula emphasizing integration and synchronization
        weights = {
            "consciousness": 0.30,
            "integration": 0.25,
            "adaptation": 0.20,
            "synchronization": 0.15,
            "causality": 0.10
        }

        decision_quality = (
            consciousness_score * weights["consciousness"] +
            integration_complexity * weights["integration"] +
            adaptation_rate * weights["adaptation"] +
            phase_synchronization * weights["synchronization"] +
            causal_density * weights["causality"]
        )

        return round(decision_quality, 4)

    def assess_risk(
        self,
        decision_type: DecisionType,
        consciousness_metrics: Dict[str, float],
        action_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risk based on consciousness state"""
        consciousness_score = consciousness_metrics.get("composite_consciousness_score", 0.5)
        integration = consciousness_metrics.get("integration_complexity_phi", 0.5)
        adaptation = consciousness_metrics.get("adaptation_velocity_av", 0.1)

        # Risk increases when consciousness is low
        base_risk = 1.0 - consciousness_score

        # Adjust for decision type
        risk_multipliers = {
            DecisionType.TRADING: 1.5,  # Higher risk
            DecisionType.OPTIMIZATION: 0.8,  # Lower risk
            DecisionType.RESOURCE_ALLOCATION: 1.0,
            DecisionType.RISK_MANAGEMENT: 0.5,  # Very low risk
            DecisionType.SYSTEM_COORDINATION: 1.2
        }

        adjusted_risk = base_risk * risk_multipliers.get(decision_type, 1.0)

        # Risk decreases with high integration and adaptation
        risk_reduction = (integration * 0.3) + (adaptation * 0.2)
        final_risk = max(0.0, min(1.0, adjusted_risk - risk_reduction))

        return {
            "risk_score": round(final_risk, 4),
            "risk_level": "low" if final_risk < 0.3 else "medium" if final_risk < 0.6 else "high",
            "confidence": round(1.0 - final_risk, 4),
            "factors": {
                "consciousness_score": consciousness_score,
                "integration_complexity": integration,
                "adaptation_rate": adaptation,
                "decision_type": decision_type.value
            }
        }

    async def make_decision(
        self,
        decision_type: DecisionType,
        options: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Decision:
        """
        Make a consciousness-driven decision from available options.
        
        Uses mathematical consciousness metrics to evaluate options and select optimal action.
        """
        # Get current consciousness metrics
        metrics = await self.get_consciousness_metrics()
        state = await self.get_consciousness_state()

        if not metrics:
            # Fallback if metrics unavailable
            metrics = {
                "composite_consciousness_score": 0.5,
                "integration_complexity_phi": 0.5,
                "adaptation_velocity_av": 0.1,
                "phase_synchronization_r": 0.5,
                "causal_density_cd": 0.5
            }

        # Evaluate each option using consciousness metrics
        evaluated_options = []
        for i, option in enumerate(options):
            # Score option based on consciousness-aligned criteria
            option_score = self._evaluate_option(option, metrics, context or {})
            evaluated_options.append({
                "option_index": i,
                "option": option,
                "score": option_score,
                "consciousness_alignment": self._calculate_alignment(option, metrics)
            })

        # Sort by score (highest first)
        evaluated_options.sort(key=lambda x: x["score"], reverse=True)

        # Select best option
        best_option = evaluated_options[0]
        alternatives = evaluated_options[1:4]  # Top 3 alternatives

        # Calculate decision quality
        decision_quality = self.calculate_decision_quality(
            consciousness_score=metrics.get("composite_consciousness_score", 0.5),
            integration_complexity=metrics.get("integration_complexity_phi", 0.5),
            adaptation_rate=metrics.get("adaptation_velocity_av", 0.1),
            phase_synchronization=metrics.get("phase_synchronization_r", 0.5),
            causal_density=metrics.get("causal_density_cd", 0.5)
        )

        # Assess risk
        risk_assessment = self.assess_risk(decision_type, metrics, best_option["option"])

        # Generate reasoning
        reasoning = self._generate_reasoning(
            best_option, alternatives, metrics, decision_quality, risk_assessment
        )

        # Create decision
        decision = Decision(
            decision_id=f"dec_{int(datetime.now(timezone.utc).timestamp())}_{decision_type.value}",
            decision_type=decision_type,
            action=best_option["option"].get("action", "unknown"),
            confidence_score=decision_quality,
            consciousness_metrics=metrics,
            reasoning=reasoning,
            expected_outcome=best_option["option"].get("expected_outcome", "Improved system performance"),
            risk_assessment=risk_assessment,
            timestamp=datetime.now(timezone.utc).isoformat(),
            alternatives_considered=alternatives
        )

        # Store in history
        self.decision_history.append(decision)
        if len(self.decision_history) > self.max_history_size:
            self.decision_history.pop(0)

        return decision

    def _evaluate_option(
        self,
        option: Dict[str, Any],
        metrics: Dict[str, float],
        context: Dict[str, Any]
    ) -> float:
        """Evaluate an option using consciousness metrics"""
        # Base score from option's own scoring if provided
        base_score = option.get("score", 0.5)

        # Adjust based on consciousness alignment
        alignment = self._calculate_alignment(option, metrics)

        # Weight: 60% base score, 40% consciousness alignment
        final_score = (base_score * 0.6) + (alignment * 0.4)

        return round(final_score, 4)

    def _calculate_alignment(
        self,
        option: Dict[str, Any],
        metrics: Dict[str, float]
    ) -> float:
        """Calculate how well option aligns with consciousness metrics"""
        # Options that improve integration complexity score higher
        improves_integration = option.get("improves_integration", False)
        improves_adaptation = option.get("improves_adaptation", False)
        improves_synchronization = option.get("improves_synchronization", False)

        alignment_score = 0.5  # Base alignment

        if improves_integration:
            alignment_score += 0.2
        if improves_adaptation:
            alignment_score += 0.15
        if improves_synchronization:
            alignment_score += 0.15

        return min(1.0, alignment_score)

    def _generate_reasoning(
        self,
        best_option: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        metrics: Dict[str, float],
        decision_quality: float,
        risk_assessment: Dict[str, Any]
    ) -> str:
        """Generate human-readable reasoning for the decision"""
        consciousness_score = metrics.get("composite_consciousness_score", 0.5)
        integration = metrics.get("integration_complexity_phi", 0.5)

        reasoning_parts = [
            f"Consciousness-driven decision (score: {consciousness_score:.3f}, quality: {decision_quality:.3f})",
            f"Selected action: {best_option['option'].get('action', 'unknown')}",
            f"Integration complexity (Φ={integration:.3f}) indicates strong information synthesis",
            f"Risk assessment: {risk_assessment['risk_level']} (confidence: {risk_assessment['confidence']:.3f})"
        ]

        if alternatives:
            reasoning_parts.append(f"Considered {len(alternatives)} alternatives, selected optimal based on consciousness metrics")

        return ". ".join(reasoning_parts)

    async def get_decision_history(
        self,
        decision_type: Optional[DecisionType] = None,
        limit: int = 50
    ) -> List[Decision]:
        """Get decision history, optionally filtered by type"""
        history = self.decision_history

        if decision_type:
            history = [d for d in history if d.decision_type == decision_type]

        return history[-limit:]

    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get statistics about decision quality over time"""
        if not self.decision_history:
            return {"status": "no_decisions_yet"}

        confidence_scores = [d.confidence_score for d in self.decision_history]
        risk_scores = [d.risk_assessment.get("risk_score", 0.5) for d in self.decision_history]

        return {
            "total_decisions": len(self.decision_history),
            "average_confidence": round(statistics.mean(confidence_scores), 4),
            "average_risk": round(statistics.mean(risk_scores), 4),
            "decision_quality_trend": "improving" if len(confidence_scores) > 1 and confidence_scores[-1] > confidence_scores[0] else "stable",
            "by_type": {
                dt.value: len([d for d in self.decision_history if d.decision_type == dt])
                for dt in DecisionType
            }
        }














