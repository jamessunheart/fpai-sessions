#!/usr/bin/env python3
"""
ARIA ULTRA POWER - WORKFLOW ENGINE
===================================

Core engine for compound action workflows.
Manages workflow lifecycle, trigger evaluation, and action execution.
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

logger = logging.getLogger("aria.workflows.engine")


class WorkflowStatus(Enum):
    """Workflow states."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class WorkflowExecution:
    """Record of a workflow execution."""
    execution_id: str
    workflow_id: str
    trigger_type: str
    trigger_data: Dict
    actions_executed: List[Dict]
    success: bool
    error: Optional[str]
    started_at: float
    completed_at: float
    duration_ms: float


@dataclass
class Workflow:
    """A compound action workflow definition."""
    id: str
    name: str
    description: str
    owner_id: str  # Chat ID of owner
    triggers: List[Dict]  # Trigger definitions
    actions: List[Dict]  # Action definitions
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_triggered: Optional[float] = None
    execution_count: int = 0
    cooldown_seconds: int = 60  # Min time between executions
    max_executions: Optional[int] = None  # None = unlimited
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "triggers": self.triggers,
            "actions": self.actions,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_triggered": self.last_triggered,
            "execution_count": self.execution_count,
            "cooldown_seconds": self.cooldown_seconds,
            "max_executions": self.max_executions,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Workflow":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            owner_id=data["owner_id"],
            triggers=data["triggers"],
            actions=data["actions"],
            status=WorkflowStatus(data.get("status", "active")),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            last_triggered=data.get("last_triggered"),
            execution_count=data.get("execution_count", 0),
            cooldown_seconds=data.get("cooldown_seconds", 60),
            max_executions=data.get("max_executions"),
        )


class WorkflowEngine:
    """
    Core workflow engine for Aria Ultra Power.
    
    Manages:
    - Workflow registration and storage
    - Trigger evaluation loop
    - Action execution with error handling
    - Execution history and audit
    """
    
    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._execution_history: List[WorkflowExecution] = []
        self._max_history = 1000
        
        # Callbacks for notifications
        self._on_execution: Optional[callable] = None
        self._on_error: Optional[callable] = None
        
        logger.info("WorkflowEngine initialized")
    
    def set_callbacks(
        self,
        on_execution: callable = None,
        on_error: callable = None
    ):
        """Set callback functions for notifications."""
        self._on_execution = on_execution
        self._on_error = on_error
    
    def register_workflow(self, workflow: Workflow) -> str:
        """Register a new workflow."""
        self._workflows[workflow.id] = workflow
        logger.info(f"Registered workflow: {workflow.name} ({workflow.id})")
        return workflow.id
    
    def create_workflow(
        self,
        name: str,
        description: str,
        owner_id: str,
        triggers: List[Dict],
        actions: List[Dict],
        cooldown_seconds: int = 60,
        max_executions: Optional[int] = None
    ) -> Workflow:
        """Create and register a new workflow."""
        workflow = Workflow(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            owner_id=owner_id,
            triggers=triggers,
            actions=actions,
            cooldown_seconds=cooldown_seconds,
            max_executions=max_executions,
        )
        self.register_workflow(workflow)
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self, owner_id: str = None) -> List[Workflow]:
        """List all workflows, optionally filtered by owner."""
        workflows = list(self._workflows.values())
        if owner_id:
            workflows = [w for w in workflows if w.owner_id == owner_id]
        return workflows
    
    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a workflow."""
        if workflow_id in self._workflows:
            self._workflows[workflow_id].status = WorkflowStatus.PAUSED
            self._workflows[workflow_id].updated_at = time.time()
            logger.info(f"Paused workflow: {workflow_id}")
            return True
        return False
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        if workflow_id in self._workflows:
            self._workflows[workflow_id].status = WorkflowStatus.ACTIVE
            self._workflows[workflow_id].updated_at = time.time()
            logger.info(f"Resumed workflow: {workflow_id}")
            return True
        return False
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            logger.info(f"Deleted workflow: {workflow_id}")
            return True
        return False
    
    async def start(self):
        """Start the workflow engine loop."""
        if self._running:
            logger.warning("WorkflowEngine already running")
            return
        
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("WorkflowEngine started")
    
    async def stop(self):
        """Stop the workflow engine loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("WorkflowEngine stopped")
    
    async def _run_loop(self):
        """Main workflow evaluation loop."""
        while self._running:
            try:
                await self._evaluate_all_workflows()
            except Exception as e:
                logger.error(f"Workflow loop error: {e}")
            
            # Check every 5 seconds
            await asyncio.sleep(5)
    
    async def _evaluate_all_workflows(self):
        """Evaluate all active workflows."""
        from .triggers import evaluate_trigger
        from .actions import execute_action
        
        current_time = time.time()
        
        for workflow in list(self._workflows.values()):
            # Skip non-active workflows
            if workflow.status != WorkflowStatus.ACTIVE:
                continue
            
            # Check cooldown
            if workflow.last_triggered:
                elapsed = current_time - workflow.last_triggered
                if elapsed < workflow.cooldown_seconds:
                    continue
            
            # Check max executions
            if workflow.max_executions and workflow.execution_count >= workflow.max_executions:
                workflow.status = WorkflowStatus.COMPLETED
                continue
            
            # Evaluate triggers
            try:
                for trigger_def in workflow.triggers:
                    triggered, trigger_data = await evaluate_trigger(trigger_def)
                    
                    if triggered:
                        await self._execute_workflow(workflow, trigger_def, trigger_data)
                        break  # Only execute once per evaluation
            
            except Exception as e:
                logger.error(f"Error evaluating workflow {workflow.id}: {e}")
    
    async def _execute_workflow(
        self,
        workflow: Workflow,
        trigger_def: Dict,
        trigger_data: Dict
    ):
        """Execute a triggered workflow."""
        from .actions import execute_action
        
        execution_id = str(uuid.uuid4())[:8]
        started_at = time.time()
        actions_executed = []
        success = True
        error = None
        
        logger.info(f"Executing workflow: {workflow.name} ({workflow.id})")
        
        try:
            # Execute each action in sequence
            context = {
                "workflow_id": workflow.id,
                "owner_id": workflow.owner_id,
                "trigger_data": trigger_data,
            }
            
            for action_def in workflow.actions:
                # Handle conditional actions
                if "if_price" in action_def or "if_condition" in action_def:
                    # Evaluate condition before executing
                    condition_met = await self._evaluate_condition(action_def, context)
                    if not condition_met:
                        continue
                    # Execute the 'then' actions
                    for then_action in action_def.get("then", []):
                        result = await execute_action(then_action, context)
                        actions_executed.append({
                            "action": then_action,
                            "result": result.to_dict() if hasattr(result, 'to_dict') else str(result)
                        })
                        if not result.success:
                            success = False
                            error = result.error
                            break
                else:
                    # Regular action
                    result = await execute_action(action_def, context)
                    actions_executed.append({
                        "action": action_def,
                        "result": result.to_dict() if hasattr(result, 'to_dict') else str(result)
                    })
                    if not result.success:
                        success = False
                        error = result.error
                        break
            
            # Update workflow state
            workflow.last_triggered = time.time()
            workflow.execution_count += 1
            workflow.updated_at = time.time()
            
        except Exception as e:
            success = False
            error = str(e)
            logger.error(f"Workflow execution error: {e}")
        
        completed_at = time.time()
        
        # Record execution
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow.id,
            trigger_type=trigger_def.get("type", "unknown"),
            trigger_data=trigger_data,
            actions_executed=actions_executed,
            success=success,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=(completed_at - started_at) * 1000,
        )
        
        self._execution_history.append(execution)
        
        # Trim history
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]
        
        # Notify callbacks
        if self._on_execution:
            try:
                await self._on_execution(workflow, execution)
            except Exception as e:
                logger.error(f"Execution callback error: {e}")
        
        if not success and self._on_error:
            try:
                await self._on_error(workflow, execution, error)
            except Exception as e:
                logger.error(f"Error callback error: {e}")
        
        logger.info(f"Workflow {workflow.id} execution complete: success={success}, duration={execution.duration_ms:.2f}ms")
    
    async def _evaluate_condition(self, action_def: Dict, context: Dict) -> bool:
        """Evaluate a conditional action."""
        from .triggers import evaluate_trigger
        
        if "if_price" in action_def:
            # Price-based condition
            price_condition = action_def["if_price"]
            triggered, _ = await evaluate_trigger({
                "type": "price",
                "asset": price_condition.get("asset"),
                "condition": price_condition.get("condition"),
            })
            return triggered
        
        if "if_condition" in action_def:
            # Generic condition
            condition = action_def["if_condition"]
            triggered, _ = await evaluate_trigger(condition)
            return triggered
        
        return True
    
    def get_execution_history(
        self,
        workflow_id: str = None,
        limit: int = 50
    ) -> List[WorkflowExecution]:
        """Get execution history."""
        history = self._execution_history
        if workflow_id:
            history = [e for e in history if e.workflow_id == workflow_id]
        return list(reversed(history[-limit:]))
    
    def get_stats(self) -> Dict:
        """Get engine statistics."""
        active = sum(1 for w in self._workflows.values() if w.status == WorkflowStatus.ACTIVE)
        paused = sum(1 for w in self._workflows.values() if w.status == WorkflowStatus.PAUSED)
        
        return {
            "total_workflows": len(self._workflows),
            "active_workflows": active,
            "paused_workflows": paused,
            "total_executions": len(self._execution_history),
            "running": self._running,
        }


# Singleton instance
_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get the global workflow engine instance."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine


