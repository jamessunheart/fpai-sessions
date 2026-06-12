"""
System Aggregator
=================
Pulls data from all subsystems to build a unified view.
"""

import asyncio
import httpx
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aggregator")

# Service endpoints
SERVICES = {
    "observatory": "http://localhost:8113",
    "thinking": "http://localhost:8101",
    "intelligence": "http://localhost:8111",
    "scaling": "http://localhost:8115",
    "workers": "http://localhost:8114",
    "genesis": "http://198.54.123.234:8150",
    "team_hub": "http://198.54.123.234:8355",
}

THINKING_DB = "/opt/fpai/ai-brain/v2/thinking_v2.db"


class SystemAggregator:
    """Aggregates data from all subsystems."""
    
    def __init__(self):
        self.cache = {}
        self.last_fetch = {}
        self.cache_ttl = 3  # seconds
    
    async def _fetch_json(self, url: str, timeout: float = 5.0) -> Optional[Dict]:
        """Fetch JSON from a URL with caching."""
        now = datetime.now().timestamp()
        
        # Check cache
        if url in self.cache and url in self.last_fetch:
            if now - self.last_fetch[url] < self.cache_ttl:
                return self.cache[url]
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    self.cache[url] = data
                    self.last_fetch[url] = now
                    return data
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
        
        return self.cache.get(url)  # Return stale cache if available
    
    async def get_thinking_status(self) -> Dict[str, Any]:
        """Get thinking system status."""
        data = await self._fetch_json(f"{SERVICES['thinking']}/api/thinking/status")
        if data:
            return {
                "status": data.get("status", "unknown"),
                "cycles_today": data.get("cycles_today", 0),
                "insights_today": data.get("insights_today", 0),
                "pending_insights": data.get("pending_insights", 0),
                "last_cycle": data.get("last_cycle"),
                "next_cycle": data.get("next_cycle_in", "~15m"),
            }
        return {"status": "offline", "cycles_today": 0, "insights_today": 0, "pending_insights": 0}
    
    async def get_builder_status(self) -> Dict[str, Any]:
        """Get builder/hive status."""
        data = await self._fetch_json(f"{SERVICES['observatory']}/api/status")
        if data:
            return {
                "phase": data.get("current_phase", "unknown"),
                "proposals_pending": data.get("proposals_pending", 0),
                "proposals_building": data.get("proposals_building", 0),
                "queue_depth": data.get("build_queue_depth", 0),
                "builds_running": data.get("builds_running", 0),
            }
        return {"phase": "offline", "proposals_pending": 0, "proposals_building": 0, "queue_depth": 0, "builds_running": 0}
    
    async def get_gpu_status(self) -> Dict[str, Any]:
        """Get GPU infrastructure status."""
        data = await self._fetch_json(f"{SERVICES['scaling']}/api/all-providers")
        if data:
            instances = data.get("instances", [])
            running = [i for i in instances if i.get("status") == "running"]
            return {
                "total_pods": len(instances),
                "running_pods": len(running),
                "pods": instances,
                "hourly_cost": data.get("total_hourly_cost", 0),
                "daily_estimate": data.get("daily_estimate", 0),
                "monthly_estimate": data.get("monthly_estimate", 0),
            }
        return {"total_pods": 0, "running_pods": 0, "pods": [], "hourly_cost": 0, "daily_estimate": 0}
    
    async def get_service_health(self) -> Dict[str, str]:
        """Check health of all services."""
        health = {}
        
        checks = [
            ("genesis", f"{SERVICES['genesis']}/health"),
            ("observatory", f"{SERVICES['observatory']}/health"),
            ("thinking", f"{SERVICES['thinking']}/api/thinking/status"),
            ("intelligence", f"{SERVICES['intelligence']}/health"),
            ("scaling", f"{SERVICES['scaling']}/health"),
            ("workers", f"{SERVICES['workers']}/health"),
        ]
        
        for name, url in checks:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(url)
                    health[name] = "online" if resp.status_code == 200 else "degraded"
            except:
                health[name] = "offline"
        
        return health
    
    async def get_recent_proposals(self, limit: int = 10) -> List[Dict]:
        """Get recent proposals from the builder."""
        data = await self._fetch_json(f"{SERVICES['observatory']}/api/proposals?limit={limit}")
        if data:
            return data.get("proposals", [])[:limit]
        return []
    
    async def get_escalations(self, limit: int = 10) -> List[Dict]:
        """Get pending escalations."""
        data = await self._fetch_json(f"{SERVICES['observatory']}/api/escalations?limit={limit}")
        if data:
            return data.get("escalations", [])[:limit]
        return []
    
    def get_recent_insights(self, limit: int = 10) -> List[Dict]:
        """Get recent insights from the database."""
        try:
            conn = sqlite3.connect(THINKING_DB)
            c = conn.cursor()
            c.execute("""
                SELECT id, category, content, priority, created_at 
                FROM insights 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            rows = c.fetchall()
            conn.close()
            
            return [
                {
                    "id": r[0],
                    "category": r[1],
                    "content": r[2][:200] if r[2] else "",
                    "priority": r[3],
                    "created_at": r[4]
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get insights: {e}")
            return []
    
    async def get_full_pulse(self) -> Dict[str, Any]:
        """Get complete system pulse."""
        # Fetch all data in parallel
        thinking, builder, gpu, health = await asyncio.gather(
            self.get_thinking_status(),
            self.get_builder_status(),
            self.get_gpu_status(),
            self.get_service_health(),
        )
        
        # Determine current focus
        if builder.get("builds_running", 0) > 0:
            focus = {
                "activity": "building",
                "description": f"Running {builder['builds_running']} builds",
                "subsystem": "builder"
            }
        elif thinking.get("status") == "active":
            focus = {
                "activity": "thinking",
                "description": f"Cycle in progress, {thinking['pending_insights']} insights pending",
                "subsystem": "thinking"
            }
        elif builder.get("queue_depth", 0) > 0:
            focus = {
                "activity": "queued",
                "description": f"{builder['queue_depth']} builds in queue",
                "subsystem": "builder"
            }
        else:
            focus = {
                "activity": "monitoring",
                "description": "System idle, observing",
                "subsystem": "observatory"
            }
        
        # Calculate health score
        online_count = sum(1 for s in health.values() if s == "online")
        health_score = (online_count / len(health)) * 100 if health else 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "focus": focus,
            "thinking": thinking,
            "builder": builder,
            "gpu": gpu,
            "health_score": round(health_score, 1),
            "services": health,
            "resources": {
                "gpu_pods_running": gpu.get("running_pods", 0),
                "gpu_hourly_cost": gpu.get("hourly_cost", 0),
                "gpu_daily_estimate": gpu.get("daily_estimate", 0),
                "active_builds": builder.get("builds_running", 0),
                "pending_proposals": builder.get("proposals_pending", 0),
                "thinking_cycles_today": thinking.get("cycles_today", 0),
                "insights_pending": thinking.get("pending_insights", 0),
            }
        }


# Singleton
aggregator = SystemAggregator()





















