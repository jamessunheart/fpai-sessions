"""
EVOLUTION MODULE
=================

Self-evolution capabilities for Aria.

The system learns from issues and evolves its own behavior,
verification, healing, and alerting over time.

Key Components:
- SelfEvolutionEngine: Core evolution logic
- ProactiveEvolutionDaemon: Continuous evolution cycles
- EvolutionMemory: Persistent wisdom storage
"""

from .self_evolution_engine import (
    SelfEvolutionEngine,
    EvolutionMemory,
    LessonLearned,
    ProposedEvolution,
    EvolutionType,
    RiskLevel,
    ApprovalStatus,
    get_evolution_engine,
    analyze_and_evolve,
    run_evolution_cycle
)

from .proactive_daemon import (
    ProactiveEvolutionDaemon,
    get_evolution_daemon,
    start_evolution_daemon,
    on_issue_detected,
    get_evolution_recommendations
)

__all__ = [
    # Engine
    "SelfEvolutionEngine",
    "EvolutionMemory",
    "LessonLearned",
    "ProposedEvolution",
    "EvolutionType",
    "RiskLevel",
    "ApprovalStatus",
    "get_evolution_engine",
    "analyze_and_evolve",
    "run_evolution_cycle",
    
    # Daemon
    "ProactiveEvolutionDaemon",
    "get_evolution_daemon",
    "start_evolution_daemon",
    "on_issue_detected",
    "get_evolution_recommendations",
]








