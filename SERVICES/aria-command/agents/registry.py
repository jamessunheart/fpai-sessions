#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - MULTI-AGENT REGISTRY
============================================

Agent registration, discovery, and coordination.

Agents:
- Aria: Command center, orchestrator
- Builder: Autonomous code builder
- Trader: WhaleTrack trading agent
- Monitor: 24/7 system monitor
"""

import os
import asyncio
import logging
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
import httpx

logger = logging.getLogger("aria.agents")

# ============================================================================
# CONFIGURATION
# ============================================================================

AGENT_STATE_DIR = Path(os.getenv("AGENT_STATE_DIR", "/tmp/aria-agents"))
AGENT_STATE_DIR.mkdir(parents=True, exist_ok=True)


class AgentStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class AgentCapability(str, Enum):
    BUILD = "build"           # Can build code
    EXECUTE = "execute"       # Can execute commands
    TRADE = "trade"           # Can execute trades
    MONITOR = "monitor"       # Can monitor systems
    COMMUNICATE = "communicate"  # Can send messages
    LEARN = "learn"           # Can learn/improve


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    id: str
    name: str
    description: str
    capabilities: List[AgentCapability]
    endpoint: str  # Health/API endpoint
    status: AgentStatus = AgentStatus.OFFLINE
    last_heartbeat: datetime = field(default_factory=datetime.now)
    current_task: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "endpoint": self.endpoint,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "current_task": self.current_task,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AgentInfo":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            capabilities=[AgentCapability(c) for c in data.get("capabilities", [])],
            endpoint=data["endpoint"],
            status=AgentStatus(data.get("status", "offline")),
            last_heartbeat=datetime.fromisoformat(data.get("last_heartbeat", datetime.now().isoformat())),
            current_task=data.get("current_task"),
            metadata=data.get("metadata", {})
        )


@dataclass
class AgentMessage:
    """A message between agents."""
    id: str
    from_agent: str
    to_agent: str
    message_type: str
    payload: Dict
    created_at: datetime = field(default_factory=datetime.now)
    read: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "read": self.read
        }


# Default agent definitions
DEFAULT_AGENTS = [
    AgentInfo(
        id="aria",
        name="Aria",
        description="Command center and orchestrator",
        capabilities=[
            AgentCapability.COMMUNICATE,
            AgentCapability.EXECUTE,
            AgentCapability.MONITOR
        ],
        endpoint="http://162.0.208.88:8710/health"
    ),
    AgentInfo(
        id="builder",
        name="Builder",
        description="Autonomous code builder",
        capabilities=[
            AgentCapability.BUILD,
            AgentCapability.LEARN
        ],
        endpoint="http://162.0.208.88:8720/health"
    ),
    AgentInfo(
        id="trader",
        name="WhaleTrack Trader",
        description="Trading signal generator and executor",
        capabilities=[
            AgentCapability.TRADE,
            AgentCapability.MONITOR,
            AgentCapability.LEARN
        ],
        endpoint="http://198.54.123.234:8600/health"
    ),
    AgentInfo(
        id="monitor",
        name="System Monitor",
        description="24/7 system health monitor",
        capabilities=[
            AgentCapability.MONITOR,
            AgentCapability.COMMUNICATE
        ],
        endpoint="http://162.0.208.88:8710/health"  # Part of Aria for now
    )
]


class AgentRegistry:
    """
    Central registry for all agents.
    
    Features:
    - Agent registration and discovery
    - Health checking
    - Status tracking
    - File lock coordination
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.messages: List[AgentMessage] = []
        self.file_locks: Dict[str, str] = {}  # path -> agent_id
        self.http = httpx.AsyncClient(timeout=10.0)
        self.message_handlers: Dict[str, List[Callable]] = {}
        
        # Load default agents
        for agent in DEFAULT_AGENTS:
            self.agents[agent.id] = agent
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    def register_agent(self, agent: AgentInfo):
        """Register a new agent."""
        self.agents[agent.id] = agent
        self._persist_state()
        logger.info(f"Registered agent: {agent.id}")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._persist_state()
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_agents_by_capability(self, capability: AgentCapability) -> List[AgentInfo]:
        """Get all agents with a specific capability."""
        return [a for a in self.agents.values() if capability in a.capabilities]
    
    def get_online_agents(self) -> List[AgentInfo]:
        """Get all online agents."""
        return [a for a in self.agents.values() if a.status == AgentStatus.ONLINE]
    
    async def check_agent_health(self, agent_id: str) -> bool:
        """Check if an agent is healthy."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False
        
        try:
            response = await self.http.get(agent.endpoint)
            healthy = response.status_code == 200
            
            agent.status = AgentStatus.ONLINE if healthy else AgentStatus.ERROR
            agent.last_heartbeat = datetime.now()
            
            return healthy
        except Exception as e:
            logger.debug(f"Health check failed for {agent_id}: {e}")
            agent.status = AgentStatus.OFFLINE
            return False
    
    async def check_all_agents(self) -> Dict[str, bool]:
        """Check health of all agents."""
        results = {}
        for agent_id in self.agents.keys():
            results[agent_id] = await self.check_agent_health(agent_id)
        return results
    
    def heartbeat(self, agent_id: str, task: Optional[str] = None):
        """Record agent heartbeat."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.last_heartbeat = datetime.now()
            agent.status = AgentStatus.BUSY if task else AgentStatus.ONLINE
            agent.current_task = task
    
    # ========== FILE LOCKING ==========
    
    def acquire_lock(self, path: str, agent_id: str) -> bool:
        """
        Acquire a file lock for an agent.
        
        Returns True if lock acquired, False if already locked by another agent.
        """
        if path in self.file_locks:
            if self.file_locks[path] != agent_id:
                return False
        
        self.file_locks[path] = agent_id
        self._persist_state()
        return True
    
    def release_lock(self, path: str, agent_id: str) -> bool:
        """Release a file lock."""
        if path in self.file_locks and self.file_locks[path] == agent_id:
            del self.file_locks[path]
            self._persist_state()
            return True
        return False
    
    def check_lock(self, path: str) -> Optional[str]:
        """Check who holds a lock on a path."""
        return self.file_locks.get(path)
    
    def get_agent_locks(self, agent_id: str) -> List[str]:
        """Get all locks held by an agent."""
        return [p for p, a in self.file_locks.items() if a == agent_id]
    
    # ========== MESSAGING ==========
    
    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        payload: Dict
    ) -> AgentMessage:
        """Send a message to another agent."""
        import hashlib
        
        msg = AgentMessage(
            id=hashlib.md5(f"{from_agent}{to_agent}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload
        )
        
        self.messages.append(msg)
        
        # Trigger handlers
        if to_agent in self.message_handlers:
            for handler in self.message_handlers[to_agent]:
                asyncio.create_task(handler(msg))
        
        # Keep only last 100 messages
        if len(self.messages) > 100:
            self.messages = self.messages[-100:]
        
        logger.info(f"Message sent: {from_agent} -> {to_agent}: {message_type}")
        return msg
    
    def get_messages(self, agent_id: str, unread_only: bool = False) -> List[AgentMessage]:
        """Get messages for an agent."""
        messages = [m for m in self.messages if m.to_agent == agent_id]
        if unread_only:
            messages = [m for m in messages if not m.read]
        return messages
    
    def mark_read(self, message_id: str):
        """Mark a message as read."""
        for msg in self.messages:
            if msg.id == message_id:
                msg.read = True
                break
    
    def register_message_handler(self, agent_id: str, handler: Callable):
        """Register a message handler for an agent."""
        if agent_id not in self.message_handlers:
            self.message_handlers[agent_id] = []
        self.message_handlers[agent_id].append(handler)
    
    # ========== PERSISTENCE ==========
    
    def _persist_state(self):
        """Persist registry state to file."""
        state = {
            "agents": {k: v.to_dict() for k, v in self.agents.items()},
            "file_locks": self.file_locks,
            "messages": [m.to_dict() for m in self.messages[-50:]]  # Keep last 50
        }
        
        state_file = AGENT_STATE_DIR / "registry.json"
        state_file.write_text(json.dumps(state, indent=2))
    
    def _load_state(self):
        """Load registry state from file."""
        state_file = AGENT_STATE_DIR / "registry.json"
        
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                
                for agent_id, data in state.get("agents", {}).items():
                    self.agents[agent_id] = AgentInfo.from_dict(data)
                
                self.file_locks = state.get("file_locks", {})
                
            except Exception as e:
                logger.error(f"Failed to load registry state: {e}")
    
    # ========== STATUS ==========
    
    def get_status(self) -> Dict:
        """Get overall registry status."""
        return {
            "agents": {k: {
                "name": v.name,
                "status": v.status.value,
                "last_heartbeat": v.last_heartbeat.isoformat(),
                "current_task": v.current_task
            } for k, v in self.agents.items()},
            "file_locks": len(self.file_locks),
            "pending_messages": len([m for m in self.messages if not m.read])
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get or create global registry."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


async def check_agent(agent_id: str) -> bool:
    """Check if an agent is online."""
    return await get_registry().check_agent_health(agent_id)


def send_to_agent(to_agent: str, message_type: str, payload: Dict) -> AgentMessage:
    """Send message from Aria to another agent."""
    return get_registry().send_message("aria", to_agent, message_type, payload)


def get_agent_status() -> Dict:
    """Get status of all agents."""
    return get_registry().get_status()


