"""
Proactive layer - Monitoring, suggestions, and digest generation.
"""

from .monitors import (
    SystemMonitor,
    MonitoringDaemon,
    get_monitor,
    quick_health_check,
    get_server_status,
    Alert,
    AlertLevel,
    MonitorResult
)

from .suggestions import (
    SuggestionEngine,
    get_suggestion_engine,
    analyze_and_suggest,
    get_top_suggestions,
    Suggestion,
    SuggestionCategory,
    Priority
)

from .digest import (
    DigestGenerator,
    get_generator,
    generate_digest,
    get_quick_brief,
    DailyDigest,
    DigestSection
)

__all__ = [
    "SystemMonitor",
    "MonitoringDaemon",
    "get_monitor",
    "quick_health_check",
    "get_server_status",
    "Alert",
    "AlertLevel",
    "MonitorResult",
    "SuggestionEngine",
    "get_suggestion_engine",
    "analyze_and_suggest",
    "get_top_suggestions",
    "Suggestion",
    "SuggestionCategory",
    "Priority",
    "DigestGenerator",
    "get_generator",
    "generate_digest",
    "get_quick_brief",
    "DailyDigest",
    "DigestSection"
]


