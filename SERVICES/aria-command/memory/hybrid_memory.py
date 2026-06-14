"""
ARIA HYBRID MEMORY SYSTEM
==========================

Combines cloud (Mem0) and local (SQLite) memory for maximum reliability.

Strategy:
1. ALWAYS store to local first (fast, reliable)
2. SYNC to Mem0 in background (cloud backup)
3. SEARCH both, merge results (best of both)
4. If Mem0 down, local works fine
5. If local corrupted, Mem0 has backup

This is the REDUNDANT memory James asked for.
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

from .local_store import (
    LocalMemoryStore, 
    LocalMemory, 
    MemoryType, 
    SyncStatus,
    get_local_store
)
from .mem0_client import (
    Mem0Client,
    MemoryResult,
    MemoryCategory,
    get_mem0_client
)

logger = logging.getLogger("aria.memory.hybrid")


@dataclass
class HybridMemory:
    """A memory from the hybrid system."""
    id: str
    content: str
    source: str  # "local", "cloud", "both"
    importance: float
    memory_type: str
    created_at: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "importance": self.importance,
            "memory_type": self.memory_type,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


class HybridMemorySystem:
    """
    Redundant memory system with local + cloud.
    
    Provides:
    - store: Saves to both local and cloud
    - search: Searches both, merges results
    - sync: Background sync of pending memories
    - status: Health of both systems
    """
    
    def __init__(self):
        self.local = get_local_store()
        self.cloud = get_mem0_client()
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("🔄 Hybrid memory system initialized")
    
    async def store(
        self,
        content: str,
        memory_type: str = "learning",
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> HybridMemory:
        """
        Store a memory to BOTH local and cloud.
        
        Local store is synchronous (fast, guaranteed).
        Cloud store is async (may fail, will retry).
        
        Args:
            content: The memory to store
            memory_type: learning, pattern, fact, episode, preference, identity
            importance: 0-1 importance score
            metadata: Optional additional data
        
        Returns:
            HybridMemory representing the stored item
        """
        # Map string type to enum
        type_map = {
            "learning": MemoryType.LEARNING,
            "pattern": MemoryType.LEARNING,
            "fact": MemoryType.FACT,
            "episode": MemoryType.EPISODE,
            "preference": MemoryType.PREFERENCE,
            "identity": MemoryType.IDENTITY,
            "correction": MemoryType.CORRECTION,
            "decision": MemoryType.LEARNING,
            "context": MemoryType.EPISODE,
            "conversation": MemoryType.EPISODE
        }
        local_type = type_map.get(memory_type.lower(), MemoryType.LEARNING)
        
        # 1. Store to LOCAL first (guaranteed to work)
        local_mem = self.local.store(
            content=content,
            memory_type=local_type,
            importance=importance,
            metadata=metadata or {}
        )
        
        # 2. Try to store to CLOUD (best effort, async)
        cloud_success = False
        mem0_id = None
        
        if self.cloud.enabled:
            try:
                result = await self.cloud.store(
                    content=content,
                    category=memory_type,
                    importance="high" if importance > 0.7 else "medium" if importance > 0.3 else "low",
                    metadata={
                        "local_id": local_mem.id,
                        **(metadata or {})
                    }
                )
                
                if result.success:
                    cloud_success = True
                    # Handle Mem0 API returning list or dict
                    mem0_id = None
                    if result.data:
                        response = result.data.get("response")
                        if isinstance(response, list) and response:
                            # New API returns list
                            mem0_id = response[0].get("event_id") or response[0].get("id")
                        elif isinstance(response, dict):
                            # Old API returned dict
                            mem0_id = response.get("id")
                    self.local.mark_synced(local_mem.id, mem0_id)
                    logger.debug(f"☁️ Cloud sync successful for {local_mem.id}")
            except Exception as e:
                logger.warning(f"Cloud store failed (will retry): {e}")
        
        return HybridMemory(
            id=local_mem.id,
            content=content,
            source="both" if cloud_success else "local",
            importance=importance,
            memory_type=memory_type,
            created_at=local_mem.created_at,
            metadata=metadata or {}
        )
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0
    ) -> List[HybridMemory]:
        """
        Search BOTH local and cloud, merge results.
        
        Args:
            query: Search query
            limit: Max results
            memory_type: Optional type filter
            min_importance: Minimum importance threshold
        
        Returns:
            List of HybridMemory objects, deduplicated and ranked
        """
        results: Dict[str, HybridMemory] = {}
        
        # Map string type to enum for local search
        local_type = None
        if memory_type:
            type_map = {
                "learning": MemoryType.LEARNING,
                "fact": MemoryType.FACT,
                "episode": MemoryType.EPISODE,
                "preference": MemoryType.PREFERENCE,
                "identity": MemoryType.IDENTITY,
                "correction": MemoryType.CORRECTION
            }
            local_type = type_map.get(memory_type.lower())
        
        # 1. Search LOCAL (always works)
        try:
            local_results = self.local.search(
                query=query,
                limit=limit * 2,  # Get extra for dedup
                memory_type=local_type,
                min_importance=min_importance
            )
            
            for mem in local_results:
                results[mem.content[:100]] = HybridMemory(
                    id=mem.id,
                    content=mem.content,
                    source="local",
                    importance=mem.effective_importance(),
                    memory_type=mem.memory_type.value,
                    created_at=mem.created_at,
                    metadata=mem.metadata
                )
        except Exception as e:
            logger.warning(f"Local search failed: {e}")
        
        # 2. Search CLOUD (best effort)
        if self.cloud.enabled:
            try:
                cloud_result = await self.cloud.search(
                    query=query,
                    limit=limit * 2
                )
                
                if cloud_result.memories:
                    for mem in cloud_result.memories:
                        content = mem.get("memory", mem.get("text", ""))
                        if not content:
                            continue
                        
                        key = content[:100]
                        
                        if key in results:
                            # Mark as in both systems
                            results[key].source = "both"
                            # Boost importance if in both
                            results[key].importance = min(1.0, results[key].importance + 0.1)
                        else:
                            # Cloud-only memory
                            results[key] = HybridMemory(
                                id=mem.get("id", key[:16]),
                                content=content,
                                source="cloud",
                                importance=mem.get("score", 0.5),
                                memory_type=mem.get("metadata", {}).get("category", "learning"),
                                created_at=datetime.now(timezone.utc),
                                metadata=mem.get("metadata", {})
                            )
            except Exception as e:
                logger.warning(f"Cloud search failed: {e}")
        
        # 3. Sort by importance and return top N
        sorted_results = sorted(
            results.values(),
            key=lambda m: m.importance,
            reverse=True
        )
        
        return sorted_results[:limit]
    
    async def get_context_for_prompt(
        self,
        user_message: str,
        limit: int = 3
    ) -> str:
        """
        Get formatted memories to inject into system prompt.
        
        This is called before each response.
        """
        memories = await self.search(user_message, limit=limit, min_importance=0.3)
        
        if not memories:
            return ""
        
        lines = ["\n## 🧠 Relevant Past Knowledge\n"]
        
        for mem in memories:
            source_icon = "☁️" if mem.source == "cloud" else "💾" if mem.source == "local" else "🔄"
            type_label = mem.memory_type.title()
            lines.append(f"**{type_label}** {source_icon}: {mem.content[:200]}")
        
        lines.append("\n---\n")
        
        return "\n".join(lines)
    
    async def sync_pending(self) -> Dict[str, Any]:
        """
        Sync pending local memories to cloud.
        
        This should be called periodically.
        """
        if not self.cloud.enabled:
            return {"synced": 0, "failed": 0, "reason": "cloud disabled"}
        
        pending = self.local.get_pending_sync(limit=20)
        synced = 0
        failed = 0
        
        for memory_id, action in pending:
            if action == "store":
                mem = self.local.get_by_id(memory_id)
                if not mem:
                    continue
                
                try:
                    result = await self.cloud.store(
                        content=mem.content,
                        category=mem.memory_type.value,
                        importance="high" if mem.importance > 0.7 else "medium",
                        metadata={"local_id": memory_id, **mem.metadata}
                    )
                    
                    if result.success:
                        mem0_id = result.data.get("response", {}).get("id") if result.data else None
                        self.local.mark_synced(memory_id, mem0_id)
                        synced += 1
                    else:
                        self.local.mark_sync_failed(memory_id, result.message)
                        failed += 1
                        
                except Exception as e:
                    self.local.mark_sync_failed(memory_id, str(e))
                    failed += 1
            
            elif action == "delete":
                # TODO: Implement cloud deletion
                self.local.mark_synced(memory_id, None)
                synced += 1
        
        if synced > 0 or failed > 0:
            logger.info(f"🔄 Sync complete: {synced} synced, {failed} failed")
        
        return {"synced": synced, "failed": failed}
    
    async def start_background_sync(self, interval: int = 60):
        """Start background sync loop."""
        self._running = True
        
        while self._running:
            try:
                await self.sync_pending()
            except Exception as e:
                logger.error(f"Background sync error: {e}")
            
            await asyncio.sleep(interval)
    
    def stop_background_sync(self):
        """Stop background sync."""
        self._running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get hybrid memory system status."""
        local_stats = self.local.get_stats()
        
        return {
            "local": {
                "available": True,
                **local_stats
            },
            "cloud": {
                "available": self.cloud.enabled,
                "configured": bool(self.cloud.api_key)
            },
            "pending_sync": local_stats.get("pending_sync", 0),
            "redundancy": "full" if self.cloud.enabled else "local_only"
        }
    
    async def apply_decay(self):
        """Apply memory decay (should be called daily)."""
        self.local.apply_decay()


# ============================================================================
# SINGLETON
# ============================================================================

_hybrid: Optional[HybridMemorySystem] = None


def get_hybrid_memory() -> HybridMemorySystem:
    """Get or create hybrid memory system."""
    global _hybrid
    if _hybrid is None:
        _hybrid = HybridMemorySystem()
    return _hybrid


# ============================================================================
# CONVENIENCE FUNCTIONS (Drop-in replacements for mem0_client functions)
# ============================================================================

async def store_memory(
    content: str,
    category: str = "learning",
    importance: str = "medium",
    metadata: Optional[Dict] = None
) -> MemoryResult:
    """Store a memory (hybrid)."""
    hybrid = get_hybrid_memory()
    
    # Convert importance string to float
    importance_map = {"low": 0.3, "medium": 0.5, "high": 0.7, "critical": 0.9}
    importance_float = importance_map.get(importance.lower(), 0.5)
    
    result = await hybrid.store(
        content=content,
        memory_type=category,
        importance=importance_float,
        metadata=metadata
    )
    
    return MemoryResult(
        success=True,
        message=f"Stored to {result.source}",
        data=result.to_dict()
    )


async def recall_memories(
    query: str,
    limit: int = 5
) -> List[Dict]:
    """Search memories (hybrid)."""
    hybrid = get_hybrid_memory()
    results = await hybrid.search(query, limit)
    return [m.to_dict() for m in results]


async def inject_relevant_memories(
    user_message: str,
    limit: int = 3
) -> str:
    """Get formatted memories for prompt injection (hybrid)."""
    hybrid = get_hybrid_memory()
    return await hybrid.get_context_for_prompt(user_message, limit)

