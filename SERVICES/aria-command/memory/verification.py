"""
ARIA MEMORY VERIFICATION
=========================

Checks if memories are still valid.

Problems with unverified memory:
- "James prefers X" but he changed his mind
- "Service runs on port 8080" but config changed
- "The fix is to restart" but we found a better way

This module:
1. Tracks memory age and staleness
2. Marks memories as "needs verification"
3. Detects contradictions
4. Updates or deprecates outdated info
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from .local_store import get_local_store, LocalMemory, MemoryType

logger = logging.getLogger("aria.memory.verification")


class VerificationStatus(str, Enum):
    """Status of memory verification."""
    VERIFIED = "verified"       # Recently confirmed
    STALE = "stale"            # Old, needs checking
    CONTRADICTED = "contradicted"  # Conflicting info found
    DEPRECATED = "deprecated"   # Explicitly outdated


@dataclass
class VerificationResult:
    """Result of a memory verification."""
    memory_id: str
    status: VerificationStatus
    reason: str
    suggested_action: str  # update, delete, keep, verify
    
    def to_dict(self) -> Dict:
        return {
            "memory_id": self.memory_id,
            "status": self.status.value,
            "reason": self.reason,
            "suggested_action": self.suggested_action
        }


class MemoryVerifier:
    """
    Verifies and maintains memory accuracy.
    
    Features:
    - Age-based staleness detection
    - Contradiction detection
    - Verification prompts
    - Auto-deprecation
    """
    
    # Days before different memory types become stale
    STALENESS_THRESHOLDS = {
        MemoryType.FACT: 30,        # Facts should be stable
        MemoryType.LEARNING: 14,    # Learnings may evolve
        MemoryType.PREFERENCE: 7,   # Preferences change
        MemoryType.EPISODE: 60,     # Episodes are historical
        MemoryType.CORRECTION: 7,   # Corrections may be superseded
        MemoryType.IDENTITY: 90,    # Identity is stable
    }
    
    # Keywords that suggest contradiction
    CONTRADICTION_MARKERS = [
        ("no longer", "anymore"),
        ("actually", "not"),
        ("wrong", "incorrect"),
        ("changed", "updated"),
        ("instead", "rather"),
        ("new", "old"),
    ]
    
    def __init__(self):
        self.local_store = get_local_store()
        logger.info("🔍 Memory verifier initialized")
    
    def check_staleness(self, memory: LocalMemory) -> Optional[VerificationResult]:
        """
        Check if a memory is stale based on age.
        """
        threshold_days = self.STALENESS_THRESHOLDS.get(memory.memory_type, 14)
        threshold = timedelta(days=threshold_days)
        
        age = datetime.now(timezone.utc) - memory.created_at
        
        if age > threshold:
            decay_penalty = (age.days - threshold_days) * 0.01
            
            return VerificationResult(
                memory_id=memory.id,
                status=VerificationStatus.STALE,
                reason=f"Memory is {age.days} days old (threshold: {threshold_days})",
                suggested_action="verify" if memory.importance > 0.5 else "deprecate"
            )
        
        return None
    
    def check_contradiction(
        self,
        new_content: str,
        existing_memory: LocalMemory
    ) -> Optional[VerificationResult]:
        """
        Check if new content contradicts an existing memory.
        """
        new_lower = new_content.lower()
        existing_lower = existing_memory.content.lower()
        
        # Check for explicit contradiction markers
        for positive, negative in self.CONTRADICTION_MARKERS:
            if positive in new_lower and any(
                word in existing_lower for word in existing_lower.split()
            ):
                return VerificationResult(
                    memory_id=existing_memory.id,
                    status=VerificationStatus.CONTRADICTED,
                    reason=f"New info contains '{positive}' which may contradict existing memory",
                    suggested_action="update"
                )
        
        # Check for opposite sentiments
        negatives = ["not", "don't", "doesn't", "never", "stop"]
        for neg in negatives:
            if neg in new_lower and neg not in existing_lower:
                # Check if they're about the same thing
                new_words = set(new_lower.split())
                existing_words = set(existing_lower.split())
                overlap = new_words & existing_words
                
                if len(overlap) > 3:  # Significant overlap
                    return VerificationResult(
                        memory_id=existing_memory.id,
                        status=VerificationStatus.CONTRADICTED,
                        reason=f"Possible negation of existing memory",
                        suggested_action="verify"
                    )
        
        return None
    
    async def verify_before_store(self, new_content: str) -> List[VerificationResult]:
        """
        Check new content against existing memories for contradictions.
        
        Returns list of memories that may be contradicted.
        """
        results = []
        
        # Get potentially related memories
        existing = self.local_store.search(new_content, limit=10)
        
        for memory in existing:
            result = self.check_contradiction(new_content, memory)
            if result:
                results.append(result)
        
        return results
    
    def get_stale_memories(self, limit: int = 20) -> List[LocalMemory]:
        """
        Get memories that need verification.
        """
        stale = []
        
        # Get all memories
        memories = self.local_store.get_important(limit=100)
        
        for memory in memories:
            result = self.check_staleness(memory)
            if result:
                stale.append(memory)
                
                if len(stale) >= limit:
                    break
        
        return stale
    
    def mark_verified(self, memory_id: str):
        """
        Mark a memory as recently verified.
        
        This resets the staleness timer.
        """
        memory = self.local_store.get_by_id(memory_id)
        if memory:
            # Re-store with updated timestamp and boosted importance
            self.local_store.store(
                content=memory.content,
                memory_type=memory.memory_type,
                importance=min(1.0, memory.importance + 0.1),
                metadata={**memory.metadata, "verified_at": datetime.now(timezone.utc).isoformat()}
            )
    
    def deprecate(self, memory_id: str, reason: str):
        """
        Mark a memory as deprecated.
        """
        memory = self.local_store.get_by_id(memory_id)
        if memory:
            # Lower importance significantly
            self.local_store.update_importance(memory_id, memory.importance * 0.3)
    
    def get_verification_prompt(self, stale_memories: List[LocalMemory]) -> str:
        """
        Generate a prompt asking for verification of stale memories.
        """
        if not stale_memories:
            return ""
        
        lines = ["\n## 🔍 Memories Needing Verification\n"]
        lines.append("*These older memories may need updating:*\n")
        
        for mem in stale_memories[:3]:
            age = (datetime.now(timezone.utc) - mem.created_at).days
            lines.append(f"- ({age}d old) {mem.content[:100]}...")
        
        lines.append("\n*If any are outdated, please let me know.*\n---\n")
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        all_memories = self.local_store.get_important(limit=100)
        
        stale_count = 0
        verified_count = 0
        total = len(all_memories)
        
        for mem in all_memories:
            if self.check_staleness(mem):
                stale_count += 1
            elif mem.metadata.get("verified_at"):
                verified_count += 1
        
        return {
            "total_checked": total,
            "stale": stale_count,
            "verified": verified_count,
            "unverified": total - stale_count - verified_count,
            "staleness_rate": round(stale_count / max(1, total), 2)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_verifier: Optional[MemoryVerifier] = None


def get_memory_verifier() -> MemoryVerifier:
    """Get or create memory verifier instance."""
    global _verifier
    if _verifier is None:
        _verifier = MemoryVerifier()
    return _verifier









