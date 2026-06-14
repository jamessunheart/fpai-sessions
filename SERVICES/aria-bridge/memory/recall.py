"""
ARIA MEMORY RECALL
==================

Semantic recall system for finding relevant memories.

Uses keyword matching + recency + importance weighting.
(Can be upgraded to embeddings later for true semantic search)
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .store import (
    get_memory_store, Memory, MemoryStore,
    MemoryCategory, MemoryImportance
)

logger = logging.getLogger("aria.memory.recall")


@dataclass
class RecalledMemory:
    """A memory with relevance score."""
    memory: Memory
    relevance_score: float
    match_reason: str


class MemoryRecall:
    """
    Semantic recall for finding relevant memories.
    
    Combines:
    - Keyword matching
    - Recency weighting
    - Importance weighting
    - Category filtering
    """
    
    def __init__(self):
        self.store = get_memory_store()
        
        # Importance weights
        self.importance_weights = {
            MemoryImportance.CRITICAL: 2.0,
            MemoryImportance.HIGH: 1.5,
            MemoryImportance.MEDIUM: 1.0,
            MemoryImportance.LOW: 0.5
        }
        
        # Category weights for different query types
        self.category_weights = {
            MemoryCategory.IDENTITY: 1.5,
            MemoryCategory.LEARNING: 1.3,
            MemoryCategory.DECISION: 1.2,
            MemoryCategory.CONVERSATION: 1.0,
            MemoryCategory.CONTEXT: 1.0,
            MemoryCategory.PREFERENCE: 1.1,
            MemoryCategory.PATTERN: 1.2,
            MemoryCategory.OUTCOME: 1.1
        }
        
        logger.info("MemoryRecall initialized")
    
    def recall(
        self,
        query: str,
        limit: int = 10,
        categories: List[MemoryCategory] = None,
        min_importance: MemoryImportance = None,
        recency_days: int = None
    ) -> List[RecalledMemory]:
        """
        Recall memories relevant to a query.
        
        Args:
            query: What to search for
            limit: Max memories to return
            categories: Filter by categories
            min_importance: Minimum importance level
            recency_days: Only search within recent days
        """
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        
        if not keywords:
            # If no keywords, just return recent important memories
            return self._get_recent_important(limit)
        
        # Get candidate memories
        candidates = self._get_candidates(
            categories=categories,
            recency_days=recency_days,
            limit=limit * 5  # Get more candidates than needed
        )
        
        # Score each candidate
        scored = []
        for memory in candidates:
            score, reason = self._score_memory(memory, keywords, query)
            
            # Apply importance filter
            if min_importance:
                importance_order = list(MemoryImportance)
                if importance_order.index(memory.importance) > importance_order.index(min_importance):
                    continue
            
            if score > 0:
                scored.append(RecalledMemory(
                    memory=memory,
                    relevance_score=score,
                    match_reason=reason
                ))
        
        # Sort by score and return top results
        scored.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored[:limit]
    
    def recall_for_response(
        self,
        user_message: str,
        limit: int = 5
    ) -> str:
        """
        Recall context specifically for generating a response.
        
        Returns formatted string suitable for prompt injection.
        """
        # Get relevant memories
        recalled = self.recall(user_message, limit=limit)
        
        if not recalled:
            return ""
        
        # Format for prompt
        lines = ["REMEMBERED CONTEXT:"]
        
        for rm in recalled:
            mem = rm.memory
            
            if mem.category == MemoryCategory.CONVERSATION:
                # For conversations, show the exchange
                if mem.user_message and mem.aria_response:
                    lines.append(f"• Previous exchange: User asked about '{mem.user_message[:50]}...' → Aria responded about {mem.aria_response[:50]}...")
            elif mem.category == MemoryCategory.LEARNING:
                # For learnings, show the insight
                if mem.insight:
                    lines.append(f"• Learned: {mem.insight}")
            elif mem.category == MemoryCategory.PREFERENCE:
                lines.append(f"• Preference: {mem.content[:100]}")
            elif mem.category == MemoryCategory.DECISION:
                lines.append(f"• Past decision: {mem.content[:100]}")
            else:
                lines.append(f"• {mem.content[:100]}")
        
        return "\n".join(lines)
    
    def get_identity_context(self) -> str:
        """Get formatted identity context for prompt."""
        identity = self.store.get_identity()
        
        if not identity:
            return ""
        
        lines = ["IDENTITY (Who Sunheart is):"]
        
        for key, value in identity.items():
            if isinstance(value, list):
                lines.append(f"• {key}: {', '.join(str(v) for v in value[:5])}")
            elif isinstance(value, dict):
                lines.append(f"• {key}: {list(value.keys())[:5]}")
            else:
                lines.append(f"• {key}: {str(value)[:100]}")
        
        return "\n".join(lines)
    
    def get_context_summary(self) -> str:
        """Get formatted current context for prompt."""
        context = self.store.get_context()
        
        if not context:
            return ""
        
        lines = ["CURRENT CONTEXT:"]
        
        for key, value in context.items():
            lines.append(f"• {key}: {str(value)[:100]}")
        
        return "\n".join(lines)
    
    def build_full_context(
        self,
        user_message: str,
        include_identity: bool = True,
        include_context: bool = True,
        memory_limit: int = 5
    ) -> str:
        """Build complete context for a response."""
        parts = []
        
        if include_identity:
            identity = self.get_identity_context()
            if identity:
                parts.append(identity)
        
        if include_context:
            context = self.get_context_summary()
            if context:
                parts.append(context)
        
        # Get relevant memories
        recalled = self.recall_for_response(user_message, limit=memory_limit)
        if recalled:
            parts.append(recalled)
        
        return "\n\n".join(parts)
    
    # ==================== PRIVATE METHODS ====================
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Remove common words
        stopwords = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'between', 'under', 'again', 'further', 'then', 'once',
            'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'just', 'and', 'but', 'if', 'or', 'because', 'until', 'while',
            'what', 'which', 'who', 'this', 'that', 'these', 'those', 'i',
            'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you',
            'your', 'yours', 'yourself', 'he', 'him', 'his', 'himself',
            'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they',
            'them', 'their', 'theirs', 'themselves', 'about', 'tell', 'know'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter stopwords and return unique
        keywords = [w for w in words if w not in stopwords]
        return list(dict.fromkeys(keywords))  # Preserve order, remove duplicates
    
    def _get_candidates(
        self,
        categories: List[MemoryCategory] = None,
        recency_days: int = None,
        limit: int = 100
    ) -> List[Memory]:
        """Get candidate memories for scoring."""
        return self.store.get_recent(
            limit=limit,
            categories=categories
        )
    
    def _get_recent_important(self, limit: int) -> List[RecalledMemory]:
        """Get recent important memories when no query keywords."""
        memories = self.store.get_recent(limit=limit * 2)
        
        # Sort by importance then recency
        memories.sort(
            key=lambda m: (
                self.importance_weights.get(m.importance, 1.0),
                m.created_at
            ),
            reverse=True
        )
        
        return [
            RecalledMemory(
                memory=m,
                relevance_score=self.importance_weights.get(m.importance, 1.0),
                match_reason="recent important"
            )
            for m in memories[:limit]
        ]
    
    def _score_memory(
        self,
        memory: Memory,
        keywords: List[str],
        original_query: str
    ) -> Tuple[float, str]:
        """Score a memory's relevance to the query."""
        score = 0.0
        reasons = []
        
        content_lower = memory.content.lower()
        
        # Keyword matching
        keyword_matches = 0
        for kw in keywords:
            if kw in content_lower:
                keyword_matches += 1
        
        if keyword_matches > 0:
            keyword_score = (keyword_matches / len(keywords)) * 2.0
            score += keyword_score
            reasons.append(f"{keyword_matches} keywords")
        
        # Check user_message and aria_response too
        if memory.user_message:
            for kw in keywords:
                if kw in memory.user_message.lower():
                    score += 0.3
        
        if memory.aria_response:
            for kw in keywords:
                if kw in memory.aria_response.lower():
                    score += 0.2
        
        # Importance weighting
        importance_multiplier = self.importance_weights.get(memory.importance, 1.0)
        score *= importance_multiplier
        
        # Category weighting
        category_multiplier = self.category_weights.get(memory.category, 1.0)
        score *= category_multiplier
        
        # Recency bonus (memories from last 7 days get a boost)
        try:
            created = datetime.fromisoformat(memory.created_at)
            days_old = (datetime.utcnow() - created).days
            if days_old < 7:
                recency_bonus = 0.3 * (1 - days_old / 7)
                score += recency_bonus
                reasons.append("recent")
        except:
            pass
        
        return score, ", ".join(reasons) if reasons else "low match"


# Singleton
_recall: Optional[MemoryRecall] = None


def get_memory_recall() -> MemoryRecall:
    """Get or create memory recall instance."""
    global _recall
    if _recall is None:
        _recall = MemoryRecall()
    return _recall


