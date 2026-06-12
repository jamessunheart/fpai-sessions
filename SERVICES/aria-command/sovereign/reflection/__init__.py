#!/usr/bin/env python3
"""
ARIA AI-TO-AI REFLECTION SYSTEM
===============================

An autonomous improvement loop where AI agents:
1. Review recent chat logs and system performance
2. Have structured multi-round dialogues about what to improve
3. Generate actionable specs from insights
4. Feed specs into the builder pipeline
5. Implement changes automatically (with safety guardrails)
6. Report results cost-efficiently

Usage:
    # Manual reflection cycle
    from sovereign.reflection import run_manual_cycle
    await run_manual_cycle("Testing reflection system")
    
    # Get status
    from sovereign.reflection import get_daemon_status
    status = get_daemon_status()
    
    # Increment interaction counter (call after each user interaction)
    from sovereign.reflection import increment_interactions
    increment_interactions()
"""

from .trigger import (
    ReflectionTrigger,
    TriggerEvent,
    TriggerType,
    get_trigger,
    increment_interactions,
    get_trigger_status,
    pause_triggers,
    resume_triggers,
    trigger_manual
)

from .summarizer import (
    InteractionSummarizer,
    InteractionSummary,
    get_summarizer,
    summarize_interactions
)

from .dialogue import (
    DialogueEngine,
    DialogueResult,
    DialogueMessage,
    DialogueRole,
    ImprovementProposal,
    get_dialogue_engine,
    run_dialogue
)

from .spec_generator import (
    SpecGenerator,
    GeneratedSpec,
    FileChange,
    get_spec_generator,
    generate_specs,
    list_specs,
    get_spec
)

from .builder_bridge import (
    BuilderBridge,
    BuildJob,
    BuildStatus,
    get_builder_bridge,
    queue_specs,
    process_build_queue,
    get_queue_status,
    approve_spec,
    reject_spec,
    rollback_build
)

from .cost_tracker import (
    ReflectionCostTracker,
    CycleCost,
    get_cost_tracker,
    start_cycle,
    end_cycle,
    record_cost,
    get_cost_summary
)

from .reporter import (
    ReflectionReporter,
    CycleReport,
    get_reporter,
    report_cycle,
    send_telegram,
    send_daily_digest,
    send_weekly_digest,
    get_status_message
)

from .daemon import (
    ReflectionDaemon,
    get_daemon,
    run_manual_cycle,
    get_daemon_status
)

__all__ = [
    # Trigger
    "ReflectionTrigger",
    "TriggerEvent",
    "TriggerType",
    "get_trigger",
    "increment_interactions",
    "get_trigger_status",
    "pause_triggers",
    "resume_triggers",
    "trigger_manual",
    
    # Summarizer
    "InteractionSummarizer",
    "InteractionSummary",
    "get_summarizer",
    "summarize_interactions",
    
    # Dialogue
    "DialogueEngine",
    "DialogueResult",
    "DialogueMessage",
    "DialogueRole",
    "ImprovementProposal",
    "get_dialogue_engine",
    "run_dialogue",
    
    # Spec Generator
    "SpecGenerator",
    "GeneratedSpec",
    "FileChange",
    "get_spec_generator",
    "generate_specs",
    "list_specs",
    "get_spec",
    
    # Builder Bridge
    "BuilderBridge",
    "BuildJob",
    "BuildStatus",
    "get_builder_bridge",
    "queue_specs",
    "process_build_queue",
    "get_queue_status",
    "approve_spec",
    "reject_spec",
    "rollback_build",
    
    # Cost Tracker
    "ReflectionCostTracker",
    "CycleCost",
    "get_cost_tracker",
    "start_cycle",
    "end_cycle",
    "record_cost",
    "get_cost_summary",
    
    # Reporter
    "ReflectionReporter",
    "CycleReport",
    "get_reporter",
    "report_cycle",
    "send_telegram",
    "send_daily_digest",
    "send_weekly_digest",
    "get_status_message",
    
    # Daemon
    "ReflectionDaemon",
    "get_daemon",
    "run_manual_cycle",
    "get_daemon_status",
]


