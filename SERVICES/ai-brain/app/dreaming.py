"""
Dreaming Engine - THINKING Layer Component
============================================
Part of the Conscious Architecture THINKING pillar.

Pipeline: Replay → Synthesize → Cleanup

The Dreaming box handles:
- Creative association across domains
- Offline processing of accumulated intelligence
- Pattern discovery through novel connections
- Memory consolidation and cleanup

Runs as a scheduled background task (nightly or on-demand).
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import random
import re
from collections import Counter
import json

logger = logging.getLogger(__name__)


@dataclass
class Dream:
    """A synthesized insight from the dreaming process."""
    id: str
    title: str
    insight: str
    source_items: List[str]  # IDs of items that contributed to this dream
    connections: List[Tuple[str, str]]  # Pairs of connected concepts
    dream_type: str  # "pattern", "association", "synthesis", "question"
    confidence: float  # 0-1, how strong is this insight
    created_at: datetime
    categories: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "insight": self.insight,
            "source_items": self.source_items,
            "connections": self.connections,
            "dream_type": self.dream_type,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "categories": self.categories
        }


@dataclass
class DreamCycleReport:
    """Report from a dreaming cycle."""
    cycle_id: str
    started_at: datetime
    completed_at: datetime
    items_processed: int
    dreams_generated: int
    patterns_found: int
    items_cleaned: int
    dreams: List[Dream]
    
    def to_dict(self) -> Dict:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": (self.completed_at - self.started_at).total_seconds(),
            "items_processed": self.items_processed,
            "dreams_generated": self.dreams_generated,
            "patterns_found": self.patterns_found,
            "items_cleaned": self.items_cleaned,
            "dreams": [d.to_dict() for d in self.dreams]
        }


class DreamingEngine:
    """
    The Dreaming Engine for offline creative synthesis.
    
    Mimics biological dreaming by:
    1. Replaying recent intelligence
    2. Finding unexpected connections
    3. Synthesizing novel insights
    4. Consolidating valuable patterns
    5. Cleaning up low-value data
    """
    
    def __init__(self, memory_engine=None, llm_engine=None):
        self.memory_engine = memory_engine
        self.llm_engine = llm_engine
        self.dreams: List[Dream] = []
        self.last_cycle: Optional[DreamCycleReport] = None
        self.cycle_count = 0
        
        # Configuration
        self.min_items_for_dreaming = 10
        self.max_dreams_per_cycle = 5
        self.cleanup_age_days = 7
        self.min_relevance_to_keep = 0.3
    
    async def dream_cycle(self, intelligence_items: List[Dict]) -> DreamCycleReport:
        """
        Run a complete dreaming cycle.
        
        Steps:
        1. Replay - Load and review recent intelligence
        2. Synthesize - Find connections and generate insights
        3. Cleanup - Remove old, low-value items
        """
        started_at = datetime.now(timezone.utc)
        self.cycle_count += 1
        cycle_id = f"dream_cycle_{self.cycle_count}_{started_at.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🌙 Starting dream cycle {cycle_id} with {len(intelligence_items)} items")
        
        dreams = []
        patterns_found = 0
        
        if len(intelligence_items) >= self.min_items_for_dreaming:
            # Phase 1: REPLAY - Review and categorize
            categorized = self._categorize_items(intelligence_items)
            logger.info(f"   Categorized items into {len(categorized)} groups")
            
            # Phase 2: SYNTHESIZE - Find cross-domain connections
            connections = self._find_cross_domain_connections(categorized)
            patterns_found = len(connections)
            logger.info(f"   Found {patterns_found} cross-domain connections")
            
            # Phase 3: Generate dreams from connections
            dreams = await self._generate_dreams(connections, intelligence_items)
            logger.info(f"   Generated {len(dreams)} dreams")
            
            # Store dreams
            self.dreams.extend(dreams)
            self.dreams = self.dreams[-50:]  # Keep last 50 dreams
        
        # Phase 4: CLEANUP - Remove old low-value items
        items_cleaned = self._identify_items_to_cleanup(intelligence_items)
        
        completed_at = datetime.now(timezone.utc)
        
        report = DreamCycleReport(
            cycle_id=cycle_id,
            started_at=started_at,
            completed_at=completed_at,
            items_processed=len(intelligence_items),
            dreams_generated=len(dreams),
            patterns_found=patterns_found,
            items_cleaned=items_cleaned,
            dreams=dreams
        )
        
        self.last_cycle = report
        logger.info(f"🌙 Dream cycle complete: {len(dreams)} dreams, {patterns_found} patterns")
        
        return report
    
    def _categorize_items(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize items by their primary domain."""
        categories = {}
        
        for item in items:
            category = item.get("category", "general")
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        return categories
    
    def _find_cross_domain_connections(self, categorized: Dict[str, List[Dict]]) -> List[Dict]:
        """Find interesting connections between different domains."""
        connections = []
        categories = list(categorized.keys())
        
        if len(categories) < 2:
            return connections
        
        # Look for shared keywords between categories
        keyword_by_category = {}
        
        for cat, items in categorized.items():
            all_text = " ".join(
                f"{i.get('title', '')} {i.get('summary', '')}"
                for i in items
            ).lower()
            
            # Extract keywords
            words = re.findall(r'\b[a-z]{4,}\b', all_text)
            stopwords = {"the", "a", "an", "is", "are", "to", "of", "in", "for", "with", "that", "this"}
            keywords = [w for w in words if w not in stopwords]
            keyword_by_category[cat] = Counter(keywords)
        
        # Find shared keywords between pairs of categories
        for i, cat1 in enumerate(categories):
            for cat2 in categories[i+1:]:
                shared = set(keyword_by_category[cat1].keys()) & set(keyword_by_category[cat2].keys())
                
                # Filter to significant shared keywords
                significant_shared = [
                    kw for kw in shared
                    if keyword_by_category[cat1][kw] >= 2 or keyword_by_category[cat2][kw] >= 2
                ]
                
                if significant_shared:
                    connections.append({
                        "domain_1": cat1,
                        "domain_2": cat2,
                        "shared_concepts": significant_shared[:5],
                        "strength": len(significant_shared)
                    })
        
        return sorted(connections, key=lambda x: x["strength"], reverse=True)[:10]
    
    async def _generate_dreams(self, connections: List[Dict], items: List[Dict]) -> List[Dream]:
        """Generate dream insights from connections."""
        dreams = []
        
        for i, conn in enumerate(connections[:self.max_dreams_per_cycle]):
            # Find items that contain shared concepts
            source_items = []
            for item in items:
                text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
                if any(concept in text for concept in conn["shared_concepts"]):
                    source_items.append(item.get("id", "unknown"))
                    if len(source_items) >= 5:
                        break
            
            # Generate dream based on connection type
            dream_type = self._determine_dream_type(conn)
            insight = self._generate_insight(conn, dream_type)
            
            dream = Dream(
                id=f"dream_{self.cycle_count}_{i}",
                title=f"Connection: {conn['domain_1']} ↔ {conn['domain_2']}",
                insight=insight,
                source_items=source_items,
                connections=[(conn["domain_1"], conn["domain_2"])],
                dream_type=dream_type,
                confidence=min(0.9, 0.3 + conn["strength"] * 0.1),
                created_at=datetime.now(timezone.utc),
                categories=[conn["domain_1"], conn["domain_2"]]
            )
            dreams.append(dream)
        
        return dreams
    
    def _determine_dream_type(self, connection: Dict) -> str:
        """Determine what type of dream to generate."""
        strength = connection.get("strength", 0)
        
        if strength >= 5:
            return "pattern"  # Strong recurring pattern
        elif strength >= 3:
            return "synthesis"  # Meaningful synthesis
        elif strength >= 2:
            return "association"  # Interesting association
        else:
            return "question"  # Worth exploring
    
    def _generate_insight(self, connection: Dict, dream_type: str) -> str:
        """Generate an insight description based on the connection."""
        d1, d2 = connection["domain_1"], connection["domain_2"]
        concepts = connection["shared_concepts"][:3]
        concepts_str = ", ".join(concepts)
        
        templates = {
            "pattern": f"Strong pattern detected: {d1} and {d2} share significant overlap around [{concepts_str}]. This suggests a fundamental connection worth investigating.",
            "synthesis": f"Synthesis opportunity: Concepts from {d1} ({concepts_str}) appear relevant to {d2}. Consider how learnings transfer between domains.",
            "association": f"Interesting association: {d1} and {d2} both discuss [{concepts_str}]. These connections may reveal hidden relationships.",
            "question": f"Open question: Why do {d1} and {d2} both reference [{concepts_str}]? Worth exploring the underlying connection."
        }
        
        return templates.get(dream_type, templates["question"])
    
    def _identify_items_to_cleanup(self, items: List[Dict]) -> int:
        """Identify items that should be cleaned up."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.cleanup_age_days)
        cleanup_count = 0
        
        for item in items:
            timestamp = item.get("timestamp")
            relevance = item.get("relevance_score", 0)
            
            # Items to cleanup: old AND low relevance
            if timestamp and relevance < self.min_relevance_to_keep:
                try:
                    item_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if item_date < cutoff_date:
                        cleanup_count += 1
                except:
                    pass
        
        return cleanup_count
    
    def get_recent_dreams(self, limit: int = 10) -> List[Dream]:
        """Get most recent dreams."""
        return self.dreams[-limit:]
    
    def get_dreams_by_category(self, category: str) -> List[Dream]:
        """Get dreams related to a specific category."""
        return [d for d in self.dreams if category in d.categories]
    
    def get_high_confidence_dreams(self, min_confidence: float = 0.7) -> List[Dream]:
        """Get dreams with high confidence scores."""
        return [d for d in self.dreams if d.confidence >= min_confidence]
    
    async def dream_on_demand(self, focus_categories: List[str], items: List[Dict]) -> List[Dream]:
        """
        Run a focused dreaming session on specific categories.
        
        Useful for exploring specific domains without running a full cycle.
        """
        # Filter items to focus categories
        focused_items = [
            i for i in items
            if i.get("category") in focus_categories
        ]
        
        if len(focused_items) < 5:
            return []
        
        categorized = self._categorize_items(focused_items)
        connections = self._find_cross_domain_connections(categorized)
        dreams = await self._generate_dreams(connections, focused_items)
        
        return dreams


# Singleton instance
_dreaming_engine: Optional[DreamingEngine] = None


def get_dreaming_engine() -> DreamingEngine:
    """Get or create the singleton dreaming engine."""
    global _dreaming_engine
    if _dreaming_engine is None:
        _dreaming_engine = DreamingEngine()
    return _dreaming_engine


async def run_nightly_dream_cycle(intelligence_items: List[Dict]) -> DreamCycleReport:
    """
    Run the nightly dream cycle.
    
    Called by scheduler at configured time (default: 3am).
    """
    engine = get_dreaming_engine()
    return await engine.dream_cycle(intelligence_items)
















