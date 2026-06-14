"""
ARIA PROACTIVE MEMORY
======================

Surfaces relevant memories without being asked.

Human memory is proactive:
- "Oh, this reminds me of..."
- "Wasn't there something about...?"
- "I remember you said..."

This module:
1. Monitors context for triggers
2. Surfaces relevant past experiences
3. Warns about patterns (e.g., past errors)
4. Suggests based on preferences
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from .hybrid_memory import get_hybrid_memory, HybridMemory
from .episodic_memory import get_episodic_memory, Episode, EpisodeType
from .knowledge_graph import get_knowledge_graph
from .local_store import MemoryType

logger = logging.getLogger("aria.memory.proactive")


@dataclass
class ProactiveInsight:
    """A proactively surfaced memory insight."""
    insight_type: str  # reminder, warning, pattern, preference, related
    content: str
    confidence: float
    source: str  # memory_id or episode_id
    trigger: str  # what triggered this insight
    importance: float
    
    def to_dict(self) -> Dict:
        return {
            "type": self.insight_type,
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "trigger": self.trigger,
            "importance": self.importance
        }
    
    def to_prompt(self) -> str:
        """Format for prompt injection."""
        icons = {
            "reminder": "💭",
            "warning": "⚠️",
            "pattern": "🔄",
            "preference": "👤",
            "related": "🔗"
        }
        icon = icons.get(self.insight_type, "💡")
        return f"{icon} **{self.insight_type.title()}**: {self.content}"


class ProactiveMemory:
    """
    Proactively surfaces relevant memories.
    
    Called during message processing to add context
    that Aria "remembers" without being asked.
    """
    
    # Keywords that trigger memory searches
    TRIGGER_PATTERNS = {
        "error_warning": ["error", "fail", "broken", "down", "issue", "bug", "problem"],
        "trading": ["sol", "btc", "eth", "trading", "signal", "whale", "price"],
        "building": ["build", "create", "implement", "add", "feature", "module"],
        "preference": ["want", "like", "prefer", "should", "always", "never"],
        "status": ["status", "health", "how is", "what's", "check"],
    }
    
    def __init__(self):
        self.hybrid = get_hybrid_memory()
        self.episodic = get_episodic_memory()
        self.graph = get_knowledge_graph()
        
        # Track what we've surfaced recently to avoid repetition
        self._recently_surfaced: Dict[str, datetime] = {}
        self._surface_cooldown = timedelta(minutes=30)
        
        logger.info("💡 Proactive memory initialized")
    
    async def get_insights(
        self,
        user_message: str,
        chat_id: str = None,
        max_insights: int = 3
    ) -> List[ProactiveInsight]:
        """
        Get proactive insights for a user message.
        
        This is called before generating a response.
        """
        insights = []
        
        # 1. Check for error warnings (past similar problems)
        error_insights = await self._check_error_patterns(user_message)
        insights.extend(error_insights)
        
        # 2. Check for preference reminders
        pref_insights = await self._check_preferences(user_message)
        insights.extend(pref_insights)
        
        # 3. Check for related episodes
        episode_insights = await self._check_related_episodes(user_message)
        insights.extend(episode_insights)
        
        # 4. Check knowledge graph for connections
        graph_insights = await self._check_knowledge_graph(user_message)
        insights.extend(graph_insights)
        
        # 5. Check for patterns in learnings
        pattern_insights = await self._check_patterns(user_message)
        insights.extend(pattern_insights)
        
        # Filter out recently surfaced insights
        insights = self._filter_recently_surfaced(insights)
        
        # Sort by importance and return top N
        insights.sort(key=lambda x: x.importance, reverse=True)
        
        # Record what we're surfacing
        for insight in insights[:max_insights]:
            self._recently_surfaced[insight.source] = datetime.now(timezone.utc)
        
        return insights[:max_insights]
    
    async def _check_error_patterns(self, message: str) -> List[ProactiveInsight]:
        """Check if message relates to past errors."""
        insights = []
        message_lower = message.lower()
        
        # Check for error-related triggers
        has_error_trigger = any(
            trigger in message_lower 
            for trigger in self.TRIGGER_PATTERNS["error_warning"]
        )
        
        if not has_error_trigger:
            return insights
        
        # Search for past error-related memories
        memories = await self.hybrid.search(
            query=message,
            limit=3,
            memory_type="correction"
        )
        
        for mem in memories:
            if mem.importance > 0.5:
                insights.append(ProactiveInsight(
                    insight_type="warning",
                    content=f"Past learning: {mem.content[:150]}",
                    confidence=mem.importance,
                    source=mem.id,
                    trigger=message[:50],
                    importance=mem.importance + 0.2  # Boost warnings
                ))
        
        return insights
    
    async def _check_preferences(self, message: str) -> List[ProactiveInsight]:
        """Check if message relates to known preferences."""
        insights = []
        
        # Search for preferences
        memories = await self.hybrid.search(
            query=message,
            limit=3,
            memory_type="preference"
        )
        
        for mem in memories:
            if mem.importance > 0.4:
                insights.append(ProactiveInsight(
                    insight_type="preference",
                    content=mem.content[:150],
                    confidence=mem.importance,
                    source=mem.id,
                    trigger=message[:50],
                    importance=mem.importance
                ))
        
        return insights
    
    async def _check_related_episodes(self, message: str) -> List[ProactiveInsight]:
        """Check for related past episodes."""
        insights = []
        
        # Get episodes related to keywords in message
        episodes = self.episodic.search(query=message, limit=2)
        
        for ep in episodes:
            if ep.importance > 0.5:
                insights.append(ProactiveInsight(
                    insight_type="related",
                    content=f"Related: {ep.title} - {ep.summary[:100]}",
                    confidence=ep.importance,
                    source=ep.id,
                    trigger=message[:50],
                    importance=ep.importance - 0.1  # Slightly lower than direct memories
                ))
        
        return insights
    
    async def _check_knowledge_graph(self, message: str) -> List[ProactiveInsight]:
        """Check knowledge graph for related concepts."""
        insights = []
        
        # Extract concepts from message
        concepts = self.graph.extract_concepts_from_text(message)
        
        for concept_name, _ in concepts[:3]:
            # Get related concepts
            related = self.graph.get_related(concept_name, depth=1, limit=3)
            
            if related:
                related_names = [r["concept"]["name"] for r in related]
                insights.append(ProactiveInsight(
                    insight_type="related",
                    content=f"'{concept_name}' connects to: {', '.join(related_names[:3])}",
                    confidence=0.6,
                    source=f"graph:{concept_name}",
                    trigger=message[:50],
                    importance=0.5
                ))
        
        return insights[:2]  # Limit graph insights
    
    async def _check_patterns(self, message: str) -> List[ProactiveInsight]:
        """Check for learned patterns."""
        insights = []
        
        # Search for pattern-type memories
        memories = await self.hybrid.search(
            query=message,
            limit=2,
            memory_type="pattern"
        )
        
        for mem in memories:
            if mem.importance > 0.5:
                insights.append(ProactiveInsight(
                    insight_type="pattern",
                    content=mem.content[:150],
                    confidence=mem.importance,
                    source=mem.id,
                    trigger=message[:50],
                    importance=mem.importance
                ))
        
        return insights
    
    def _filter_recently_surfaced(self, insights: List[ProactiveInsight]) -> List[ProactiveInsight]:
        """Filter out insights surfaced recently."""
        now = datetime.now(timezone.utc)
        filtered = []
        
        for insight in insights:
            last_surfaced = self._recently_surfaced.get(insight.source)
            
            if not last_surfaced or (now - last_surfaced) > self._surface_cooldown:
                filtered.append(insight)
        
        return filtered
    
    def get_prompt_context(self, insights: List[ProactiveInsight]) -> str:
        """Format insights for prompt injection."""
        if not insights:
            return ""
        
        lines = ["\n## 💡 Proactive Insights\n"]
        lines.append("*I'm recalling these relevant things without being asked:*\n")
        
        for insight in insights:
            lines.append(insight.to_prompt())
        
        lines.append("\n---\n")
        return "\n".join(lines)


# ============================================================================
# SINGLETON
# ============================================================================

_proactive: Optional[ProactiveMemory] = None


def get_proactive_memory() -> ProactiveMemory:
    """Get or create proactive memory instance."""
    global _proactive
    if _proactive is None:
        _proactive = ProactiveMemory()
    return _proactive


async def get_proactive_insights(message: str, chat_id: str = None) -> str:
    """Convenience function to get proactive context for prompt."""
    proactive = get_proactive_memory()
    insights = await proactive.get_insights(message, chat_id)
    return proactive.get_prompt_context(insights)









