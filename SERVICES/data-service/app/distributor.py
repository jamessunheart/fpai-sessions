"""
Data Distributor
================
Proactively pushes data to consumers.

"I don't wait to be asked. I feed intelligence before it needs me."
"""

import asyncio
import logging
import httpx
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger("data.distributor")

# SSOT routing defaults
STRATEGIC_INTEL_URL = os.getenv("STRATEGIC_INTEL_URL", "http://198.54.123.234:8500")
NERVE_CENTER_URL = os.getenv("NERVE_CENTER_URL", "http://198.54.123.234:8120")
WHALETRACK_URL = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8601")

# Consumer endpoints
CONSUMERS = {
    "strategic_intelligence": {
        "url": f"{STRATEGIC_INTEL_URL}/api/v1/signals",
        "priority": 1,
        "filter": lambda item: item.get("relevance_score", 0) >= 0.7
    },
    "nerve_center": {
        "url": f"{NERVE_CENTER_URL}/api/event",
        "priority": 2,
        "filter": lambda item: True  # All items
    },
    "whaletrack": {
        "url": f"{WHALETRACK_URL}/api/activity/event",
        "priority": 1,
        "filter": lambda item: item.get("category") == "markets"
    }
}


class DataDistributor:
    """
    Pushes data to consumers proactively.
    """
    
    def __init__(self):
        self.push_queue = asyncio.Queue()
        self.push_history: List[Dict] = []
        self.consumer_status: Dict[str, str] = {}
        
    async def push_item(self, item: Dict, consumers: List[str] = None) -> Dict:
        """Push a single item to specified consumers"""
        if consumers is None:
            consumers = list(CONSUMERS.keys())
        
        results = {}
        
        for consumer_name in consumers:
            consumer = CONSUMERS.get(consumer_name)
            if not consumer:
                continue
            
            # Check filter
            if not consumer["filter"](item):
                continue
            
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    payload = self.format_for_consumer(consumer_name, item)
                    resp = await client.post(consumer["url"], json=payload)
                    
                    results[consumer_name] = {
                        "status": "success" if resp.status_code in [200, 201, 202] else "failed",
                        "status_code": resp.status_code
                    }
                    
                    self.consumer_status[consumer_name] = "healthy" if resp.status_code in [200,201,202] else "degraded"
                    
            except Exception as e:
                results[consumer_name] = {
                    "status": "error",
                    "error": str(e)
                }
                self.consumer_status[consumer_name] = "unhealthy"
        
        self.push_history.append({
            "item_id": item.get("id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results
        })
        
        return results
    
    async def push_batch(self, items: List[Dict], consumers: List[str] = None) -> Dict:
        """Push multiple items efficiently"""
        if consumers is None:
            consumers = list(CONSUMERS.keys())
        
        results = {consumer: {"sent": 0, "failed": 0} for consumer in consumers}
        
        for consumer_name in consumers:
            consumer = CONSUMERS.get(consumer_name)
            if not consumer:
                continue
            
            # Filter items for this consumer
            filtered = [item for item in items if consumer["filter"](item)]
            
            if not filtered:
                continue
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    payload = self.format_batch_for_consumer(consumer_name, filtered)
                    resp = await client.post(consumer["url"], json=payload)
                    
                    if resp.status_code in [200, 201, 202]:
                        results[consumer_name]["sent"] = len(filtered)
                        self.consumer_status[consumer_name] = "healthy"
                    else:
                        results[consumer_name]["failed"] = len(filtered)
                        # treat 404 as degraded, not error
                        if resp.status_code == 404:
                            self.consumer_status[consumer_name] = "degraded"
                        else:
                            self.consumer_status[consumer_name] = "unhealthy"
                    
            except Exception as e:
                results[consumer_name]["failed"] = len(filtered)
                results[consumer_name]["error"] = str(e)
                self.consumer_status[consumer_name] = "unhealthy"
        
        return results
    
    async def push_alert(self, alert: Dict) -> Dict:
        """Push high-priority alert to all consumers"""
        results = {}
        
        for consumer_name, consumer in CONSUMERS.items():
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    payload = {
                        "type": "data.alert",
                        "priority": "high",
                        "alert": alert,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    resp = await client.post(consumer["url"], json=payload)
                    
                    results[consumer_name] = resp.status_code in [200, 201, 202]
                    
            except Exception as e:
                results[consumer_name] = False
                logger.error(f"Alert push to {consumer_name} failed: {e}")
        
        return results
    
    async def push_pattern(self, pattern: Dict) -> Dict:
        """Push detected pattern to relevant consumers"""
        # Patterns go to Strategic Intelligence primarily
        results = {}
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{STRATEGIC_INTEL_URL}/api/v1/patterns",
                    json={
                        "source": "data_service",
                        "pattern": pattern,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                results["strategic_intelligence"] = resp.status_code in [200, 201, 202]
        except:
            results["strategic_intelligence"] = False
        
        # Also notify Nerve Center
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{NERVE_CENTER_URL}/api/event",
                    json={
                        "type": "data.pattern.detected",
                        "source": "data_service",
                        "data": pattern
                    }
                )
                results["nerve_center"] = True
        except:
            results["nerve_center"] = False
        
        return results
    
    async def push_synthesis(self, synthesis: Dict) -> Dict:
        """Push daily synthesis to consumers"""
        results = {}
        
        # Strategic Intelligence gets full synthesis
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{STRATEGIC_INTEL_URL}/api/v1/synthesis",
                    json={
                        "source": "data_service",
                        "synthesis": synthesis,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                results["strategic_intelligence"] = resp.status_code in [200, 201, 202]
        except:
            results["strategic_intelligence"] = False
        
        # Nerve Center gets summary
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{NERVE_CENTER_URL}/api/event",
                    json={
                        "type": "data.synthesis.complete",
                        "source": "data_service",
                        "data": {
                            "date": synthesis.get("date"),
                            "items_analyzed": synthesis.get("items_analyzed"),
                            "patterns_detected": synthesis.get("patterns_detected"),
                            "key_insights": synthesis.get("key_insights", [])[:3]
                        }
                    }
                )
                results["nerve_center"] = True
        except:
            results["nerve_center"] = False
        
        return results
    
    def format_for_consumer(self, consumer_name: str, item: Dict) -> Dict:
        """Format item for specific consumer"""
        if consumer_name == "strategic_intelligence":
            return {
                "source": "data_service",
                "signal": {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "category": item.get("category"),
                    "relevance": item.get("relevance_score"),
                    "sentiment": item.get("sentiment", 0),
                    "entities": item.get("entities", []),
                    "source_name": item.get("source"),
                    "url": item.get("source_url")
                }
            }
        elif consumer_name == "nerve_center":
            return {
                "type": "data.item.new",
                "source": "data_service",
                "data": {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "category": item.get("category"),
                    "relevance": item.get("relevance_score")
                }
            }
        elif consumer_name == "whaletrack":
            return {
                "type": "market_data",
                "source": "data_service",
                "data": item
            }
        else:
            return item
    
    def format_batch_for_consumer(self, consumer_name: str, items: List[Dict]) -> Dict:
        """Format batch for specific consumer"""
        if consumer_name == "strategic_intelligence":
            return {
                "source": "data_service",
                "signals": [
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "category": item.get("category"),
                        "relevance": item.get("relevance_score"),
                        "source_name": item.get("source")
                    }
                    for item in items
                ]
            }
        elif consumer_name == "nerve_center":
            return {
                "type": "data.batch",
                "source": "data_service",
                "count": len(items),
                "categories": list(set(item.get("category") for item in items))
            }
        else:
            return {"items": items}
    
    def get_status(self) -> Dict:
        """Get distributor status"""
        return {
            "consumers": self.consumer_status,
            "recent_pushes": len(self.push_history),
            "last_push": self.push_history[-1] if self.push_history else None
        }


# Singleton
distributor = DataDistributor()


async def push_to_all(items: List[Dict], patterns: List[Dict] = None, synthesis: Dict = None):
    """Push all data to consumers"""
    results = {}
    
    # Push items
    if items:
        results["items"] = await distributor.push_batch(items)
    
    # Push patterns
    if patterns:
        pattern_results = []
        for pattern in patterns:
            if pattern.get("significance", 0) >= 0.5:
                r = await distributor.push_pattern(pattern)
                pattern_results.append(r)
        results["patterns"] = pattern_results
    
    # Push synthesis
    if synthesis:
        results["synthesis"] = await distributor.push_synthesis(synthesis)
    
    return results

