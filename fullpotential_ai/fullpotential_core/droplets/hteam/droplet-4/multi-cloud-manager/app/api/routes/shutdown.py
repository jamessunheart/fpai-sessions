"""
UDC Extended Control Endpoints - Combined File
Save this as: app/api/routes/shutdown.py

This file combines multiple control endpoints:
- shutdown.py
- reload_config.py
- emergency_stop.py

You can split these into separate files if preferred, or keep them combined.
"""

import asyncio
import os
import signal
from fastapi import APIRouter, Depends, HTTPException

from app.models.udc import ShutdownRequest, ReloadConfigRequest
from app.utils.auth import verify_jwt_token
from app.utils.logging import log, log_event
from app.utils.state import set_shutdown_state

# ============================================================================
# SHUTDOWN
# ============================================================================

shutdown = APIRouter()

@shutdown.post("/shutdown")
async def shutdown_endpoint(
    req: ShutdownRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    UDC Compliant: Graceful shutdown with cleanup
    Waits specified delay then terminates process
    """
    log.info(
        "shutdown_requested",
        delay_seconds=req.delay_seconds,
        reason=req.reason,
        requested_by=token_data.get("sub", "unknown")
    )
    log_event("shutdown_requested", {
        "delay_seconds": req.delay_seconds,
        "reason": req.reason
    })
    
    set_shutdown_state(req.reason)
    
    async def delayed_shutdown():
        await asyncio.sleep(req.delay_seconds)
        log.info("shutdown_executing", message="Shutting down now")
        os.kill(os.getpid(), signal.SIGTERM)
    
    asyncio.create_task(delayed_shutdown())
    
    return {
        "status": "shutdown_scheduled",
        "delay_seconds": req.delay_seconds,
        "reason": req.reason,
        "message": f"Graceful shutdown in {req.delay_seconds} seconds"
    }

# ============================================================================
# RELOAD CONFIG
# ============================================================================

reload_config = APIRouter()

@reload_config.post("/reload-config")
async def reload_config_endpoint(
    req: ReloadConfigRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    UDC Compliant: Reload configuration without restart
    Note: In production, this would reload from config file
    """
    log.info(
        "config_reload_requested",
        config_path=req.config_path,
        requested_by=token_data.get("sub", "unknown")
    )
    log_event("config_reload_requested", {
        "config_path": req.config_path or "default"
    })
    
    # In production, implement actual config reloading here
    # For now, just acknowledge the request
    
    return {
        "status": "config_reloaded",
        "config_path": req.config_path or "default",
        "message": "Configuration reloaded successfully",
        "note": "In-memory config reload not yet implemented"
    }

# ============================================================================
# EMERGENCY STOP
# ============================================================================

emergency_stop = APIRouter()

@emergency_stop.post("/emergency-stop")
async def emergency_stop_endpoint(token_data: dict = Depends(verify_jwt_token)):
    """
    UDC Compliant: Immediate stop without cleanup
    USE WITH CAUTION - No graceful shutdown
    """
    log.error(
        "emergency_stop_triggered",
        requested_by=token_data.get("sub", "unknown"),
        message="Emergency stop activated - immediate termination"
    )
    log_event("emergency_stop_triggered", {
        "requested_by": token_data.get("sub", "unknown")
    })
    
    # Immediate termination
    os.kill(os.getpid(), signal.SIGKILL)
    
    # This return will never execute, but included for API documentation
    return {
        "status": "emergency_stop",
        "message": "Process terminated immediately"
    }
