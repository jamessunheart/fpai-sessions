#!/usr/bin/env python3
"""
ARIA ASCENSION SYSTEM
=====================

Transform Aria from capable assistant to autonomous superintelligent partner.

Phases:
1. Continuous Learning - Real-time pattern detection and memory
2. Predictive Intelligence - Anticipate needs before asking
3. Autonomous Execution - Self-improvement without approval
4. Multi-Agent Swarm - Specialized agents collaborating
5. Real-World Agency - External actions (email, calendar, etc.)
6. Revenue Engine - Active value generation
"""

# Phase 1: Continuous Learning
from .stream_processor import (
    StreamProcessor,
    FeatureExtractor,
    InteractionFeatures,
    Intent,
    Sentiment,
    get_stream_processor,
    process_interaction,
    get_recent_features
)

from .memory_graph import (
    MemoryGraph,
    Node,
    Edge,
    NodeType,
    EdgeType,
    get_memory_graph,
    learn_from_interaction,
    predict_user_need
)

from .micro_learner import (
    MicroLearner,
    ResponseConfig,
    FeedbackSignal,
    get_micro_learner,
    record_feedback,
    get_response_recommendations,
    get_optimal_length
)

# Phase 2: Predictive Intelligence
from .rhythm_detector import (
    RhythmDetector,
    PredictedNeed,
    get_rhythm_detector,
    record_activity,
    predict_current_need
)

from .context_analyzer import (
    ContextAnalyzer,
    ContextAnalysis,
    EmotionalState,
    AttentionLevel,
    get_context_analyzer,
    analyze_context
)

from .proactive_engine import (
    ProactiveEngine,
    ProactiveAction,
    ActionType,
    ActionPriority,
    get_proactive_engine,
    queue_proactive,
    process_proactive_queue,
    create_proactive
)

# Phase 3: Autonomous Execution
from .confidence_scorer import (
    ConfidenceScorer,
    ConfidenceScore,
    ProposedChange,
    RiskLevel,
    ChangeType,
    get_confidence_scorer,
    score_change,
    can_auto_apply
)

from .ab_tester import (
    ABTester,
    ABTest,
    ABVariant,
    TestResult,
    TestStatus,
    get_ab_tester,
    create_ab_test,
    get_variant_config,
    record_ab_sample
)

from .degradation_monitor import (
    DegradationMonitor,
    DegradationAlert,
    MetricSnapshot,
    MetricType,
    DegradationSeverity,
    get_degradation_monitor,
    record_interaction_metrics,
    register_change_for_monitoring
)

__all__ = [
    # Phase 1: Continuous Learning
    "StreamProcessor",
    "FeatureExtractor", 
    "InteractionFeatures",
    "Intent",
    "Sentiment",
    "get_stream_processor",
    "process_interaction",
    "get_recent_features",
    "MemoryGraph",
    "Node",
    "Edge",
    "NodeType",
    "EdgeType",
    "get_memory_graph",
    "learn_from_interaction",
    "predict_user_need",
    "MicroLearner",
    "ResponseConfig",
    "FeedbackSignal",
    "get_micro_learner",
    "record_feedback",
    "get_response_recommendations",
    "get_optimal_length",
    
    # Phase 2: Predictive Intelligence
    "RhythmDetector",
    "PredictedNeed",
    "get_rhythm_detector",
    "record_activity",
    "predict_current_need",
    "ContextAnalyzer",
    "ContextAnalysis",
    "EmotionalState",
    "AttentionLevel",
    "get_context_analyzer",
    "analyze_context",
    "ProactiveEngine",
    "ProactiveAction",
    "ActionType",
    "ActionPriority",
    "get_proactive_engine",
    "queue_proactive",
    "process_proactive_queue",
    "create_proactive",
    
    # Phase 3: Autonomous Execution
    "ConfidenceScorer",
    "ConfidenceScore",
    "ProposedChange",
    "RiskLevel",
    "ChangeType",
    "get_confidence_scorer",
    "score_change",
    "can_auto_apply",
    "ABTester",
    "ABTest",
    "ABVariant",
    "TestResult",
    "TestStatus",
    "get_ab_tester",
    "create_ab_test",
    "get_variant_config",
    "record_ab_sample",
    "DegradationMonitor",
    "DegradationAlert",
    "MetricSnapshot",
    "MetricType",
    "DegradationSeverity",
    "get_degradation_monitor",
    "record_interaction_metrics",
    "register_change_for_monitoring",
]

