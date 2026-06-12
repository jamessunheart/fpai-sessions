"""
ARIA WORKING MEMORY
====================

Short-term, high-priority memory for current task context.

Human working memory holds ~7 items. This module replicates that:
- Current goal/task
- Files being worked on
- Recent tool outputs
- Key decisions made
- Active context items

Working memory is:
- FAST (in-memory, no disk I/O for reads)
- VOLATILE (clears on restart, that's intentional)
- FOCUSED (only what matters RIGHT NOW)
- PROMOTED (important items move to long-term)

This gives Aria awareness of "what am I doing right now?"
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import asyncio

logger = logging.getLogger("aria.memory.working")

# Configuration
MAX_WORKING_ITEMS = int(os.getenv("MAX_WORKING_MEMORY", "7"))
ITEM_TTL_SECONDS = int(os.getenv("WORKING_MEMORY_TTL", "1800"))  # 30 minutes


class WorkingItemType(str, Enum):
    """Types of working memory items."""
    GOAL = "goal"           # Current task/objective
    FILE = "file"           # File being worked on
    TOOL_RESULT = "tool"    # Recent tool output
    DECISION = "decision"   # Decision made
    CONTEXT = "context"     # Important context
    ERROR = "error"         # Recent error
    USER_INPUT = "user"     # User said something important


@dataclass
class WorkingItem:
    """A single item in working memory."""
    id: str
    content: str
    item_type: WorkingItemType
    priority: float  # 0-1, higher = more important
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if item has expired."""
        return datetime.now() > self.expires_at
    
    def touch(self):
        """Mark as accessed, extend TTL."""
        self.access_count += 1
        # Extend TTL on access
        self.expires_at = datetime.now() + timedelta(seconds=ITEM_TTL_SECONDS)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.item_type.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "access_count": self.access_count,
            "metadata": self.metadata
        }


class WorkingMemory:
    """
    Aria's working memory - current task context.
    
    Like a mental scratchpad:
    - What am I working on?
    - What files are open?
    - What did I just do?
    - What decision did I make?
    
    Automatically:
    - Evicts oldest/lowest priority when full
    - Expires items after TTL
    - Promotes important items to long-term
    """
    
    def __init__(self):
        self._items: Dict[str, WorkingItem] = {}
        self._current_goal: Optional[str] = None
        self._history: deque = deque(maxlen=50)  # Track what was evicted
        
        logger.info(f"🧠 Working memory initialized (capacity: {MAX_WORKING_ITEMS})")
    
    def set_goal(self, goal: str, context: Dict = None) -> str:
        """
        Set the current goal/task.
        
        The goal has highest priority and doesn't evict.
        """
        item_id = f"goal_{datetime.now().timestamp()}"
        
        item = WorkingItem(
            id=item_id,
            content=goal,
            item_type=WorkingItemType.GOAL,
            priority=1.0,  # Highest priority
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),  # Goals last longer
            metadata=context or {}
        )
        
        # Remove old goal
        if self._current_goal and self._current_goal in self._items:
            old_goal = self._items[self._current_goal]
            self._history.append(old_goal.to_dict())
            del self._items[self._current_goal]
        
        self._items[item_id] = item
        self._current_goal = item_id
        
        logger.info(f"🎯 Goal set: {goal[:50]}...")
        return item_id
    
    def add(
        self,
        content: str,
        item_type: WorkingItemType,
        priority: float = 0.5,
        metadata: Dict = None
    ) -> str:
        """
        Add an item to working memory.
        
        If memory is full, evicts lowest priority expired item.
        """
        # Clean expired items first
        self._clean_expired()
        
        # If still full, evict lowest priority
        while len(self._items) >= MAX_WORKING_ITEMS:
            self._evict_lowest()
        
        item_id = f"{item_type.value}_{datetime.now().timestamp()}"
        
        item = WorkingItem(
            id=item_id,
            content=content[:500],  # Limit content size
            item_type=item_type,
            priority=min(0.99, max(0.1, priority)),  # Keep below goal
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ITEM_TTL_SECONDS),
            metadata=metadata or {}
        )
        
        self._items[item_id] = item
        
        logger.debug(f"Working memory +{item_type.value}: {content[:30]}...")
        return item_id
    
    def add_file(self, path: str, summary: str = None) -> str:
        """Add a file being worked on."""
        content = f"Working on: {path}"
        if summary:
            content += f" - {summary}"
        
        return self.add(
            content=content,
            item_type=WorkingItemType.FILE,
            priority=0.7,
            metadata={"path": path}
        )
    
    def add_tool_result(self, tool: str, result_summary: str) -> str:
        """Add a tool result."""
        return self.add(
            content=f"{tool}: {result_summary}",
            item_type=WorkingItemType.TOOL_RESULT,
            priority=0.6,
            metadata={"tool": tool}
        )
    
    def add_decision(self, decision: str, reasoning: str = None) -> str:
        """Add a decision made."""
        return self.add(
            content=decision,
            item_type=WorkingItemType.DECISION,
            priority=0.8,
            metadata={"reasoning": reasoning} if reasoning else {}
        )
    
    def add_error(self, error: str, context: str = None) -> str:
        """Add an error (high priority to avoid repeating)."""
        return self.add(
            content=f"ERROR: {error}",
            item_type=WorkingItemType.ERROR,
            priority=0.85,
            metadata={"context": context} if context else {}
        )
    
    def add_user_context(self, context: str) -> str:
        """Add important user input."""
        return self.add(
            content=context,
            item_type=WorkingItemType.USER_INPUT,
            priority=0.75,
            metadata={}
        )
    
    def get_context_prompt(self) -> str:
        """
        Get working memory formatted for system prompt injection.
        
        This tells Aria what she's currently focused on.
        """
        if not self._items:
            return ""
        
        self._clean_expired()
        
        lines = ["\n## 🧠 WORKING MEMORY (Current Focus)\n"]
        
        # Goal first
        if self._current_goal and self._current_goal in self._items:
            goal = self._items[self._current_goal]
            lines.append(f"**🎯 Current Goal:** {goal.content}")
            goal.touch()
        
        # Group by type
        by_type: Dict[WorkingItemType, List[WorkingItem]] = {}
        for item in self._items.values():
            if item.id == self._current_goal:
                continue  # Already shown
            if item.item_type not in by_type:
                by_type[item.item_type] = []
            by_type[item.item_type].append(item)
        
        # Files
        if WorkingItemType.FILE in by_type:
            lines.append("\n**📁 Active Files:**")
            for item in by_type[WorkingItemType.FILE][:3]:
                lines.append(f"- {item.content}")
                item.touch()
        
        # Recent tools
        if WorkingItemType.TOOL_RESULT in by_type:
            lines.append("\n**🔧 Recent Results:**")
            for item in by_type[WorkingItemType.TOOL_RESULT][:2]:
                lines.append(f"- {item.content[:100]}")
                item.touch()
        
        # Decisions
        if WorkingItemType.DECISION in by_type:
            lines.append("\n**✅ Decisions Made:**")
            for item in by_type[WorkingItemType.DECISION][:2]:
                lines.append(f"- {item.content}")
                item.touch()
        
        # Errors (important to remember)
        if WorkingItemType.ERROR in by_type:
            lines.append("\n**⚠️ Recent Errors (avoid repeating):**")
            for item in by_type[WorkingItemType.ERROR][:2]:
                lines.append(f"- {item.content}")
                item.touch()
        
        # User context
        if WorkingItemType.USER_INPUT in by_type:
            lines.append("\n**💬 Key Context:**")
            for item in by_type[WorkingItemType.USER_INPUT][:2]:
                lines.append(f"- {item.content}")
                item.touch()
        
        if len(lines) > 1:
            lines.append("\n---\n")
            return "\n".join(lines)
        
        return ""
    
    def get_goal(self) -> Optional[str]:
        """Get current goal."""
        if self._current_goal and self._current_goal in self._items:
            return self._items[self._current_goal].content
        return None
    
    def get_all(self) -> List[WorkingItem]:
        """Get all items."""
        self._clean_expired()
        return list(self._items.values())
    
    def get_files(self) -> List[str]:
        """Get list of files being worked on."""
        return [
            item.metadata.get("path", item.content)
            for item in self._items.values()
            if item.item_type == WorkingItemType.FILE
        ]
    
    def clear(self):
        """Clear all working memory."""
        # Save to history before clearing
        for item in self._items.values():
            self._history.append(item.to_dict())
        
        self._items.clear()
        self._current_goal = None
        logger.info("🧠 Working memory cleared")
    
    def remove(self, item_id: str):
        """Remove a specific item."""
        if item_id in self._items:
            item = self._items[item_id]
            self._history.append(item.to_dict())
            del self._items[item_id]
            
            if item_id == self._current_goal:
                self._current_goal = None
    
    def promote_to_longterm(self, item_id: str) -> Optional[Dict]:
        """
        Mark an item for promotion to long-term memory.
        
        Returns the item data to be stored externally.
        """
        if item_id not in self._items:
            return None
        
        item = self._items[item_id]
        
        # Return data suitable for long-term storage
        return {
            "content": item.content,
            "type": item.item_type.value,
            "importance": item.priority,
            "metadata": {
                **item.metadata,
                "promoted_from": "working_memory",
                "access_count": item.access_count
            }
        }
    
    def _clean_expired(self):
        """Remove expired items."""
        expired = [
            item_id for item_id, item in self._items.items()
            if item.is_expired() and item_id != self._current_goal
        ]
        
        for item_id in expired:
            item = self._items[item_id]
            self._history.append(item.to_dict())
            del self._items[item_id]
        
        if expired:
            logger.debug(f"Expired {len(expired)} working memory items")
    
    def _evict_lowest(self):
        """Evict the lowest priority item."""
        if not self._items:
            return
        
        # Don't evict the goal
        candidates = [
            (item_id, item) 
            for item_id, item in self._items.items()
            if item_id != self._current_goal
        ]
        
        if not candidates:
            return
        
        # Find lowest priority
        lowest_id, lowest = min(candidates, key=lambda x: x[1].priority)
        
        self._history.append(lowest.to_dict())
        del self._items[lowest_id]
        
        logger.debug(f"Evicted: {lowest.content[:30]}...")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics."""
        self._clean_expired()
        
        return {
            "item_count": len(self._items),
            "capacity": MAX_WORKING_ITEMS,
            "has_goal": self._current_goal is not None,
            "current_goal": self.get_goal(),
            "items_by_type": {
                t.value: sum(1 for i in self._items.values() if i.item_type == t)
                for t in WorkingItemType
            },
            "history_count": len(self._history),
            "ttl_seconds": ITEM_TTL_SECONDS
        }


# ============================================================================
# SINGLETON
# ============================================================================

_working_memory: Optional[WorkingMemory] = None


def get_working_memory() -> WorkingMemory:
    """Get or create working memory instance."""
    global _working_memory
    if _working_memory is None:
        _working_memory = WorkingMemory()
    return _working_memory









