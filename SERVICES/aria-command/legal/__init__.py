# SERVICES/aria-command/legal/__init__.py
"""
Legal modules for Aria's jurisdiction optimization and legal awareness.
"""

from .jurisdiction_optimizer import (
    JurisdictionOptimizer,
    JurisdictionPurpose,
    JurisdictionProfile,
    JurisdictionRecommendation,
    get_jurisdiction_optimizer,
    JURISDICTIONS
)

__all__ = [
    "JurisdictionOptimizer",
    "JurisdictionPurpose", 
    "JurisdictionProfile",
    "JurisdictionRecommendation",
    "get_jurisdiction_optimizer",
    "JURISDICTIONS"
]









