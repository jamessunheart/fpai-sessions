import json
import logging
import httpx
from pathlib import Path
from typing import Dict, Any, List
from .config import settings

logger = logging.getLogger("StateMonitor")

class StateMonitor:
    """
    Continuously monitors system state (SSOT, Health, Revenue).
    Builds the 'World Model' for the intelligence engine.
    """
    
    def __init__(self):
        self.ssot_path = settings.ssot_path
        self.world_model: Dict[str, Any] = {
            "services": {},
            "sessions": {},
            "revenue": {},
            "gaps": []
        }

    async def update(self) -> Dict[str, Any]:
        """Update the world model with fresh data."""
        logger.info("🔄 Refreshing World Model...")
        
        # 1. Load SSOT
        await self._load_ssot()
        
        # 2. Check Service Health
        await self._check_services_health()
        
        # 3. Load Revenue Data (Mock for now, or read from file)
        self._load_revenue_data()
        
        return self.world_model

    async def _load_ssot(self):
        try:
            if self.ssot_path.exists():
                with open(self.ssot_path, 'r') as f:
                    data = json.load(f)
                    self.world_model["ssot"] = data
                    self.world_model["sessions"] = data.get("claude_sessions", {})
            else:
                logger.warning(f"SSOT not found at {self.ssot_path}")
        except Exception as e:
            logger.error(f"Failed to load SSOT: {e}")

    async def _check_services_health(self):
        """Ping known services."""
        services = self.world_model.get("ssot", {}).get("services", {}).get("services", [])
        
        async with httpx.AsyncClient(timeout=2.0) as client:
            for service in services:
                url = service.get("url_local")
                name = service.get("name")
                if not url:
                    continue
                    
                try:
                    resp = await client.get(f"{url}/health")
                    status = "healthy" if resp.status_code == 200 else "degraded"
                except:
                    status = "down"
                
                self.world_model["services"][name] = status

    def _load_revenue_data(self):
        # Placeholder for revenue data logic
        # In real impl, read from docs/coordination/revenue/current.json
        self.world_model["revenue"] = {"mrr": 0, "growth": 0}

