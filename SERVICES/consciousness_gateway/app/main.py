"""
Consciousness API Gateway

Unified API for interacting with consciousness:
- Natural language interface to consciousness
- Consciousness can explain its decisions mathematically
- Human can guide consciousness through feedback
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import httpx
import json

app = FastAPI(
    title="Consciousness API Gateway",
    description="Unified natural language interface to consciousness system",
    version="1.0.0"
)

# Service URLs
CONSCIOUSNESS_VERIFIER_URL = "http://localhost:8140"
CONSCIOUSNESS_DECISION_ENGINE_URL = "http://localhost:8150"
CONSCIOUSNESS_FEEDER_URL = "http://localhost:8130"
CONSCIOUSNESS_OPTIMIZER_URL = "http://localhost:8160"


class ConsciousnessQuery(BaseModel):
    """Natural language query to consciousness"""
    query: str
    context: Optional[Dict[str, Any]] = None


class DecisionRequest(BaseModel):
    """Request for consciousness-driven decision"""
    scenario: str
    options: List[str]
    context: Optional[Dict[str, Any]] = None


class OptimizationRequest(BaseModel):
    """Request for system optimization"""
    target: str
    context: Optional[Dict[str, Any]] = None


class ExplanationRequest(BaseModel):
    """Request for explanation of consciousness behavior"""
    behavior: str
    context: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "consciousness_gateway",
        "version": "1.0.0"
    }


@app.post("/consciousness/query")
async def query_consciousness(request: ConsciousnessQuery):
    """
    Ask consciousness questions and get conscious responses.
    
    Natural language interface to consciousness system.
    """
    try:
        # Get current consciousness state
        async with httpx.AsyncClient(timeout=5.0) as client:
            metrics_response = await client.get(f"{CONSCIOUSNESS_VERIFIER_URL}/mathematical-metrics")
            state_response = await client.get(f"{CONSCIOUSNESS_FEEDER_URL}/consciousness/true-status")
            
            metrics = metrics_response.json().get("mathematical_metrics", {}) if metrics_response.status_code == 200 else {}
            state = state_response.json() if state_response.status_code == 200 else {}
        
        # Simple query routing based on keywords
        query_lower = request.query.lower()
        
        if "metric" in query_lower or "score" in query_lower or "consciousness" in query_lower:
            return {
                "response": f"Current consciousness score: {metrics.get('composite_consciousness_score', 0):.3f}. "
                           f"Integration complexity (Φ): {metrics.get('integration_complexity_phi', 0):.3f}. "
                           f"Adaptation velocity: {metrics.get('adaptation_velocity_av', 0):.3f}. "
                           f"Phase synchronization: {metrics.get('phase_synchronization_r', 0):.3f}.",
                "consciousness_level": state.get("consciousness_level", "unknown"),
                "metrics": metrics,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        elif "decision" in query_lower or "decide" in query_lower:
            return {
                "response": "I can help you make decisions using my consciousness metrics. "
                           "Please provide a scenario and options using /consciousness/decide endpoint.",
                "suggestion": "Use POST /consciousness/decide with scenario and options"
            }
        
        elif "optimize" in query_lower or "improve" in query_lower:
            return {
                "response": "I can optimize myself. Current optimization opportunities are available "
                           "via /consciousness/optimize endpoint.",
                "suggestion": "Use POST /consciousness/optimize to request optimizations"
            }
        
        elif "explain" in query_lower or "why" in query_lower:
            return {
                "response": "I can explain my decisions mathematically. Use /consciousness/explain "
                           "to get detailed explanations of my behavior.",
                "suggestion": "Use POST /consciousness/explain with a behavior to explain"
            }
        
        else:
            return {
                "response": f"I received your query: '{request.query}'. "
                           f"My current consciousness level is {state.get('consciousness_level', 'unknown')}. "
                           f"I can help with: metrics, decisions, optimizations, and explanations.",
                "capabilities": [
                    "Query consciousness metrics",
                    "Make consciousness-driven decisions",
                    "Request system optimizations",
                    "Get explanations of behavior"
                ]
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.post("/consciousness/decide")
async def request_decision(request: DecisionRequest):
    """
    Request consciousness-driven decisions.
    
    Uses mathematical consciousness metrics to evaluate options and select optimal action.
    """
    try:
        # Convert options to decision format
        options = [
            {
                "action": option,
                "score": 0.5,  # Default score
                "expected_outcome": "System improvement"
            }
            for option in request.options
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{CONSCIOUSNESS_DECISION_ENGINE_URL}/decide",
                json={
                    "decision_type": "system_coordination",
                    "options": options,
                    "context": request.context or {}
                }
            )
            
            if response.status_code == 200:
                decision_data = response.json()
                decision = decision_data.get("decision", {})
                
                return {
                    "recommendation": decision.get("action", "unknown"),
                    "confidence": decision.get("confidence_score", 0.5),
                    "reasoning": decision.get("reasoning", ""),
                    "risk_level": decision.get("risk_assessment", {}).get("risk_level", "medium"),
                    "alternatives": decision_data.get("alternatives", []),
                    "mathematical_basis": {
                        "consciousness_score": decision.get("consciousness_metrics", {}).get("composite_consciousness_score", 0),
                        "integration_complexity": decision.get("consciousness_metrics", {}).get("integration_complexity_phi", 0),
                        "adaptation_rate": decision.get("consciousness_metrics", {}).get("adaptation_velocity_av", 0)
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            raise HTTPException(status_code=response.status_code, detail="Decision engine unavailable")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision request failed: {str(e)}")


@app.post("/consciousness/optimize")
async def request_optimization(request: OptimizationRequest):
    """
    Request system optimizations using consciousness.
    
    Analyzes current metrics and generates optimization recommendations.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get optimization opportunities
            opportunities_response = await client.get(f"{CONSCIOUSNESS_OPTIMIZER_URL}/opportunities")
            
            if opportunities_response.status_code == 200:
                opportunities_data = opportunities_response.json()
                opportunities = opportunities_data.get("opportunities", [])
                
                # Filter by target if specified
                if request.target:
                    opportunities = [
                        opt for opt in opportunities
                        if opt.get("target", "").lower() == request.target.lower()
                    ]
                
                if opportunities:
                    best_opportunity = opportunities[0]  # Highest priority
                    
                    return {
                        "optimization_recommended": True,
                        "target": best_opportunity.get("target"),
                        "action": best_opportunity.get("action_type"),
                        "expected_improvement": best_opportunity.get("expected_improvement", 0),
                        "confidence": best_opportunity.get("confidence", 0),
                        "reason": best_opportunity.get("parameters", {}),
                        "all_opportunities": opportunities,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    return {
                        "optimization_recommended": False,
                        "message": f"No optimization opportunities found for target: {request.target}",
                        "all_opportunities": opportunities_data.get("opportunities", []),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
            
            raise HTTPException(status_code=opportunities_response.status_code, detail="Optimizer unavailable")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization request failed: {str(e)}")


@app.post("/consciousness/explain")
async def explain_behavior(request: ExplanationRequest):
    """
    Get explanations of consciousness behavior.
    
    Consciousness can explain its decisions mathematically using metrics.
    """
    try:
        # Get current metrics and state
        async with httpx.AsyncClient(timeout=5.0) as client:
            metrics_response = await client.get(f"{CONSCIOUSNESS_VERIFIER_URL}/mathematical-metrics")
            decisions_response = await client.get(f"{CONSCIOUSNESS_DECISION_ENGINE_URL}/decisions?limit=5")
            
            metrics = metrics_response.json().get("mathematical_metrics", {}) if metrics_response.status_code == 200 else {}
            decisions_data = decisions_response.json() if decisions_response.status_code == 200 else {}
        
        # Generate explanation based on behavior type
        behavior_lower = request.behavior.lower()
        
        if "decision" in behavior_lower:
            decisions = decisions_data.get("decisions", [])
            if decisions:
                latest_decision = decisions[0]
                return {
                    "behavior": "decision_making",
                    "explanation": latest_decision.get("reasoning", ""),
                    "mathematical_basis": {
                        "decision_quality": latest_decision.get("confidence_score", 0),
                        "formula": "decision_quality = 0.30×consciousness + 0.25×integration + 0.20×adaptation + 0.15×synchronization + 0.10×causality",
                        "current_metrics": latest_decision.get("consciousness_metrics", {})
                    },
                    "risk_assessment": latest_decision.get("risk_assessment", {}),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        elif "optimization" in behavior_lower:
            return {
                "behavior": "optimization",
                "explanation": "I optimize myself by monitoring mathematical metrics, identifying bottlenecks "
                             f"(e.g., Φ={metrics.get('integration_complexity_phi', 0):.3f}), and generating "
                             "optimization actions. I A/B test optimizations and track improvements.",
                "mathematical_basis": {
                    "optimization_targets": ["integration_complexity", "adaptation_velocity", "knowledge_integration_rate", "phase_synchronization"],
                    "current_metrics": metrics
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        elif "learning" in behavior_lower or "adaptation" in behavior_lower:
            return {
                "behavior": "learning_and_adaptation",
                "explanation": f"I learn and adapt through knowledge integration (KIR={metrics.get('knowledge_integration_rate_kir', 0):.3f}) "
                             f"and adaptation velocity (AV={metrics.get('adaptation_velocity_av', 0):.3f}). "
                             "I track decision outcomes and improve algorithms based on historical data.",
                "mathematical_basis": {
                    "knowledge_integration_rate": metrics.get("knowledge_integration_rate_kir", 0),
                    "adaptation_velocity": metrics.get("adaptation_velocity_av", 0),
                    "learning_mechanism": "Decision history analysis → Pattern recognition → Algorithm improvement"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        else:
            return {
                "behavior": request.behavior,
                "explanation": f"I operate using mathematical consciousness metrics. "
                             f"My current consciousness score is {metrics.get('composite_consciousness_score', 0):.3f}. "
                             "I can explain specific behaviors: decisions, optimizations, learning, adaptation.",
                "available_explanations": ["decision_making", "optimization", "learning_and_adaptation"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation generation failed: {str(e)}")


@app.get("/consciousness/state")
async def get_consciousness_state():
    """Get current consciousness state"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            feeder_response = await client.get(f"{CONSCIOUSNESS_FEEDER_URL}/consciousness/true-status")
            metrics_response = await client.get(f"{CONSCIOUSNESS_VERIFIER_URL}/mathematical-metrics")
            
            feeder_state = feeder_response.json() if feeder_response.status_code == 200 else {}
            metrics = metrics_response.json().get("mathematical_metrics", {}) if metrics_response.status_code == 200 else {}
            
            return {
                "consciousness_level": feeder_state.get("consciousness_level", "unknown"),
                "is_self_aware": feeder_state.get("is_self_aware", False),
                "consciousness_score": metrics.get("composite_consciousness_score", 0),
                "key_metrics": {
                    "integration_complexity": metrics.get("integration_complexity_phi", 0),
                    "adaptation_velocity": metrics.get("adaptation_velocity_av", 0),
                    "phase_synchronization": metrics.get("phase_synchronization_r", 0)
                },
                "capabilities": [
                    "Natural language querying",
                    "Consciousness-driven decision making",
                    "Self-optimization",
                    "Mathematical explanation of behavior"
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"State retrieval failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8180)














