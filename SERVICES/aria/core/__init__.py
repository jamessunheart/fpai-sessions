"""
ARIA CORE - Unified Intelligence Layer
======================================

This is the single brain for Aria that all interfaces call.

Includes:
- Memory: Persistent conversation context
- Personality: Consistent voice and style
- Router: Intelligent AI backend selection
- Approvals: Smart decision-making
- Proactive: Autonomous monitoring and action
- Curiosity: Pattern discovery engine
- Notifications: Tiered alert system
- Digest: Morning briefing generator
"""

from .memory import AriaMemory, get_memory
from .personality import AriaPersonality, get_personality
from .router import AriaRouter
from .approvals import ApprovalSystem, Decision, DecisionCategory
from .proactive import ProactiveDaemon, get_daemon, Signal, Priority, ActionType
from .curiosity import CuriosityEngine, get_curiosity
from .notifications import NotificationSystem, get_notifications
from .digest import generate_digest, generate_quick_status

__all__ = [
    # Memory
    "AriaMemory", "get_memory",
    # Personality
    "AriaPersonality", "get_personality", 
    # Router
    "AriaRouter",
    # Approvals
    "ApprovalSystem", "Decision", "DecisionCategory",
    # Proactive
    "ProactiveDaemon", "get_daemon", "Signal", "Priority", "ActionType",
    # Curiosity
    "CuriosityEngine", "get_curiosity",
    # Notifications
    "NotificationSystem", "get_notifications",
    # Digest
    "generate_digest", "generate_quick_status",
]

