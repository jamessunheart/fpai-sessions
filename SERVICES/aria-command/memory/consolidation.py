"""
ARIA MEMORY CONSOLIDATION
==========================

Like sleep for the brain - consolidates memories.

What happens during consolidation:
1. Working memory → Long-term (important items promoted)
2. Episodic → Semantic (patterns extracted from stories)
3. Decay applied (old unused memories fade)
4. Cloud sync (local → Mem0)
5. Cleanup (old episodes summarized)

This should run periodically (every few hours or daily).
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from .local_store import get_local_store, MemoryType
from .hybrid_memory import get_hybrid_memory
from .working_memory import get_working_memory, WorkingItemType
from .episodic_memory import get_episodic_memory, Outcome

logger = logging.getLogger("aria.memory.consolidation")

# Configuration
CONSOLIDATION_INTERVAL = int(os.getenv("CONSOLIDATION_INTERVAL", "14400"))  # 4 hours
EPISODE_RETENTION_DAYS = int(os.getenv("EPISODE_RETENTION_DAYS", "30"))


@dataclass
class ConsolidationReport:
    """Report from a consolidation cycle."""
    timestamp: datetime
    duration_ms: float
    working_promoted: int
    episodes_summarized: int
    decay_applied: int
    synced_to_cloud: int
    errors: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "working_promoted": self.working_promoted,
            "episodes_summarized": self.episodes_summarized,
            "decay_applied": self.decay_applied,
            "synced_to_cloud": self.synced_to_cloud,
            "errors": self.errors,
            "success": len(self.errors) == 0
        }


class MemoryConsolidator:
    """
    Consolidates memories across all layers.
    
    Like sleep for the brain - essential for long-term memory formation.
    """
    
    def __init__(self):
        self._last_consolidation: Optional[datetime] = None
        self._consolidation_count = 0
        self._running = False
        
        logger.info("💤 Memory consolidator initialized")
    
    async def consolidate(self) -> ConsolidationReport:
        """
        Run a full memory consolidation cycle.
        
        Returns a report of what was consolidated.
        """
        start_time = datetime.now(timezone.utc)
        errors = []
        
        working_promoted = 0
        episodes_summarized = 0
        decay_applied = 0
        synced = 0
        
        logger.info("💤 Starting memory consolidation...")
        
        # 1. PROMOTE WORKING MEMORY
        try:
            working_promoted = await self._promote_working_memory()
        except Exception as e:
            errors.append(f"Working memory promotion failed: {e}")
            logger.error(f"Working memory promotion failed: {e}")
        
        # 2. EXTRACT PATTERNS FROM EPISODES
        try:
            episodes_summarized = await self._extract_episode_patterns()
        except Exception as e:
            errors.append(f"Episode pattern extraction failed: {e}")
            logger.error(f"Episode pattern extraction failed: {e}")
        
        # 3. APPLY DECAY
        try:
            decay_applied = await self._apply_decay()
        except Exception as e:
            errors.append(f"Decay application failed: {e}")
            logger.error(f"Decay application failed: {e}")
        
        # 4. SYNC TO CLOUD
        try:
            hybrid = get_hybrid_memory()
            sync_result = await hybrid.sync_pending()
            synced = sync_result.get("synced", 0)
        except Exception as e:
            errors.append(f"Cloud sync failed: {e}")
            logger.error(f"Cloud sync failed: {e}")
        
        # 5. CLEANUP OLD EPISODES
        try:
            await self._cleanup_old_episodes()
        except Exception as e:
            errors.append(f"Episode cleanup failed: {e}")
            logger.error(f"Episode cleanup failed: {e}")
        
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        self._last_consolidation = start_time
        self._consolidation_count += 1
        
        report = ConsolidationReport(
            timestamp=start_time,
            duration_ms=duration_ms,
            working_promoted=working_promoted,
            episodes_summarized=episodes_summarized,
            decay_applied=decay_applied,
            synced_to_cloud=synced,
            errors=errors
        )
        
        if errors:
            logger.warning(f"💤 Consolidation completed with {len(errors)} errors")
        else:
            logger.info(f"💤 Consolidation complete: {working_promoted} promoted, {synced} synced, {decay_applied} decayed")
        
        return report
    
    async def _promote_working_memory(self) -> int:
        """
        Promote important working memory items to long-term storage.
        """
        working = get_working_memory()
        hybrid = get_hybrid_memory()
        
        promoted_count = 0
        
        # Get all working memory items
        items = working.get_all()
        
        for item in items:
            # Promote if:
            # - High priority (decisions, errors, important context)
            # - Accessed multiple times
            # - Is a decision or error
            should_promote = (
                item.priority >= 0.7 or
                item.access_count >= 3 or
                item.item_type in [WorkingItemType.DECISION, WorkingItemType.ERROR, WorkingItemType.GOAL]
            )
            
            if should_promote:
                # Store to long-term
                memory_type = {
                    WorkingItemType.GOAL: "learning",
                    WorkingItemType.DECISION: "decision",
                    WorkingItemType.ERROR: "correction",
                    WorkingItemType.FILE: "context",
                    WorkingItemType.TOOL_RESULT: "context",
                    WorkingItemType.CONTEXT: "context",
                    WorkingItemType.USER_INPUT: "preference"
                }.get(item.item_type, "learning")
                
                await hybrid.store(
                    content=item.content,
                    memory_type=memory_type,
                    importance=item.priority,
                    metadata={
                        "promoted_from": "working_memory",
                        "original_type": item.item_type.value,
                        "access_count": item.access_count
                    }
                )
                
                promoted_count += 1
                logger.debug(f"Promoted: {item.content[:50]}...")
        
        return promoted_count
    
    async def _extract_episode_patterns(self) -> int:
        """
        Extract patterns from recent episodes and store as learnings.
        """
        episodic = get_episodic_memory()
        hybrid = get_hybrid_memory()
        
        patterns_extracted = 0
        
        # Get episodes from the last week
        since = datetime.now(timezone.utc) - timedelta(days=7)
        episodes = episodic.search(since=since, limit=20)
        
        # Group by topic to find patterns
        topic_episodes: Dict[str, List] = {}
        for ep in episodes:
            for topic in ep.topics:
                if topic not in topic_episodes:
                    topic_episodes[topic] = []
                topic_episodes[topic].append(ep)
        
        # Extract patterns from topics that appear multiple times
        for topic, eps in topic_episodes.items():
            if len(eps) >= 2:
                # Create a pattern memory
                outcomes = [ep.outcome.value for ep in eps]
                success_rate = outcomes.count("success") / len(outcomes)
                
                lessons = []
                for ep in eps:
                    lessons.extend(ep.lessons_learned)
                
                if lessons:
                    pattern_content = f"When working on '{topic}': {'; '.join(set(lessons[:3]))}. Success rate: {success_rate:.0%}"
                    
                    await hybrid.store(
                        content=pattern_content,
                        memory_type="pattern",
                        importance=0.6 + (success_rate * 0.3),
                        metadata={
                            "topic": topic,
                            "episode_count": len(eps),
                            "success_rate": success_rate
                        }
                    )
                    
                    patterns_extracted += 1
        
        return patterns_extracted
    
    async def _apply_decay(self) -> int:
        """
        Apply decay to old, unused memories.
        """
        local_store = get_local_store()
        local_store.apply_decay(decay_rate=0.01)  # 1% decay
        
        # Count decayed items
        stats = local_store.get_stats()
        return stats.get("total_memories", 0)  # Approximate
    
    async def _cleanup_old_episodes(self):
        """
        Summarize and archive old episodes.
        """
        episodic = get_episodic_memory()
        hybrid = get_hybrid_memory()
        
        # Get old episodes
        cutoff = datetime.now(timezone.utc) - timedelta(days=EPISODE_RETENTION_DAYS)
        old_episodes = episodic.search(limit=100)  # Get all
        
        for ep in old_episodes:
            if ep.started_at < cutoff and ep.importance < 0.7:
                # Create a summary memory before deletion
                summary = f"Episode '{ep.title}': {ep.summary}"
                if ep.lessons_learned:
                    summary += f" Learned: {'; '.join(ep.lessons_learned)}"
                
                await hybrid.store(
                    content=summary,
                    memory_type="episode",
                    importance=ep.importance,
                    metadata={
                        "original_episode_id": ep.id,
                        "episode_type": ep.episode_type.value,
                        "outcome": ep.outcome.value
                    }
                )
                
                # Note: We don't delete the episode here - just archive to long-term
                # A separate cleanup job could delete very old episodes
    
    async def run_scheduled(self):
        """Run consolidation on a schedule."""
        self._running = True
        
        logger.info(f"💤 Consolidation scheduler started (interval: {CONSOLIDATION_INTERVAL}s)")
        
        while self._running:
            try:
                await self.consolidate()
            except Exception as e:
                logger.error(f"Scheduled consolidation failed: {e}")
            
            await asyncio.sleep(CONSOLIDATION_INTERVAL)
    
    def stop(self):
        """Stop scheduled consolidation."""
        self._running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get consolidator status."""
        return {
            "last_consolidation": self._last_consolidation.isoformat() if self._last_consolidation else None,
            "consolidation_count": self._consolidation_count,
            "interval_seconds": CONSOLIDATION_INTERVAL,
            "running": self._running,
            "next_consolidation": (
                (self._last_consolidation + timedelta(seconds=CONSOLIDATION_INTERVAL)).isoformat()
                if self._last_consolidation else "pending"
            )
        }


# ============================================================================
# SINGLETON
# ============================================================================

_consolidator: Optional[MemoryConsolidator] = None


def get_consolidator() -> MemoryConsolidator:
    """Get or create memory consolidator."""
    global _consolidator
    if _consolidator is None:
        _consolidator = MemoryConsolidator()
    return _consolidator


async def run_consolidation() -> ConsolidationReport:
    """Run a consolidation cycle."""
    return await get_consolidator().consolidate()









