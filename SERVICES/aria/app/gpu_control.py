"""
GPU Control Module for Aria
============================

Gives Aria the ability to monitor and control GPU resources.

Usage in Aria:
    from gpu_control import GPUControl
    
    gpu = GPUControl()
    status = await gpu.get_status()
    await gpu.scale_down_idle()
"""

import os
import httpx
from typing import Dict, Any, Optional
from dataclasses import dataclass

# GPU Manager endpoint (on secondary server)
GPU_MANAGER_URL = os.getenv("GPU_MANAGER_URL", "http://162.0.208.88:8450")


@dataclass
class GPUStatus:
    """Current GPU fleet status"""
    running_gpus: int
    daily_cost: float
    budget_limit: float
    budget_remaining: float
    mode: str
    enabled: bool
    gpus: list
    
    def summary(self) -> str:
        """Human-readable summary"""
        if self.running_gpus == 0:
            return f"No GPUs running. Budget: ${self.budget_limit}/day available."
        return (
            f"{self.running_gpus} GPUs running at ${self.daily_cost:.2f}/day. "
            f"Budget: ${self.budget_remaining:.2f} remaining of ${self.budget_limit}/day. "
            f"Mode: {self.mode}"
        )


class GPUControl:
    """
    GPU Control interface for Aria.
    
    Capabilities:
    - get_status(): Check current GPU fleet status
    - scale_down_idle(): Release idle GPUs to save money
    - emergency_stop(): Destroy all GPUs immediately
    - set_mode(mode): Change scaling mode
    - get_cost_history(): View cost history
    """
    
    def __init__(self, base_url: str = GPU_MANAGER_URL):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def get_status(self) -> GPUStatus:
        """
        Get current GPU fleet status.
        
        Returns:
            GPUStatus with running count, costs, and details
        
        Example response:
            running_gpus: 3
            daily_cost: 5.50
            budget_limit: 20.0
            mode: "scale_down_only"
        """
        client = await self._get_client()
        try:
            r = await client.get(f"{self.base_url}/status")
            r.raise_for_status()
            data = r.json()
            return GPUStatus(
                running_gpus=data.get("running_gpus", 0),
                daily_cost=data.get("daily_cost", 0.0),
                budget_limit=data.get("budget_limit", 20.0),
                budget_remaining=data.get("budget_remaining", 20.0),
                mode=data.get("mode", "unknown"),
                enabled=data.get("enabled", False),
                gpus=data.get("gpus", [])
            )
        except Exception as e:
            # Return empty status if manager unreachable
            return GPUStatus(
                running_gpus=0,
                daily_cost=0.0,
                budget_limit=20.0,
                budget_remaining=20.0,
                mode="error",
                enabled=False,
                gpus=[]
            )
    
    async def scale_down_idle(self) -> Dict[str, Any]:
        """
        Release idle GPUs to save money.
        
        This is safe to call anytime - only releases GPUs that are not being used.
        
        Returns:
            {"success": True, "released": 3, "remaining": 2}
        """
        client = await self._get_client()
        try:
            r = await client.post(f"{self.base_url}/release-idle")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def emergency_stop(self) -> Dict[str, Any]:
        """
        EMERGENCY: Destroy all GPU instances immediately.
        
        Use this if:
        - Costs are out of control
        - GPUs are being created unexpectedly
        - You need to stop all spending NOW
        
        Returns:
            {"success": True, "destroyed": 5}
        """
        client = await self._get_client()
        try:
            r = await client.post(f"{self.base_url}/emergency-stop")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def set_mode(self, mode: str) -> Dict[str, Any]:
        """
        Change GPU scaling mode.
        
        Modes:
        - "monitor_only": Just watch, don't take action
        - "scale_down_only": Release idle GPUs, don't create new ones (SAFE)
        - "full_auto": Automatically scale up and down based on demand
        
        Args:
            mode: One of "monitor_only", "scale_down_only", "full_auto"
        
        Returns:
            {"success": True, "new_mode": "scale_down_only"}
        """
        if mode not in ["monitor_only", "scale_down_only", "full_auto"]:
            return {"success": False, "error": f"Invalid mode: {mode}"}
        
        client = await self._get_client()
        try:
            r = await client.post(f"{self.base_url}/set-mode/{mode}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_cost_history(self) -> Dict[str, Any]:
        """
        Get GPU cost history.
        
        Returns:
            Daily/hourly cost breakdown
        """
        client = await self._get_client()
        try:
            r = await client.get(f"{self.base_url}/cost")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"success": False, "error": str(e)}


# Convenience functions for direct use
_gpu_control: Optional[GPUControl] = None

def get_gpu_control() -> GPUControl:
    global _gpu_control
    if _gpu_control is None:
        _gpu_control = GPUControl()
    return _gpu_control


async def gpu_status() -> str:
    """Quick status check - returns human-readable summary"""
    gpu = get_gpu_control()
    status = await gpu.get_status()
    return status.summary()


async def gpu_scale_down() -> str:
    """Release idle GPUs"""
    gpu = get_gpu_control()
    result = await gpu.scale_down_idle()
    if result.get("success"):
        return f"Released {result.get('released', 0)} idle GPUs. {result.get('remaining', 0)} remaining."
    return f"Failed: {result.get('error')}"


async def gpu_emergency_stop() -> str:
    """Emergency: destroy all GPUs"""
    gpu = get_gpu_control()
    result = await gpu.emergency_stop()
    if result.get("success"):
        return f"EMERGENCY STOP: Destroyed {result.get('destroyed', 0)} GPUs."
    return f"Failed: {result.get('error')}"

