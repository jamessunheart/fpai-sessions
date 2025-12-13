"""
Question Router
===============
Asks the human for guidance when uncertainty/stakes are high.
"""

import httpx
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os

AI_BRAIN_URL = "http://localhost:8101"
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_URL = "https://api.mem0.ai/v1"


class ClarificationQuestion(BaseModel):
    id: str
    created_at: str
    context: Dict[str, Any]
    question: str
    options: List[str]
    recommended_option: Optional[str] = None
    status: str = "open"
    answer: Optional[str] = None


async def maybe_ask_user(state: Dict, prediction: Dict, decision: Dict) -> Optional[ClarificationQuestion]:
    """
    Generate a human question when risk is high and calibration is weak.
    """
    try:
        prompt = f"""You are the question router for a trading/intelligence system.
When risk is high or calibration is weak, ask the human a concise, multiple-choice question.

STATE:
{json.dumps(state, default=str)}

PREDICTION:
{json.dumps(prediction, default=str)}

DECISION:
{json.dumps(decision, default=str)}

Produce a short question with 2-3 options. Respond JSON:
{{
  "question": "...",
  "options": ["A) ...", "B) ...", "C) ..."],
  "recommended_option": "A) ..."  # optional
}}
"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{AI_BRAIN_URL}/generate",
                json={
                    "prompt": prompt,
                    "system_message": "You are concise and context-rich. Output JSON only.",
                    "model_preference": "smart",
                    "max_tokens": 200
                }
            )
            if resp.status_code != 200:
                return None
            text = resp.json().get("text", "{}")
            if "{" not in text:
                return None
            data = json.loads(text[text.find("{"):text.rfind("}")+1])
            q = ClarificationQuestion(
                id=f"q_{int(datetime.now().timestamp())}",
                created_at=datetime.now(timezone.utc).isoformat(),
                context={"state": state, "prediction": prediction, "decision": decision},
                question=data.get("question", ""),
                options=data.get("options", []),
                recommended_option=data.get("recommended_option")
            )
            await _store_question(q)
            return q
    except Exception:
        return None


async def _store_question(question: ClarificationQuestion):
    if not MEM0_API_KEY:
        return
    try:
        text = f"QUESTION: {question.question} OPTIONS: {question.options}"
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            await client.post(
                f"{MEM0_URL}/memories/",
                headers={"Authorization": f"Token {MEM0_API_KEY}", "Content-Type": "application/json"},
                json={
                    "messages": [{"role": "user", "content": text}],
                    "user_id": "fpai_question_router",
                    "metadata": {"type": "preference_question", "question_id": question.id}
                }
            )
    except Exception:
        pass












