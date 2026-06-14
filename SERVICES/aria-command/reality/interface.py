"""
Reality Interface - Unified API for real-world actions.

Provides a single interface for all reality-affecting operations,
with appropriate safety checks and logging.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger("aria.reality.interface")


class RealityDomain(Enum):
    """Domains of reality Aria can interact with."""
    SERVER = "server"
    TRADING = "trading"
    PAYMENT = "payment"
    COMMUNICATION = "communication"
    EXTERNAL_API = "external_api"


class ActionRisk(Enum):
    """Risk levels for reality-affecting actions."""
    SAFE = "safe"           # No real-world consequences
    LOW = "low"             # Minor consequences, reversible
    MEDIUM = "medium"       # Significant but recoverable
    HIGH = "high"           # Major consequences
    CRITICAL = "critical"   # Irreversible or financial


@dataclass
class RealityAction:
    """A request to affect reality."""
    id: str
    domain: RealityDomain
    action_type: str
    description: str
    
    # Parameters
    params: Dict[str, Any] = field(default_factory=dict)
    
    # Risk assessment
    risk: ActionRisk = ActionRisk.MEDIUM
    requires_approval: bool = True
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    
    # Result
    success: Optional[bool] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class RealityResult:
    """Result of a reality-affecting action."""
    success: bool
    action_id: str
    domain: RealityDomain
    output: str
    
    # Details
    data: Dict[str, Any] = field(default_factory=dict)
    side_effects: List[str] = field(default_factory=list)
    
    # Reversibility
    can_rollback: bool = False
    rollback_instructions: Optional[str] = None


class RealityProvider(ABC):
    """Base class for reality providers."""
    
    def __init__(self, domain: RealityDomain):
        self.domain = domain
        self.is_available = True
    
    @abstractmethod
    async def execute(self, action: RealityAction) -> RealityResult:
        """Execute a reality-affecting action."""
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """Check if this provider is healthy."""
        pass


class ServerProvider(RealityProvider):
    """Provider for server operations."""
    
    def __init__(self):
        super().__init__(RealityDomain.SERVER)
    
    async def execute(self, action: RealityAction) -> RealityResult:
        """Execute a server operation."""
        from ops.server_ops import (
            get_server_status, restart_service, get_memory_usage,
            fix_memory_issues, fix_docker_issues
        )
        
        action_type = action.action_type
        params = action.params
        
        try:
            if action_type == "status":
                result = await get_server_status()
                return RealityResult(
                    success=True,
                    action_id=action.id,
                    domain=self.domain,
                    output="Server status retrieved",
                    data=result
                )
            
            elif action_type == "restart":
                service = params.get("service")
                server = params.get("server", "secondary")
                result = await restart_service(service, server)
                return RealityResult(
                    success=result.get("success", False),
                    action_id=action.id,
                    domain=self.domain,
                    output=result.get("output", ""),
                    data=result,
                    can_rollback=False
                )
            
            elif action_type == "fix_memory":
                result = await fix_memory_issues()
                return RealityResult(
                    success=True,
                    action_id=action.id,
                    domain=self.domain,
                    output="Memory cleanup completed",
                    data=result,
                    side_effects=result.get("stopped_services", [])
                )
            
            elif action_type == "fix_docker":
                result = await fix_docker_issues()
                return RealityResult(
                    success=True,
                    action_id=action.id,
                    domain=self.domain,
                    output="Docker issues addressed",
                    data=result
                )
            
            else:
                return RealityResult(
                    success=False,
                    action_id=action.id,
                    domain=self.domain,
                    output=f"Unknown action type: {action_type}"
                )
                
        except Exception as e:
            logger.error(f"Server action failed: {e}")
            return RealityResult(
                success=False,
                action_id=action.id,
                domain=self.domain,
                output=f"Error: {str(e)}"
            )
    
    async def check_health(self) -> bool:
        """Check server provider health."""
        try:
            from ops.server_ops import get_server_status
            result = await get_server_status()
            return result.get("secondary", {}).get("status") == "healthy"
        except:
            return False


class TradingProvider(RealityProvider):
    """Provider for trading operations."""
    
    def __init__(self):
        super().__init__(RealityDomain.TRADING)
    
    async def execute(self, action: RealityAction) -> RealityResult:
        """Execute a trading operation."""
        import httpx
        
        action_type = action.action_type
        params = action.params
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if action_type == "get_positions":
                    response = await client.get("http://198.54.123.234:8601/api/positions")
                    if response.status_code == 200:
                        return RealityResult(
                            success=True,
                            action_id=action.id,
                            domain=self.domain,
                            output="Positions retrieved",
                            data=response.json()
                        )
                
                elif action_type == "get_signals":
                    response = await client.get("http://198.54.123.234:8601/api/signals")
                    if response.status_code == 200:
                        return RealityResult(
                            success=True,
                            action_id=action.id,
                            domain=self.domain,
                            output="Signals retrieved",
                            data=response.json()
                        )
                
                elif action_type == "execute_trade":
                    # Trading execution requires explicit approval
                    return RealityResult(
                        success=False,
                        action_id=action.id,
                        domain=self.domain,
                        output="Trade execution requires explicit approval. Use /trade commands."
                    )
                
                return RealityResult(
                    success=False,
                    action_id=action.id,
                    domain=self.domain,
                    output=f"Unknown action type: {action_type}"
                )
                
        except Exception as e:
            logger.error(f"Trading action failed: {e}")
            return RealityResult(
                success=False,
                action_id=action.id,
                domain=self.domain,
                output=f"Error: {str(e)}"
            )
    
    async def check_health(self) -> bool:
        """Check trading provider health."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://198.54.123.234:8601/health")
                return response.status_code == 200
        except:
            return False


class CommunicationProvider(RealityProvider):
    """Provider for communication operations."""
    
    def __init__(self):
        super().__init__(RealityDomain.COMMUNICATION)
    
    async def execute(self, action: RealityAction) -> RealityResult:
        """Execute a communication operation."""
        action_type = action.action_type
        params = action.params
        
        try:
            if action_type == "telegram_message":
                from telegram.bot import send_message
                chat_id = params.get("chat_id")
                text = params.get("text")
                
                success = await send_message(chat_id, text)
                return RealityResult(
                    success=success,
                    action_id=action.id,
                    domain=self.domain,
                    output="Message sent" if success else "Message failed"
                )
            
            elif action_type == "voice_message":
                from telegram.bot import send_voice_message
                chat_id = params.get("chat_id")
                text = params.get("text")
                
                success = await send_voice_message(chat_id, text)
                return RealityResult(
                    success=success,
                    action_id=action.id,
                    domain=self.domain,
                    output="Voice message sent" if success else "Voice message failed"
                )
            
            elif action_type == "phone_call":
                from voice.speak import initiate_call
                phone = params.get("phone")
                message = params.get("message")
                
                success = await initiate_call(phone, message)
                return RealityResult(
                    success=success,
                    action_id=action.id,
                    domain=self.domain,
                    output="Call initiated" if success else "Call failed"
                )
            
            return RealityResult(
                success=False,
                action_id=action.id,
                domain=self.domain,
                output=f"Unknown action type: {action_type}"
            )
            
        except Exception as e:
            logger.error(f"Communication action failed: {e}")
            return RealityResult(
                success=False,
                action_id=action.id,
                domain=self.domain,
                output=f"Error: {str(e)}"
            )
    
    async def check_health(self) -> bool:
        """Check communication provider health."""
        # Check Telegram bot is configured
        import os
        return bool(os.getenv("TELEGRAM_BOT_TOKEN"))


class RealityInterface:
    """
    Unified interface for all reality-affecting operations.
    
    Routes actions to appropriate providers, handles approval flows,
    and logs all reality interactions.
    """
    
    def __init__(self):
        self.providers: Dict[RealityDomain, RealityProvider] = {
            RealityDomain.SERVER: ServerProvider(),
            RealityDomain.TRADING: TradingProvider(),
            RealityDomain.COMMUNICATION: CommunicationProvider()
        }
        
        self.action_log: List[RealityAction] = []
        self.pending_approval: Dict[str, RealityAction] = {}
    
    async def execute(
        self,
        domain: RealityDomain,
        action_type: str,
        params: Dict[str, Any] = None,
        description: str = "",
        force: bool = False
    ) -> RealityResult:
        """
        Execute a reality-affecting action.
        
        Args:
            domain: The reality domain
            action_type: Type of action to perform
            params: Action parameters
            description: Human-readable description
            force: Skip approval for safe operations
        
        Returns:
            RealityResult with outcome
        """
        import hashlib
        
        # Create action
        action_id = hashlib.md5(f"{domain.value}:{action_type}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        action = RealityAction(
            id=action_id,
            domain=domain,
            action_type=action_type,
            description=description or f"{domain.value}:{action_type}",
            params=params or {},
            risk=self._assess_risk(domain, action_type)
        )
        
        # Check if approval is needed
        action.requires_approval = not force and action.risk.value in ["high", "critical"]
        
        if action.requires_approval:
            self.pending_approval[action_id] = action
            return RealityResult(
                success=False,
                action_id=action_id,
                domain=domain,
                output=f"Action requires approval. Use /approve {action_id} to proceed.",
                data={"status": "pending_approval"}
            )
        
        # Execute
        provider = self.providers.get(domain)
        if not provider:
            return RealityResult(
                success=False,
                action_id=action_id,
                domain=domain,
                output=f"No provider for domain: {domain.value}"
            )
        
        result = await provider.execute(action)
        
        # Log
        action.executed_at = datetime.now()
        action.success = result.success
        action.result = result.data
        action.error = None if result.success else result.output
        self.action_log.append(action)
        
        return result
    
    async def approve(self, action_id: str) -> RealityResult:
        """Approve a pending action and execute it."""
        if action_id not in self.pending_approval:
            return RealityResult(
                success=False,
                action_id=action_id,
                domain=RealityDomain.SERVER,
                output=f"Action {action_id} not found in pending approvals"
            )
        
        action = self.pending_approval.pop(action_id)
        
        provider = self.providers.get(action.domain)
        if not provider:
            return RealityResult(
                success=False,
                action_id=action_id,
                domain=action.domain,
                output=f"No provider for domain: {action.domain.value}"
            )
        
        result = await provider.execute(action)
        
        # Log
        action.executed_at = datetime.now()
        action.success = result.success
        self.action_log.append(action)
        
        return result
    
    def _assess_risk(self, domain: RealityDomain, action_type: str) -> ActionRisk:
        """Assess the risk level of an action."""
        # High risk actions
        high_risk = {
            (RealityDomain.TRADING, "execute_trade"),
            (RealityDomain.SERVER, "restart"),
            (RealityDomain.SERVER, "fix_memory"),
        }
        
        # Critical risk actions
        critical_risk = {
            (RealityDomain.TRADING, "emergency_stop"),
            (RealityDomain.SERVER, "shutdown"),
        }
        
        if (domain, action_type) in critical_risk:
            return ActionRisk.CRITICAL
        if (domain, action_type) in high_risk:
            return ActionRisk.HIGH
        if domain == RealityDomain.COMMUNICATION:
            return ActionRisk.LOW
        
        return ActionRisk.MEDIUM
    
    async def check_all_health(self) -> Dict[str, bool]:
        """Check health of all providers."""
        health = {}
        for domain, provider in self.providers.items():
            health[domain.value] = await provider.check_health()
        return health
    
    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approvals."""
        return [
            {
                "id": action.id,
                "domain": action.domain.value,
                "action_type": action.action_type,
                "description": action.description,
                "risk": action.risk.value,
                "created_at": action.created_at.isoformat()
            }
            for action in self.pending_approval.values()
        ]
    
    def get_recent_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent action log."""
        return [
            {
                "id": action.id,
                "domain": action.domain.value,
                "action_type": action.action_type,
                "success": action.success,
                "executed_at": action.executed_at.isoformat() if action.executed_at else None
            }
            for action in self.action_log[-limit:]
        ]


# Singleton instance
_interface: Optional[RealityInterface] = None

def get_reality_interface() -> RealityInterface:
    """Get or create reality interface instance."""
    global _interface
    if _interface is None:
        _interface = RealityInterface()
    return _interface


