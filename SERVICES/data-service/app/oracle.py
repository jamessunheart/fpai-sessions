"""
The Oracle
==========
Verifies predictions against reality.
The impartial judge of truth.
"""

import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import json
import os

from .prophet import Prediction, prophet
from .calibration import PredictionOutcome, calibration_store
from .causal_graph import causal_graph, CausalNode, CausalEdge
from .learner import learner

logger = logging.getLogger("oracle")

WHALETRACK_URL = "http://localhost:8600"
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_URL = "https://api.mem0.ai/v1"


class Oracle:
    """
    Checks predictions against real-world data and scores accuracy.
    """
    
    async def verify_all(self) -> List[Dict]:
        """Verify all pending predictions that have matured"""
        results = []
        
        now = datetime.now(timezone.utc)
        
        for pred_id, prediction in list(prophet.predictions.items()):
            if prediction.status != "pending":
                continue
                
            # Check if time has passed
            created = datetime.fromisoformat(prediction.created_at.replace("Z", "+00:00"))
            deadline = created + timedelta(hours=prediction.timeframe_hours)
            
            if now >= deadline:
                result = await self.verify_prediction(prediction)
                results.append(result)
                
        return results
    
    async def verify_prediction(self, prediction: Prediction) -> Dict:
        """Verify a single prediction"""
        actual_value = await self.get_actual_value(prediction.target_metric)
        
        if actual_value is None:
            logger.warning(f"Could not verify {prediction.target_metric}")
            return {"id": prediction.id, "status": "unverifiable"}
            
        # Determine outcome
        passed = False
        start_value = prediction.source_pattern.get("start_value") if isinstance(prediction.source_pattern, dict) else None
        if start_value is None:
            start_value = prediction.predicted_value or actual_value

        if prediction.predicted_direction == "up":
            passed = actual_value > start_value
        elif prediction.predicted_direction == "down":
            passed = actual_value < start_value

        # Specific target check with margin
        if prediction.predicted_value:
            margin = abs(prediction.predicted_value) * 0.05
            passed = abs(actual_value - prediction.predicted_value) <= margin
            
        status = "verified" if passed else "failed"
        
        # Update prediction status
        prediction.status = status
        
        # Store outcome
        outcome = {
            "id": prediction.id,
            "metric": prediction.target_metric,
            "predicted": f"{prediction.predicted_direction} ({prediction.predicted_value})",
            "actual": actual_value,
            "result": status,
            "confidence": prediction.confidence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Calibration update
        calibration_store.update_stats(PredictionOutcome(
            prediction_id=prediction.id,
            target_metric=prediction.target_metric,
            predicted_direction=prediction.predicted_direction,
            predicted_value=prediction.predicted_value,
            actual_value=actual_value,
            result=status,
            confidence=prediction.confidence,
            error_abs=abs(actual_value - prediction.predicted_value) if prediction.predicted_value else None,
            created_at=datetime.now(timezone.utc),
            timeframe_hours=prediction.timeframe_hours
        ))

        # Causal update: outcome node and edge
        try:
            causal_graph.add_node(CausalNode(
                id=f"outcome_{prediction.id}",
                type="outcome",
                label=f"{prediction.target_metric}:{status}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata=outcome
            ))
            causal_graph.add_edge(CausalEdge(
                source_id=prediction.id,
                target_id=f"outcome_{prediction.id}",
                relation="results_in",
                weight=1.0,
                confidence=1.0,
                created_at=datetime.now(timezone.utc).isoformat()
            ))
        except Exception:
            pass

        # Feed outcome to learner for closed-loop learning
        await learner.record_outcome(
            prediction.dict(),
            {
                **outcome,
                "actual_direction": "up" if actual_value > (start_value or 0) else "down",
                "verified_at": datetime.now(timezone.utc).isoformat()
            }
        )

        await self._record_learning(prediction, outcome)
        
        logger.info(f"⚖️ Oracle Judgement: {prediction.target_metric} prediction {status.upper()}. (Pred: {prediction.predicted_direction}, Actual: {actual_value})")
        
        return outcome
    
    async def get_actual_value(self, metric: str) -> Optional[float]:
        """Get real-time value for a metric"""
        metric = metric.lower()
        
        try:
            # Crypto Prices
            if "btc" in metric or "bitcoin" in metric:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{WHALETRACK_URL}/api/state")
                    if resp.status_code == 200:
                        return resp.json().get("hero", {}).get("price")
            
            # Hacker News Score (requires fetching current top story)
            # Implemented simplified for now
            
        except Exception as e:
            logger.error(f"Failed to get actual value for {metric}: {e}")
            
        return None

    async def _record_learning(self, prediction: Prediction, outcome: Dict):
        """Store the lesson in Mem0"""
        if not MEM0_API_KEY:
            return
            
        try:
            if outcome["result"] == "verified":
                lesson = f"✅ PREDICTION CONFIRMED: Pattern '{prediction.source_pattern.get('type')}' correctly predicted {prediction.target_metric} move. Confidence was {prediction.confidence:.2f}."
            else:
                lesson = f"❌ PREDICTION FAILED: Pattern '{prediction.source_pattern.get('type')}' failed to predict {prediction.target_metric}. Predicted {prediction.predicted_direction}, got {outcome['actual']}. Reasoning was: {prediction.reasoning}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{MEM0_URL}/memories/",
                    headers={"Authorization": f"Token {MEM0_API_KEY}"},
                    json={
                        "messages": [{"role": "user", "content": lesson}],
                        "user_id": "fpai_oracle",
                        "metadata": {
                            "type": "learning",
                            "prediction_id": prediction.id,
                            "outcome": outcome["result"]
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Failed to record learning: {e}")


# Singleton
oracle = Oracle()

