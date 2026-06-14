# SERVICES/aria-command/knowledge/__init__.py
"""
Knowledge modules for Aria's awareness of Full Potential systems.
"""

from .legal_framework import (
    LEGAL_FRAMEWORK, 
    get_legal_context,
    get_ip_awareness_context,
    check_forbidden_language,
    get_disclaimer_for_context
)
from .money_systems import MONEY_SYSTEMS, get_money_context

def get_legal_framework_context() -> str:
    """Get combined legal and IP awareness context."""
    return get_legal_context() + "\n" + get_ip_awareness_context()

def get_money_systems_context() -> str:
    """Get money systems context."""
    return get_money_context()

__all__ = [
    "LEGAL_FRAMEWORK",
    "MONEY_SYSTEMS", 
    "get_legal_context",
    "get_money_context",
    "get_legal_framework_context",
    "get_money_systems_context",
    "get_ip_awareness_context",
    "check_forbidden_language",
    "get_disclaimer_for_context"
]

