"""
Agent Orchestrator - Coordinates multi-agent decision making.

Routes tasks to appropriate agents, aggregates opinions,
calculates consensus, and manages execution flow.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from .base import (
    Agent, Task, TaskPriority, AgentOpinion, ExecutionResult,
    AgentSpecialty, register_agent, get_all_agents, get_agent
)

logger = logging.getLogger("aria.agents.orchestrator")


@dataclass
class ConsensusResult:
    """Result of multi-agent consensus."""
    task_id: str
    
    # Overall decision
    decision: str  # "approve", "reject", "review"
    confidence: float
    
    # Agent opinions
    opinions: List[AgentOpinion]
    
    # Tier based on confidence
    tier: int  # 1-4
    tier_description: str
    
    # For human review
    requires_approval: bool
    approval_reason: Optional[str] = None
    
    # Merged suggestions
    concerns: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class AgentOrchestrator:
    """
    Coordinates multiple specialized agents for task evaluation and execution.
    
    Flow:
    1. Task arrives
    2. Route to relevant agents based on task type
    3. Collect opinions from each agent
    4. Calculate consensus
    5. Based on confidence tier, either auto-execute or request approval
    6. Execute and track results
    """
    
    # Confidence tiers
    TIER_1_THRESHOLD = 0.90  # Auto-execute
    TIER_2_THRESHOLD = 0.70  # Preview + Quick approve
    TIER_3_THRESHOLD = 0.50  # Detailed review
    # Below TIER_3 = Human required
    
    def __init__(self):
        self.pending_tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []
        self.execution_history: List[ExecutionResult] = []
        
        # Initialize agents
        self._initialize_agents()
        
        logger.info("AgentOrchestrator initialized")
    
    def _initialize_agents(self):
        """Initialize all specialized agents."""
        from .builder import BuilderAgent
        from .reviewer import ReviewerAgent
        from .deployer import DeployerAgent
        from .trader import TraderAgent
        from .monitor import MonitorAgent
        
        # Create and register agents
        agents = [
            BuilderAgent(),
            ReviewerAgent(),
            DeployerAgent(),
            TraderAgent(),
            MonitorAgent()
        ]
        
        for agent in agents:
            register_agent(agent)
        
        logger.info(f"Initialized {len(agents)} agents")
    
    def _get_agents_for_task(self, task: Task) -> List[Agent]:
        """Determine which agents should evaluate a task."""
        agents = []
        all_agents = get_all_agents()
        
        task_type = task.type.lower()
        
        # Map task types to required agent specialties
        type_to_specialties = {
            "code_change": [AgentSpecialty.BUILD, AgentSpecialty.REVIEW],
            "new_feature": [AgentSpecialty.BUILD, AgentSpecialty.REVIEW],
            "bug_fix": [AgentSpecialty.BUILD, AgentSpecialty.REVIEW],
            "refactor": [AgentSpecialty.BUILD, AgentSpecialty.REVIEW],
            "deploy": [AgentSpecialty.DEPLOY, AgentSpecialty.REVIEW],
            "config_change": [AgentSpecialty.DEPLOY],
            "trade": [AgentSpecialty.TRADE],
            "trading_signal": [AgentSpecialty.TRADE],
            "health_check": [AgentSpecialty.MONITOR],
            "alert": [AgentSpecialty.MONITOR],
            "infrastructure": [AgentSpecialty.DEPLOY, AgentSpecialty.MONITOR]
        }
        
        required_specialties = type_to_specialties.get(task_type, [AgentSpecialty.BUILD])
        
        for agent in all_agents:
            if agent.specialty in required_specialties and agent.is_active:
                agents.append(agent)
        
        # Always include monitor for critical tasks
        if task.priority == TaskPriority.CRITICAL:
            monitor = get_agent("monitor")
            if monitor and monitor not in agents:
                agents.append(monitor)
        
        return agents
    
    def _calculate_tier(self, confidence: float, task: Task) -> tuple:
        """Calculate the action tier based on confidence and task type."""
        # Certain task types always require human review regardless of confidence
        high_risk_types = {"deploy", "delete", "security", "production"}
        
        if task.type.lower() in high_risk_types:
            return 4, "High-risk operation requires human approval"
        
        if confidence >= self.TIER_1_THRESHOLD:
            return 1, "Auto-execute (high confidence)"
        elif confidence >= self.TIER_2_THRESHOLD:
            return 2, "Preview + Quick approve"
        elif confidence >= self.TIER_3_THRESHOLD:
            return 3, "Detailed review required"
        else:
            return 4, "Human approval required"
    
    async def process_task(
        self,
        task: str,
        context: Dict[str, Any] = None,
        auto_execute: bool = False,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> Dict[str, Any]:
        """
        Process a task through the multi-agent system.
        
        Args:
            task: Task description
            context: Additional context (files, state, etc.)
            auto_execute: Whether to auto-execute if confidence is high
            priority: Task priority
        
        Returns:
            Processing result with consensus and execution status
        """
        # Create task object
        import hashlib
        task_id = hashlib.sha256(f"{task}:{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        task_obj = Task(
            id=task_id,
            type=self._infer_task_type(task),
            description=task,
            payload={"original_request": task},
            context=context or {},
            priority=priority,
            source="user"
        )
        
        logger.info(f"Processing task: {task_obj.id} - {task_obj.type}")
        
        # Get relevant agents
        agents = self._get_agents_for_task(task_obj)
        logger.info(f"Selected agents: {[a.name for a in agents]}")
        
        # Collect opinions in parallel
        task_obj.status = "processing"
        opinions = await asyncio.gather(*[
            agent.evaluate(task_obj) for agent in agents
        ], return_exceptions=True)
        
        # Filter out errors and collect valid opinions
        valid_opinions = []
        for opinion in opinions:
            if isinstance(opinion, AgentOpinion):
                valid_opinions.append(opinion)
                task_obj.opinions.append(opinion)
            elif isinstance(opinion, Exception):
                logger.error(f"Agent evaluation error: {opinion}")
        
        # Calculate consensus
        consensus = self._build_consensus(task_obj, valid_opinions)
        
        # Determine action based on tier
        result = {
            "task_id": task_id,
            "task_type": task_obj.type,
            "consensus": {
                "decision": consensus.decision,
                "confidence": consensus.confidence,
                "tier": consensus.tier,
                "tier_description": consensus.tier_description
            },
            "opinions": [
                {
                    "agent": o.agent_name,
                    "recommendation": o.recommendation,
                    "confidence": o.confidence,
                    "reasoning": o.reasoning
                }
                for o in valid_opinions
            ],
            "concerns": consensus.concerns,
            "suggestions": consensus.suggestions,
            "requires_approval": consensus.requires_approval
        }
        
        # Auto-execute if allowed and tier 1
        if auto_execute and consensus.tier == 1 and consensus.decision == "approve":
            logger.info(f"Auto-executing task {task_id} (Tier 1)")
            execution = await self._execute_task(task_obj, agents)
            result["execution"] = {
                "success": execution.success,
                "output": execution.output,
                "error": execution.error,
                "files_modified": execution.files_modified
            }
            task_obj.status = "executed" if execution.success else "failed"
        else:
            # Store for manual approval
            self.pending_tasks[task_id] = task_obj
            task_obj.status = "pending_approval"
            result["awaiting_approval"] = True
            result["approval_instructions"] = self._get_approval_instructions(consensus)
        
        return result
    
    def _infer_task_type(self, task: str) -> str:
        """Infer task type from description."""
        task_lower = task.lower()
        
        if any(w in task_lower for w in ["deploy", "release", "push to prod"]):
            return "deploy"
        if any(w in task_lower for w in ["trade", "buy", "sell", "position"]):
            return "trade"
        if any(w in task_lower for w in ["fix", "bug", "error", "issue"]):
            return "bug_fix"
        if any(w in task_lower for w in ["refactor", "clean", "reorganize"]):
            return "refactor"
        if any(w in task_lower for w in ["add", "create", "implement", "build", "new"]):
            return "new_feature"
        if any(w in task_lower for w in ["delete", "remove"]):
            return "delete"
        if any(w in task_lower for w in ["config", "setting", "environment"]):
            return "config_change"
        if any(w in task_lower for w in ["check", "monitor", "health", "status"]):
            return "health_check"
        
        return "code_change"
    
    def _build_consensus(self, task: Task, opinions: List[AgentOpinion]) -> ConsensusResult:
        """Build consensus from agent opinions."""
        if not opinions:
            return ConsensusResult(
                task_id=task.id,
                decision="defer",
                confidence=0.0,
                opinions=[],
                tier=4,
                tier_description="No agent opinions available",
                requires_approval=True,
                approval_reason="No agents could evaluate this task"
            )
        
        # Calculate average confidence
        avg_confidence = sum(o.confidence for o in opinions) / len(opinions)
        
        # Check for rejections
        rejections = [o for o in opinions if o.recommendation == "reject"]
        approvals = [o for o in opinions if o.recommendation == "approve"]
        modifications = [o for o in opinions if o.recommendation == "modify"]
        
        # Determine decision
        if rejections:
            decision = "reject"
            # Lower confidence if there are rejections
            avg_confidence *= 0.5
        elif len(approvals) == len(opinions):
            decision = "approve"
        elif modifications:
            decision = "modify"
            avg_confidence *= 0.8
        else:
            decision = "review"
            avg_confidence *= 0.7
        
        # Calculate tier
        tier, tier_desc = self._calculate_tier(avg_confidence, task)
        
        # Aggregate concerns and suggestions
        all_concerns = []
        all_suggestions = []
        for o in opinions:
            all_concerns.extend(o.concerns)
            all_suggestions.extend(o.suggestions)
        
        # Deduplicate
        concerns = list(set(all_concerns))
        suggestions = list(set(all_suggestions))
        
        return ConsensusResult(
            task_id=task.id,
            decision=decision,
            confidence=avg_confidence,
            opinions=opinions,
            tier=tier,
            tier_description=tier_desc,
            requires_approval=tier >= 2,
            approval_reason=tier_desc if tier >= 2 else None,
            concerns=concerns,
            suggestions=suggestions
        )
    
    async def _execute_task(self, task: Task, agents: List[Agent]) -> ExecutionResult:
        """Execute a task using the appropriate agent."""
        # Find the builder agent for execution
        builder = None
        for agent in agents:
            if agent.specialty == AgentSpecialty.BUILD:
                builder = agent
                break
        
        if not builder:
            builder = get_agent("builder")
        
        if not builder:
            return ExecutionResult(
                task_id=task.id,
                success=False,
                output="",
                error="No builder agent available"
            )
        
        try:
            result = await builder.execute(task)
            self.execution_history.append(result)
            return result
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return ExecutionResult(
                task_id=task.id,
                success=False,
                output="",
                error=str(e)
            )
    
    def _get_approval_instructions(self, consensus: ConsensusResult) -> str:
        """Get human-readable approval instructions."""
        if consensus.tier == 2:
            return "Quick approval needed. Review the preview and confirm."
        elif consensus.tier == 3:
            return "Detailed review required. Please examine the proposed changes carefully."
        else:
            return "Human approval required due to high-risk nature of this operation."
    
    async def approve_task(self, task_id: str) -> Dict[str, Any]:
        """Approve a pending task for execution."""
        if task_id not in self.pending_tasks:
            return {"error": "Task not found"}
        
        task = self.pending_tasks.pop(task_id)
        agents = self._get_agents_for_task(task)
        
        result = await self._execute_task(task, agents)
        task.status = "executed" if result.success else "failed"
        self.completed_tasks.append(task)
        
        return {
            "task_id": task_id,
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "files_modified": result.files_modified
        }
    
    async def reject_task(self, task_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a pending task."""
        if task_id not in self.pending_tasks:
            return {"error": "Task not found"}
        
        task = self.pending_tasks.pop(task_id)
        task.status = "rejected"
        self.completed_tasks.append(task)
        
        return {
            "task_id": task_id,
            "status": "rejected",
            "reason": reason
        }
    
    async def get_all_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        agents = get_all_agents()
        return {
            "agents": [agent.get_status() for agent in agents],
            "pending_tasks": len(self.pending_tasks),
            "completed_tasks": len(self.completed_tasks),
            "recent_executions": len(self.execution_history)
        }
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending tasks."""
        return [
            {
                "id": task.id,
                "type": task.type,
                "description": task.description,
                "priority": task.priority.name,
                "confidence": task.consensus_confidence,
                "recommendation": task.consensus_recommendation
            }
            for task in self.pending_tasks.values()
        ]


# Singleton orchestrator
_orchestrator: Optional[AgentOrchestrator] = None

def get_orchestrator() -> AgentOrchestrator:
    """Get or create the orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


