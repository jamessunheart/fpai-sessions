"""
ARIA COMMAND - MEM0 CLIENT
===========================

Direct integration with Mem0 cloud memory.

This provides:
- store_memory: Save important learnings/patterns
- recall_memories: Search past knowledge
- inject_relevant_memories: Auto-inject context into prompts

The goal: Aria actually REMEMBERS across sessions.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import httpx
import asyncio

logger = logging.getLogger("aria.memory")

# Mem0 Configuration
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo")
MEM0_BASE_URL = "https://api.mem0.ai/v1"

# Entity IDs for different memory types
ENTITY_IDS = {
    "identity": "aria_identity",
    "learnings": "aria_learnings", 
    "patterns": "aria_patterns",
    "conversations": "aria_conversations"
}


class MemoryCategory(str, Enum):
    """Categories of memory."""
    LEARNING = "learning"
    PATTERN = "pattern"
    DECISION = "decision"
    CONTEXT = "context"
    PREFERENCE = "preference"
    IDENTITY = "identity"
    CONVERSATION = "conversation"


class MemoryImportance(str, Enum):
    """Importance levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryResult:
    """Result of a memory operation."""
    success: bool
    message: str
    data: Optional[Dict] = None
    memories: Optional[List[Dict]] = None


class Mem0Client:
    """
    Client for Mem0 cloud memory.
    
    Provides Aria with persistent memory that survives restarts
    and grows over time.
    """
    
    def __init__(self):
        self.api_key = MEM0_API_KEY
        self.enabled = bool(self.api_key) and self.api_key != "m0-your-api-key-here"
        
        if self.enabled:
            self.headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }
            logger.info("🧠 Mem0 cloud memory connected")
        else:
            self.headers = {}
            logger.warning("⚠️ Mem0 not configured - memory disabled")
    
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
    
    async def store(
        self,
        content: str,
        category: str = "learning",
        importance: str = "medium",
        metadata: Optional[Dict] = None
    ) -> MemoryResult:
        """
        Store a memory to Mem0 cloud.
        
        Args:
            content: The memory content to store
            category: learning, pattern, decision, context, preference
            importance: low, medium, high, critical
            metadata: Optional additional metadata
        
        Returns:
            MemoryResult with success status
        """
        if not self.enabled:
            return MemoryResult(
                success=False,
                message="Mem0 not configured"
            )
        
        # Map category to entity ID
        entity_map = {
            "learning": "aria_learnings",
            "pattern": "aria_patterns",
            "decision": "aria_learnings",
            "context": "aria_conversations",
            "preference": "aria_learnings",
            "identity": "aria_identity",
            "conversation": "aria_conversations"
        }
        user_id = entity_map.get(category.lower(), "aria_learnings")
        
        # Build the message
        try:
            result = await self._post("memories", {
                "messages": [{"role": "user", "content": content}],
                "user_id": user_id,
                "metadata": {
                    "category": category,
                    "importance": importance,
                    "stored_at": datetime.now(timezone.utc).isoformat(),
                    **(metadata or {})
                }
            })
            
            if result:
                logger.info(f"☁️ Memory stored: {content[:50]}...")
                return MemoryResult(
                    success=True,
                    message="Memory stored successfully",
                    data={"entity": user_id, "response": result}
                )
            else:
                return MemoryResult(
                    success=False,
                    message="Failed to store memory to Mem0"
                )
                
        except Exception as e:
            logger.error(f"Store memory failed: {e}")
            return MemoryResult(
                success=False,
                message=f"Error: {e}"
            )
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        entity: str = None
    ) -> MemoryResult:
        """
        Search Mem0 for relevant memories.
        
        Args:
            query: What to search for
            limit: Max results to return
            entity: Specific entity to search (or all if None)
        
        Returns:
            MemoryResult with memories list
        """
        if not self.enabled:
            return MemoryResult(
                success=False,
                message="Mem0 not configured",
                memories=[]
            )
        
        try:
            all_memories = []
            
            # Search specific entity or all
            entities = [entity] if entity else list(ENTITY_IDS.values())
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                for ent in entities:
                    try:
                        resp = await client.post(
                            f"{MEM0_BASE_URL}/memories/search/",
                            headers=self.headers,
                            json={"query": query, "user_id": ent, "limit": limit}
                        )
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            memories = data if isinstance(data, list) else data.get("results", data.get("memories", []))
                            
                            for mem in memories:
                                mem["_entity"] = ent
                            all_memories.extend(memories)
                    except Exception as e:
                        logger.warning(f"Search failed for entity {ent}: {e}")
            
            # Sort by score and limit
            all_memories.sort(key=lambda x: x.get("score", 0), reverse=True)
            all_memories = all_memories[:limit]
            
            return MemoryResult(
                success=True,
                message=f"Found {len(all_memories)} memories",
                memories=all_memories
            )
            
        except Exception as e:
            logger.error(f"Search memories failed: {e}")
            return MemoryResult(
                success=False,
                message=f"Search failed: {e}",
                memories=[]
            )
    
    async def get_context_for_prompt(
        self,
        user_message: str,
        limit: int = 3
    ) -> str:
        """
        Get relevant memories to inject into the system prompt.
        
        This is called automatically before each response to give
        Aria context from past conversations.
        
        Args:
            user_message: The current user message
            limit: Max memories to include
        
        Returns:
            Formatted string to inject into prompt, or empty string
        """
        if not self.enabled:
            return ""
        
        try:
            result = await self.search(user_message, limit=limit)
            
            if not result.memories:
                return ""
            
            # Format memories for injection
            lines = ["## 🧠 Relevant Past Knowledge\n"]
            
            for i, mem in enumerate(result.memories, 1):
                memory_text = mem.get("memory", mem.get("text", ""))
                if memory_text:
                    entity = mem.get("_entity", "unknown")
                    entity_label = {
                        "aria_identity": "Identity",
                        "aria_learnings": "Learning",
                        "aria_patterns": "Pattern",
                        "aria_conversations": "Context"
                    }.get(entity, "Memory")
                    
                    lines.append(f"**{entity_label}:** {memory_text[:200]}")
            
            lines.append("\n---\n")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.warning(f"Failed to get context: {e}")
            return ""
    
    async def get_status(self) -> Dict:
        """Get Mem0 connection status."""
        return {
            "enabled": self.enabled,
            "api_configured": bool(self.api_key),
            "entities": ENTITY_IDS
        }


# ============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# ============================================================================

_client: Optional[Mem0Client] = None


def get_mem0_client() -> Mem0Client:
    """Get or create Mem0 client instance."""
    global _client
    if _client is None:
        _client = Mem0Client()
    return _client


async def store_memory(
    content: str,
    category: str = "learning",
    importance: str = "medium",
    metadata: Optional[Dict] = None
) -> MemoryResult:
    """Store a memory to Mem0 cloud."""
    client = get_mem0_client()
    return await client.store(content, category, importance, metadata)


async def recall_memories(
    query: str,
    limit: int = 5
) -> List[Dict]:
    """Search Mem0 for relevant memories."""
    client = get_mem0_client()
    result = await client.search(query, limit)
    return result.memories or []


async def search_memories(
    query: str,
    limit: int = 5,
    entity: str = None
) -> MemoryResult:
    """Search Mem0 with full result object."""
    client = get_mem0_client()
    return await client.search(query, limit, entity)


async def inject_relevant_memories(
    user_message: str,
    limit: int = 3
) -> str:
    """Get formatted memories to inject into prompt."""
    client = get_mem0_client()
    return await client.get_context_for_prompt(user_message, limit)









