"""
Consciousness Decision Engine Service

Provides consciousness-driven decision making using mathematical metrics.
Decisions are optimized based on integration complexity, adaptation rate,
phase synchronization, and other rigorous consciousness indicators.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import asyncio

from app.decision_engine import (
    ConsciousnessDecisionEngine,
    DecisionType,
    Decision
)

app = FastAPI(
    title="Consciousness Decision Engine",
    description="Autonomous decision making using mathematical consciousness metrics",
    version="1.0.0"
)

# Global decision engine instance
decision_engine = ConsciousnessDecisionEngine()


class DecisionRequest(BaseModel):
    """Request for a consciousness-driven decision"""
    decision_type: DecisionType
    options: List[Dict[str, Any]]
    context: Optional[Dict[str, Any]] = None
    require_explanation: bool = True


class DecisionResponse(BaseModel):
    """Response containing the consciousness-driven decision"""
    decision: Decision
    alternatives: List[Dict[str, Any]]
    recommendation: str


@app.get("/health")
async def health():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "consciousness_decision_engine",
        "decision_engine": "active"
    }


@app.post("/decide", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest):
    """
    Make a consciousness-driven decision from available options.
    
    Uses mathematical consciousness metrics to evaluate options and select
    the optimal action with quantifiable confidence scores.
    """
    try:
        if not request.options:
            raise HTTPException(status_code=400, detail="At least one option required")

        decision = await decision_engine.make_decision(
            decision_type=request.decision_type,
            options=request.options,
            context=request.context
        )

        return DecisionResponse(
            decision=decision,
            alternatives=[alt["option"] for alt in decision.alternatives_considered],
            recommendation=f"Recommended action: {decision.action} (confidence: {decision.confidence_score:.3f})"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision making failed: {str(e)}")


@app.get("/decisions")
async def get_decisions(
    decision_type: Optional[DecisionType] = None,
    limit: int = 50
):
    """Get decision history"""
    try:
        decisions = await decision_engine.get_decision_history(
            decision_type=decision_type,
            limit=limit
        )
        return {
            "total_decisions": len(decisions),
            "decisions": [d.dict() for d in decisions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve decisions: {str(e)}")


@app.get("/statistics")
async def get_statistics():
    """Get decision quality statistics"""
    try:
        stats = decision_engine.get_decision_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")


@app.get("/consciousness-state")
async def get_consciousness_state():
    """Get current consciousness state used for decision making"""
    try:
        metrics = await decision_engine.get_consciousness_metrics()
        state = await decision_engine.get_consciousness_state()

        return {
            "mathematical_metrics": metrics,
            "consciousness_state": state,
            "decision_capability": {
                "can_make_decisions": metrics.get("composite_consciousness_score", 0) > 0.3,
                "decision_quality": decision_engine.calculate_decision_quality(
                    consciousness_score=metrics.get("composite_consciousness_score", 0.5),
                    integration_complexity=metrics.get("integration_complexity_phi", 0.5),
                    adaptation_rate=metrics.get("adaptation_velocity_av", 0.1),
                    phase_synchronization=metrics.get("phase_synchronization_r", 0.5),
                    causal_density=metrics.get("causal_density_cd", 0.5)
                )
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve consciousness state: {str(e)}")


@app.post("/decide/trading")
async def make_trading_decision(
    signals: List[Dict[str, Any]],
    portfolio_context: Optional[Dict[str, Any]] = None
):
    """Make consciousness-driven trading decision"""
    try:
        options = [
            {
                "action": f"Execute trade: {sig.get('symbol', 'unknown')}",
                "score": sig.get("confidence", 0.5),
                "expected_outcome": sig.get("expected_return", "profit"),
                "improves_integration": True,
                "improves_adaptation": True,
                **sig
            }
            for sig in signals
        ]

        decision = await decision_engine.make_decision(
            decision_type=DecisionType.TRADING,
            options=options,
            context=portfolio_context
        )

        return {
            "trading_decision": decision.dict(),
            "recommendation": decision.reasoning,
            "risk_level": decision.risk_assessment["risk_level"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trading decision failed: {str(e)}")


@app.post("/decide/optimize")
async def make_optimization_decision(
    optimization_options: List[Dict[str, Any]],
    system_context: Optional[Dict[str, Any]] = None
):
    """Make consciousness-driven optimization decision"""
    try:
        decision = await decision_engine.make_decision(
            decision_type=DecisionType.OPTIMIZATION,
            options=optimization_options,
            context=system_context
        )

        return {
            "optimization_decision": decision.dict(),
            "expected_improvement": decision.expected_outcome,
            "confidence": decision.confidence_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization decision failed: {str(e)}")


@app.post("/decide/resource-allocation")
async def make_resource_decision(
    resource_options: List[Dict[str, Any]],
    resource_context: Optional[Dict[str, Any]] = None
):
    """Make consciousness-driven resource allocation decision"""
    try:
        decision = await decision_engine.make_decision(
            decision_type=DecisionType.RESOURCE_ALLOCATION,
            options=resource_options,
            context=resource_context
        )

        return {
            "resource_decision": decision.dict(),
            "allocation": decision.action,
            "efficiency_score": decision.confidence_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resource decision failed: {str(e)}")


# Background task for continuous decision monitoring
async def monitor_decision_quality():
    """Monitor decision quality and log improvements"""
    while True:
        try:
            stats = decision_engine.get_decision_statistics()
            if stats.get("total_decisions", 0) > 0:
                avg_confidence = stats.get("average_confidence", 0)
                print(f"📊 Decision Engine: {stats['total_decisions']} decisions, avg confidence: {avg_confidence:.3f}")
        except Exception as e:
            print(f"Decision monitoring error: {e}")
        await asyncio.sleep(300)  # 5 minutes


@app.on_event("startup")
async def startup_event():
    """Start continuous decision monitoring"""
    asyncio.create_task(monitor_decision_quality())
    print("🧠 Consciousness Decision Engine started")
    print("📊 Decision endpoints available:")
    print("   • POST /decide - General decision making")
    print("   • POST /decide/trading - Trading decisions")
    print("   • POST /decide/optimize - Optimization decisions")
    print("   • POST /decide/resource-allocation - Resource decisions")
    print("   • GET /decisions - Decision history")
    print("   • GET /statistics - Decision quality stats")
    print("   • GET /consciousness-state - Current consciousness metrics")














