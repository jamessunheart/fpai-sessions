#!/usr/bin/env python3
"""
GPU Manager API - Monitoring and Control Endpoint
=================================================

FastAPI service that exposes:
- Health check
- Current GPU status
- Cost tracking
- Manual controls (with safety checks)
- Action history
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import config, load_config
from manager import GPUManager, GPUInstance


# Global manager instance
manager: Optional[GPUManager] = None
manager_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    global manager, manager_task
    
    # Initialize manager
    manager = GPUManager(load_config())
    
    # Start manager in background if enabled
    if config.enabled:
        manager_task = asyncio.create_task(manager.start())
    
    yield
    
    # Cleanup
    if manager_task:
        manager_task.cancel()
        try:
            await manager_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="GPU Manager",
    description="Unified GPU Management - Actually Smart This Time",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Models
# ============================================================================

class GPUStatus(BaseModel):
    id: str
    gpu_name: str
    hourly_cost: float
    status: str
    is_idle: bool


class ManagerStatus(BaseModel):
    enabled: bool
    mode: str
    running_gpus: int
    hourly_cost: float
    daily_cost: float
    budget_limit: float
    budget_remaining: float
    utilization: float
    last_check: Optional[str]
    emergency_stop_active: bool
    gpus: List[GPUStatus]


class ActionResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict] = None


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "gpu-manager",
        "version": "2.0.0",
        "enabled": config.enabled,
        "mode": config.mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/status", response_model=ManagerStatus)
async def get_status():
    """Get current GPU manager status"""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")
    
    # Get instances
    instances = await manager._get_instances()
    running = [i for i in instances if i.status == "running"]
    
    # Calculate costs
    hourly_cost = sum(i.hourly_cost for i in running)
    daily_cost = hourly_cost * 24
    
    # Get utilization
    utilization = await manager._get_utilization()
    
    return ManagerStatus(
        enabled=config.enabled,
        mode=config.mode,
        running_gpus=len(running),
        hourly_cost=hourly_cost,
        daily_cost=daily_cost,
        budget_limit=config.budget.daily_hard_limit_usd,
        budget_remaining=config.budget.daily_hard_limit_usd - daily_cost,
        utilization=utilization,
        last_check=manager.state.last_check.isoformat() if manager.state.last_check else None,
        emergency_stop_active=manager.state.emergency_stop_active,
        gpus=[
            GPUStatus(
                id=g.id,
                gpu_name=g.gpu_name,
                hourly_cost=g.hourly_cost,
                status=g.status,
                is_idle=g.is_idle
            )
            for g in running
        ]
    )


@app.get("/cost")
async def get_cost():
    """Get detailed cost breakdown"""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")
    
    instances = await manager._get_instances()
    running = [i for i in instances if i.status == "running"]
    
    hourly_cost = sum(i.hourly_cost for i in running)
    
    return {
        "running_gpus": len(running),
        "hourly_cost_usd": round(hourly_cost, 3),
        "daily_cost_usd": round(hourly_cost * 24, 2),
        "monthly_cost_usd": round(hourly_cost * 24 * 30, 2),
        "budget": {
            "daily_hard_limit": config.budget.daily_hard_limit_usd,
            "daily_soft_limit": config.budget.daily_soft_limit_usd,
            "remaining": round(config.budget.daily_hard_limit_usd - (hourly_cost * 24), 2)
        },
        "per_gpu": [
            {
                "id": g.id,
                "name": g.gpu_name,
                "hourly": round(g.hourly_cost, 3),
                "daily": round(g.hourly_cost * 24, 2)
            }
            for g in running
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/history")
async def get_history():
    """Get action history"""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")
    
    return {
        "actions": manager.state.actions[-50:],  # Last 50 actions
        "stats": {
            "last_scale_up": manager.state.last_scale_up.isoformat() if manager.state.last_scale_up else None,
            "last_scale_down": manager.state.last_scale_down.isoformat() if manager.state.last_scale_down else None,
            "gpus_created_this_hour": manager.state.gpus_created_this_hour,
            "emergency_stop_active": manager.state.emergency_stop_active
        }
    }


@app.post("/emergency-stop", response_model=ActionResponse)
async def emergency_stop():
    """
    EMERGENCY STOP - Destroy ALL GPU instances immediately
    """
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")
    
    instances = await manager._get_instances()
    running = [i for i in instances if i.status == "running"]
    
    if not running:
        return ActionResponse(
            success=True,
            message="No running instances to stop",
            details={"running": 0}
        )
    
    await manager._emergency_shutdown(running, "manual_emergency_stop")
    
    return ActionResponse(
        success=True,
        message=f"Emergency stop executed - destroyed {len(running)} instances",
        details={"destroyed": len(running)}
    )


@app.post("/release-idle", response_model=ActionResponse)
async def release_idle():
    """Release all idle GPU instances"""
    if not manager:
        raise HTTPException(status_code=503, detail="Manager not initialized")
    
    instances = await manager._get_instances()
    running = [i for i in instances if i.status == "running"]
    
    # Get utilization
    utilization = await manager._get_utilization()
    
    # Force scale down
    released = 0
    for gpu in running:
        if gpu.is_idle or utilization < config.scaling.scale_down_utilization:
            success = await manager._destroy_instance(gpu.id)
            if success:
                released += 1
    
    return ActionResponse(
        success=True,
        message=f"Released {released} idle instances",
        details={"released": released, "remaining": len(running) - released}
    )


@app.post("/set-mode/{mode}", response_model=ActionResponse)
async def set_mode(mode: str):
    """
    Change operating mode:
    - monitor_only: Just watch, don't act
    - scale_down_only: Only release GPUs
    - full_auto: Full automatic scaling
    """
    valid_modes = ["monitor_only", "scale_down_only", "full_auto"]
    
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid mode. Must be one of: {valid_modes}"
        )
    
    config.mode = mode
    
    return ActionResponse(
        success=True,
        message=f"Mode changed to: {mode}",
        details={"previous_mode": config.mode, "new_mode": mode}
    )


@app.get("/config")
async def get_config():
    """Get current configuration (redacted)"""
    return {
        "enabled": config.enabled,
        "mode": config.mode,
        "budget": {
            "daily_hard_limit": config.budget.daily_hard_limit_usd,
            "daily_soft_limit": config.budget.daily_soft_limit_usd,
            "max_gpu_hourly_cost": config.budget.max_gpu_hourly_cost
        },
        "scaling": {
            "min_gpus": config.scaling.min_gpus,
            "max_gpus": config.scaling.max_gpus,
            "scale_up_utilization": config.scaling.scale_up_utilization,
            "scale_down_utilization": config.scaling.scale_down_utilization
        },
        "circuit_breaker": {
            "emergency_stop_daily_cost": config.circuit_breaker.emergency_stop_daily_cost,
            "emergency_stop_gpu_count": config.circuit_breaker.emergency_stop_gpu_count,
            "max_gpus_per_hour": config.circuit_breaker.max_gpus_per_hour
        },
        "monitoring": {
            "check_interval_seconds": config.monitoring.check_interval_seconds,
            "utilization_endpoints": config.monitoring.utilization_endpoints
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8450)
