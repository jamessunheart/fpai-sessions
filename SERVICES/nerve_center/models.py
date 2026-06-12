"""
Nerve Center Data Models
========================
Defines the structure of events, state, and priorities for real-time awareness.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json


class EventType(str, Enum):
    # Thinking System
    THINKING_CYCLE_STARTED = "thinking.cycle.started"
    THINKING_CYCLE_COMPLETED = "thinking.cycle.completed"
    INSIGHT_GENERATED = "thinking.insight.generated"
    
    # Builder/Hive System
    PROPOSAL_CREATED = "builder.proposal.created"
    BUILD_STARTED = "builder.build.started"
    BUILD_COMPLETED = "builder.build.completed"
    BUILD_FAILED = "builder.build.failed"
    DEPLOYMENT_STARTED = "builder.deployment.started"
    DEPLOYMENT_COMPLETED = "builder.deployment.completed"
    
    # GPU Infrastructure
    GPU_POD_CREATED = "gpu.pod.created"
    GPU_POD_STARTED = "gpu.pod.started"
    GPU_POD_STOPPED = "gpu.pod.stopped"
    GPU_POD_TERMINATED = "gpu.pod.terminated"
    GPU_COST_UPDATE = "gpu.cost.update"
    
    # Service Health
    SERVICE_UP = "service.up"
    SERVICE_DOWN = "service.down"
    SERVICE_DEGRADED = "service.degraded"
    
    # Agent Activity
    AGENT_REGISTERED = "agent.registered"
    AGENT_CLAIMED_WORK = "agent.claimed"
    AGENT_COMPLETED_WORK = "agent.completed"
    AGENT_HEARTBEAT = "agent.heartbeat"
    
    # Escalations
    ESCALATION_CREATED = "escalation.created"
    ESCALATION_RESOLVED = "escalation.resolved"
    
    # System
    SYSTEM_PULSE = "system.pulse"
    FOCUS_CHANGED = "system.focus.changed"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SystemEvent:
    """A single event in the system."""
    id: str
    event_type: str
    source: str  # Which subsystem generated this
    timestamp: str
    data: Dict[str, Any]
    priority: str = "medium"
    
    def to_dict(self):
        return asdict(self)
    
    def to_json(self):
        return json.dumps(self.to_dict())


@dataclass
class CurrentFocus:
    """What the system is currently focused on."""
    activity: str  # e.g., "thinking", "building", "deploying", "idle"
    description: str
    started_at: str
    subsystem: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ResourceAllocation:
    """Where resources are being spent."""
    gpu_pods_running: int
    gpu_hourly_cost: float
    gpu_daily_estimate: float
    active_builds: int
    pending_proposals: int
    thinking_cycles_today: int
    insights_pending: int
    
    def to_dict(self):
        return asdict(self)


@dataclass
class PriorityItem:
    """An item in the priority queue."""
    id: str
    title: str
    category: str  # proposal, escalation, insight, etc.
    priority: str
    created_at: str
    claimed_by: Optional[str] = None
    status: str = "pending"
    
    def to_dict(self):
        return asdict(self)


@dataclass
class AgentState:
    """State of a connected agent (human or AI)."""
    agent_id: str
    agent_type: str  # "human", "cursor", "daemon"
    current_task: Optional[str] = None
    last_heartbeat: str = ""
    connected_at: str = ""
    
    def to_dict(self):
        return asdict(self)


@dataclass
class SystemPulse:
    """Complete system state snapshot."""
    timestamp: str
    focus: CurrentFocus
    resources: ResourceAllocation
    recent_events: List[SystemEvent]
    priority_queue: List[PriorityItem]
    active_agents: List[AgentState]
    health_score: float
    services_status: Dict[str, str]
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "focus": self.focus.to_dict(),
            "resources": self.resources.to_dict(),
            "recent_events": [e.to_dict() for e in self.recent_events],
            "priority_queue": [p.to_dict() for p in self.priority_queue],
            "active_agents": [a.to_dict() for a in self.active_agents],
            "health_score": self.health_score,
            "services_status": self.services_status
        }
    
    def to_json(self):
        return json.dumps(self.to_dict())





















