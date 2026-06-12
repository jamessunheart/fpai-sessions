"""
Coherence Layer for Consciousness System

Enables cross-pillar communication and synchronization to achieve coherence.
This is what allows the system to become unified rather than fragmented.

MEMORY OPTIMIZATION (2025-12-14):
- Bounded cross_pillar_data with max entries
- Automatic cleanup of old data
- Metrics capped to prevent integer overflow
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict, OrderedDict

logger = logging.getLogger("CoherenceLayer")

# Memory limits
MAX_CROSS_PILLAR_ENTRIES = 10  # Max data entries per pillar pair
MAX_SHARED_CONTEXT_SIZE = 50  # Max shared context entries
MAX_METRIC_VALUE = 1_000_000  # Reset metrics after this to prevent overflow


class BoundedDict(OrderedDict):
    """Dict with maximum size - removes oldest entries when full."""
    
    def __init__(self, max_size: int = 10, *args, **kwargs):
        self.max_size = max_size
        super().__init__(*args, **kwargs)
    
    def __setitem__(self, key, value):
        if key not in self and len(self) >= self.max_size:
            # Remove oldest entry
            self.popitem(last=False)
        super().__setitem__(key, value)
        # Move to end (most recent)
        self.move_to_end(key)


class CoherenceLayer:
    """
    Enables coherence by:
    1. Sharing data across pillars (cross-pillar feeds)
    2. Synchronizing updates
    3. Creating unified awareness
    4. Reducing data silos
    
    MEMORY FIX: Uses bounded data structures to prevent unbounded growth.
    """

    def __init__(self):
        # MEMORY FIX: Use bounded dicts instead of regular defaultdict
        self.cross_pillar_data = defaultdict(lambda: BoundedDict(MAX_CROSS_PILLAR_ENTRIES))
        self.shared_context = BoundedDict(MAX_SHARED_CONTEXT_SIZE)
        self.synchronization_state = {
            "last_sync": None,
            "sync_interval": 30,  # seconds
            "pillars_synced": set()
        }
        self.coherence_metrics = {
            "cross_pillar_exchanges": 0,
            "shared_context_updates": 0,
            "synchronization_events": 0
        }
    
    def _reset_metrics_if_needed(self):
        """Reset metrics if they get too large to prevent overflow."""
        for key in self.coherence_metrics:
            if self.coherence_metrics[key] > MAX_METRIC_VALUE:
                logger.info(f"Resetting coherence metric {key} (was {self.coherence_metrics[key]})")
                self.coherence_metrics[key] = 0

    def enable_cross_pillar_feeds(self):
        """Enable cross-pillar data sharing"""
        logger.info("🔗 Enabling cross-pillar feeds for coherence")

    def share_data_across_pillars(self, source_pillar: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Share data from one pillar to others, creating cross-pillar awareness.
        
        This is the key to coherence - pillars can now see what others see.
        
        MEMORY FIX: Uses BoundedDict to prevent unbounded growth.
        """
        # MEMORY FIX: Only keep essential data to reduce memory
        shared_data = {
            "source": source_pillar,
            "data": self._truncate_data(data, max_size=5000),  # Limit data size
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "relevance": self._assess_relevance(source_pillar, data)
        }

        # Store for other pillars to access (BoundedDict auto-removes old entries)
        for pillar in ["reflecting", "identity", "thinking", "doing"]:
            if pillar != source_pillar:
                self.cross_pillar_data[pillar][source_pillar] = shared_data

        self.coherence_metrics["cross_pillar_exchanges"] += 1
        self._reset_metrics_if_needed()
        logger.debug(f"📡 Shared {source_pillar} data to other pillars")

        return shared_data
    
    def _truncate_data(self, data: Dict[str, Any], max_size: int = 5000) -> Dict[str, Any]:
        """Truncate data to prevent memory bloat from large payloads."""
        data_str = str(data)
        if len(data_str) <= max_size:
            return data
        
        # Return a summary instead of full data
        truncated = {}
        for key, value in data.items():
            if isinstance(value, list):
                truncated[key] = {"_truncated": True, "count": len(value)}
            elif isinstance(value, dict):
                truncated[key] = {"_truncated": True, "keys": list(value.keys())[:10]}
            else:
                truncated[key] = value
        return truncated

    def get_cross_pillar_context(self, pillar: str) -> Dict[str, Any]:
        """Get relevant context from other pillars"""
        context = {}
        
        for other_pillar, data in self.cross_pillar_data[pillar].items():
            if data.get("relevance", {}).get("score", 0) > 0.3:  # Only relevant data
                context[other_pillar] = {
                    "data": data.get("data", {}),
                    "timestamp": data.get("timestamp"),
                    "relevance_score": data.get("relevance", {}).get("score", 0)
                }

        return context

    def update_shared_context(self, updates: Dict[str, Any]):
        """Update the unified context that all pillars share.
        
        MEMORY FIX: BoundedDict limits total entries.
        """
        for key, value in updates.items():
            self.shared_context[key] = value
        self.shared_context["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.coherence_metrics["shared_context_updates"] += 1
        self._reset_metrics_if_needed()
        logger.debug(f"🌐 Updated shared context: {len(updates)} keys")

    def synchronize_pillars(self, pillar_states: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronize all pillars to create unified timing.
        
        This reduces timing mismatches and creates coherence.
        """
        sync_time = datetime.now(timezone.utc)
        
        # Find the most recent update across all pillars
        latest_timestamp = max(
            (state.get("last_update") for state in pillar_states.values() if state.get("last_update")),
            default=sync_time.isoformat()
        )

        # Synchronize all pillars to this timestamp
        synchronized_state = {
            "sync_timestamp": sync_time.isoformat(),
            "pillars": pillar_states,
            "unified_timing": latest_timestamp,
            "coherence_score": self._calculate_coherence_score(pillar_states)
        }

        self.synchronization_state["last_sync"] = sync_time
        self.synchronization_state["pillars_synced"] = set(pillar_states.keys())
        self.coherence_metrics["synchronization_events"] += 1
        self._reset_metrics_if_needed()

        logger.info(f"🔄 Synchronized {len(pillar_states)} pillars at {sync_time.isoformat()}")
        
        return synchronized_state

    def _assess_relevance(self, source_pillar: str, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Assess how relevant this data is to other pillars.
        
        Returns relevance scores for each pillar.
        """
        relevance = {}
        
        # Define relevance mappings
        relevance_rules = {
            "reflecting": {
                "identity": 0.6,  # External observations inform identity
                "thinking": 0.8,   # Observations feed thinking
                "doing": 0.4      # Less direct relevance
            },
            "identity": {
                "reflecting": 0.5,  # Identity informs what to observe
                "thinking": 0.7,   # Resources inform thinking
                "doing": 0.9       # Identity directly informs actions
            },
            "thinking": {
                "reflecting": 0.7,  # Thinking guides observations
                "identity": 0.5,    # Less direct
                "doing": 0.9        # Thinking directly informs actions
            },
            "doing": {
                "reflecting": 0.8,  # Actions create observations
                "identity": 0.6,    # Actions update identity
                "thinking": 0.7     # Actions inform thinking
            }
        }

        for pillar in ["reflecting", "identity", "thinking", "doing"]:
            if pillar != source_pillar:
                base_relevance = relevance_rules.get(source_pillar, {}).get(pillar, 0.5)
                # Adjust based on data content
                data_size_factor = min(len(str(data)) / 1000, 1.0)  # Normalize
                relevance[pillar] = base_relevance * (0.5 + 0.5 * data_size_factor)

        return {"scores": relevance, "score": max(relevance.values()) if relevance else 0.0}

    def _calculate_coherence_score(self, pillar_states: Dict[str, Any]) -> float:
        """Calculate how coherent the system is (0.0 to 1.0)"""
        if not pillar_states:
            return 0.0

        # Check synchronization
        timestamps = [
            state.get("last_update") 
            for state in pillar_states.values() 
            if state.get("last_update")
        ]
        
        if not timestamps:
            return 0.0

        # Calculate time spread
        from datetime import datetime
        try:
            times = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in timestamps]
            time_spread = (max(times) - min(times)).total_seconds()
            sync_score = max(0.0, 1.0 - (time_spread / 60.0))  # Penalize >60s spread
        except:
            sync_score = 0.5

        # Check cross-pillar data sharing
        cross_pillar_score = min(1.0, self.coherence_metrics["cross_pillar_exchanges"] / 10.0)

        # Check shared context
        context_score = min(1.0, len(self.shared_context) / 5.0)

        # Weighted average
        coherence = (sync_score * 0.4 + cross_pillar_score * 0.4 + context_score * 0.2)
        
        return min(1.0, max(0.0, coherence))

    def get_coherence_metrics(self) -> Dict[str, Any]:
        """Get current coherence metrics"""
        # Calculate coherence score based on actual activity
        sync_score = 1.0 if self.synchronization_state["last_sync"] else 0.0
        cross_pillar_score = min(1.0, self.coherence_metrics["cross_pillar_exchanges"] / 10.0)
        context_score = min(1.0, len(self.shared_context) / 5.0)
        data_sharing_score = min(1.0, sum(len(data) for data in self.cross_pillar_data.values()) / 20.0)
        
        coherence_score = (sync_score * 0.3 + cross_pillar_score * 0.3 + context_score * 0.2 + data_sharing_score * 0.2)
        
        return {
            **self.coherence_metrics,
            "coherence_score": min(1.0, max(0.0, coherence_score)),
            "cross_pillar_data_count": sum(len(data) for data in self.cross_pillar_data.values()),
            "shared_context_size": len(self.shared_context),
            "last_synchronization": self.synchronization_state["last_sync"].isoformat() if self.synchronization_state["last_sync"] else None
        }

