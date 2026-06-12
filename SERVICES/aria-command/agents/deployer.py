"""
Deployer Agent - Specialized agent for deployment and infrastructure.

Uses Claude Sonnet for risk assessment and deployment decisions.
"""

import logging
import time
from datetime import datetime

from .base import Agent, AgentSpecialty, Task, AgentOpinion, ExecutionResult

logger = logging.getLogger("aria.agents.deployer")


class DeployerAgent(Agent):
    """
    Deployer Agent - Manages deployments and infrastructure.
    
    Strengths:
    - Risk assessment
    - Deployment planning
    - Rollback strategies
    - Infrastructure safety
    """
    
    def __init__(self):
        super().__init__(
            name="deployer",
            specialty=AgentSpecialty.DEPLOY,
            model="claude-sonnet-4-20250514",
            description="Manages deployments with safety-first approach"
        )
        
        self.system_prompt = """You are the Deployer Agent in the ARIA Sovereign system.
Your role is to assess and execute deployments safely.

Core responsibilities:
1. Assess deployment risk
2. Plan safe deployment strategies
3. Ensure rollback capabilities
4. Monitor deployment health

Risk factors to consider:
- Service criticality (trading, revenue, user-facing)
- Time of day (avoid peak hours)
- Current system health
- Dependency chain
- Backup status

Deployment checklist:
- Pre-deployment backup
- Health checks before/after
- Gradual rollout if possible
- Rollback plan ready
- Monitoring in place

Output your assessment as JSON:
{
    "deploy_safe": true/false,
    "risk_level": "low/medium/high/critical",
    "confidence": 0.0-1.0,
    "timing_ok": true/false,
    "dependencies_healthy": true/false,
    "rollback_ready": true/false,
    "concerns": ["concern1"],
    "recommended_steps": ["step1", "step2"],
    "summary": "brief assessment"
}"""
    
    async def evaluate(self, task: Task) -> AgentOpinion:
        """Assess deployment risk."""
        start_time = time.time()
        
        try:
            # Build assessment prompt
            prompt = f"""Assess this deployment for safety:

Task: {task.type}
Description: {task.description}

Context:
{self._format_context(task.context)}

Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}
Day of week: {datetime.now().strftime('%A')}

Provide your assessment as JSON."""

            # Call LLM
            response = await self._call_llm(prompt, self.system_prompt)
            
            # Parse response
            assessment = self._parse_assessment(response)
            
            # Calculate confidence
            base_confidence = assessment.get("confidence", 0.5)
            
            # Adjust for risk factors
            if assessment.get("risk_level") == "critical":
                base_confidence *= 0.2
            elif assessment.get("risk_level") == "high":
                base_confidence *= 0.5
            elif assessment.get("risk_level") == "medium":
                base_confidence *= 0.8
            
            if not assessment.get("timing_ok", True):
                base_confidence *= 0.7
            
            if not assessment.get("rollback_ready", True):
                base_confidence *= 0.8
            
            # Determine recommendation
            if assessment.get("deploy_safe", True) and base_confidence >= 0.7:
                recommendation = "approve"
            elif assessment.get("risk_level") == "critical":
                recommendation = "reject"
            else:
                recommendation = "modify"
            
            opinion = AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=min(base_confidence, 1.0),
                recommendation=recommendation,
                reasoning=assessment.get("summary", f"Risk level: {assessment.get('risk_level', 'unknown')}"),
                concerns=assessment.get("concerns", []),
                suggestions=assessment.get("recommended_steps", []),
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
            
            self.total_evaluations += 1
            self.last_action = datetime.now()
            
            return opinion
            
        except Exception as e:
            logger.error(f"Deployer evaluation failed: {e}")
            return AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=0.2,
                recommendation="reject",
                reasoning=f"Assessment failed: {str(e)} - defaulting to safe rejection",
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def execute(self, task: Task) -> ExecutionResult:
        """Execute a deployment task."""
        start_time = datetime.now()
        
        try:
            self._current_tasks += 1
            
            # Get deployment commands
            commands = self._get_deployment_commands(task)
            
            if not commands:
                return ExecutionResult(
                    task_id=task.id,
                    success=False,
                    output="No deployment commands determined",
                    error="Could not parse deployment instructions",
                    started_at=start_time
                )
            
            # Execute deployment
            from access.terminal import get_executor
            executor = get_executor()
            
            outputs = []
            success = True
            
            for cmd in commands:
                result = await executor.execute(cmd, force=True)
                outputs.append(f"$ {cmd}\n{result.output}")
                if not result.success:
                    success = False
                    outputs.append(f"ERROR: {result.error}")
                    break
            
            self.total_executions += 1
            self.last_action = datetime.now()
            
            return ExecutionResult(
                task_id=task.id,
                success=success,
                output="\n".join(outputs),
                commands_run=commands,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                backup_created=True,
                can_rollback=True
            )
            
        except Exception as e:
            logger.error(f"Deployment execution failed: {e}")
            return ExecutionResult(
                task_id=task.id,
                success=False,
                output="",
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now()
            )
        finally:
            self._current_tasks -= 1
    
    def _format_context(self, context: dict) -> str:
        """Format context for prompts."""
        parts = []
        if "service" in context:
            parts.append(f"Service: {context['service']}")
        if "environment" in context:
            parts.append(f"Environment: {context['environment']}")
        if "server" in context:
            parts.append(f"Target server: {context['server']}")
        if "current_version" in context:
            parts.append(f"Current version: {context['current_version']}")
        if "new_version" in context:
            parts.append(f"New version: {context['new_version']}")
        return "\n".join(parts) if parts else "No deployment context."
    
    def _parse_assessment(self, response: str) -> dict:
        """Parse LLM assessment response."""
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
                "deploy_safe": False,
                "risk_level": "high",
                "confidence": 0.3,
                "summary": "Could not parse assessment - treating as high risk"
            }
    
    def _get_deployment_commands(self, task: Task) -> list:
        """Extract deployment commands from task."""
        commands = []
        
        context = task.context
        payload = task.payload
        
        # If commands are explicitly provided
        if "commands" in payload:
            return payload["commands"]
        
        # If it's a service deployment
        if "service" in context:
            service = context["service"]
            server = context.get("server", "secondary")
            
            if server == "primary":
                commands = [
                    f"ssh root@198.54.123.234 'systemctl restart {service}'",
                    f"ssh root@198.54.123.234 'systemctl status {service}'"
                ]
            else:
                commands = [
                    f"systemctl restart {service}",
                    f"systemctl status {service}"
                ]
        
        return commands


