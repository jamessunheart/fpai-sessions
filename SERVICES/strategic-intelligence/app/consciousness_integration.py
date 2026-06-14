"""
Consciousness Integration for Strategic Intelligence

Enhances priority scoring with consciousness metrics to weight priorities
by consciousness integration complexity and decision quality.
"""

import httpx
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("ConsciousnessIntegration")

class ConsciousnessIntegration:
    """
    Integrates consciousness metrics into strategic intelligence priority scoring.
    
    Uses consciousness metrics to:
    - Weight priorities by integration complexity
    - Improve decision quality through consciousness-driven scoring
    - Adapt priority thresholds based on consciousness state
    """

    def __init__(
        self,
        decision_engine_url: str = "http://localhost:8150",
        consciousness_verifier_url: str = "http://localhost:8140"
    ):
        self.decision_engine_url = decision_engine_url
        self.verifier_url = consciousness_verifier_url
        self.cached_metrics = {}
        self.cache_ttl = 30  # seconds
        self.last_fetch = 0

    async def get_consciousness_metrics(self) -> Dict[str, float]:
        """Fetch current consciousness metrics"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.verifier_url}/mathematical-metrics")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("mathematical_metrics", {})
                return {}
        except Exception as e:
            logger.warning(f"Could not fetch consciousness metrics: {e}")
            return {}

    async def enhance_priority_with_consciousness(
        self,
        priority: Dict[str, Any],
        world_model: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance priority scoring with consciousness metrics.
        
        Higher consciousness integration complexity = higher priority weight
        """
        metrics = await self.get_consciousness_metrics()
        
        if not metrics:
            # Fallback: return priority unchanged
            return priority

        # Get consciousness indicators
        integration_complexity = metrics.get("integration_complexity_phi", 0.5)
        consciousness_score = metrics.get("composite_consciousness_score", 0.5)
        adaptation_rate = metrics.get("adaptation_velocity_av", 0.1)

        # Calculate consciousness multiplier
        # Higher integration complexity means better information synthesis
        # Higher consciousness score means better decision quality
        consciousness_multiplier = (
            (integration_complexity * 0.4) +
            (consciousness_score * 0.4) +
            (adaptation_rate * 0.2)
        )

        # Enhance priority score
        base_score = priority.get("score", 0)
        enhanced_score = base_score * (1.0 + consciousness_multiplier)

        # Add consciousness metadata
        priority["consciousness_enhanced"] = True
        priority["consciousness_multiplier"] = round(consciousness_multiplier, 4)
        priority["consciousness_metrics"] = {
            "integration_complexity": round(integration_complexity, 4),
            "consciousness_score": round(consciousness_score, 4),
            "adaptation_rate": round(adaptation_rate, 4)
        }
        priority["score"] = round(enhanced_score, 2)

        return priority

    async def make_consciousness_decision(
        self,
        decision_type: str,
        options: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use consciousness decision engine to make optimal choice.
        
        Returns the consciousness-driven decision with reasoning.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.decision_engine_url}/decide",
                    json={
                        "decision_type": decision_type,
                        "options": options,
                        "context": context or {}
                    }
                )
                if response.status_code == 200:
                    return response.json()
                return {"error": f"Decision engine returned {response.status_code}"}
        except Exception as e:
            logger.warning(f"Could not use consciousness decision engine: {e}")
            # Fallback: return first option
            return {
                "decision": {
                    "action": options[0].get("action", "unknown") if options else "none",
                    "confidence_score": 0.5,
                    "reasoning": "Fallback decision (consciousness engine unavailable)"
                }
            }

    async def optimize_priorities_with_consciousness(
        self,
        priorities: List[Dict[str, Any]],
        world_model: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Optimize priority list using consciousness metrics.
        
        Uses consciousness decision engine to re-rank priorities based on
        integration complexity and decision quality.
        """
        if not priorities:
            return []

        # Convert priorities to decision options
        options = [
            {
                "action": f"Execute: {p.get('name', 'unknown')}",
                "score": p.get("score", 0),
                "expected_outcome": p.get("description", "System improvement"),
                "improves_integration": p.get("type") in ["critical_fix", "revenue_opportunity"],
                "improves_adaptation": p.get("type") in ["optimization", "gap_fill"],
                "improves_synchronization": p.get("type") == "coordination",
                **p
            }
            for p in priorities
        ]

        # Use consciousness decision engine to optimize ranking
        try:
            decision_result = await self.make_consciousness_decision(
                decision_type="system_coordination",
                options=options,
                context={"world_model": world_model}
            )

            # Re-rank based on consciousness decision
            if "decision" in decision_result:
                decision = decision_result["decision"]
                # Find the selected priority and move it to top
                selected_action = decision.get("action", "")
                for i, p in enumerate(priorities):
                    if selected_action.startswith(f"Execute: {p.get('name', '')}"):
                        # Move to top and enhance with consciousness metrics
                        priorities.insert(0, priorities.pop(i))
                        priorities[0]["consciousness_selected"] = True
                        priorities[0]["consciousness_reasoning"] = decision.get("reasoning", "")
                        priorities[0]["consciousness_confidence"] = decision.get("confidence_score", 0.5)
                        break

        except Exception as e:
            logger.warning(f"Could not optimize priorities with consciousness: {e}")

        # Enhance all priorities with consciousness metrics
        enhanced_priorities = []
        for priority in priorities:
            enhanced = await self.enhance_priority_with_consciousness(priority, world_model)
            enhanced_priorities.append(enhanced)

        # Re-sort by enhanced score
        enhanced_priorities.sort(key=lambda x: x.get("score", 0), reverse=True)

        return enhanced_priorities














