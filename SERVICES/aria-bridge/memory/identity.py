"""
ARIA IDENTITY MEMORY
====================

Core identity memory from the Aria Constitution.

This is who Sunheart IS - rarely changes, always remembered.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .store import get_memory_store, MemoryStore

logger = logging.getLogger("aria.memory.identity")


# The core identity from the Aria Constitution
CORE_IDENTITY = {
    # Who he is
    "name": "Sunheart",
    "role": "sovereignty architect, Tide Turner, field holder",
    "gift": "holding massive complexity, seeing deep connections",
    "challenge": "singular focus is difficult (same gift)",
    "pattern": "Tide Turner - joins losing sides to shift momentum",
    "current_mission": "transition from extraction capitalism to conscious abundance",
    
    # The lesson
    "the_lesson": {
        "event": "$330K liquidated at SOL $138",
        "principle": "The fund must survive",
        "warning": "Never leverage-hunt",
        "timestamp": "historical"
    },
    
    # Constraints
    "constraints": {
        "zen_care": "$12K/month (non-negotiable)",
        "monthly_burn": "$5-12K beyond Zen",
        "liquid_assets": "~$430K (protect this)",
        "onebpo_income": "~$10K/month (stable)",
        "defi_yield": "~8-9% (don't break what works)"
    },
    
    # Values
    "values": [
        "EASINESS over effort",
        "AUTOMATION over attention",
        "COHERENCY over fragmentation",
        "CIRCULATION over extraction",
        "PROOF over promises"
    ],
    
    # Decision patterns
    "decision_patterns": {
        "uncertainty_threshold": "If uncertainty > 30%, give options not recommendations",
        "reversible": "Move fast",
        "irreversible": "Move slow",
        "format": "One-line verdict before details",
        "priority_check": "When in doubt: Does this advance T1?"
    },
    
    # T1 Focus
    "t1": "Revenue or Building Aria",
    "t2_plus": "Everything else",
    
    # The irreducible
    "irreducible": [
        "Only Sunheart can hold the field",
        "Ceremony, music, shamanic containers",
        "Group coherence, altered-state wisdom",
        "Performer transmission",
        "These cannot be automated"
    ],
    
    # Proof
    "proof": {
        "case_study": "Alice",
        "before": "$7/hour",
        "after": "50% partner earning $10K/month",
        "how": "Discernment and generosity over time",
        "proves": "Circulation economics works"
    }
}


class IdentityMemory:
    """
    Identity memory manager.
    
    Loads and manages the core identity that defines who Sunheart is.
    """
    
    def __init__(self):
        self.store = get_memory_store()
        self._ensure_identity_loaded()
        logger.info("IdentityMemory initialized")
    
    def _ensure_identity_loaded(self):
        """Make sure core identity is in the database."""
        existing = self.store.get_identity()
        
        if not existing or len(existing) < 5:
            logger.info("Loading core identity into memory...")
            self._load_core_identity()
    
    def _load_core_identity(self):
        """Load the core identity into the database."""
        for key, value in CORE_IDENTITY.items():
            self.store.set_identity(key, value, category="core")
        
        logger.info(f"Loaded {len(CORE_IDENTITY)} identity keys")
    
    def get_full_identity(self) -> Dict:
        """Get the complete identity."""
        return self.store.get_identity()
    
    def get_identity_value(self, key: str) -> Any:
        """Get a specific identity value."""
        return self.store.get_identity(key)
    
    def update_identity(self, key: str, value: Any, category: str = "dynamic"):
        """
        Update an identity value.
        
        Core values use category='core'.
        Dynamic/changing values use category='dynamic'.
        """
        self.store.set_identity(key, value, category)
        logger.info(f"Updated identity: {key}")
    
    def update_t1(self, new_t1: str):
        """Update the current T1 focus."""
        self.update_identity("t1", new_t1, category="dynamic")
        
        # Also set in context for easy access
        self.store.set_context("current_t1", new_t1)
    
    def update_constraints(self, key: str, value: str):
        """Update a constraint value."""
        constraints = self.get_identity_value("constraints") or {}
        constraints[key] = value
        self.update_identity("constraints", constraints, category="core")
    
    def get_formatted_identity(self) -> str:
        """Get identity formatted for prompt injection."""
        identity = self.get_full_identity()
        
        lines = [
            "═══════════════════════════════════════════════════════════════",
            "SUNHEART IDENTITY (What Aria Remembers)",
            "═══════════════════════════════════════════════════════════════",
            "",
            f"**WHO:** {identity.get('name', 'Sunheart')} - {identity.get('role', '')}",
            f"**GIFT:** {identity.get('gift', '')}",
            f"**CHALLENGE:** {identity.get('challenge', '')}",
            f"**PATTERN:** {identity.get('pattern', '')}",
            "",
            "**THE LESSON:**",
        ]
        
        lesson = identity.get("the_lesson", {})
        if isinstance(lesson, dict):
            lines.append(f"  {lesson.get('event', '')}")
            lines.append(f"  Principle: {lesson.get('principle', '')}")
            lines.append(f"  Warning: {lesson.get('warning', '')}")
        
        lines.append("")
        lines.append("**CONSTRAINTS:**")
        constraints = identity.get("constraints", {})
        if isinstance(constraints, dict):
            for k, v in constraints.items():
                lines.append(f"  • {k}: {v}")
        
        lines.append("")
        lines.append("**VALUES:**")
        values = identity.get("values", [])
        if isinstance(values, list):
            for v in values:
                lines.append(f"  • {v}")
        
        lines.append("")
        lines.append(f"**T1:** {identity.get('t1', 'Revenue or Building Aria')}")
        lines.append(f"**Everything else is T2+**")
        
        lines.append("")
        lines.append("**DECISION PATTERNS:**")
        patterns = identity.get("decision_patterns", {})
        if isinstance(patterns, dict):
            for k, v in patterns.items():
                lines.append(f"  • {v}")
        
        return "\n".join(lines)
    
    def get_quick_identity(self) -> str:
        """Get a shorter identity summary."""
        identity = self.get_full_identity()
        
        return f"""You serve {identity.get('name', 'Sunheart')} - {identity.get('role', '')}.
His gift: {identity.get('gift', '')}
His challenge: {identity.get('challenge', '')}
The lesson: {identity.get('the_lesson', {}).get('principle', 'The fund must survive')}
T1 = {identity.get('t1', 'Revenue or Building Aria')}. Everything else is T2+."""


class ContextMemory:
    """
    Current context/state memory.
    
    Things that change daily/weekly.
    """
    
    def __init__(self):
        self.store = get_memory_store()
        logger.info("ContextMemory initialized")
    
    def set(self, key: str, value: Any, expires_hours: int = None):
        """Set a context value."""
        self.store.set_context(key, value, expires_hours)
    
    def get(self, key: str = None) -> Any:
        """Get context value(s)."""
        return self.store.get_context(key)
    
    def set_current_project(self, project: str):
        """Set current project focus."""
        self.set("current_project", project)
    
    def set_active_visions(self, vision_ids: list):
        """Set active vision IDs."""
        self.set("active_visions", vision_ids)
    
    def set_treasury_state(self, state: Dict):
        """Set treasury state summary."""
        self.set("treasury_state", state, expires_hours=24)
    
    def get_formatted_context(self) -> str:
        """Get formatted current context."""
        context = self.get()
        
        if not context:
            return "No active context set."
        
        lines = ["CURRENT CONTEXT:"]
        for key, value in context.items():
            if isinstance(value, list):
                lines.append(f"• {key}: {', '.join(str(v) for v in value[:5])}")
            elif isinstance(value, dict):
                lines.append(f"• {key}: {list(value.keys())}")
            else:
                lines.append(f"• {key}: {value}")
        
        return "\n".join(lines)


# Singletons
_identity: Optional[IdentityMemory] = None
_context: Optional[ContextMemory] = None


def get_identity_memory() -> IdentityMemory:
    """Get or create identity memory instance."""
    global _identity
    if _identity is None:
        _identity = IdentityMemory()
    return _identity


def get_context_memory() -> ContextMemory:
    """Get or create context memory instance."""
    global _context
    if _context is None:
        _context = ContextMemory()
    return _context


