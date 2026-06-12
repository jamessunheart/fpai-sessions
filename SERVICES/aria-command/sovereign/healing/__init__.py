"""
Aria Self-Healing System

Automatically detects, diagnoses, and repairs common failures.
"""

from .patterns import (
    HEALING_PATTERNS,
    HealingPattern,
    Severity,
    match_error_pattern
)

from .actions import (
    HealingAction,
    execute_healing_action,
    clear_conversation_history,
    restart_service,
    clear_caches,
    switch_model_fallback
)

from .daemon import (
    SelfHealingDaemon,
    get_healing_daemon,
    start_healing_daemon
)

__all__ = [
    # Patterns
    "HEALING_PATTERNS",
    "HealingPattern", 
    "Severity",
    "match_error_pattern",
    
    # Actions
    "HealingAction",
    "execute_healing_action",
    "clear_conversation_history",
    "restart_service",
    "clear_caches",
    "switch_model_fallback",
    
    # Daemon
    "SelfHealingDaemon",
    "get_healing_daemon",
    "start_healing_daemon",
]


