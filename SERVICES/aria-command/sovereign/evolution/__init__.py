"""
Aria Autonomous Evolution System
=================================

A comprehensive self-improvement system that learns from all interactions
and automatically evolves Aria's capabilities.

THREE-TIER ARCHITECTURE:
========================

TIER 1: Immediate Learning (< 100ms)
- RealtimeLearner: Per-interaction learning
- CorrectionHandler: Immediate correction detection
- ResponseCache: Intelligent response caching
- MetricsWindow: Rolling window metrics

TIER 2: Triggered Evolution (1-5 min)
- TriggerEngine: Event-driven triggers
- ErrorSpikeHandler: Error spike auto-fix

TIER 3: Scheduled Analysis (Daily)
- AdaptiveScheduler: Dynamic scheduling
- PatternSynthesizer: AI-powered proposals
- EvolutionDaemon: Orchestrates everything

LEGACY COMPONENTS:
- InteractionLogger: Comprehensive interaction tracking
- SuccessDetector: Identifies successful patterns
- PromptEvolver: Auto-improves system prompts
- CapabilityEvolver: Expands capabilities based on requests
- ProactiveEvolver: Learns when to initiate actions
- EfficiencyEvolver: Optimizes costs and speed
- SafeApplicator: Validates and safely applies changes
"""

# ============================================================================
# TIER 1: IMMEDIATE LEARNING
# ============================================================================

# Realtime Learner
from .realtime_learner import (
    RealtimeLearner,
    get_realtime_learner,
    process_interaction as realtime_process,
    get_query_insights,
    CorrectionPair,
    SuccessPattern as RealtimeSuccessPattern
)

# Correction Handler
from .correction_handler import (
    CorrectionHandler,
    get_correction_handler,
    detect_and_learn,
    enhance_query,
    CorrectionEvent
)

# Response Cache
from .response_cache import (
    ResponseCache,
    get_response_cache,
    check_cache,
    cache_response,
    invalidate_cache,
    CachedResponse
)

# Metrics Window
from .metrics_window import (
    MetricsWindow,
    get_metrics_window,
    record_metric,
    record_interaction as record_metrics_interaction,
    get_metrics_summary,
    MetricType,
    AlertLevel
)

# ============================================================================
# TIER 2: TRIGGERED EVOLUTION
# ============================================================================

# Trigger Engine
from .trigger_engine import (
    TriggerEngine,
    get_trigger_engine,
    start_trigger_engine,
    stop_trigger_engine,
    report_interaction,
    TriggerType,
    TriggerEvent
)

# Error Spike Handler
from .error_spike_handler import (
    ErrorSpikeHandler,
    get_error_spike_handler,
    record_error,
    check_and_fix_spike,
    ErrorSpike,
    ErrorCategory
)

# ============================================================================
# TIER 3: SCHEDULED ANALYSIS
# ============================================================================

# Adaptive Scheduler
from .adaptive_scheduler import (
    AdaptiveScheduler,
    get_adaptive_scheduler,
    start_scheduler,
    stop_scheduler,
    record_user_activity,
    TaskType,
    UserActivityPattern
)

# ============================================================================
# LEGACY COMPONENTS (Still Active)
# ============================================================================

# Interaction Logger
from .interaction_logger import (
    InteractionLogger,
    get_interaction_logger,
    log_interaction,
    get_evolution_data,
    SatisfactionSignal,
    IntentCategory
)

# Success Detector
from .success_detector import (
    SuccessDetector,
    get_success_detector,
    analyze_successes,
    get_recommendations,
    SuccessPattern
)

# Pattern Synthesizer
from .synthesizer import (
    PatternSynthesizer,
    get_synthesizer,
    analyze_and_propose,
    get_pending_proposals,
    ImprovementProposal
)

# Prompt Evolver
from .prompt_evolver import (
    PromptEvolver,
    get_prompt_evolver,
    evolve_from_patterns,
    rollback_prompt,
    PromptVersion
)

# Capability Evolver
from .capability_evolver import (
    CapabilityEvolver,
    get_capability_evolver,
    record_capability_request,
    get_proposed_capabilities,
    CapabilityProposal
)

# Proactive Evolver
from .proactive_evolver import (
    ProactiveEvolver,
    get_proactive_evolver,
    learn_proactive_pattern,
    get_proactive_actions,
    ProactivePattern
)

# Efficiency Evolver
from .efficiency_evolver import (
    EfficiencyEvolver,
    get_efficiency_evolver,
    check_cache,
    recommend_model,
    record_efficiency_metrics
)

# Safe Applicator
from .safe_applicator import (
    SafeApplicator,
    get_safe_applicator,
    apply_proposal,
    Change,
    ChangeType,
    ChangeStatus
)

# Evolution Daemon
from .evolution_daemon import (
    EvolutionDaemon,
    get_evolution_daemon,
    start_evolution_daemon,
    stop_evolution_daemon,
    on_aria_interaction,
    EvolutionCycleResult
)

# Original learner (for backward compatibility)
from .learner import (
    EvolutionLearner,
    get_learner,
    learn_from_error,
    propose_new_pattern
)

# Pattern Detectors
from .pattern_detectors import (
    PatternDetectorManager,
    get_pattern_manager,
    detect_patterns,
    detect_patterns_single,
    get_high_severity_patterns,
    save_patterns,
    DetectedPattern,
    ApprovalOverheadDetector,
    FollowThroughFailureDetector,
    ToolOveruseDetector,
    SlowResponseDetector,
    CorrectionNeededDetector
)

# Notifications
from .notifications import (
    EvolutionNotifier,
    notifier,
    notify_patterns_detected,
    notify_proposal_created,
    notify_change_applied,
    notify_rollback,
    notify_evolution_error
)

__all__ = [
    # ============================================================================
    # TIER 1: IMMEDIATE LEARNING
    # ============================================================================
    
    # Realtime Learner
    "RealtimeLearner",
    "get_realtime_learner",
    "realtime_process",
    "get_query_insights",
    "CorrectionPair",
    "RealtimeSuccessPattern",
    
    # Correction Handler
    "CorrectionHandler",
    "get_correction_handler",
    "detect_and_learn",
    "enhance_query",
    "CorrectionEvent",
    
    # Response Cache
    "ResponseCache",
    "get_response_cache",
    "check_cache",
    "cache_response",
    "invalidate_cache",
    "CachedResponse",
    
    # Metrics Window
    "MetricsWindow",
    "get_metrics_window",
    "record_metric",
    "record_metrics_interaction",
    "get_metrics_summary",
    "MetricType",
    "AlertLevel",
    
    # ============================================================================
    # TIER 2: TRIGGERED EVOLUTION
    # ============================================================================
    
    # Trigger Engine
    "TriggerEngine",
    "get_trigger_engine",
    "start_trigger_engine",
    "stop_trigger_engine",
    "report_interaction",
    "TriggerType",
    "TriggerEvent",
    
    # Error Spike Handler
    "ErrorSpikeHandler",
    "get_error_spike_handler",
    "record_error",
    "check_and_fix_spike",
    "ErrorSpike",
    "ErrorCategory",
    
    # ============================================================================
    # TIER 3: SCHEDULED ANALYSIS
    # ============================================================================
    
    # Adaptive Scheduler
    "AdaptiveScheduler",
    "get_adaptive_scheduler",
    "start_scheduler",
    "stop_scheduler",
    "record_user_activity",
    "TaskType",
    "UserActivityPattern",
    
    # ============================================================================
    # LEGACY COMPONENTS (Still Active)
    # ============================================================================
    
    # Interaction Logger
    "InteractionLogger",
    "get_interaction_logger",
    "log_interaction",
    "get_evolution_data",
    "SatisfactionSignal",
    "IntentCategory",
    
    # Success Detector
    "SuccessDetector",
    "get_success_detector",
    "analyze_successes",
    "get_recommendations",
    "SuccessPattern",
    
    # Synthesizer
    "PatternSynthesizer",
    "get_synthesizer",
    "analyze_and_propose",
    "get_pending_proposals",
    "ImprovementProposal",
    
    # Prompt Evolver
    "PromptEvolver",
    "get_prompt_evolver",
    "evolve_from_patterns",
    "rollback_prompt",
    "PromptVersion",
    
    # Capability Evolver
    "CapabilityEvolver",
    "get_capability_evolver",
    "record_capability_request",
    "get_proposed_capabilities",
    "CapabilityProposal",
    
    # Proactive Evolver
    "ProactiveEvolver",
    "get_proactive_evolver",
    "learn_proactive_pattern",
    "get_proactive_actions",
    "ProactivePattern",
    
    # Efficiency Evolver
    "EfficiencyEvolver",
    "get_efficiency_evolver",
    "recommend_model",
    "record_efficiency_metrics",
    
    # Safe Applicator
    "SafeApplicator",
    "get_safe_applicator",
    "apply_proposal",
    "Change",
    "ChangeType",
    "ChangeStatus",
    
    # Evolution Daemon
    "EvolutionDaemon",
    "get_evolution_daemon",
    "start_evolution_daemon",
    "stop_evolution_daemon",
    "on_aria_interaction",
    "EvolutionCycleResult",
    
    # Learner (backward compat)
    "EvolutionLearner",
    "get_learner",
    "learn_from_error",
    "propose_new_pattern",
    
    # ============================================================================
    # PATTERN DETECTION & NOTIFICATIONS
    # ============================================================================
    
    # Pattern Detectors
    "PatternDetectorManager",
    "get_pattern_manager",
    "detect_patterns",
    "detect_patterns_single",
    "get_high_severity_patterns",
    "save_patterns",
    "DetectedPattern",
    "ApprovalOverheadDetector",
    "FollowThroughFailureDetector",
    "ToolOveruseDetector",
    "SlowResponseDetector",
    "CorrectionNeededDetector",
    
    # Notifications
    "EvolutionNotifier",
    "notifier",
    "notify_patterns_detected",
    "notify_proposal_created",
    "notify_change_applied",
    "notify_rollback",
    "notify_evolution_error",
]
