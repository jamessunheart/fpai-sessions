import httpx
import asyncio
from typing import Dict, Any
from ..config import settings
from ..utils.logging import get_logger
from ..utils.metrics import metrics

log = get_logger(__name__)


class OrchestratorService:
    """Service for Orchestrator communication"""
    
    def __init__(self):
        self.base_url = settings.orchestrator_url
        self._heartbeat_task = None
    
    async def start_heartbeat(self):
        """Start heartbeat task"""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def stop_heartbeat(self):
        """Stop heartbeat task"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
    
    async def _heartbeat_loop(self):
        """Send heartbeat every 60 seconds"""
        while True:
            try:
                await self.send_heartbeat()
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Heartbeat failed: {str(e)}")
                await asyncio.sleep(60)
    
    async def send_heartbeat(self):
        """Send heartbeat to Orchestrator"""
        status_data = {
            "droplet_id": settings.droplet_id,
            "status": "active",
            "timestamp": metrics.get_current_timestamp(),
            "metrics": metrics.get_state_metrics()
        }
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.base_url}/heartbeat",
                    json=status_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    log.debug(f"Heartbeat sent for droplet {settings.droplet_id}")
                else:
                    log.warning(f"Heartbeat failed - Status: {response.status_code}, Response: {response.text}")
                    
        except Exception as e:
            log.error(f"Heartbeat error: {str(e)}")
            raise