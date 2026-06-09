"""
ARIA MEMORY - MEM0 CLOUD SYNC
=============================

Syncs important memories to Mem0 for cloud-based persistence.

Architecture:
- Local SQLite: Fast reads/writes, instant access
- Mem0 Cloud: Long-term persistence, cross-system access

Only HIGH and CRITICAL importance memories are synced to save costs.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import httpx
import asyncio

from .store import Memory, MemoryCategory, MemoryImportance, get_memory_store

logger = logging.getLogger("aria.memory.mem0")

# Mem0 Configuration
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo")
MEM0_BASE_URL = "https://api.mem0.ai/v1"

# Entity IDs for Aria in Mem0
ARIA_IDENTITY = "aria_identity"        # Who Sunheart is
ARIA_LEARNINGS = "aria_learnings"      # What Aria has learned
ARIA_PATTERNS = "aria_patterns"        # Detected patterns
ARIA_CONVERSATIONS = "aria_conversations"  # Important conversations


class Mem0Sync:
    """
    Syncs Aria's memories to Mem0 cloud.
    
    Only syncs important memories to save API costs.
    """
    
    def __init__(self):
        self.api_key = MEM0_API_KEY
        self.enabled = bool(self.api_key) and self.api_key != "m0-your-api-key-here"
        self.store = get_memory_store()
        
        if self.enabled:
            self.headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }
            logger.info("🧠 Mem0 cloud sync enabled")
        else:
            self.headers = {}
            logger.warning("⚠️ Mem0 not configured - cloud sync disabled")
    
    async def _post(self, endpoint: str, data: Dict) -> Optional[Dict]:
        """Make POST request to Mem0 API."""
        if not self.enabled:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                url = f"{MEM0_BASE_URL}/{endpoint}"
                if not url.endswith('/'):
                    url += '/'
                
                resp = await client.post(url, headers=self.headers, json=data)
                
                if resp.status_code == 200:
                    return resp.json()
                else:
                    logger.error(f"Mem0 API error: {resp.status_code} - {resp.text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"Mem0 request failed: {e}")
            return None
    
    async def _search(self, query: str, user_id: str, limit: int = 10) -> List[Dict]:
        """Search Mem0 memories."""
        if not self.enabled:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.post(
                    f"{MEM0_BASE_URL}/memories/search/",
                    headers=self.headers,
                    json={"query": query, "user_id": user_id, "limit": limit}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
                    return data.get("results", data.get("memories", []))
                return []
        except Exception as e:
            logger.error(f"Mem0 search failed: {e}")
            return []
    
    # ==================== SYNC OPERATIONS ====================
    
    async def sync_memory(self, memory: Memory) -> bool:
        """
        Sync a single memory to Mem0 if it's important enough.
        
        Only syncs HIGH and CRITICAL importance.
        """
        if not self.enabled:
            return False
        
        # Only sync important memories
        if memory.importance not in [MemoryImportance.HIGH, MemoryImportance.CRITICAL]:
            return False
        
        # Determine user_id based on category
        user_id = {
            MemoryCategory.IDENTITY: ARIA_IDENTITY,
            MemoryCategory.LEARNING: ARIA_LEARNINGS,
            MemoryCategory.PATTERN: ARIA_PATTERNS,
            MemoryCategory.CONVERSATION: ARIA_CONVERSATIONS,
            MemoryCategory.DECISION: ARIA_LEARNINGS,
            MemoryCategory.PREFERENCE: ARIA_LEARNINGS,
        }.get(memory.category, ARIA_LEARNINGS)
        
        # Format the message for Mem0
        message = self._format_for_mem0(memory)
        
        result = await self._post("memories", {
            "messages": [{"role": "user", "content": message}],
            "user_id": user_id,
            "metadata": {
                "aria_memory_id": memory.id,
                "category": memory.category.value,
                "importance": memory.importance.value,
                "synced_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        if result:
            logger.info(f"☁️ Synced to Mem0: {memory.id[:20]}...")
            return True
        return False
    
    async def sync_identity(self, identity: Dict) -> bool:
        """Sync identity to Mem0."""
        if not self.enabled:
            return False
        
        # Format identity as a message
        message = f"""SUNHEART IDENTITY:
Name: {identity.get('name', 'Sunheart')}
Role: {identity.get('role', '')}
Gift: {identity.get('gift', '')}
Challenge: {identity.get('challenge', '')}
Pattern: {identity.get('pattern', '')}
Core Values: {', '.join(identity.get('values', []))}
T1 Focus: {identity.get('t1', 'Revenue or Building Aria')}
The Lesson: {identity.get('the_lesson', {}).get('principle', 'The fund must survive')}
"""
        
        result = await self._post("memories", {
            "messages": [{"role": "user", "content": message}],
            "user_id": ARIA_IDENTITY,
            "metadata": {
                "type": "core_identity",
                "synced_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        return bool(result)
    
    async def sync_learning(
        self,
        action: str,
        outcome: str,
        insight: str
    ) -> bool:
        """Sync a learning to Mem0."""
        if not self.enabled:
            return False
        
        message = f"{insight}. Action: {action}. Outcome: {outcome}."
        
        result = await self._post("memories", {
            "messages": [{"role": "user", "content": message}],
            "user_id": ARIA_LEARNINGS,
            "metadata": {
                "type": "learning",
                "synced_at": datetime.now(timezone.utc).isoformat()
            }
        })
        
        return bool(result)
    
    # ==================== RECALL FROM CLOUD ====================
    
    async def search_cloud(self, query: str, limit: int = 10) -> List[Dict]:
        """Search all Aria memories in Mem0."""
        if not self.enabled:
            return []
        
        # Search across all entity types
        results = []
        for user_id in [ARIA_IDENTITY, ARIA_LEARNINGS, ARIA_PATTERNS, ARIA_CONVERSATIONS]:
            memories = await self._search(query, user_id, limit=limit)
            for mem in memories:
                mem["aria_entity"] = user_id
            results.extend(memories)
        
        # Sort by score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]
    
    async def get_identity_from_cloud(self) -> List[Dict]:
        """Get identity memories from Mem0."""
        return await self._search("identity values pattern", ARIA_IDENTITY, limit=10)
    
    async def get_learnings_from_cloud(self, topic: str = None) -> List[Dict]:
        """Get learnings from Mem0."""
        query = topic or "what worked learning insight"
        return await self._search(query, ARIA_LEARNINGS, limit=10)
    
    # ==================== HELPERS ====================
    
    def _format_for_mem0(self, memory: Memory) -> str:
        """Format a memory for Mem0 storage."""
        if memory.category == MemoryCategory.CONVERSATION:
            if memory.user_message and memory.aria_response:
                return f"Conversation: User asked '{memory.user_message[:100]}'. Aria responded '{memory.aria_response[:100]}'."
            return memory.content[:300]
        
        elif memory.category == MemoryCategory.LEARNING:
            if memory.insight:
                return f"Learning: {memory.insight}"
            return f"Learned: {memory.content[:300]}"
        
        elif memory.category == MemoryCategory.PATTERN:
            return f"Pattern detected: {memory.content[:300]}"
        
        elif memory.category == MemoryCategory.DECISION:
            return f"Decision made: {memory.content[:300]}"
        
        else:
            return memory.content[:300]
    
    async def get_status(self) -> Dict:
        """Get Mem0 sync status."""
        return {
            "enabled": self.enabled,
            "api_configured": bool(self.api_key),
            "entity_ids": {
                "identity": ARIA_IDENTITY,
                "learnings": ARIA_LEARNINGS,
                "patterns": ARIA_PATTERNS,
                "conversations": ARIA_CONVERSATIONS
            }
        }


# Singleton
_sync: Optional[Mem0Sync] = None


def get_mem0_sync() -> Mem0Sync:
    """Get or create Mem0 sync instance."""
    global _sync
    if _sync is None:
        _sync = Mem0Sync()
    return _sync


async def sync_important_memories():
    """
    Background task to sync important memories to Mem0.
    
    Run periodically (e.g., every hour) to keep cloud in sync.
    """
    sync = get_mem0_sync()
    if not sync.enabled:
        return {"synced": 0, "reason": "disabled"}
    
    store = get_memory_store()
    
    # Get recent high-importance memories
    from .store import MemoryCategory
    
    synced = 0
    for category in [MemoryCategory.LEARNING, MemoryCategory.PATTERN, MemoryCategory.DECISION]:
        memories = store.get_by_category(category, limit=20)
        for memory in memories:
            if memory.importance in [MemoryImportance.HIGH, MemoryImportance.CRITICAL]:
                if await sync.sync_memory(memory):
                    synced += 1
    
    return {"synced": synced}


