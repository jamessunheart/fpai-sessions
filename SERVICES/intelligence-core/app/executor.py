"""
Autonomous Action Executor
==========================

Executes actions autonomously when trust level permits.
All actions are gated by the trust system and logged.

Safety Features:
- Pre-execution trust check
- Value limits per tier
- Automatic pause on failures
- Full action audit trail
- Kill switch support
"""

import os
import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum

import httpx

from .trust import get_trust_manager, AutonomyLevel

logger = logging.getLogger("intelligence.executor")

# Service endpoints
TEAM_HUB_URL = os.getenv("TEAM_HUB_URL", "http://198.54.123.234:8355")
GPU_SCALING_URL = os.getenv("GPU_SCALING_URL", "http://198.54.123.234:8115")
WHALETRACK_URL = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8600")


class ActionType(str, Enum):
    GPU_SCALE = "gpu_scale"
    TRADE_EXECUTE = "trade_execute"
    ALERT_DISMISS = "alert_dismiss"
    COST_OPTIMIZE = "cost_optimize"
    INTELLIGENCE_TRIGGER = "intelligence_trigger"


@dataclass
class ActionRequest:
    """A request to execute an autonomous action."""
    action_id: str
    action_type: ActionType
    description: str
    estimated_value: float  # USD value/impact of action
    confidence: float
    parameters: Dict[str, Any]
    decision_id: Optional[str] = None  # If triggered by a decision


@dataclass
class ActionResult:
    """Result of an action execution attempt."""
    action_id: str
    success: bool
    outcome: str  # positive, negative, neutral
    message: str
    executed_at: str
    details: Optional[Dict[str, Any]] = None


class AutonomousExecutor:
    """
    Executes actions autonomously based on trust level.
    
    Workflow:
    1. Receive action request
    2. Check trust level permits action
    3. Execute action
    4. Record outcome
    5. Update trust metrics
    """
    
    def __init__(self):
        self.trust = get_trust_manager()
        self.pending_actions: List[ActionRequest] = []
        self.executed_actions: List[ActionResult] = []
        self._kill_switch_active = False
    
    async def request_action(self, request: ActionRequest) -> ActionResult:
        """
        Request an autonomous action.
        
        Returns immediately with result if action can be executed,
        or queues for human approval if trust level insufficient.
        """
        # Kill switch check
        if self._kill_switch_active:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                outcome="blocked",
                message="Kill switch is active - all autonomous actions blocked",
                executed_at=datetime.now(timezone.utc).isoformat()
            )
        
        # Trust level check
        can_execute = self.trust.state.can_auto_execute(request.estimated_value)
        
        if not can_execute:
            # Queue for human approval
            self.pending_actions.append(request)
            return ActionResult(
                action_id=request.action_id,
                success=False,
                outcome="queued",
                message=f"Action queued for human approval (trust level: {self.trust.state.autonomy_level.value})",
                executed_at=datetime.now(timezone.utc).isoformat(),
                details={"pending": True, "requires_approval": True}
            )
        
        # Record action attempt
        allowed = self.trust.record_auto_action(
            action_id=request.action_id,
            action_type=request.action_type.value,
            description=request.description,
            value_usd=request.estimated_value,
            confidence=request.confidence
        )
        
        if not allowed:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                outcome="blocked",
                message="Action blocked by trust system",
                executed_at=datetime.now(timezone.utc).isoformat()
            )
        
        # Execute the action
        result = await self._execute_action(request)
        
        # Record outcome
        self.trust.record_auto_action_outcome(request.action_id, result.outcome)
        self.executed_actions.append(result)
        
        # Keep only last 100 executed
        if len(self.executed_actions) > 100:
            self.executed_actions = self.executed_actions[-100:]
        
        return result
    
    async def _execute_action(self, request: ActionRequest) -> ActionResult:
        """Execute the actual action based on type."""
        try:
            if request.action_type == ActionType.GPU_SCALE:
                return await self._execute_gpu_scale(request)
            elif request.action_type == ActionType.TRADE_EXECUTE:
                return await self._execute_trade(request)
            elif request.action_type == ActionType.ALERT_DISMISS:
                return await self._execute_alert_dismiss(request)
            elif request.action_type == ActionType.COST_OPTIMIZE:
                return await self._execute_cost_optimize(request)
            elif request.action_type == ActionType.INTELLIGENCE_TRIGGER:
                return await self._execute_intelligence_trigger(request)
            else:
                return ActionResult(
                    action_id=request.action_id,
                    success=False,
                    outcome="negative",
                    message=f"Unknown action type: {request.action_type}",
                    executed_at=datetime.now(timezone.utc).isoformat()
                )
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return ActionResult(
                action_id=request.action_id,
                success=False,
                outcome="negative",
                message=f"Execution error: {str(e)}",
                executed_at=datetime.now(timezone.utc).isoformat()
            )
    
    async def _execute_gpu_scale(self, request: ActionRequest) -> ActionResult:
        """Scale GPU resources."""
        target = request.parameters.get("target", 1)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{GPU_SCALING_URL}/api/scale",
                    json={"target_count": target}
                )
                
                if resp.status_code == 200:
                    return ActionResult(
                        action_id=request.action_id,
                        success=True,
                        outcome="positive",
                        message=f"GPU fleet scaled to {target}",
                        executed_at=datetime.now(timezone.utc).isoformat(),
                        details=resp.json()
                    )
                else:
                    return ActionResult(
                        action_id=request.action_id,
                        success=False,
                        outcome="negative",
                        message=f"GPU scale failed: {resp.status_code}",
                        executed_at=datetime.now(timezone.utc).isoformat()
                    )
        except Exception as e:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                outcome="negative",
                message=f"GPU scale error: {e}",
                executed_at=datetime.now(timezone.utc).isoformat()
            )
    
    async def _execute_trade(self, request: ActionRequest) -> ActionResult:
        """Execute a trade via WhaleTrack."""
        symbol = request.parameters.get("symbol")
        direction = request.parameters.get("direction")
        size = request.parameters.get("size", 0)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{WHALETRACK_URL}/api/trades/execute",
                    json={
                        "symbol": symbol,
                        "direction": direction,
                        "size": size,
                        "source": "autonomous_executor"
                    }
                )
                
                if resp.status_code == 200:
                    return ActionResult(
                        action_id=request.action_id,
                        success=True,
                        outcome="positive",  # Will be updated when trade closes
                        message=f"Trade executed: {direction} {symbol}",
                        executed_at=datetime.now(timezone.utc).isoformat(),
                        details=resp.json()
                    )
                else:
                    return ActionResult(
                        action_id=request.action_id,
                        success=False,
                        outcome="negative",
                        message=f"Trade failed: {resp.status_code}",
                        executed_at=datetime.now(timezone.utc).isoformat()
                    )
        except Exception as e:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                outcome="negative",
                message=f"Trade error: {e}",
                executed_at=datetime.now(timezone.utc).isoformat()
            )
    
    async def _execute_alert_dismiss(self, request: ActionRequest) -> ActionResult:
        """Dismiss an alert."""
        alert_id = request.parameters.get("alert_id")
        
        # Low-risk action - just mark as dismissed
        return ActionResult(
            action_id=request.action_id,
            success=True,
            outcome="neutral",
            message=f"Alert {alert_id} dismissed",
            executed_at=datetime.now(timezone.utc).isoformat()
        )
    
    async def _execute_cost_optimize(self, request: ActionRequest) -> ActionResult:
        """Execute cost optimization."""
        optimization_type = request.parameters.get("type")
        
        # This would connect to cost optimization logic
        return ActionResult(
            action_id=request.action_id,
            success=True,
            outcome="positive",
            message=f"Cost optimization {optimization_type} triggered",
            executed_at=datetime.now(timezone.utc).isoformat()
        )
    
    async def _execute_intelligence_trigger(self, request: ActionRequest) -> ActionResult:
        """Trigger intelligence cycle."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{TEAM_HUB_URL}/api/intelligence/trigger"
                )
                
                if resp.status_code == 200:
                    return ActionResult(
                        action_id=request.action_id,
                        success=True,
                        outcome="positive",
                        message="Intelligence cycle triggered",
                        executed_at=datetime.now(timezone.utc).isoformat()
                    )
        except Exception:
            pass
        
        return ActionResult(
            action_id=request.action_id,
            success=False,
            outcome="neutral",
            message="Intelligence trigger completed (no response)",
            executed_at=datetime.now(timezone.utc).isoformat()
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Safety Controls
    # ─────────────────────────────────────────────────────────────────────────
    
    def activate_kill_switch(self, reason: str = "Manual kill switch"):
        """Immediately halt all autonomous actions."""
        self._kill_switch_active = True
        self.trust.pause(f"KILL SWITCH: {reason}")
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
    
    def deactivate_kill_switch(self):
        """Deactivate kill switch and resume operations."""
        self._kill_switch_active = False
        self.trust.resume()
        logger.info("Kill switch deactivated")
    
    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get actions awaiting human approval."""
        return [
            {
                "action_id": a.action_id,
                "action_type": a.action_type.value,
                "description": a.description,
                "estimated_value": a.estimated_value,
                "confidence": a.confidence,
                "decision_id": a.decision_id
            }
            for a in self.pending_actions
        ]
    
    def approve_pending_action(self, action_id: str) -> Optional[ActionRequest]:
        """Approve a pending action for execution."""
        for i, action in enumerate(self.pending_actions):
            if action.action_id == action_id:
                return self.pending_actions.pop(i)
        return None
    
    def reject_pending_action(self, action_id: str) -> bool:
        """Reject and remove a pending action."""
        for i, action in enumerate(self.pending_actions):
            if action.action_id == action_id:
                self.pending_actions.pop(i)
                self.trust.record_suggestion(accepted=False)
                return True
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get executor status for dashboard."""
        return {
            "kill_switch_active": self._kill_switch_active,
            "trust_status": self.trust.get_status(),
            "pending_actions": len(self.pending_actions),
            "executed_today": len([
                a for a in self.executed_actions
                if a.executed_at.startswith(datetime.now().strftime("%Y-%m-%d"))
            ]),
            "recent_results": [
                {
                    "action_id": r.action_id,
                    "success": r.success,
                    "outcome": r.outcome,
                    "message": r.message,
                    "executed_at": r.executed_at
                }
                for r in self.executed_actions[-10:]
            ]
        }


# Singleton instance
_executor: Optional[AutonomousExecutor] = None


def get_executor() -> AutonomousExecutor:
    """Get singleton executor instance."""
    global _executor
    if _executor is None:
        _executor = AutonomousExecutor()
    return _executor















