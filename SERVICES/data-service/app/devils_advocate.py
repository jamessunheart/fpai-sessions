"""
Devil's Advocate
================
Challenges high-confidence predictions with the strongest opposing case.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import httpx
from pydantic import BaseModel

AI_BRAIN_URL = "http://localhost:8101"
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_URL = "https://api.mem0.ai/v1"

logger = logging.getLogger("devils_advocate")


class AdversarialAnalysis(BaseModel):
    prediction_id: str
    counter_argument: str
    identified_risks: List[str]
    alternative_scenarios: List[str]
    adversary_confidence: float  # 0-1: confidence that prediction may be wrong
    verdict: str  # "confirm" | "flag" | "reject"
    created_at: str


async def challenge_prediction(prediction) -> Optional[AdversarialAnalysis]:
    """
    Generate a counterfactual analysis for a prediction.
    """
    try:
        pattern = prediction.source_pattern if hasattr(prediction, "source_pattern") else {}
        prompt = f"""You are a Devil's Advocate for trading and intelligence signals.
Assume this prediction is wrong. Build the strongest opposing case.

PREDICTION:
Target: {prediction.target_metric}
Direction: {prediction.predicted_direction}
Value: {prediction.predicted_value}
Timeframe (h): {prediction.timeframe_hours}
Confidence: {prediction.confidence}
Reasoning: {prediction.reasoning}

PATTERN CONTEXT:
{json.dumps(pattern, default=str)}

TASK:
- List the strongest counter-argument.
- List key risks or scenarios that invalidate this prediction.
- Provide 1-2 alternative scenarios.
- Rate your own confidence (0-1) that the prediction will fail.

Respond as JSON:
{{
  "counter_argument": "...",
  "identified_risks": ["..."],
  "alternative_scenarios": ["..."],
  "adversary_confidence": 0.6
}}
"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            text = "{}"
            # Try AI Brain first
            try:
                resp = await client.post(
                    f"{AI_BRAIN_URL}/generate",
                    json={
                        "prompt": prompt,
                        "system_message": "You are a rigorous Devil's Advocate. Output valid JSON only.",
                        "model_preference": "fast",
                        "max_tokens": 300
                    },
                    timeout=10.0
                )
                if resp.status_code == 200:
                    text = resp.json().get("text", "{}")
            except:
                pass
            
            # Fallback to Ollama (using small model for memory)
            if "{" not in text:
                try:
                    resp = await client.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": "qwen2.5:0.5b",
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=90.0
                    )
                    if resp.status_code == 200:
                        text = resp.json().get("response", "{}")
                except:
                    pass
            if "{" not in text:
                return None
            data = json.loads(text[text.find("{"):text.rfind("}")+1])

            adversary_conf = float(data.get("adversary_confidence", 0))
            if adversary_conf <= 0.3:
                verdict = "confirm"
            elif adversary_conf < 0.6:
                verdict = "flag"
            else:
                verdict = "reject"

            analysis = AdversarialAnalysis(
                prediction_id=prediction.id,
                counter_argument=data.get("counter_argument", ""),
                identified_risks=data.get("identified_risks", []),
                alternative_scenarios=data.get("alternative_scenarios", []),
                adversary_confidence=adversary_conf,
                verdict=verdict,
                created_at=datetime.now(timezone.utc).isoformat()
            )

            await _store_adversarial_memory(analysis, prediction)
            return analysis
    except Exception as e:
        logger.error(f"Devil's Advocate failed: {e}")
        return None


async def _store_adversarial_memory(analysis: AdversarialAnalysis, prediction):
    if not MEM0_API_KEY:
        return
    try:
        text = (
            f"DA verdict ({analysis.verdict}) for {prediction.target_metric} "
            f"direction {prediction.predicted_direction}. "
            f"Risks: {analysis.identified_risks}"
        )
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            await client.post(
                f"{MEM0_URL}/memories/",
                headers={"Authorization": f"Token {MEM0_API_KEY}", "Content-Type": "application/json"},
                json={
                    "messages": [{"role": "user", "content": text}],
                    "user_id": "fpai_devils_advocate",
                    "metadata": {
                        "type": "adversarial_review",
                        "prediction_id": analysis.prediction_id,
                        "verdict": analysis.verdict
                    }
                }
            )
    except Exception as e:
        logger.error(f"Failed to store adversarial memory: {e}")


