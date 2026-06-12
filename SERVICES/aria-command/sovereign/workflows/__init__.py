#!/usr/bin/env python3
"""
ARIA ULTRA POWER - WORKFLOW SYSTEM
===================================

Compound action workflows that execute multiple actions based on triggers.
Enables "if-then" automation chains for trading, alerts, and server ops.
"""

from .engine import (
    WorkflowEngine,
    get_workflow_engine,
    Workflow,
    WorkflowStatus,
)

from .triggers import (
    Trigger,
    TriggerType,
    PriceTrigger,
    TimeTrigger,
    EventTrigger,
    CompoundTrigger,
    evaluate_trigger,
)

from .actions import (
    ActionType,
    ActionResult,
    ActionLibrary,
    execute_action,
    get_action_library,
)

from .store import (
    WorkflowStore,
    get_workflow_store,
)

__all__ = [
    # Engine
    "WorkflowEngine",
    "get_workflow_engine",
    "Workflow",
    "WorkflowStatus",
    # Triggers
    "Trigger",
    "TriggerType",
    "PriceTrigger",
    "TimeTrigger",
    "EventTrigger",
    "CompoundTrigger",
    "evaluate_trigger",
    # Actions
    "ActionType",
    "ActionResult",
    "ActionLibrary",
    "execute_action",
    "get_action_library",
    # Store
    "WorkflowStore",
    "get_workflow_store",
]

