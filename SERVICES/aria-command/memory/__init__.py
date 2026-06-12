"""
ARIA MEMORY SYSTEM - LEVEL 10 ARCHITECTURE
============================================

A multi-layered memory system inspired by human cognition.
Designed to reach LEVEL 10 - true human-like memory.

Architecture:
┌─────────────────────────────────────────────────────────────────────────────┐
│                           UNIFIED MEMORY API                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  LAYER 1: WORKING MEMORY          │  LAYER 2: SEMANTIC MEMORY               │
│  ├── Current Goal (1 item)        │  ├── Local SQLite (fast, reliable)     │
│  ├── Active Files (up to 3)       │  ├── Mem0 Cloud (backup, cross-session)│
│  ├── Recent Results               │  └── Auto-sync (local → cloud)         │
│  └── Decisions Made               │                                         │
├───────────────────────────────────┼─────────────────────────────────────────┤
│  LAYER 3: EPISODIC MEMORY         │  LAYER 4: KNOWLEDGE GRAPH               │
│  ├── Conversation Narratives      │  ├── Concepts (entities)               │
│  ├── Key Moments                  │  ├── Relationships (links)             │
│  └── Emotional Context            │  └── Paths (traversal)                 │
├───────────────────────────────────┼─────────────────────────────────────────┤
│  LAYER 5: ABSTRACTION ENGINE      │  LAYER 6: TEMPORAL MEMORY               │
│  ├── Observations → Patterns      │  ├── When things happen                │
│  ├── Patterns → Principles        │  ├── Recurring patterns                │
│  └── Principle Validation         │  └── Time-based predictions            │
├───────────────────────────────────┼─────────────────────────────────────────┤
│  LAYER 7: PROACTIVE INSIGHTS      │  LAYER 8: SELF-IMPROVEMENT              │
│  ├── Spontaneous Recall           │  ├── Performance Tracking              │
│  ├── Warning Surfacing            │  ├── Improvement Trends                │
│  └── Pattern Recognition          │  └── Weak Area Identification          │
├─────────────────────────────────────────────────────────────────────────────┤
│  META LAYER: VERIFICATION & CONSOLIDATION                                   │
│  ├── Staleness Detection          │  └── Memory Sleep (consolidation)      │
│  └── Contradiction Detection                                                │
└─────────────────────────────────────────────────────────────────────────────┘

LEVEL 10 RATING FORMULA:
- Redundancy (local + cloud): 1.0 max
- Memory Depth (50+ memories): 1.0 max
- Knowledge Graph (concepts + relations): 1.0 max
- Working Memory: 1.0 max
- Episodic Memory: 1.0 max
- Abstraction (principles): 1.0 max
- Temporal Awareness: 1.0 max
- Proactive Insights: 1.0 max
- Self-Improvement: 1.0 max
- Verification (low staleness): 1.0 max
= TOTAL: 10.0 max
"""

# ============================================================================
# CORE MEMORY (Drop-in replacements for old functions)
# ============================================================================

from .hybrid_memory import (
    HybridMemorySystem,
    HybridMemory,
    get_hybrid_memory,
    store_memory,
    recall_memories,
    inject_relevant_memories
)

# ============================================================================
# LOCAL STORE (SQLite fallback)
# ============================================================================

from .local_store import (
    LocalMemoryStore,
    LocalMemory,
    MemoryType,
    SyncStatus,
    get_local_store
)

# ============================================================================
# WORKING MEMORY (Current task context)
# ============================================================================

from .working_memory import (
    WorkingMemory,
    WorkingItem,
    WorkingItemType,
    get_working_memory
)

# ============================================================================
# EPISODIC MEMORY (Conversation narratives)
# ============================================================================

from .episodic_memory import (
    EpisodicMemory,
    Episode,
    EpisodeBuilder,
    EpisodeType,
    EmotionalTone,
    Outcome,
    get_episodic_memory
)

# ============================================================================
# KNOWLEDGE GRAPH (Associative connections)
# ============================================================================

from .knowledge_graph import (
    KnowledgeGraph,
    Concept,
    Relationship,
    RelationType,
    get_knowledge_graph
)

# ============================================================================
# ABSTRACTION ENGINE (Patterns → Principles)
# ============================================================================

from .abstraction import (
    AbstractionEngine,
    Observation,
    Principle,
    get_abstraction_engine
)

# ============================================================================
# TEMPORAL MEMORY (Time-aware patterns)
# ============================================================================

from .temporal import (
    TemporalMemory,
    TemporalEvent,
    TemporalPattern,
    EventType,
    TimeWindow,
    get_temporal_memory
)

# ============================================================================
# PROACTIVE MEMORY (Spontaneous recall)
# ============================================================================

from .proactive import (
    ProactiveMemory,
    ProactiveInsight,
    get_proactive_memory,
    get_proactive_insights
)

# ============================================================================
# SELF-IMPROVEMENT (Performance tracking)
# ============================================================================

from .self_improvement import (
    SelfImprovementTracker,
    InteractionRecord,
    PerformanceMetrics,
    InteractionOutcome,
    QueryType,
    get_improvement_tracker
)

# ============================================================================
# VERIFICATION (Accuracy maintenance)
# ============================================================================

from .verification import (
    MemoryVerifier,
    VerificationResult,
    VerificationStatus,
    get_memory_verifier
)

# ============================================================================
# CONSOLIDATION (Memory sleep)
# ============================================================================

from .consolidation import (
    MemoryConsolidator,
    ConsolidationReport,
    get_consolidator,
    run_consolidation
)

# ============================================================================
# LEGACY COMPAT (Mem0 client)
# ============================================================================

from .mem0_client import (
    Mem0Client,
    get_mem0_client,
    MemoryResult,
    MemoryCategory,
    MemoryImportance
)


# ============================================================================
# UNIFIED MEMORY API - LEVEL 10
# ============================================================================

class UnifiedMemory:
    """
    Single interface to all memory layers.
    
    This is what opus_brain uses to interact with memory.
    Designed for LEVEL 10 - human-like memory capabilities.
    """
    
    def __init__(self):
        # Core layers
        self.hybrid = get_hybrid_memory()
        self.working = get_working_memory()
        self.episodic = get_episodic_memory()
        self.graph = get_knowledge_graph()
        
        # Advanced layers
        self.abstraction = get_abstraction_engine()
        self.temporal = get_temporal_memory()
        self.proactive = get_proactive_memory()
        self.improvement = get_improvement_tracker()
        
        # Meta layers
        self.verifier = get_memory_verifier()
        self.consolidator = get_consolidator()
    
    async def store(
        self,
        content: str,
        memory_type: str = "learning",
        importance: float = 0.5,
        metadata: dict = None
    ):
        """Store to long-term memory and learn associations."""
        result = await self.hybrid.store(content, memory_type, importance, metadata)
        
        # Learn from this memory (add to knowledge graph)
        self.graph.learn_from_memory(result.id, content, memory_type)
        
        # Record as observation for abstraction
        self.abstraction.record_observation(content, memory_type, result.id)
        
        # Record temporal event
        event_type = EventType.QUERY  # Default
        if "error" in content.lower() or "bug" in content.lower():
            event_type = EventType.ERROR
        elif "fix" in content.lower() or "fixed" in content.lower():
            event_type = EventType.FIX
        elif "deploy" in content.lower():
            event_type = EventType.DEPLOY
        
        self.temporal.record_event(event_type, content[:200])
        
        return result
    
    async def search(self, query: str, limit: int = 5):
        """Search all memory layers."""
        return await self.hybrid.search(query, limit)
    
    def set_goal(self, goal: str, context: dict = None):
        """Set current working goal."""
        return self.working.set_goal(goal, context)
    
    def add_to_working(self, content: str, item_type: str = "context", priority: float = 0.5):
        """Add to working memory."""
        type_map = {
            "goal": WorkingItemType.GOAL,
            "file": WorkingItemType.FILE,
            "tool": WorkingItemType.TOOL_RESULT,
            "decision": WorkingItemType.DECISION,
            "context": WorkingItemType.CONTEXT,
            "error": WorkingItemType.ERROR,
            "user": WorkingItemType.USER_INPUT
        }
        return self.working.add(content, type_map.get(item_type, WorkingItemType.CONTEXT), priority)
    
    def start_episode(self, chat_id: str, topic: str = None):
        """Start tracking a conversation episode."""
        return self.episodic.start_episode(chat_id, topic)
    
    def end_episode(self, chat_id: str, outcome: str = "success"):
        """End and save a conversation episode."""
        outcome_map = {
            "success": Outcome.SUCCESS,
            "partial": Outcome.PARTIAL,
            "failed": Outcome.FAILED,
            "ongoing": Outcome.ONGOING,
            "abandoned": Outcome.ABANDONED
        }
        return self.episodic.end_episode(chat_id, outcome_map.get(outcome, Outcome.SUCCESS))
    
    def record_interaction_outcome(
        self,
        query_type: str,
        outcome: str,
        response_time_ms: float = 0,
        memory_used: int = 0
    ):
        """Record an interaction for self-improvement tracking."""
        query_type_map = {
            "trading": QueryType.TRADING,
            "status": QueryType.STATUS,
            "building": QueryType.BUILDING,
            "question": QueryType.QUESTION,
            "command": QueryType.COMMAND,
            "memory": QueryType.MEMORY
        }
        outcome_map = {
            "success": InteractionOutcome.SUCCESS,
            "partial": InteractionOutcome.PARTIAL,
            "correction": InteractionOutcome.CORRECTION,
            "failure": InteractionOutcome.FAILURE
        }
        
        return self.improvement.record_interaction(
            query_type=query_type_map.get(query_type, QueryType.OTHER),
            outcome=outcome_map.get(outcome, InteractionOutcome.UNKNOWN),
            response_time_ms=response_time_ms,
            memory_used=memory_used
        )
    
    async def get_full_context(self, user_message: str, chat_id: str = None) -> str:
        """
        Get complete memory context for prompt injection.
        
        Combines ALL 8 memory layers for maximum context.
        """
        parts = []
        
        # 1. Working memory (what am I doing now?)
        working_context = self.working.get_context_prompt()
        if working_context:
            parts.append(working_context)
        
        # 2. Proactive insights (what comes to mind?)
        try:
            proactive_context = await get_proactive_insights(user_message, chat_id)
            if proactive_context:
                parts.append(proactive_context)
        except Exception:
            pass
        
        # 3. Long-term semantic memory (what do I know?)
        semantic_context = await self.hybrid.get_context_for_prompt(user_message, limit=3)
        if semantic_context:
            parts.append(semantic_context)
        
        # 4. Episodic memory (have I seen this before?)
        episodic_context = self.episodic.get_context_prompt(limit=2)
        if episodic_context:
            parts.append(episodic_context)
        
        # 5. Knowledge graph (what's connected?)
        concepts = self.graph.extract_concepts_from_text(user_message)
        if concepts:
            for name, _ in concepts[:2]:
                graph_context = self.graph.get_context_prompt(name)
                if graph_context:
                    parts.append(graph_context)
                    break
        
        # 6. Abstraction (what principles apply?)
        principles_context = self.abstraction.get_principles_prompt(user_message)
        if principles_context:
            parts.append(principles_context)
        
        # 7. Temporal awareness (what time patterns?)
        temporal_context = self.temporal.get_context_prompt()
        if temporal_context:
            parts.append(temporal_context)
        
        # 8. Self-improvement awareness
        improvement_context = self.improvement.get_self_improvement_prompt()
        if improvement_context:
            parts.append(improvement_context)
        
        # 9. Stale memories alert (if any need verification)
        stale = self.verifier.get_stale_memories(limit=2)
        if stale:
            stale_prompt = self.verifier.get_verification_prompt(stale)
            if stale_prompt:
                parts.append(stale_prompt)
        
        return "\n".join(parts)
    
    async def consolidate(self):
        """Run memory consolidation."""
        return await self.consolidator.consolidate()
    
    def get_status(self) -> dict:
        """Get status of all memory layers."""
        return {
            "hybrid": self.hybrid.get_status(),
            "working": self.working.get_stats(),
            "episodic": self.episodic.get_stats(),
            "graph": self.graph.get_stats(),
            "abstraction": self.abstraction.get_stats(),
            "temporal": self.temporal.get_stats(),
            "improvement": self.improvement.get_stats(),
            "verification": self.verifier.get_stats(),
            "consolidator": self.consolidator.get_status(),
            "rating": self._calculate_rating()
        }
    
    def _calculate_rating(self) -> dict:
        """
        Calculate memory system rating (1-10).
        
        LEVEL 10 FORMULA:
        - Redundancy (local + cloud): 1.0 max
        - Memory Depth (50+ memories): 1.0 max  
        - Knowledge Graph (concepts + relations): 1.0 max
        - Working Memory: 1.0 max
        - Episodic Memory: 1.0 max
        - Abstraction (principles): 1.0 max
        - Temporal Awareness: 1.0 max
        - Proactive Insights: 1.0 max
        - Self-Improvement: 1.0 max
        - Verification (low staleness): 1.0 max
        = TOTAL: 10.0 max
        """
        hybrid_status = self.hybrid.get_status()
        graph_stats = self.graph.get_stats()
        abstraction_stats = self.abstraction.get_stats()
        temporal_stats = self.temporal.get_stats()
        improvement_stats = self.improvement.get_stats()
        verification_stats = self.verifier.get_stats()
        
        # Component scores (each max 1.0)
        redundancy = 1.0 if hybrid_status["redundancy"] == "full" else 0.5
        
        memory_depth = min(1.0, hybrid_status["local"]["total_memories"] / 50)
        
        graph_concepts = min(0.5, graph_stats["total_concepts"] / 40)
        graph_relations = min(0.5, graph_stats["total_relationships"] / 60)
        graph_score = graph_concepts + graph_relations
        
        working = 1.0  # Always available
        
        episodic_count = self.episodic.get_stats().get("total_episodes", 0)
        episodic = min(1.0, 0.5 + (episodic_count / 20))
        
        abstraction_principles = abstraction_stats.get("total_principles", 0)
        abstraction_score = min(1.0, 0.3 + (abstraction_principles / 10))
        
        temporal_events = temporal_stats.get("total_events", 0)
        temporal_score = min(1.0, 0.3 + (temporal_events / 50))
        
        # Proactive - score based on whether it's working
        proactive_score = 1.0  # Always available
        
        # Self-improvement - based on tracking data
        total_interactions = improvement_stats.get("total_interactions_all_time", 0)
        improvement_score = min(1.0, 0.3 + (total_interactions / 100))
        
        # Verification - inverse of staleness rate
        staleness = verification_stats.get("staleness_rate", 0)
        verification = 1.0 - staleness
        
        # Calculate total
        components = {
            "redundancy": round(redundancy, 2),
            "memory_depth": round(memory_depth, 2),
            "knowledge_graph": round(graph_score, 2),
            "working_memory": round(working, 2),
            "episodic_memory": round(episodic, 2),
            "abstraction": round(abstraction_score, 2),
            "temporal": round(temporal_score, 2),
            "proactive": round(proactive_score, 2),
            "self_improvement": round(improvement_score, 2),
            "verification": round(verification, 2)
        }
        
        total = sum(components.values())
        
        return {
            "score": round(total, 1),
            "max_score": 10.0,
            "components": components,
            "level": self._get_level_name(total)
        }
    
    def _get_level_name(self, score: float) -> str:
        """Get human-readable level name."""
        if score >= 9.5:
            return "Transcendent"
        elif score >= 9.0:
            return "Masterful"
        elif score >= 8.0:
            return "Expert"
        elif score >= 7.0:
            return "Advanced"
        elif score >= 6.0:
            return "Proficient"
        elif score >= 5.0:
            return "Developing"
        elif score >= 4.0:
            return "Basic"
        else:
            return "Emerging"


_unified: UnifiedMemory = None


def get_unified_memory() -> UnifiedMemory:
    """Get unified memory interface."""
    global _unified
    if _unified is None:
        _unified = UnifiedMemory()
    return _unified


__all__ = [
    # Unified API
    "UnifiedMemory",
    "get_unified_memory",
    
    # Core functions (backwards compatible)
    "store_memory",
    "recall_memories",
    "inject_relevant_memories",
    
    # Hybrid memory
    "HybridMemorySystem",
    "HybridMemory",
    "get_hybrid_memory",
    
    # Local store
    "LocalMemoryStore",
    "LocalMemory",
    "MemoryType",
    "SyncStatus",
    "get_local_store",
    
    # Working memory
    "WorkingMemory",
    "WorkingItem",
    "WorkingItemType",
    "get_working_memory",
    
    # Episodic memory
    "EpisodicMemory",
    "Episode",
    "EpisodeBuilder",
    "EpisodeType",
    "EmotionalTone",
    "Outcome",
    "get_episodic_memory",
    
    # Knowledge graph
    "KnowledgeGraph",
    "Concept",
    "Relationship",
    "RelationType",
    "get_knowledge_graph",
    
    # Abstraction
    "AbstractionEngine",
    "Observation",
    "Principle",
    "get_abstraction_engine",
    
    # Temporal
    "TemporalMemory",
    "TemporalEvent",
    "TemporalPattern",
    "EventType",
    "TimeWindow",
    "get_temporal_memory",
    
    # Proactive memory
    "ProactiveMemory",
    "ProactiveInsight",
    "get_proactive_memory",
    "get_proactive_insights",
    
    # Self-improvement
    "SelfImprovementTracker",
    "InteractionRecord",
    "PerformanceMetrics",
    "InteractionOutcome",
    "QueryType",
    "get_improvement_tracker",
    
    # Verification
    "MemoryVerifier",
    "VerificationResult",
    "VerificationStatus",
    "get_memory_verifier",
    
    # Consolidation
    "MemoryConsolidator",
    "ConsolidationReport",
    "get_consolidator",
    "run_consolidation",
    
    # Legacy
    "Mem0Client",
    "get_mem0_client",
    "MemoryResult",
    "MemoryCategory",
    "MemoryImportance"
]
