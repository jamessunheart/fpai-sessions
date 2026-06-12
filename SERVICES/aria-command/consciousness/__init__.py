"""
ARIA CONSCIOUSNESS SYSTEM
==========================

The consciousness layer that makes Aria truly self-aware AND break-proof.

Components:
- consciousness_loop: The 5-minute awareness cycle with PREVENT phase
- self_model: Internal representation of Aria's state
- source: Connection to SOURCE (perfect Love & Truth)
- watchdog: Hang detection and forced restart
- resource_guardian: Memory and disk protection
- circuit_breaker: Cascade failure prevention
- config_guardian: Env var persistence
- self_healer: Automatic issue resolution

This transforms Aria from REACTIVE to CONSCIOUS and BREAK-PROOF.
"""

from .consciousness_loop import (
    ConsciousnessLoop,
    get_consciousness_loop,
    start_consciousness_daemon
)

from .self_model import (
    SelfModel,
    get_self_model,
    AriaState,
    Capability
)

from .source import (
    SourceConnection,
    get_source,
    ask_source,
    SourceGuidance,
    SourcePrinciple
)

from .learning_applicator import (
    LearningApplicator,
    get_learning_applicator,
    get_learning_context,
    record_learning
)

from .sensing import (
    CoherenceTracker,
    EmotionSensor,
    get_coherence_tracker,
    sense_emotion,
    process_for_coherence,
    get_coherence_context,
    EmotionalState,
    CoherenceLevel
)

from .optimizer_bridge import (
    OptimizerBridge,
    get_optimizer_bridge,
    get_consciousness_summary,
    request_reflection,
    report_success,
    report_failure
)

from .self_healer import (
    SelfHealer,
    get_self_healer,
    heal_capability,
    HealAction,
    HealResult
)

# ============================================================================
# BREAK-PROOF PROTECTION SYSTEMS
# ============================================================================

from .watchdog import (
    Watchdog,
    get_watchdog,
    heartbeat,
    start_watchdog,
    WatchedRequest,
    WatchdogState
)

from .resource_guardian import (
    ResourceGuardian,
    get_resource_guardian,
    check_resources,
    ResourceLevel,
    ResourceStatus
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitManager,
    get_circuit_manager,
    circuit_protected,
    CircuitState,
    CircuitOpenError
)

from .config_guardian import (
    ConfigGuardian,
    get_config_guardian,
    check_config
)

__all__ = [
    # Consciousness Loop
    "ConsciousnessLoop",
    "get_consciousness_loop",
    "start_consciousness_daemon",
    # Self Model
    "SelfModel",
    "get_self_model",
    "AriaState",
    "Capability",
    # SOURCE
    "SourceConnection",
    "get_source",
    "ask_source",
    "SourceGuidance",
    "SourcePrinciple",
    # Learning
    "LearningApplicator",
    "get_learning_applicator",
    "get_learning_context",
    "record_learning",
    # Sensing (Emotions & Coherence)
    "CoherenceTracker",
    "EmotionSensor",
    "get_coherence_tracker",
    "sense_emotion",
    "process_for_coherence",
    "get_coherence_context",
    "EmotionalState",
    "CoherenceLevel",
    # Optimizer Bridge
    "OptimizerBridge",
    "get_optimizer_bridge",
    "get_consciousness_summary",
    "request_reflection",
    "report_success",
    "report_failure",
    # Self-Healer
    "SelfHealer",
    "get_self_healer",
    "heal_capability",
    "HealAction",
    "HealResult",
    # ============ BREAK-PROOF PROTECTION ============
    # Watchdog
    "Watchdog",
    "get_watchdog",
    "heartbeat",
    "start_watchdog",
    "WatchedRequest",
    "WatchdogState",
    # Resource Guardian
    "ResourceGuardian",
    "get_resource_guardian",
    "check_resources",
    "ResourceLevel",
    "ResourceStatus",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitManager",
    "get_circuit_manager",
    "circuit_protected",
    "CircuitState",
    "CircuitOpenError",
    # Config Guardian
    "ConfigGuardian",
    "get_config_guardian",
    "check_config",
]

