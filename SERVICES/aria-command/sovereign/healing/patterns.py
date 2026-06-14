#!/usr/bin/env python3
"""
ARIA ERROR PATTERN DATABASE
============================

Known failure patterns and their corresponding auto-fix actions.
Each pattern includes:
- Regex pattern to match in logs
- Fix action to execute
- Severity level
- Description for humans
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger("aria.healing.patterns")


class Severity(str, Enum):
    """Severity levels for errors."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


@dataclass
class HealingPattern:
    """A pattern that triggers healing."""
    id: str
    name: str
    pattern: str  # Regex pattern
    fix_action: str  # Name of healing action to execute
    severity: Severity
    description: str
    
    # Tracking
    match_count: int = 0
    last_match: Optional[datetime] = None
    last_heal: Optional[datetime] = None
    heal_success_count: int = 0
    heal_fail_count: int = 0
    
    # Options
    cooldown_seconds: int = 300  # Min time between heals
    max_heals_per_hour: int = 3
    requires_approval: bool = False
    
    def matches(self, error_text: str) -> bool:
        """Check if error matches this pattern."""
        try:
            if re.search(self.pattern, error_text, re.IGNORECASE | re.MULTILINE):
                self.match_count += 1
                self.last_match = datetime.now()
                return True
        except re.error as e:
            logger.error(f"Invalid regex pattern {self.id}: {e}")
        return False
    
    def can_heal(self) -> bool:
        """Check if we can heal (not in cooldown, not exceeded max)."""
        now = datetime.now()
        
        # Check cooldown
        if self.last_heal:
            elapsed = (now - self.last_heal).total_seconds()
            if elapsed < self.cooldown_seconds:
                logger.debug(f"Pattern {self.id} in cooldown ({elapsed:.0f}s < {self.cooldown_seconds}s)")
                return False
        
        # Check hourly limit
        # TODO: Track per-hour heal count
        
        return True
    
    def record_heal(self, success: bool):
        """Record a healing attempt."""
        self.last_heal = datetime.now()
        if success:
            self.heal_success_count += 1
        else:
            self.heal_fail_count += 1


# ============================================================================
# KNOWN ERROR PATTERNS
# ============================================================================

HEALING_PATTERNS: Dict[str, HealingPattern] = {
    
    # --- API Errors ---
    
    "anthropic_tool_calls_error": HealingPattern(
        id="anthropic_tool_calls_error",
        name="Anthropic Tool Calls Format Error",
        pattern=r"tool_calls.*Extra inputs|Extra inputs.*tool_calls",
        fix_action="clear_conversation_history",
        severity=Severity.CRITICAL,
        description="Conversation history contains tool_calls which Anthropic rejects",
        cooldown_seconds=60
    ),
    
    "anthropic_rate_limit": HealingPattern(
        id="anthropic_rate_limit",
        name="Anthropic Rate Limit",
        pattern=r"rate_limit|429.*anthropic|anthropic.*429",
        fix_action="rate_limit_backoff",
        severity=Severity.WARNING,
        description="Hit Anthropic API rate limit",
        cooldown_seconds=60
    ),
    
    "anthropic_overloaded": HealingPattern(
        id="anthropic_overloaded",
        name="Anthropic Overloaded",
        pattern=r"overloaded|529.*anthropic|anthropic.*529",
        fix_action="switch_model_fallback",
        severity=Severity.WARNING,
        description="Anthropic servers overloaded",
        cooldown_seconds=30
    ),
    
    "openai_rate_limit": HealingPattern(
        id="openai_rate_limit",
        name="OpenAI Rate Limit",
        pattern=r"rate_limit.*openai|openai.*rate_limit|429.*openai",
        fix_action="rate_limit_backoff",
        severity=Severity.WARNING,
        description="Hit OpenAI API rate limit"
    ),
    
    "api_key_invalid": HealingPattern(
        id="api_key_invalid",
        name="API Key Invalid",
        pattern=r"invalid.*api.*key|api.*key.*invalid|401.*unauthorized",
        fix_action="alert_human",
        severity=Severity.FATAL,
        description="API key is invalid - requires human intervention",
        requires_approval=True
    ),
    
    # --- Service Errors ---
    
    "service_connection_refused": HealingPattern(
        id="service_connection_refused",
        name="Service Connection Refused",
        pattern=r"Connection refused|ECONNREFUSED|ConnectionRefusedError",
        fix_action="restart_service",
        severity=Severity.CRITICAL,
        description="Service is not accepting connections",
        cooldown_seconds=300,  # 5 min cooldown for restarts
        max_heals_per_hour=2
    ),
    
    "service_timeout": HealingPattern(
        id="service_timeout",
        name="Service Timeout",
        pattern=r"timeout|TimeoutError|timed out|ETIMEDOUT",
        fix_action="restart_service",
        severity=Severity.WARNING,
        description="Service taking too long to respond",
        cooldown_seconds=300
    ),
    
    "service_unhealthy": HealingPattern(
        id="service_unhealthy",
        name="Service Unhealthy",
        pattern=r"unhealthy|health.*fail|failed.*health",
        fix_action="restart_service",
        severity=Severity.CRITICAL,
        description="Service health check failed",
        cooldown_seconds=300
    ),
    
    # --- Memory Errors ---
    
    "memory_error": HealingPattern(
        id="memory_error",
        name="Memory Exhausted",
        pattern=r"MemoryError|Cannot allocate|Out of memory|OOM|memory.*exhaust",
        fix_action="clear_caches_restart",
        severity=Severity.CRITICAL,
        description="System ran out of memory",
        cooldown_seconds=600,
        max_heals_per_hour=2
    ),
    
    # --- Database Errors ---
    
    "database_locked": HealingPattern(
        id="database_locked",
        name="Database Locked",
        pattern=r"database.*locked|OperationalError.*locked|sqlite.*locked",
        fix_action="clear_database_locks",
        severity=Severity.WARNING,
        description="SQLite database is locked"
    ),
    
    "database_corrupted": HealingPattern(
        id="database_corrupted",
        name="Database Corrupted",
        pattern=r"database.*corrupt|malformed|disk.*image.*malformed",
        fix_action="restore_database_backup",
        severity=Severity.CRITICAL,
        description="Database file is corrupted",
        requires_approval=True
    ),
    
    # --- Import/Module Errors ---
    
    "import_error": HealingPattern(
        id="import_error",
        name="Import Error",
        pattern=r"ImportError|ModuleNotFoundError|No module named",
        fix_action="alert_human",
        severity=Severity.FATAL,
        description="Missing Python module - requires human fix",
        requires_approval=True
    ),
    
    "syntax_error": HealingPattern(
        id="syntax_error",
        name="Syntax Error",
        pattern=r"SyntaxError|invalid syntax",
        fix_action="rollback_last_change",
        severity=Severity.FATAL,
        description="Python syntax error in code",
        requires_approval=True
    ),
    
    # --- Network Errors ---
    
    "ssl_error": HealingPattern(
        id="ssl_error",
        name="SSL Certificate Error",
        pattern=r"SSLError|SSL.*certificate|certificate.*verify",
        fix_action="alert_human",
        severity=Severity.CRITICAL,
        description="SSL certificate issue",
        requires_approval=True
    ),
    
    "dns_error": HealingPattern(
        id="dns_error",
        name="DNS Resolution Error",
        pattern=r"getaddrinfo failed|Name.*resolution|DNS.*fail",
        fix_action="retry_with_backoff",
        severity=Severity.WARNING,
        description="DNS resolution failed"
    ),
}


def match_error_pattern(error_text: str) -> Optional[HealingPattern]:
    """
    Find a matching pattern for an error.
    
    Returns the first matching pattern, prioritizing by severity.
    """
    matches = []
    
    for pattern in HEALING_PATTERNS.values():
        if pattern.matches(error_text):
            matches.append(pattern)
    
    if not matches:
        return None
    
    # Sort by severity (fatal > critical > warning > info)
    severity_order = {
        Severity.FATAL: 0,
        Severity.CRITICAL: 1,
        Severity.WARNING: 2,
        Severity.INFO: 3
    }
    
    matches.sort(key=lambda p: severity_order.get(p.severity, 99))
    
    return matches[0]


def get_pattern_stats() -> Dict[str, Any]:
    """Get statistics about pattern matching."""
    stats = {
        "total_patterns": len(HEALING_PATTERNS),
        "patterns": {}
    }
    
    for pid, pattern in HEALING_PATTERNS.items():
        stats["patterns"][pid] = {
            "name": pattern.name,
            "match_count": pattern.match_count,
            "heal_success": pattern.heal_success_count,
            "heal_fail": pattern.heal_fail_count,
            "last_match": pattern.last_match.isoformat() if pattern.last_match else None,
            "last_heal": pattern.last_heal.isoformat() if pattern.last_heal else None
        }
    
    return stats


