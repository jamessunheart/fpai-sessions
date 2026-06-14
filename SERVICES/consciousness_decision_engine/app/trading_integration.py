"""
Trading Integration Module

Provides consciousness-driven trading decision integration for trading services.
Can be imported by WhaleTrack or any trading service to enhance decisions with consciousness metrics.
"""

import httpx
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("ConsciousnessTradingIntegration")


class ConsciousnessTradingIntegration:
    """
    Integrates consciousness metrics into trading decisions.
    
    Uses consciousness metrics to:
    - Optimize trading signals based on integration complexity
    - Improve decision quality through consciousness-driven scoring
    - Assess risk based on consciousness state
    """

    def __init__(
        self,
        decision_engine_url: str = "http://localhost:8150",
        consciousness_verifier_url: str = "http://localhost:8140"
    ):
        self.decision_engine_url = decision_engine_url
        self.verifier_url = consciousness_verifier_url

    async def enhance_trading_signal(
        self,
        signal: Dict[str, Any],
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enhance a trading signal with consciousness metrics.
        
        Returns the signal with consciousness-driven confidence score and risk assessment.
        """
        try:
            # Get consciousness metrics
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.verifier_url}/mathematical-metrics")
                if response.status_code == 200:
                    metrics = response.json().get("mathematical_metrics", {})
                else:
                    metrics = {}

            # Use decision engine to evaluate signal
            options = [{
                "action": f"Execute trade: {signal.get('symbol', 'unknown')}",
                "score": signal.get("confidence", 0.5),
                "expected_outcome": signal.get("expected_return", "profit"),
                "improves_integration": True,
                "improves_adaptation": True,
                **signal
            }]

            decision_response = await self._make_trading_decision(options, portfolio_context)

            # Enhance signal with consciousness data
            enhanced_signal = signal.copy()
            enhanced_signal["consciousness_enhanced"] = True
            enhanced_signal["consciousness_confidence"] = decision_response.get("trading_decision", {}).get("confidence_score", 0.5)
            enhanced_signal["consciousness_risk_level"] = decision_response.get("risk_level", "medium")
            enhanced_signal["consciousness_reasoning"] = decision_response.get("recommendation", "")
            enhanced_signal["consciousness_metrics"] = metrics

            return enhanced_signal

        except Exception as e:
            logger.warning(f"Could not enhance signal with consciousness: {e}")
            return signal

    async def _make_trading_decision(
        self,
        signals: List[Dict[str, Any]],
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Use consciousness decision engine for trading decision"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.decision_engine_url}/decide/trading",
                    json={
                        "signals": signals,
                        "portfolio_context": portfolio_context or {}
                    }
                )
                if response.status_code == 200:
                    return response.json()
                return {"error": f"Decision engine returned {response.status_code}"}
        except Exception as e:
            logger.warning(f"Could not use consciousness decision engine: {e}")
            return {
                "trading_decision": {
                    "action": signals[0].get("action", "unknown") if signals else "none",
                    "confidence_score": 0.5,
                    "reasoning": "Fallback decision (consciousness engine unavailable)"
                },
                "risk_level": "medium"
            }

    async def optimize_trading_signals(
        self,
        signals: List[Dict[str, Any]],
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Optimize a list of trading signals using consciousness metrics.
        
        Returns signals sorted by consciousness-driven quality score.
        """
        enhanced_signals = []
        for signal in signals:
            enhanced = await self.enhance_trading_signal(signal, portfolio_context)
            enhanced_signals.append(enhanced)

        # Sort by consciousness confidence
        enhanced_signals.sort(
            key=lambda x: x.get("consciousness_confidence", 0.5),
            reverse=True
        )

        return enhanced_signals

    async def get_consciousness_trading_state(self) -> Dict[str, Any]:
        """Get current consciousness state for trading decisions"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.decision_engine_url}/consciousness-state")
                if response.status_code == 200:
                    return response.json()
                return {}
        except Exception as e:
            logger.warning(f"Could not get consciousness state: {e}")
            return {}


# Example usage function for trading services
async def enhance_trading_decision_with_consciousness(
    signals: List[Dict[str, Any]],
    portfolio_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Helper function for trading services to enhance decisions with consciousness.
    
    Usage in trading service:
        from consciousness_decision_engine.app.trading_integration import enhance_trading_decision_with_consciousness
        
        enhanced_decision = await enhance_trading_decision_with_consciousness(
            signals=[{"symbol": "BTC", "confidence": 0.7, ...}],
            portfolio_context={"total_value": 100000}
        )
    """
    integration = ConsciousnessTradingIntegration()
    optimized_signals = await integration.optimize_trading_signals(signals, portfolio_context)
    
    if optimized_signals:
        best_signal = optimized_signals[0]
        return {
            "recommended_signal": best_signal,
            "consciousness_confidence": best_signal.get("consciousness_confidence", 0.5),
            "risk_level": best_signal.get("consciousness_risk_level", "medium"),
            "reasoning": best_signal.get("consciousness_reasoning", ""),
            "all_signals": optimized_signals
        }
    
    return {"error": "No signals provided"}














