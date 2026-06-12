"""
Agent Base Classes - Foundation for the multi-agent system.

Each agent has a specialty and can evaluate/execute tasks
in their domain. Agents collaborate through the orchestrator.
"""

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

logger = logging.getLogger("aria.agents.base")


class AgentSpecialty(Enum):
    """Agent specialization areas."""
    BUILD = "build"      # Code creation and modification
    REVIEW = "review"    # Code validation and security
    DEPLOY = "deploy"    # Deployment and infrastructure
    TRADE = "trade"      # Trading decisions
    MONITOR = "monitor"  # System health and monitoring


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentOpinion:
    """An agent's opinion on a task."""
    agent_name: str
    specialty: AgentSpecialty
    
    # Core opinion
    confidence: float  # 0.0 - 1.0
    recommendation: str  # "approve", "reject", "modify", "defer"
    
    # Details
    reasoning: str
    concerns: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    # Proposed changes (if recommendation is "modify")
    proposed_changes: Optional[str] = None
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    evaluation_time_ms: int = 0


@dataclass
class Task:
    """A task to be processed by agents."""
    id: str
    type: str  # "code_change", "deploy", "trade", "config", etc.
    description: str
    
    # Task details
    payload: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    priority: TaskPriority = TaskPriority.MEDIUM
    source: str = "user"  # "user", "proactive", "agent"
    created_at: datetime = field(default_factory=datetime.now)
    
    # Processing state
    status: str = "pending"  # "pending", "processing", "approved", "rejected", "executed"
    opinions: List[AgentOpinion] = field(default_factory=list)
    
    @property
    def consensus_confidence(self) -> float:
        """Calculate consensus confidence from all opinions."""
        if not self.opinions:
            return 0.0
        return sum(o.confidence for o in self.opinions) / len(self.opinions)
    
    @property
    def consensus_recommendation(self) -> str:
        """Get the consensus recommendation."""
        if not self.opinions:
            return "pending"
        
        approvals = sum(1 for o in self.opinions if o.recommendation == "approve")
        rejections = sum(1 for o in self.opinions if o.recommendation == "reject")
        
        if rejections > 0:
            return "reject"
        if approvals == len(self.opinions):
            return "approve"
        return "review"
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        return (
            f"Task [{self.id[:8]}] {self.type}: {self.description}\n"
            f"Status: {self.status} | Priority: {self.priority.name}\n"
            f"Confidence: {self.consensus_confidence:.1%} | Recommendation: {self.consensus_recommendation}"
        )


@dataclass
class ExecutionResult:
    """Result of task execution."""
    task_id: str
    success: bool
    output: str
    error: Optional[str] = None
    
    # Changes made
    files_modified: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)
    
    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    
    # Rollback info
    backup_created: bool = False
    backup_path: Optional[str] = None
    can_rollback: bool = False


class Agent(ABC):
    """
    Base class for all specialized agents.
    
    Each agent:
    - Has a specialty (build, review, deploy, trade, monitor)
    - Is powered by a specific LLM
    - Can evaluate tasks in their domain
    - Can execute approved tasks
    """
    
    def __init__(
        self,
        name: str,
        specialty: AgentSpecialty,
        model: str,
        description: str = ""
    ):
        self.name = name
        self.specialty = specialty
        self.model = model
        self.description = description
        
        # State
        self.is_active = True
        self.last_action = None
        self.total_evaluations = 0
        self.total_executions = 0
        self.success_rate = 1.0
        
        # Configuration
        self.confidence_threshold = 0.7  # Minimum confidence to approve
        self.max_concurrent_tasks = 3
        self._current_tasks = 0
        
        logger.info(f"Agent initialized: {name} ({specialty.value}) using {model}")
    
    @abstractmethod
    async def evaluate(self, task: Task) -> AgentOpinion:
        """
        Evaluate a task and provide an opinion.
        
        Must be implemented by each specialized agent.
        """
        pass
    
    @abstractmethod
    async def execute(self, task: Task) -> ExecutionResult:
        """
        Execute an approved task.
        
        Must be implemented by each specialized agent.
        """
        pass
    
    async def can_handle(self, task: Task) -> bool:
        """Check if this agent can handle a task type."""
        # Override in subclasses for more specific checks
        return self.is_active and self._current_tasks < self.max_concurrent_tasks
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "name": self.name,
            "specialty": self.specialty.value,
            "model": self.model,
            "is_active": self.is_active,
            "current_tasks": self._current_tasks,
            "total_evaluations": self.total_evaluations,
            "total_executions": self.total_executions,
            "success_rate": self.success_rate,
            "last_action": self.last_action.isoformat() if self.last_action else None
        }
    
    def _generate_task_id(self, task_type: str, content: str) -> str:
        """Generate a unique task ID."""
        data = f"{task_type}:{content}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def _call_llm(self, prompt: str, system: str = None) -> str:
        """Call the agent's LLM model."""
        import httpx
        
        # Route based on model
        if "claude" in self.model.lower():
            return await self._call_claude(prompt, system)
        elif "gpt" in self.model.lower():
            return await self._call_openai(prompt, system)
        elif "gemini" in self.model.lower():
            return await self._call_gemini(prompt, system)
        elif "ollama" in self.model.lower() or "llama" in self.model.lower():
            return await self._call_ollama(prompt, system)
        else:
            # Default to Ollama (free, local)
            return await self._call_ollama(prompt, system)
    
    async def _call_claude(self, prompt: str, system: str = None) -> str:
        """Call Claude API."""
        import httpx
        import os
        
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            messages = [{"role": "user", "content": prompt}]
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": messages
            }
            if system:
                payload["system"] = system
            
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Claude API error: {response.text}")
            
            data = response.json()
            return data["content"][0]["text"]
    
    async def _call_openai(self, prompt: str, system: str = None) -> str:
        """Call OpenAI API."""
        import httpx
        import os
        
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 4096
                }
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"OpenAI API error: {response.text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _call_gemini(self, prompt: str, system: str = None) -> str:
        """Call Gemini API."""
        import httpx
        import os
        
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not configured")
        
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                headers={"Content-Type": "application/json"},
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}]
                }
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Gemini API error: {response.text}")
            
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    
    async def _call_ollama(self, prompt: str, system: str = None) -> str:
        """Call local Ollama."""
        import httpx
        
        ollama_url = "http://localhost:11434/api/generate"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                ollama_url,
                json={
                    "model": self.model.replace("ollama/", ""),
                    "prompt": prompt,
                    "system": system or "",
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama error: {response.text}")
            
            data = response.json()
            return data.get("response", "")


# Singleton agent instances (created by orchestrator)
_agents: Dict[str, Agent] = {}

def register_agent(agent: Agent):
    """Register an agent instance."""
    _agents[agent.name] = agent
    logger.info(f"Registered agent: {agent.name}")

def get_agent(name: str) -> Optional[Agent]:
    """Get an agent by name."""
    return _agents.get(name)

def get_all_agents() -> List[Agent]:
    """Get all registered agents."""
    return list(_agents.values())


