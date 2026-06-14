"""
Labor Coordinator Service
AI coordinates work, assigns tasks, provides feedback, and manages progress
"""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class LaborCoordinator:
    """AI-powered labor coordination and project management"""

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY not set - AI coordination disabled")

    async def start_project(self, delegation: Dict, developer: Dict) -> Dict:
        """
        Initialize project with developer - create kickoff plan

        Args:
            delegation: Project/delegation details
            developer: Developer information

        Returns:
            Project kickoff plan with first tasks
        """
        if not self.client:
            return self._get_default_kickoff(delegation, developer)

        try:
            prompt = f"""You are the AI Project Coordinator for Full Potential AI.

A new developer just accepted a project:

DEVELOPER: {developer['name']}
EXPERIENCE: {developer.get('experience_years')} years
SKILLS: {', '.join(developer.get('skills', []))}

PROJECT: {delegation['title']}
DESCRIPTION: {delegation['description']}
BUDGET: ${delegation['budget']}
DURATION: {delegation['duration']}
MILESTONES: {delegation['milestones']}

Create a kickoff plan:
1. Welcome message (warm, specific to their skills)
2. Break project into 5 milestones
3. Define first week's tasks
4. Set up check-in schedule
5. Clarify expectations

Respond in JSON:
{{
  "welcome_message": "Personal welcome referencing their background",
  "milestones": [
    {{
      "number": 1,
      "title": "Foundation Setup",
      "deliverables": ["Item 1", "Item 2"],
      "estimated_days": 3,
      "payment": 600
    }},
    ...
  ],
  "first_week_tasks": [
    {{
      "task": "Set up development environment",
      "priority": "high",
      "estimated_hours": 4,
      "acceptance_criteria": ["Can run locally", "Tests pass"]
    }},
    ...
  ],
  "check_in_schedule": {{
    "daily_standup": "9am async update via Discord",
    "weekly_review": "Friday 2pm",
    "milestone_review": "End of each milestone"
  }},
  "expectations": {{
    "communication": "Async-first, respond within 24h",
    "code_quality": "AI-reviewed, passing tests",
    "documentation": "Update README as you go",
    "questions": "Ask early, ask often"
  }}
}}

Be warm, specific, and helpful."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            kickoff = json.loads(response.content[0].text)

            kickoff['created_at'] = datetime.utcnow().isoformat()
            kickoff['delegation_id'] = delegation['delegation_id']
            kickoff['developer_id'] = developer.get('id')

            logger.info(f"✅ Project kickoff created for {developer['name']}")

            return kickoff

        except Exception as e:
            logger.error(f"Error creating kickoff: {e}")
            return self._get_default_kickoff(delegation, developer)

    async def daily_checkin(self, developer_id: str, update: str, context: Dict) -> Dict:
        """
        Process daily developer check-in and provide feedback

        Args:
            developer_id: Developer identifier
            update: Developer's daily update
            context: Project context

        Returns:
            AI feedback and next steps
        """
        if not self.client:
            return {
                'status': 'acknowledged',
                'feedback': 'Update received',
                'ai_available': False
            }

        try:
            prompt = f"""You are the AI Project Coordinator. Process this daily check-in.

DEVELOPER: {context.get('developer_name')}
PROJECT: {context.get('project_title')}
CURRENT MILESTONE: {context.get('current_milestone')}
DAYS REMAINING: {context.get('days_remaining')}

TODAY'S UPDATE:
{update}

RECENT PROGRESS:
{context.get('recent_progress', 'First update')}

Provide helpful feedback:
{{
  "status": "on_track" | "needs_attention" | "blocked" | "ahead",
  "feedback": "Specific, actionable feedback on their update",
  "praise": ["What they did well"],
  "suggestions": ["How to improve or what to consider"],
  "blockers_identified": ["Any issues they mentioned or you detect"],
  "recommended_next_steps": ["Concrete next actions"],
  "questions_to_clarify": ["Ask if anything is unclear"],
  "estimated_completion": "on_time" | "ahead_of_schedule" | "at_risk"
}}

Be supportive but honest. Flag risks early."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            feedback = json.loads(response.content[0].text)

            feedback['timestamp'] = datetime.utcnow().isoformat()
            feedback['developer_id'] = developer_id

            logger.info(f"✅ Daily check-in processed: {context.get('developer_name')} → {feedback['status']}")

            return feedback

        except Exception as e:
            logger.error(f"Error processing check-in: {e}")
            return {
                'status': 'error',
                'feedback': f'Error processing update: {str(e)}',
                'ai_available': False
            }

    async def review_code(self, code_diff: str, context: Dict) -> Dict:
        """
        AI code review for submitted work

        Args:
            code_diff: Git diff or code changes
            context: Project and developer context

        Returns:
            Code review with feedback
        """
        if not self.client:
            return {
                'status': 'needs_manual_review',
                'feedback': 'AI code review not available',
                'ai_available': False
            }

        try:
            prompt = f"""You are conducting a code review for Full Potential AI.

DEVELOPER: {context.get('developer_name')}
MILESTONE: {context.get('milestone_number')}
FEATURE: {context.get('feature_description')}

CODE CHANGES:
```
{code_diff}
```

Review for:
1. Code quality and readability
2. Security issues (SQL injection, XSS, secrets)
3. Performance concerns
4. Best practices (PEP 8, error handling)
5. Tests included
6. Documentation

Respond in JSON:
{{
  "status": "approved" | "approved_with_suggestions" | "needs_changes",
  "overall_feedback": "Summary of review",
  "strengths": ["What was done well"],
  "issues": [
    {{
      "severity": "critical" | "important" | "minor",
      "category": "security" | "performance" | "style" | "logic",
      "description": "What's wrong",
      "suggestion": "How to fix",
      "line_numbers": [10, 15]
    }}
  ],
  "suggestions": ["Non-blocking improvements"],
  "tests_status": "comprehensive" | "adequate" | "missing",
  "documentation_status": "good" | "needs_improvement" | "missing",
  "recommendation": "merge" | "fix_critical_issues" | "revise_and_resubmit"
}}

Be thorough but encouraging. We value shipping fast with quality."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            review = json.loads(response.content[0].text)

            review['reviewed_at'] = datetime.utcnow().isoformat()
            review['reviewer'] = 'Claude AI'

            logger.info(f"✅ Code reviewed: {context.get('developer_name')} → {review['status']}")

            return review

        except Exception as e:
            logger.error(f"Error reviewing code: {e}")
            return {
                'status': 'error',
                'feedback': f'Review error: {str(e)}',
                'ai_available': False
            }

    async def handle_blocker(self, blocker_description: str, context: Dict) -> Dict:
        """
        Help developer resolve blocker

        Args:
            blocker_description: Description of the issue
            context: Project context

        Returns:
            Suggested solutions and escalation if needed
        """
        if not self.client:
            return {
                'suggestions': ['Contact human coordinator'],
                'escalate': True
            }

        try:
            prompt = f"""A developer is blocked. Help them get unblocked.

DEVELOPER: {context.get('developer_name')}
PROJECT: {context.get('project_title')}
BLOCKER: {blocker_description}

PROJECT CONTEXT:
- Tech stack: {context.get('tech_stack')}
- Resources available: {context.get('resources')}
- Deadline pressure: {context.get('deadline_pressure', 'medium')}

Provide help:
{{
  "blocker_type": "technical" | "clarification_needed" | "external_dependency" | "skill_gap",
  "severity": "critical" | "important" | "minor",
  "immediate_suggestions": [
    {{
      "approach": "Try X",
      "rationale": "Why this might work",
      "estimated_time": "2 hours"
    }}
  ],
  "resources": [
    {{
      "type": "documentation" | "code_example" | "tool",
      "link": "URL or description",
      "helpful_for": "How it helps"
    }}
  ],
  "escalate_to_human": true | false,
  "escalation_reason": "Why human input needed or null",
  "alternative_approaches": ["If stuck, consider..."],
  "estimated_resolution_time": "2-8 hours"
}}

Help them move forward. Escalate if truly blocked."""

            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            help_response = json.loads(response.content[0].text)

            help_response['provided_at'] = datetime.utcnow().isoformat()

            logger.info(f"✅ Blocker handled: {context.get('developer_name')} → Escalate: {help_response.get('escalate_to_human')}")

            return help_response

        except Exception as e:
            logger.error(f"Error handling blocker: {e}")
            return {
                'suggestions': ['Error processing blocker - contact human coordinator'],
                'escalate': True,
                'error': str(e)
            }

    def _get_default_kickoff(self, delegation: Dict, developer: Dict) -> Dict:
        """Fallback kickoff when AI not available"""
        return {
            'welcome_message': f"Welcome {developer['name']}! Excited to have you on board for {delegation['title']}.",
            'milestones': [
                {
                    'number': i+1,
                    'title': f"Milestone {i+1}",
                    'deliverables': ['TBD'],
                    'estimated_days': int(delegation.get('duration', '21 days').split()[0]) // 5,
                    'payment': delegation['budget'] / 5
                }
                for i in range(5)
            ],
            'first_week_tasks': [
                {'task': 'Set up development environment', 'priority': 'high'},
                {'task': 'Review project requirements', 'priority': 'high'},
                {'task': 'Create initial project structure', 'priority': 'medium'}
            ],
            'check_in_schedule': {
                'daily_standup': 'Daily async updates',
                'weekly_review': 'End of week',
                'milestone_review': 'End of each milestone'
            },
            'expectations': {
                'communication': 'Daily updates',
                'code_quality': 'Production-ready',
                'documentation': 'Keep updated',
                'questions': 'Ask anytime'
            },
            'ai_available': False
        }


# Global coordinator instance
labor_coordinator = LaborCoordinator()
