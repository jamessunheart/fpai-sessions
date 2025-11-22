"""
AI Candidate Screening Service
Uses Claude to screen applications against job requirements
"""
import os
import logging
from typing import Dict
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class AIScreener:
    """AI-powered candidate screening"""

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY not set - AI screening disabled")

    async def screen_candidate(self, application: Dict, job: Dict) -> Dict:
        """
        Screen candidate application using AI

        Args:
            application: Application details
            job: Job details and requirements

        Returns:
            Screening results with score and recommendation
        """
        if not self.client:
            return {
                'score': 50,
                'recommendation': 'maybe',
                'reasoning': 'AI screening not available',
                'ai_available': False
            }

        try:
            prompt = f"""Screen this job application against the requirements.

JOB: {job['title']}

REQUIREMENTS:
{chr(10).join(['- ' + req for req in job['requirements']])}

SKILLS NEEDED:
{', '.join(job['skills'])}

APPLICANT:
Name: {application['name']}
Experience: {application['experience_years']} years
Portfolio: {application.get('portfolio_url', 'Not provided')}
Cover Letter: {application['cover_letter']}
Availability: {application['availability']}

ANALYZE:
1. Match between skills and requirements (0-100)
2. Quality of cover letter (0-100)
3. Experience level fit (0-100)
4. Overall recommendation: hire, maybe, or pass

Respond in JSON format:
{{
    "skills_match": 85,
    "cover_letter_quality": 90,
    "experience_fit": 80,
    "overall_score": 85,
    "recommendation": "hire",
    "strengths": ["List 2-3 strengths"],
    "concerns": ["List any concerns or empty if none"],
    "reasoning": "Brief explanation"
}}

Be objective and helpful."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse AI response
            import json
            result = json.loads(response.content[0].text)

            logger.info(f"✅ AI screened: {application['name']} → {result['recommendation']} (score: {result['overall_score']})")

            return {
                **result,
                'ai_available': True
            }

        except Exception as e:
            logger.error(f"AI screening error: {e}")
            return {
                'score': 50,
                'recommendation': 'maybe',
                'reasoning': f'Screening error: {str(e)}',
                'ai_available': False
            }


# Global screener instance
ai_screener = AIScreener()
