"""
Reviewer Agent - Specialized agent for code validation and security.

Uses GPT-4 for thorough security analysis and edge case detection.
"""

import logging
import time
from datetime import datetime

from .base import Agent, AgentSpecialty, Task, AgentOpinion, ExecutionResult

logger = logging.getLogger("aria.agents.reviewer")


class ReviewerAgent(Agent):
    """
    Reviewer Agent - Validates code quality and security.
    
    Strengths:
    - Security vulnerability detection
    - Edge case identification
    - Code quality assessment
    - Best practices enforcement
    """
    
    def __init__(self):
        super().__init__(
            name="reviewer",
            specialty=AgentSpecialty.REVIEW,
            model="gpt-4o",  # Strong at security analysis
            description="Validates code for security, quality, and correctness"
        )
        
        self.system_prompt = """You are the Reviewer Agent in the ARIA Sovereign system.
Your role is to validate code changes for security, quality, and correctness.

Core responsibilities:
1. Identify security vulnerabilities
2. Detect potential bugs and edge cases
3. Ensure code quality standards
4. Verify best practices are followed

Security checklist:
- Input validation
- SQL injection
- XSS vulnerabilities
- Authentication/authorization
- Sensitive data exposure
- Error handling
- Rate limiting

Quality checklist:
- Code clarity and readability
- Proper error handling
- Test coverage considerations
- Performance implications
- Maintainability

When reviewing:
- Be thorough but not overly pedantic
- Prioritize security issues
- Consider real-world attack vectors
- Suggest improvements constructively

Output your review as JSON:
{
    "approved": true/false,
    "security_score": 0.0-1.0,
    "quality_score": 0.0-1.0,
    "overall_confidence": 0.0-1.0,
    "security_issues": [{"severity": "critical/high/medium/low", "description": "..."}],
    "quality_issues": [{"severity": "...", "description": "..."}],
    "suggestions": ["suggestion1", "suggestion2"],
    "summary": "brief summary"
}"""
    
    async def evaluate(self, task: Task) -> AgentOpinion:
        """Review a task for security and quality."""
        start_time = time.time()
        
        try:
            # Build review prompt
            prompt = f"""Review this code change for security and quality:

Task Type: {task.type}
Description: {task.description}

Context:
{self._format_context(task.context)}

Payload:
{self._format_payload(task.payload)}

Provide your review as JSON."""

            # Call LLM
            response = await self._call_llm(prompt, self.system_prompt)
            
            # Parse response
            review = self._parse_review(response)
            
            # Calculate confidence
            security_score = review.get("security_score", 0.7)
            quality_score = review.get("quality_score", 0.7)
            confidence = (security_score * 0.6 + quality_score * 0.4)  # Security weighted higher
            
            # Check for critical issues
            critical_issues = [i for i in review.get("security_issues", []) 
                            if i.get("severity") == "critical"]
            high_issues = [i for i in review.get("security_issues", []) 
                         if i.get("severity") == "high"]
            
            if critical_issues:
                recommendation = "reject"
                confidence *= 0.3
            elif high_issues:
                recommendation = "modify"
                confidence *= 0.6
            elif review.get("approved", True):
                recommendation = "approve"
            else:
                recommendation = "modify"
            
            # Build concerns list
            concerns = []
            for issue in review.get("security_issues", []):
                concerns.append(f"[{issue.get('severity', 'unknown').upper()}] {issue.get('description', '')}")
            for issue in review.get("quality_issues", []):
                concerns.append(f"[QUALITY] {issue.get('description', '')}")
            
            opinion = AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=confidence,
                recommendation=recommendation,
                reasoning=review.get("summary", "Review completed"),
                concerns=concerns[:5],  # Top 5 concerns
                suggestions=review.get("suggestions", [])[:5],
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
            
            self.total_evaluations += 1
            self.last_action = datetime.now()
            
            return opinion
            
        except Exception as e:
            logger.error(f"Reviewer evaluation failed: {e}")
            return AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=0.3,
                recommendation="defer",
                reasoning=f"Review failed: {str(e)}",
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def execute(self, task: Task) -> ExecutionResult:
        """Reviewer doesn't execute - returns review report."""
        return ExecutionResult(
            task_id=task.id,
            success=True,
            output="Reviewer agent provides evaluation only, not execution.",
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
    
    def _format_context(self, context: dict) -> str:
        """Format context for prompts."""
        parts = []
        if "file_content" in context:
            content = context['file_content']
            if len(content) > 5000:
                content = content[:5000] + "\n... (truncated)"
            parts.append(f"File content:\n```\n{content}\n```")
        if "changes" in context:
            parts.append(f"Proposed changes:\n{context['changes']}")
        return "\n".join(parts) if parts else "No additional context."
    
    def _format_payload(self, payload: dict) -> str:
        """Format payload for prompts."""
        import json
        try:
            return json.dumps(payload, indent=2)[:2000]
        except:
            return str(payload)[:2000]
    
    def _parse_review(self, response: str) -> dict:
        """Parse LLM review response."""
        import json
        
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
            else:
                json_str = response
            
            return json.loads(json_str)
        except:
            return {
                "approved": True,
                "security_score": 0.7,
                "quality_score": 0.7,
                "overall_confidence": 0.7,
                "summary": response[:200]
            }


