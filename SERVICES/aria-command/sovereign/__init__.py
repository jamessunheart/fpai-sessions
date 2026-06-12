"""
Sovereign Intelligence - Self-improving AI system.

Components:
- Meta-learning: Aria improves her own processes
- Self-modification: Safe code updates with safeguards
- Dashboard: Real-time view of Aria's state
- Opus Reviewer: AI-powered code review
- Risk Engine: Change risk classification
- Auto Executor: Safe change execution
- Cost Tracker: API cost management
"""

from .cost_tracker import (
    CostTracker,
    get_cost_tracker,
    log_cost,
    can_spend,
    get_remaining_budget
)

from .risk_engine import (
    RiskEngine,
    RiskLevel,
    RiskAssessment,
    get_risk_engine,
    assess_change,
    can_auto_execute
)

from .opus_reviewer import (
    OpusReviewer,
    ReviewDaemon,
    ImprovementProposal,
    get_reviewer,
    get_daemon,
    run_manual_review
)

from .auto_executor import (
    AutoExecutor,
    ExecutionResult,
    ChangelogEntry,
    get_executor,
    execute_improvement,
    get_changelog
)

__all__ = [
    # Cost Tracker
    "CostTracker",
    "get_cost_tracker",
    "log_cost",
    "can_spend",
    "get_remaining_budget",
    
    # Risk Engine
    "RiskEngine",
    "RiskLevel",
    "RiskAssessment",
    "get_risk_engine",
    "assess_change",
    "can_auto_execute",
    
    # Opus Reviewer
    "OpusReviewer",
    "ReviewDaemon",
    "ImprovementProposal",
    "get_reviewer",
    "get_daemon",
    "run_manual_review",
    
    # Auto Executor
    "AutoExecutor",
    "ExecutionResult",
    "ChangelogEntry",
    "get_executor",
    "execute_improvement",
    "get_changelog",
]
