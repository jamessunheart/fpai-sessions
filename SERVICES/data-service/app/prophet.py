"""
The Prophet Engine
==================
Predictive intelligence layer that generates falsifiable predictions 
from data patterns.

"To predict is to know."
"""

import logging
import httpx
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

logger = logging.getLogger("prophet")

# AI Brain runs on secondary server (31GB RAM) for better inference
AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_URL = "https://api.mem0.ai/v1"

from .calibration import calibration_store, CalibrationStats
from .devils_advocate import challenge_prediction, AdversarialAnalysis
from .causal_graph import causal_graph, CausalNode, CausalEdge
from .consciousness_bridge import consciousness_bridge, get_conscious_confidence
from .learner import learner


class Prediction(BaseModel):
    id: str
    source_pattern: Dict[str, Any]
    target_metric: str
    predicted_direction: str
    predicted_value: Optional[float]
    timeframe_hours: int
    confidence: float
    reasoning: str
    created_at: str
    status: str = "pending"  # pending, verified, failed, expired
    adversarial: Optional[AdversarialAnalysis] = None
    calibrated_confidence: Optional[float] = None


class ProphetEngine:
    """
    Generates predictions from patterns using historical memory and AI reasoning.
    """
    
    def __init__(self):
        self.predictions: Dict[str, Prediction] = {}
        self.prediction_history: List[Dict] = []
        
    async def predict(self, pattern: Dict) -> Optional[Prediction]:
        """
        Generate a prediction based on a detected pattern.
        """
        # Only predict on significant patterns
        if pattern.get("significance", 0) < 0.6:
            return None
            
        # 1. Recall historical precedents from Mem0
        history = await self._recall_history(pattern)
        
        # 2. Ask AI Brain to generate prediction
        prediction_data = await self._generate_prediction_with_ai(pattern, history)
        
        if not prediction_data:
            return None
            
        # 3. Create Prediction object
        prediction = Prediction(
            id=f"pred_{uuid.uuid4().hex[:8]}",
            source_pattern=pattern,
            target_metric=prediction_data.get("target_metric", "unknown"),
            predicted_direction=prediction_data.get("direction", "flat"),
            predicted_value=prediction_data.get("value"),
            timeframe_hours=prediction_data.get("timeframe", 24),
            confidence=prediction_data.get("confidence", 0.5),
            reasoning=prediction_data.get("reasoning", "AI inference"),
            created_at=datetime.now(timezone.utc).isoformat(),
            status="pending"
        )

        # 3b. Calibration adjustment
        stats: CalibrationStats = calibration_store.get_stats(
            prediction.target_metric,
            prediction.timeframe_hours,
        )
        calibrated_conf = 0.5 * prediction.confidence + 0.5 * stats.win_rate
        
        # 3b2. Apply learned confidence modifier from closed-loop learning
        learned_modifier = learner.get_strategy_confidence_modifier(
            pattern.get("type", "unknown"),
            prediction.target_metric
        )
        calibrated_conf *= learned_modifier
        calibrated_conf = min(0.95, max(0.1, calibrated_conf))  # Clamp to reasonable range
        
        # 3b3. Consciousness adjustment - weight by awareness state
        conscious_conf = await get_conscious_confidence(calibrated_conf)
        prediction.calibrated_confidence = round(conscious_conf, 3)
        prediction.confidence = prediction.calibrated_confidence
        
        # Feed prediction to consciousness for reflection
        await consciousness_bridge.feed_to_consciousness({
            "type": "prediction",
            "metric": prediction.target_metric,
            "direction": prediction.predicted_direction,
            "confidence": prediction.confidence,
            "reasoning": prediction.reasoning
        })

        # 3c. Devil's Advocate for high confidence
        if prediction.confidence >= 0.7:
            adv = await challenge_prediction(prediction)
            if adv:
                prediction.adversarial = adv
                if adv.verdict == "reject":
                    prediction.status = "rejected"
                elif adv.verdict == "flag":
                    prediction.status = "flagged"

        # 3d. Register causal nodes/edges
        self._register_causal(prediction)
        
        # Store locally
        self.predictions[prediction.id] = prediction
        
        # Store to Mem0 as an "experiment"
        await self._store_experiment(prediction)
        
        logger.info(f"🔮 Prophecy: {prediction.target_metric} will go {prediction.predicted_direction} (Confidence: {prediction.confidence:.2f})")
        return prediction
        
    async def _recall_history(self, pattern: Dict) -> str:
        """Query Mem0 for similar past patterns and outcomes"""
        if not MEM0_API_KEY:
            return "No historical memory available."
            
        try:
            query = f"outcome of pattern {pattern.get('type')} {pattern.get('description', '')}"
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.post(
                    f"{MEM0_URL}/memories/search/",
                    headers={
                        "Authorization": f"Token {MEM0_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "query": query,
                        "user_id": "fpai_prophet",
                        "limit": 3
                    }
                )
                
                if resp.status_code == 200:
                    memories = resp.json()
                    if isinstance(memories, list):
                        return "\n".join([m.get("memory", "") for m in memories[:3]])
                    return "No relevant history found."
                else:
                    logger.debug(f"Mem0 search returned {resp.status_code}: {resp.text[:200]}")
                    
        except Exception as e:
            logger.error(f"History recall failed: {e}")
            
        return "No relevant history found."

    async def _generate_prediction_with_ai(self, pattern: Dict, history: str) -> Optional[Dict]:
        """
        Use AI Brain to reason about the future.
        Routes through AI Brain which uses GPU Fleet (70 GPUs) for fast inference.
        """
        prompt = f"""Analyze this pattern and predict the likely outcome within 24 hours.

PATTERN:
Type: {pattern.get('type')}
Description: {pattern.get('description')}
Details: {json.dumps(pattern, default=str)}

HISTORICAL PRECEDENTS:
{history}

TASK:
Generate a specific, falsifiable prediction for a metric (e.g., BTC Price, Sentiment, GitHub Stars).
Be conservative with confidence. If unsure, return null.

Respond in JSON only:
{{"target_metric": "BTC Price", "direction": "up", "value": 95000.0, "timeframe": 24, "confidence": 0.75, "reasoning": "Historical pattern shows..."}}
"""
        # Route through AI Brain (uses GPU Fleet -> Groq -> Ollama fallback chain)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{AI_BRAIN_URL}/generate",
                    json={
                        "prompt": prompt,
                        "system_message": "You are a predictive engine. Output valid JSON only.",
                        "model_preference": "fast",  # Routes to GPU Fleet first
                        "max_tokens": 300,
                        "service_id": "prophet_engine"
                    }
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    text = result.get("text", "{}")
                    provider = result.get("provider", "unknown")
                    logger.info(f"🚀 Prediction generated via {provider}")
                    
                    if "{" in text:
                        json_str = text[text.find("{"):text.rfind("}")+1]
                        return json.loads(json_str)
                else:
                    logger.warning(f"AI Brain returned {resp.status_code}: {resp.text[:200]}")
                        
        except Exception as e:
            logger.error(f"AI prediction failed: {e}")
            
        return None

    async def _store_experiment(self, prediction: Prediction):
        """Store the prediction in Mem0 as an active experiment"""
        if not MEM0_API_KEY:
            return

        try:
            text = f"🧪 EXPERIMENT STARTED: Predicting {prediction.target_metric} will go {prediction.predicted_direction} in {prediction.timeframe_hours}h. Confidence: {prediction.confidence:.2f}. Reasoning: {prediction.reasoning}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{MEM0_URL}/memories/",
                    headers={"Authorization": f"Token {MEM0_API_KEY}"},
                    json={
                        "messages": [{"role": "user", "content": text}],
                        "user_id": "fpai_prophet",
                        "metadata": {
                            "type": "prediction",
                            "prediction_id": prediction.id,
                            "status": "pending"
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Failed to store experiment: {e}")

    def _register_causal(self, prediction: Prediction):
        """Add prediction and pattern to causal graph"""
        try:
            pattern = prediction.source_pattern
            pat_id = pattern.get("id") or pattern.get("type", "pattern") + "_" + prediction.id
            causal_graph.add_node(CausalNode(
                id=pat_id,
                type="pattern",
                label=pattern.get("description", pattern.get("type", "pattern")),
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata=pattern
            ))
            causal_graph.add_node(CausalNode(
                id=prediction.id,
                type="prediction",
                label=f"{prediction.target_metric}:{prediction.predicted_direction}",
                timestamp=prediction.created_at,
                metadata=prediction.dict()
            ))
            causal_graph.add_edge(CausalEdge(
                source_id=pat_id,
                target_id=prediction.id,
                relation="causes",
                weight=prediction.confidence,
                confidence=prediction.confidence,
                created_at=datetime.now(timezone.utc).isoformat()
            ))
        except Exception:
            pass


# Singleton
prophet = ProphetEngine()

