"""
🧠 Mem0 Memory Layer for Data Service
======================================

Persistent memory for:
- Synthesized insights (permanent wisdom)
- Discovered patterns (learnings)
- System context (decisions, outcomes)

Uses Mem0.ai for long-term memory that persists across sessions.
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("data_memory")

# Memory entity types
ENTITY_INSIGHTS = "fpai_insights"  # Synthesized intelligence
ENTITY_PATTERNS = "fpai_patterns"  # Discovered patterns
ENTITY_LEARNINGS = "fpai_learnings"  # System learnings
ENTITY_CONTEXT = "fpai_context"  # Current state/context


class Mem0Memory:
    """
    Mem0.ai integration for persistent memory.
    
    Stores:
    - Insights: High-value synthesized intelligence
    - Patterns: Discovered trends and correlations
    - Learnings: What worked, what didn't
    - Context: System state snapshots
    """
    
    # Note: Use trailing slashes to avoid 301 redirects that break POST requests
    BASE_URL = "https://api.mem0.ai/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            self.headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }
            logger.info("🧠 Mem0 memory layer initialized")
        else:
            self.headers = {}
            logger.warning("⚠️ MEM0_API_KEY not set - persistent memory disabled")
    
    async def _post(self, endpoint: str, data: Dict, memory_type: str = "unknown") -> Optional[Dict]:
        """Make async POST request to Mem0 API"""
        if not self.enabled:
            return None
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # Ensure trailing slash to avoid 301 redirects that break POST
                url = f"{self.BASE_URL}/{endpoint}"
                if not url.endswith('/'):
                    url += '/'
                
                resp = await client.post(
                    url,
                    headers=self.headers,
                    json=data
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                if resp.status_code == 200:
                    result = resp.json()
                    # Log the response for debugging
                    logger.info(f"📝 Mem0 store response: {result}")
                    
                    # Track successful store
                    tracker = get_tracker()
                    tracker.record_store(memory_type, latency_ms, success=True)
                    return result
                else:
                    logger.error(f"Mem0 API error: {resp.status_code} - {resp.text}")
                    tracker = get_tracker()
                    tracker.record_store(memory_type, latency_ms, success=False)
                    return None
        except Exception as e:
            logger.error(f"Mem0 request failed: {e}")
            latency_ms = (time.time() - start_time) * 1000
            tracker = get_tracker()
            tracker.record_store(memory_type, latency_ms, success=False)
            return None
    
    async def _search(self, query: str, user_id: str, limit: int = 10) -> List[Dict]:
        """Search memories"""
        if not self.enabled:
            return []
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/memories/search/",
                    headers=self.headers,
                    json={
                        "query": query,
                        "user_id": user_id,
                        "limit": limit
                    }
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Mem0 API returns either a list directly or a dict with "results"
                    if isinstance(data, list):
                        results = data
                    else:
                        results = data.get("results", data.get("memories", []))
                    
                    # Track search performance
                    tracker = get_tracker()
                    avg_relevance = None
                    if results and isinstance(results[0], dict) and results[0].get("score"):
                        avg_relevance = sum(r.get("score", 0) for r in results) / len(results)
                    tracker.record_search(query, len(results), latency_ms, avg_relevance)
                    
                    return results
                return []
        except Exception as e:
            logger.error(f"Mem0 search failed: {e}")
            latency_ms = (time.time() - start_time) * 1000
            tracker = get_tracker()
            tracker.record_search(query, 0, latency_ms, None)
            return []
    
    # ─────────────────────────────────────────────────────────────────────────────
    # STORE METHODS
    # ─────────────────────────────────────────────────────────────────────────────
    
    async def store_insight(
        self,
        title: str,
        content: str,
        category: str,
        relevance: float,
        sources: List[str] = None
    ) -> Optional[Dict]:
        """
        Store a synthesized insight in long-term memory.
        
        These are high-value pieces of wisdom that should persist.
        """
        # Simple, direct message for better memory extraction
        message = f"{title}: {content} (Category: {category}, Sources: {', '.join(sources or ['unknown'])})"
        
        result = await self._post("memories", {
            "messages": [{"role": "user", "content": message}],
            "user_id": ENTITY_INSIGHTS,
            "metadata": {
                "type": "insight",
                "category": category,
                "relevance": relevance,
                "title": title
            }
        }, memory_type="insight")
        
        if result:
            logger.info(f"💡 Stored insight: {title}")
        
        return result
    
    async def store_pattern(
        self,
        pattern_type: str,
        description: str,
        significance: str,
        data: Dict = None
    ) -> Optional[Dict]:
        """
        Store a discovered pattern.
        
        Patterns are trends, correlations, or recurring themes.
        """
        message = f"""PATTERN DISCOVERED: {pattern_type}

Significance: {significance}

{description}

Data: {data or {}}

Discovered: {datetime.now(timezone.utc).isoformat()}
"""
        
        result = await self._post("memories", {
            "messages": [{"role": "assistant", "content": message}],
            "user_id": ENTITY_PATTERNS,
            "metadata": {
                "type": "pattern",
                "pattern_type": pattern_type,
                "significance": significance,
                "timestamp": time.time()
            }
        }, memory_type="pattern")
        
        if result:
            logger.info(f"🔍 Stored pattern: {pattern_type}")
        
        return result
    
    async def store_learning(
        self,
        context: str,
        action: str,
        outcome: str,
        lesson: str
    ) -> Optional[Dict]:
        """
        Store a learning (what worked, what didn't).
        
        Format: Context → Action → Outcome → Lesson
        Uses user message format for better memory extraction.
        """
        # Simple, direct message that Mem0 can easily extract as a memory
        message = f"{lesson}. Context: {context}. Action taken: {action}. Outcome: {outcome}."
        
        result = await self._post("memories", {
            "messages": [{"role": "user", "content": message}],
            "user_id": ENTITY_LEARNINGS,
            "metadata": {
                "type": "learning",
                "context": context,
                "outcome": "positive" if "success" in outcome.lower() else "negative"
            }
        }, memory_type="learning")
        
        if result:
            logger.info(f"📚 Stored learning: {lesson[:50]}...")
        
        return result
    
    async def store_context(
        self,
        context_type: str,
        state: Dict
    ) -> Optional[Dict]:
        """
        Store system context/state snapshot.
        
        Useful for tracking decisions and their context.
        """
        import json
        
        message = f"""CONTEXT SNAPSHOT: {context_type}

{json.dumps(state, indent=2)}

Captured: {datetime.now(timezone.utc).isoformat()}
"""
        
        result = await self._post("memories", {
            "messages": [{"role": "assistant", "content": message}],
            "user_id": ENTITY_CONTEXT,
            "metadata": {
                "type": "context",
                "context_type": context_type,
                "timestamp": time.time()
            }
        }, memory_type="context")
        
        return result
    
    # ─────────────────────────────────────────────────────────────────────────────
    # RETRIEVE METHODS
    # ─────────────────────────────────────────────────────────────────────────────
    
    async def search_insights(self, query: str, limit: int = 5) -> List[Dict]:
        """Search past insights"""
        return await self._search(query, ENTITY_INSIGHTS, limit)
    
    async def search_patterns(self, query: str, limit: int = 5) -> List[Dict]:
        """Search discovered patterns"""
        return await self._search(query, ENTITY_PATTERNS, limit)
    
    async def search_learnings(self, query: str, limit: int = 5) -> List[Dict]:
        """Search learnings"""
        return await self._search(query, ENTITY_LEARNINGS, limit)
    
    async def get_relevant_context(self, query: str) -> Dict:
        """
        Get relevant context from all memory types.
        
        Useful for providing AI Brain with historical context.
        """
        insights = await self.search_insights(query, 3)
        patterns = await self.search_patterns(query, 3)
        learnings = await self.search_learnings(query, 3)
        
        return {
            "insights": insights,
            "patterns": patterns,
            "learnings": learnings,
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # ─────────────────────────────────────────────────────────────────────────────
    # SYNTHESIS HELPERS
    # ─────────────────────────────────────────────────────────────────────────────
    
    async def store_daily_digest(self, digest: Dict) -> Optional[Dict]:
        """Store a daily intelligence digest as insight"""
        return await self.store_insight(
            title=f"Daily Intelligence Digest - {datetime.now().strftime('%Y-%m-%d')}",
            content=f"""
Top Stories:
{chr(10).join(['- ' + item.get('title', '') for item in digest.get('top_items', [])[:5]])}

Patterns Detected: {len(digest.get('patterns', []))}
Items Analyzed: {digest.get('total_items', 0)}
""",
            category="daily_digest",
            relevance=0.9,
            sources=["data_service"]
        )
    
    async def store_market_observation(
        self,
        symbol: str,
        observation: str,
        data: Dict
    ) -> Optional[Dict]:
        """Store a market observation"""
        return await self.store_insight(
            title=f"{symbol} Market Observation",
            content=observation,
            category="markets",
            relevance=0.8,
            sources=["coinglass", "whaletrack"]
        )


# ─────────────────────────────────────────────────────────────────────────────
# LEARNING TRACKER - Study Mem0's behavior to reproduce/enhance later
# ─────────────────────────────────────────────────────────────────────────────

class MemoryExperimentTracker:
    """
    Track Mem0 behavior to learn how to build something better.
    
    We're studying:
    1. What makes memories retrievable?
    2. How does consolidation work?
    3. What's the latency/performance profile?
    4. How does semantic search compare to ChromaDB?
    """
    
    def __init__(self):
        self.experiments: List[Dict] = []
        self.metrics = {
            "stores": 0,
            "searches": 0,
            "avg_store_latency_ms": 0,
            "avg_search_latency_ms": 0,
            "search_relevance_scores": [],
            "consolidation_events": 0
        }
        self.observations: List[str] = []
    
    def record_store(self, memory_type: str, latency_ms: float, success: bool):
        """Record a store operation"""
        self.experiments.append({
            "operation": "store",
            "type": memory_type,
            "latency_ms": latency_ms,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        if success:
            self.metrics["stores"] += 1
            # Rolling average
            n = self.metrics["stores"]
            self.metrics["avg_store_latency_ms"] = (
                (self.metrics["avg_store_latency_ms"] * (n - 1) + latency_ms) / n
            )
    
    def record_search(self, query: str, num_results: int, latency_ms: float, relevance_score: float = None):
        """Record a search operation"""
        self.experiments.append({
            "operation": "search",
            "query": query[:50],
            "num_results": num_results,
            "latency_ms": latency_ms,
            "relevance_score": relevance_score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        self.metrics["searches"] += 1
        n = self.metrics["searches"]
        self.metrics["avg_search_latency_ms"] = (
            (self.metrics["avg_search_latency_ms"] * (n - 1) + latency_ms) / n
        )
        
        if relevance_score:
            self.metrics["search_relevance_scores"].append(relevance_score)
    
    def add_observation(self, observation: str):
        """Record an observation about Mem0's behavior"""
        self.observations.append({
            "observation": observation,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"🔬 Mem0 Observation: {observation}")
    
    def get_report(self) -> Dict:
        """Get learning report"""
        return {
            "total_operations": len(self.experiments),
            "metrics": self.metrics,
            "avg_relevance": (
                sum(self.metrics["search_relevance_scores"]) / 
                len(self.metrics["search_relevance_scores"])
                if self.metrics["search_relevance_scores"] else 0
            ),
            "observations": self.observations[-10:],  # Last 10
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on observations"""
        recs = []
        
        if self.metrics["avg_store_latency_ms"] > 500:
            recs.append("High store latency - consider batching stores")
        
        if self.metrics["avg_search_latency_ms"] > 300:
            recs.append("Search latency acceptable but could cache frequent queries")
        
        if self.metrics["searches"] > 100 and self.metrics["stores"] < 10:
            recs.append("Heavy search usage - memory layer is valuable, consider local cache")
        
        return recs


# Singleton instances
_memory: Optional[Mem0Memory] = None
_tracker: Optional[MemoryExperimentTracker] = None


def get_memory() -> Mem0Memory:
    """Get singleton Mem0 memory instance"""
    global _memory
    if _memory is None:
        _memory = Mem0Memory()
    return _memory


def get_tracker() -> MemoryExperimentTracker:
    """Get experiment tracker"""
    global _tracker
    if _tracker is None:
        _tracker = MemoryExperimentTracker()
    return _tracker

