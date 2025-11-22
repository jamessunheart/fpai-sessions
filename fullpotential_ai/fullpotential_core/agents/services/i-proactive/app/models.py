"""Data models for I PROACTIVE"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class TaskPriority(str, Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task execution status"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ModelType(str, Enum):
    """Available AI models for routing"""
    GPT4 = "gpt-4"
    GPT4_TURBO = "gpt-4-turbo-preview"
    CLAUDE_OPUS = "claude-3-opus-20240229"
    CLAUDE_SONNET = "claude-3-sonnet-20240229"
    GEMINI_PRO = "gemini-pro"
    LLAMA_3_1_8B = "llama3.1:8b"  # Local Ollama model - $0 cost, sovereign
    AUTO = "auto"  # Intelligent selection


class AgentRole(str, Enum):
    """CrewAI agent roles"""
    STRATEGIST = "strategist"
    BUILDER = "builder"
    OPTIMIZER = "optimizer"
    DEPLOYER = "deployer"
    ANALYZER = "analyzer"


# === Task Models ===

class Task(BaseModel):
    """A task to be orchestrated"""
    task_id: str
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.QUEUED
    assigned_agent: Optional[AgentRole] = None
    preferred_model: ModelType = ModelType.AUTO
    context: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    estimated_duration_minutes: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskResult(BaseModel):
    """Result of task execution"""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    model_used: Optional[ModelType] = None
    agent_used: Optional[AgentRole] = None
    execution_time_seconds: Optional[float] = None
    cost_usd: Optional[float] = None


# === Strategic Decision Models ===

class DecisionCriteria(BaseModel):
    """Criteria for strategic decision making"""
    revenue_impact: float = Field(ge=0.0, le=1.0, description="Expected revenue impact (0-1)")
    risk_level: float = Field(ge=0.0, le=1.0, description="Risk level (0-1)")
    time_to_value: int = Field(gt=0, description="Days until value is realized")
    resource_requirement: float = Field(ge=0.0, le=1.0, description="Resource intensity (0-1)")
    strategic_alignment: float = Field(ge=0.0, le=1.0, description="Alignment with vision (0-1)")


class Decision(BaseModel):
    """A strategic decision"""
    decision_id: str
    title: str
    description: str
    options: List[str]
    criteria: DecisionCriteria
    recommended_option: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


# === Orchestration Models ===

class BuildRequest(BaseModel):
    """Request to build a new service"""
    service_name: str
    architect_intent: str
    droplet_id: Optional[int] = None
    priority: TaskPriority = TaskPriority.HIGH
    auto_deploy: bool = True
    notify_on_completion: bool = True


class BuildStatus(BaseModel):
    """Status of a service build"""
    build_id: str
    service_name: str
    status: TaskStatus
    progress_percent: int = Field(ge=0, le=100)
    current_step: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    started_at: datetime
    estimated_completion: Optional[datetime] = None


# === UBIC Compliance Models ===

class HealthStatus(BaseModel):
    """Service health status (UBIC compliance)"""
    status: Literal["healthy", "degraded", "unhealthy"]
    droplet_id: int
    service_name: str
    version: str
    uptime_seconds: int
    active_tasks: int
    queued_tasks: int
    total_tasks_completed: int
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    last_check: datetime = Field(default_factory=datetime.now)


class Capabilities(BaseModel):
    """Service capabilities (UBIC compliance)"""
    droplet_id: int
    service_name: str
    capabilities: List[str]
    supported_models: List[ModelType]
    supported_agents: List[AgentRole]
    max_parallel_tasks: int
    features: Dict[str, bool]


class ServiceState(BaseModel):
    """Current service state (UBIC compliance)"""
    droplet_id: int
    service_name: str
    active_agents: int
    queued_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    memory_stores_active: int
    models_available: List[ModelType]
    last_updated: datetime = Field(default_factory=datetime.now)


class Dependency(BaseModel):
    """Service dependency"""
    service_name: str
    url: str
    required: bool
    status: Literal["available", "unavailable", "degraded"]


class Dependencies(BaseModel):
    """Service dependencies (UBIC compliance)"""
    droplet_id: int
    service_name: str
    dependencies: List[Dependency]


class Message(BaseModel):
    """Inter-service message (UBIC compliance)"""
    from_service: str
    to_service: str
    message_type: Literal["task", "event", "query", "response"]
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.MEDIUM
    timestamp: datetime = Field(default_factory=datetime.now)


class MessageResponse(BaseModel):
    """Response to inter-service message"""
    message_id: str
    status: Literal["received", "processing", "completed", "failed"]
    response_payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
