import asyncio
import httpx
import uuid
import psutil
from datetime import datetime, timezone
from .token_manager import token_manager
from ..config import settings

class HeartbeatService:
    def __init__(self):
        self.orchestrator_url = settings.orchestrator_url
        self.interval = 60
    
    @property
    def droplet_id(self):
        return settings.droplet_id
    
    def get_metrics(self):
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_mb": int(psutil.virtual_memory().used / 1024 / 1024),
            "requests_last_minute": 0,
            "errors_last_minute": 0
        }
    
    async def register_with_orchestrator(self):
        """Register droplet with Orchestrator if not registered"""
        token = token_manager.generate_token()
        payload = {
            "droplet_id": self.droplet_id,
            "name": settings.droplet_name,
            "endpoint": settings.droplet_url,
            "capabilities": ["udc_compliance", "health_monitoring"],
            "version": "1.0.0",
            "status": "active"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.orchestrator_url}/droplets/register",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code in [200, 201]:
                    print(f"[OK] Registered with Orchestrator")
                    return True
                else:
                    print(f"[WARN] Registration failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"[ERROR] Registration error: {e}")
                return False
    
    async def send_heartbeat(self):
        token = token_manager.generate_token()
        
        # Direct payload format (not UDC envelope)
        metrics = self.get_metrics()
        payload = {
            "status": "active",
            "cpu_percent": metrics["cpu_percent"],
            "memory_mb": metrics["memory_mb"],
            "requests_per_minute": metrics.get("requests_last_minute", 0),
            "errors_last_hour": metrics.get("errors_last_minute", 0)
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.orchestrator_url}/droplets/{self.droplet_id}/heartbeat",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 200:
                    print(f"[OK] Heartbeat sent")
                elif response.status_code == 404:
                    print(f"[INFO] Droplet not registered, attempting registration...")
                    if await self.register_with_orchestrator():
                        # Retry heartbeat after registration
                        await self.send_heartbeat()
                else:
                    print(f"[FAIL] Heartbeat failed: {response.status_code}")
            except Exception as e:
                print(f"[ERROR] Heartbeat error: {e}")
    
    async def start(self):
        print(f"Starting heartbeat service (every {self.interval}s)")
        while True:
            await self.send_heartbeat()
            await asyncio.sleep(self.interval)

heartbeat_service = HeartbeatService()
