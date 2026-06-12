"""
Task Automation Framework - AI Task Analyzer
Uses Claude API to analyze tasks and determine automation strategy
"""

import os
import json
from typing import Optional
import anthropic
from .models import Task, TaskAnalysis, AutomationLevel, BlockerType


class TaskAnalyzer:
    """AI-powered task analysis using Claude"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_task(self, task: Task) -> TaskAnalysis:
        """
        Analyze a task to determine:
        - Automation feasibility
        - Required blockers/human actions
        - Step-by-step approach
        - Time estimate
        - Risks
        """

        analysis_prompt = f"""You are an expert at analyzing automation tasks. Analyze this task:

**Task Type:** {task.type}
**Service:** {task.service}
**Description:** {task.description}
**Parameters:** {json.dumps(task.params, indent=2)}

Provide a detailed analysis in JSON format with these fields:

{{
  "can_automate": <boolean - is this task automatable?>,
  "automation_level": "<FULL|SEMI|MANUAL>",
  "estimated_difficulty": "<EASY|MEDIUM|HARD>",
  "estimated_time_minutes": <number>,
  "blockers_identified": [<list of blocker types: CAPTCHA, EMAIL_VERIFICATION, etc.>],
  "recommended_approach": "<detailed description of approach>",
  "steps": [<ordered list of steps to complete task>],
  "requirements": [<list of requirements: API keys, credentials, etc.>],
  "risks": [<list of potential risks or issues>]
}}

Consider common automation blockers:
- CAPTCHA challenges
- Email/phone verification
- Two-factor authentication
- API access requirements
- Payment requirements
- Terms of service restrictions

Be practical and specific. If the task requires human intervention, explain why and where."""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": analysis_prompt
            }]
        )

        # Extract JSON from response
        response_text = response.content[0].text

        # Try to find JSON in the response
        try:
            # Look for JSON block
            if "```json" in response_text:
                json_start = response_text.index("```json") + 7
                json_end = response_text.index("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text and "}" in response_text:
                json_start = response_text.index("{")
                json_end = response_text.rindex("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")

            analysis_data = json.loads(json_text)

        except (json.JSONDecodeError, ValueError) as e:
            # Fallback to conservative analysis
            analysis_data = {
                "can_automate": False,
                "automation_level": "MANUAL",
                "estimated_difficulty": "MEDIUM",
                "estimated_time_minutes": 15,
                "blockers_identified": ["HUMAN_APPROVAL"],
                "recommended_approach": "Manual completion recommended due to parsing error",
                "steps": ["Complete manually"],
                "requirements": ["Human intervention"],
                "risks": [f"Analysis parsing failed: {str(e)}"]
            }

        # Convert to TaskAnalysis model
        return TaskAnalysis(
            task_id=task.id,
            can_automate=analysis_data.get("can_automate", False),
            automation_level=AutomationLevel(analysis_data.get("automation_level", "manual").lower()),
            estimated_difficulty=analysis_data.get("estimated_difficulty", "MEDIUM"),
            estimated_time_minutes=analysis_data.get("estimated_time_minutes", 15),
            blockers_identified=[
                BlockerType(b.lower()) for b in analysis_data.get("blockers_identified", [])
                if b.lower() in [bt.value for bt in BlockerType]
            ],
            recommended_approach=analysis_data.get("recommended_approach", ""),
            steps=analysis_data.get("steps", []),
            requirements=analysis_data.get("requirements", []),
            risks=analysis_data.get("risks", [])
        )

    def suggest_service(self, task_description: str, category: str = "email") -> dict:
        """
        Suggest best service for a given task
        """

        suggestion_prompt = f"""Suggest the best service to use for this task:

**Category:** {category}
**Task:** {task_description}

Consider factors like:
- Free tier availability
- Ease of setup
- Automation feasibility
- Reliability
- Documentation quality

Provide response in JSON format:
{{
  "recommended_service": "<service name>",
  "reason": "<why this service>",
  "alternatives": ["<alternative 1>", "<alternative 2>"],
  "setup_complexity": "<EASY|MEDIUM|HARD>",
  "free_tier_limits": "<description of free tier>"
}}"""

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": suggestion_prompt
            }]
        )

        response_text = response.content[0].text

        # Parse JSON response
        try:
            if "```json" in response_text:
                json_start = response_text.index("```json") + 7
                json_end = response_text.index("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_start = response_text.index("{")
                json_end = response_text.rindex("}") + 1
                json_text = response_text[json_start:json_end]

            return json.loads(json_text)

        except (json.JSONDecodeError, ValueError):
            return {
                "recommended_service": "Unknown",
                "reason": "Could not parse recommendation",
                "alternatives": [],
                "setup_complexity": "MEDIUM",
                "free_tier_limits": "Unknown"
            }
