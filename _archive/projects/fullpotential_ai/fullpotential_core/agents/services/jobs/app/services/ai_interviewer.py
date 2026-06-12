"""
AI Interviewer Service
Conducts structured interviews with candidates and evaluates responses
"""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class AIInterviewer:
    """AI-powered candidate interviewing system"""

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY not set - AI interviews disabled")

    async def generate_interview_questions(self, job: Dict, application: Dict) -> List[Dict]:
        """
        Generate personalized interview questions based on job and application

        Args:
            job: Job details
            application: Candidate application

        Returns:
            List of interview questions with evaluation criteria
        """
        if not self.client:
            return self._get_default_questions()

        try:
            prompt = f"""You are an expert technical interviewer for Full Potential AI.

We're hiring for: {job['title']}

Job requirements:
{chr(10).join(['- ' + req for req in job['requirements']])}

Candidate background:
- Name: {application['name']}
- Experience: {application['experience_years']} years
- Skills: {', '.join(application.get('relevant_skills', []))}
- Portfolio: {application.get('portfolio_url', 'Not provided')}

Generate 5 interview questions that:
1. Assess technical depth in required skills
2. Evaluate alignment with autonomous AI vision
3. Test problem-solving approach
4. Check cultural fit (autonomous mindset, ship fast)
5. Verify they can work WITH AI tools (not just use them)

For each question provide:
- The question itself
- What good answer looks like
- Red flags to watch for
- How to score (1-10 scale)

Format as JSON:
{{
  "questions": [
    {{
      "id": 1,
      "category": "technical",
      "question": "Describe a time you built...",
      "good_answer": "Should mention...",
      "red_flags": ["vague", "no concrete examples"],
      "scoring_criteria": "10 = detailed example with metrics, 5 = generic answer, 1 = no relevant experience"
    }},
    ...
  ]
}}

Make questions specific to their background and our mission."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            result = json.loads(response.content[0].text)

            logger.info(f"✅ Generated {len(result['questions'])} interview questions for {application['name']}")

            return result['questions']

        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return self._get_default_questions()

    async def evaluate_interview_response(
        self,
        question: Dict,
        answer: str,
        context: Dict
    ) -> Dict:
        """
        Evaluate candidate's answer to interview question

        Args:
            question: The interview question with criteria
            answer: Candidate's response
            context: Job and candidate context

        Returns:
            Evaluation with score and feedback
        """
        if not self.client:
            return {
                'score': 5,
                'feedback': 'AI evaluation not available',
                'recommendation': 'manual_review'
            }

        try:
            prompt = f"""Evaluate this interview response objectively.

QUESTION: {question['question']}

CANDIDATE'S ANSWER:
{answer}

EVALUATION CRITERIA:
Good answer looks like: {question.get('good_answer', 'Detailed, specific, with examples')}
Red flags: {', '.join(question.get('red_flags', ['vague', 'no examples']))}
Scoring: {question.get('scoring_criteria', '10 = excellent, 5 = acceptable, 1 = poor')}

CONTEXT:
- Candidate: {context.get('candidate_name')}
- Experience: {context.get('experience_years')} years
- Job: {context.get('job_title')}

Provide evaluation in JSON:
{{
  "score": 8,
  "strengths": ["Concrete example", "Mentioned metrics", "Shows autonomous mindset"],
  "weaknesses": ["Could elaborate more on X"],
  "feedback": "Strong answer that demonstrates...",
  "recommendation": "strong_hire" | "hire" | "maybe" | "pass",
  "follow_up_questions": ["Ask about...", "Clarify..."]
}}

Be thorough but fair. We want people who ship fast and work well with AI."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            evaluation = json.loads(response.content[0].text)

            logger.info(f"✅ Evaluated response: Score {evaluation['score']}/10 - {evaluation['recommendation']}")

            return evaluation

        except Exception as e:
            logger.error(f"Error evaluating response: {e}")
            return {
                'score': 5,
                'feedback': f'Evaluation error: {str(e)}',
                'recommendation': 'manual_review'
            }

    async def conduct_async_interview(
        self,
        application_id: str,
        job: Dict,
        application: Dict
    ) -> Dict:
        """
        Conduct full async interview via email/form

        Returns interview package to send to candidate
        """
        questions = await self.generate_interview_questions(job, application)

        interview = {
            'interview_id': f"interview-{application_id}",
            'application_id': application_id,
            'candidate_name': application['name'],
            'candidate_email': application['email'],
            'job_title': job['title'],
            'created_at': datetime.utcnow().isoformat(),
            'status': 'pending',
            'questions': questions,
            'deadline': '48 hours from receipt',
            'instructions': self._generate_interview_instructions(application['name'], job['title'])
        }

        logger.info(f"📋 Interview created for {application['name']}")

        return interview

    async def evaluate_complete_interview(
        self,
        interview_id: str,
        responses: List[Dict],
        context: Dict
    ) -> Dict:
        """
        Evaluate all interview responses and make hiring recommendation

        Args:
            interview_id: Interview identifier
            responses: List of {question_id, answer} dicts
            context: Job and candidate info

        Returns:
            Complete evaluation with hire/no-hire recommendation
        """
        if not self.client:
            return {
                'overall_score': 50,
                'recommendation': 'manual_review',
                'summary': 'AI evaluation not available'
            }

        evaluations = []
        total_score = 0

        # Evaluate each response
        for resp in responses:
            question = next(
                (q for q in context['questions'] if q['id'] == resp['question_id']),
                None
            )

            if question:
                evaluation = await self.evaluate_interview_response(
                    question=question,
                    answer=resp['answer'],
                    context=context
                )
                evaluations.append({
                    'question_id': resp['question_id'],
                    'question': question['question'],
                    **evaluation
                })
                total_score += evaluation['score']

        # Overall assessment
        avg_score = total_score / len(responses) if responses else 0

        try:
            # Get AI's overall recommendation
            summary_prompt = f"""Review this complete interview and make a hiring decision.

CANDIDATE: {context['candidate_name']}
ROLE: {context['job_title']}
EXPERIENCE: {context.get('experience_years')} years

INTERVIEW SCORES:
{chr(10).join([f"Q{e['question_id']}: {e['score']}/10 - {e['feedback']}" for e in evaluations])}

AVERAGE SCORE: {avg_score:.1f}/10

Based on all responses, provide final recommendation:
{{
  "overall_score": {avg_score},
  "recommendation": "strong_hire" | "hire" | "maybe" | "pass",
  "summary": "2-3 sentence overall assessment",
  "strengths": ["Top 3 strengths"],
  "concerns": ["Any concerns or empty list"],
  "next_steps": ["If hire: what to do next", "If pass: why not good fit"]
}}

We value: autonomous mindset, ships fast, works well with AI, technical depth."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=1000,
                messages=[{"role": "user", "content": summary_prompt}]
            )

            import json
            final_assessment = json.loads(response.content[0].text)

            result = {
                'interview_id': interview_id,
                'candidate_name': context['candidate_name'],
                'evaluated_at': datetime.utcnow().isoformat(),
                'individual_scores': evaluations,
                **final_assessment
            }

            logger.info(f"✅ Interview evaluation complete: {context['candidate_name']} → {final_assessment['recommendation']}")

            return result

        except Exception as e:
            logger.error(f"Error in final evaluation: {e}")
            return {
                'interview_id': interview_id,
                'overall_score': avg_score,
                'recommendation': 'manual_review',
                'summary': f'Evaluation error: {str(e)}',
                'individual_scores': evaluations
            }

    def _get_default_questions(self) -> List[Dict]:
        """Fallback questions when AI not available"""
        return [
            {
                'id': 1,
                'category': 'technical',
                'question': 'Describe your experience building production APIs with FastAPI or similar frameworks. Include specific examples with scale metrics.',
                'good_answer': 'Concrete project, mentions request volume, discusses challenges',
                'red_flags': ['no production experience', 'vague descriptions'],
                'scoring_criteria': '10 = production experience with metrics, 5 = some API work, 1 = no relevant experience'
            },
            {
                'id': 2,
                'category': 'ai_integration',
                'question': 'Have you integrated AI APIs (Claude, GPT, etc.) into production systems? Describe your approach and any challenges you faced.',
                'good_answer': 'Specific integration, discusses prompt engineering, error handling',
                'red_flags': ['just played around', 'no production experience'],
                'scoring_criteria': '10 = production AI integration, 5 = experimentation, 1 = no AI experience'
            },
            {
                'id': 3,
                'category': 'autonomous_mindset',
                'question': 'Describe a time you shipped a project with minimal oversight. How did you decide what to build and how to prioritize?',
                'good_answer': 'Shows initiative, clear decision-making, shipped results',
                'red_flags': ['needed constant direction', 'never completed without oversight'],
                'scoring_criteria': '10 = highly autonomous, 5 = some autonomy, 1 = needs lots of direction'
            },
            {
                'id': 4,
                'category': 'ai_collaboration',
                'question': 'How do you currently use AI tools in your development workflow? What works, what doesn\'t?',
                'good_answer': 'Active user of Claude/GPT/Copilot, shares specific workflows',
                'red_flags': ['don\'t use AI tools', 'thinks AI will replace developers'],
                'scoring_criteria': '10 = power user with insights, 5 = occasional use, 1 = doesn\'t use AI tools'
            },
            {
                'id': 5,
                'category': 'problem_solving',
                'question': 'You need to build a system where AI verifies work quality. How would you approach this? What are the failure modes?',
                'good_answer': 'Thoughtful architecture, considers edge cases, mentions validation',
                'red_flags': ['superficial answer', 'doesn\'t consider failures'],
                'scoring_criteria': '10 = comprehensive approach, 5 = basic solution, 1 = no clear approach'
            }
        ]

    def _generate_interview_instructions(self, candidate_name: str, job_title: str) -> str:
        """Generate instructions for async interview"""
        return f"""# Interview for {job_title}

Hi {candidate_name}!

Thanks for your interest in Full Potential AI. We'd love to learn more about you through this brief interview.

## How This Works

This is an **async interview** conducted by our AI interviewing system. Here's what makes it unique:

- ✅ Answer on your own schedule (48-hour deadline)
- ✅ Your responses will be evaluated by Claude (our AI interviewer)
- ✅ Top candidates will be reviewed by our human team
- ✅ You'll get feedback either way

## Why AI Interviews?

We practice what we preach. Since you'd be working WITH AI agents if hired, we want to see how you communicate with AI in the interview process itself.

## Guidelines

**For each question:**
- Be specific (concrete examples > vague descriptions)
- Include metrics when possible (scale, impact, results)
- Honest > impressive (we value real experience)
- Length: 2-4 paragraphs per question

**What we're looking for:**
- Technical depth in relevant areas
- Autonomous mindset (you ship without hand-holding)
- Comfort working with AI tools
- Problem-solving approach
- Cultural fit with our mission

## Evaluation

Your responses will be scored on:
- Specificity and depth
- Relevant experience
- Alignment with autonomous AI vision
- Communication clarity

## Timeline

- **Submit by:** 48 hours from now
- **AI evaluation:** Automated (immediate)
- **Human review:** Within 24 hours of submission
- **Decision:** Within 48 hours total

## Questions?

Reply to this email if anything is unclear. Our AI can answer questions too!

Let's get started! 👇
"""


# Global interviewer instance
ai_interviewer = AIInterviewer()
