"""AI-powered candidate screening using Claude"""

from anthropic import Anthropic
from typing import Dict, Any
import json

from .config import settings


class AIScreener:
    """Screen job candidates using AI"""

    def __init__(self):
        """Initialize Claude client"""
        self.client = None
        if settings.anthropic_api_key:
            self.client = Anthropic(api_key=settings.anthropic_api_key)

    async def screen_candidate(
        self,
        task_description: str,
        task_requirements: Dict[str, Any],
        application: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Screen candidate application using AI.

        Returns:
        {
            "score": 0.0-1.0,
            "reasoning": "Why this score",
            "recommendation": "hire" | "reject" | "interview",
            "red_flags": [],
            "strengths": []
        }
        """
        if not self.client:
            # Fallback: Simple scoring
            return {
                "score": 0.5,
                "reasoning": "AI screening not available",
                "recommendation": "manual_review",
                "red_flags": [],
                "strengths": []
            }

        prompt = f"""You are an expert hiring manager screening candidates for a task.

**Task:**
{task_description}

**Requirements:**
{json.dumps(task_requirements, indent=2)}

**Candidate Application:**
Name: {application.get('helper_name')}
Platform: {application.get('platform')}
Proposed Rate: ${application.get('proposed_rate')}/hour
Estimated Hours: {application.get('estimated_hours')}

Cover Letter:
{application.get('cover_letter')}

**Your Job:**
1. Evaluate if candidate is qualified for this task
2. Look for red flags (spam, low quality, unrealistic promises)
3. Assess if rate and timeline are reasonable
4. Provide recommendation

**Output as JSON:**
{{
  "score": 0.85,  # 0.0 (terrible) to 1.0 (perfect)
  "reasoning": "Brief explanation of score",
  "recommendation": "hire" | "reject" | "interview",
  "red_flags": ["List any concerns"],
  "strengths": ["List candidate strengths"]
}}

Provide ONLY the JSON, no other text."""

        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text

            result = json.loads(json_text)
            return result

        except Exception as e:
            print(f"AI screening error: {e}")
            return {
                "score": 0.5,
                "reasoning": f"Screening error: {str(e)}",
                "recommendation": "manual_review",
                "red_flags": ["AI screening failed"],
                "strengths": []
            }


# Global instance
ai_screener = AIScreener()
