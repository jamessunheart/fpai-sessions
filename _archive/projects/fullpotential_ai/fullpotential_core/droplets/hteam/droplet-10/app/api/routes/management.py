"""
UDC Management Endpoints - FULLY UDC COMPLIANT
Remote configuration and lifecycle management
Note: These endpoints manually wrap responses for consistency with management operations
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import structlog
import asyncio
import signal
import os

from app.utils.auth import verify_jwt_token
from app.middleware.udc_middleware import get_udc_metadata
from app.config import settings

log = structlog.get_logger()
router = APIRouter()


class ReloadConfigRequest(BaseModel):
    """Request to reload configuration"""
    config_source: str = "environment"  # "environment" or "file"


class ShutdownRequest(BaseModel):
    """Request for graceful shutdown"""
    delay_seconds: int = 10
    reason: str = "Manual shutdown requested"


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

@router.post("/reload-config")
async def reload_config(
    request_data: ReloadConfigRequest,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Reload configuration without restarting the service.
    
    UDC-X Endpoint: Allows hot-reloading of environment variables
    and configuration settings.
    
    Requires: Admin permission
    REQUEST: UDC envelope with ReloadConfigRequest in payload
    RESPONSE: UDC envelope with reload status
    """
    try:
        udc = get_udc_metadata(request)
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            raise HTTPException(
                status_code=403,
                detail="Admin permission required for config reload"
            )
        
        log.info(
            "config_reload_requested",
            requested_by=f"droplet-{token_data.get('droplet_id')}",
            config_source=request_data.config_source,
            udc_trace_id=udc.get('trace_id')
        )
        
        # Reload settings
        if request_data.config_source == "environment":
            # Reload from environment variables
            settings_module = __import__('app.config', fromlist=['Settings'])
            new_settings = settings_module.Settings()
            
            # Update global settings (Note: This is simplified - in production,
            # you'd want to be more careful about what can be hot-reloaded)
            reloaded_fields = []
            for field in new_settings.model_fields:
                if field not in ['droplet_id', 'droplet_name']:  # Don't reload identity
                    old_value = getattr(settings, field)
                    new_value = getattr(new_settings, field)
                    if old_value != new_value:
                        setattr(settings, field, new_value)
                        reloaded_fields.append(field)
            
            log.info(
                "config_reloaded",
                reloaded_fields=reloaded_fields,
                config_source="environment"
            )
            
            # Return plain response - middleware wraps
            return {
                "status": "reloaded",
                "config_source": "environment",
                "reloaded_fields": reloaded_fields,
                "timestamp": settings.droplet_name
            }
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported config_source: {request_data.config_source}. Supported: ['environment']"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("config_reload_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload config: {str(e)}"
        )


# ============================================================================
# LIFECYCLE MANAGEMENT
# ============================================================================

@router.post("/shutdown")
async def graceful_shutdown(
    request_data: ShutdownRequest,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Initiate graceful shutdown of the orchestrator.
    
    UDC-X Endpoint: Stops accepting new requests, completes in-flight
    tasks, and cleanly shuts down the service.
    
    Requires: Admin permission
    REQUEST: UDC envelope with ShutdownRequest in payload
    RESPONSE: UDC envelope with shutdown acknowledgment
    """
    try:
        udc = get_udc_metadata(request)
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            raise HTTPException(
                status_code=403,
                detail="Admin permission required for shutdown"
            )
        
        log.warning(
            "graceful_shutdown_initiated",
            requested_by=f"droplet-{token_data.get('droplet_id')}",
            delay_seconds=request_data.delay_seconds,
            reason=request_data.reason,
            udc_trace_id=udc.get('trace_id')
        )
        
        # Schedule shutdown
        async def perform_shutdown():
            await asyncio.sleep(request_data.delay_seconds)
            
            log.warning("shutdown_executing", reason=request_data.reason)
            
            # Notify all connected WebSockets
            from app.services.websocket_manager import websocket_manager
            from app.utils.udc_helpers import udc_wrap
            
            shutdown_notice = udc_wrap(
                payload={
                    "event": "orchestrator_shutdown",
                    "reason": request_data.reason,
                    "message": "Orchestrator is shutting down"
                },
                source=f"droplet-{settings.droplet_id}",
                target="broadcast",
                message_type="event"
            )
            
            await websocket_manager._broadcast_to_channel(
                websocket_manager.task_connections, 
                shutdown_notice
            )
            await websocket_manager._broadcast_to_channel(
                websocket_manager.droplet_connections,
                shutdown_notice
            )
            
            # Give WebSockets time to send
            await asyncio.sleep(1)
            
            # Send SIGTERM to self (graceful shutdown)
            os.kill(os.getpid(), signal.SIGTERM)
        
        # Schedule in background
        asyncio.create_task(perform_shutdown())
        
        # Return plain response - middleware wraps
        return {
            "status": "shutdown_scheduled",
            "delay_seconds": request_data.delay_seconds,
            "reason": request_data.reason,
            "message": f"Graceful shutdown will begin in {request_data.delay_seconds} seconds"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("shutdown_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate shutdown: {str(e)}"
        )


@router.post("/emergency-stop")
async def emergency_stop(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    EMERGENCY: Immediate stop without cleanup.
    
    UDC-X Endpoint: Kills the service immediately. Use only in emergencies.
    In-flight tasks will be lost. Prefer /shutdown for normal operations.
    
    Requires: Admin permission
    REQUEST: UDC envelope (empty payload)
    RESPONSE: UDC envelope with emergency stop acknowledgment
    """
    try:
        udc = get_udc_metadata(request)
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            raise HTTPException(
                status_code=403,
                detail="Admin permission required for emergency stop"
            )
        
        log.critical(
            "emergency_stop_initiated",
            requested_by=f"droplet-{token_data.get('droplet_id')}",
            udc_trace_id=udc.get('trace_id')
        )
        
        # Immediate shutdown in background (give time to return response)
        async def perform_emergency_stop():
            await asyncio.sleep(0.5)  # Just enough time to send response
            os.kill(os.getpid(), signal.SIGKILL)
        
        asyncio.create_task(perform_emergency_stop())
        
        # Return plain response - middleware wraps
        return {
            "status": "emergency_stop_initiated",
            "message": "Service will terminate immediately"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("emergency_stop_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate emergency stop: {str(e)}"
        )


# ============================================================================
# STATUS AND VERSION
# ============================================================================

@router.get("/version")
async def get_version(request: Request):
    """
    Get build and version information.
    
    UDC Endpoint: Returns detailed version, build, and deployment metadata.
    No authentication required (public endpoint).
    
    RESPONSE: UDC envelope with version information
    """
    try:
        udc = get_udc_metadata(request)
        
        import sys
        from datetime import datetime
        
        # Return plain response - middleware wraps
        return {
            "version": settings.app_version,
            "droplet_id": settings.droplet_id,
            "droplet_name": settings.droplet_name,
            "udc_version": "1.0",
            "python_version": sys.version,
            "build_date": getattr(settings, 'build_date', 'unknown'),
            "environment": settings.environment,
            "deployed_by": getattr(settings, 'deployed_by', 'unknown'),
            "uptime_seconds": getattr(settings, 'uptime_seconds', 0)
        }
        
    except Exception as e:
        log.error("version_info_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get version info: {str(e)}"
        )


# ============================================================================
# SCHEDULER MANAGEMENT
# ============================================================================

@router.get("/scheduler/jobs")
async def list_scheduler_jobs(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    List all scheduled background jobs
    
    Requires: Admin permission
    RESPONSE: UDC envelope with scheduler jobs list
    """
    try:
        udc = get_udc_metadata(request)
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            raise HTTPException(
                status_code=403,
                detail="Admin permission required"
            )
        
        from app.main import scheduler
        
        jobs = [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "max_instances": job.max_instances,
                "coalesce": job.coalesce
            }
            for job in scheduler.get_jobs()
        ]
        
        log.debug(
            "scheduler_jobs_listed",
            total_jobs=len(jobs),
            udc_trace_id=udc.get('trace_id')
        )
        
        # Return plain response - middleware wraps
        return {
            "scheduler_running": scheduler.running,
            "total_jobs": len(jobs),
            "jobs": jobs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("scheduler_jobs_list_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list scheduler jobs: {str(e)}"
        )


@router.post("/scheduler/jobs/{job_id}/pause")
async def pause_scheduler_job(
    job_id: str,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Pause a specific scheduled job
    
    Requires: Admin permission
    REQUEST: UDC envelope (empty payload)
    RESPONSE: UDC envelope with pause confirmation
    """
    try:
        udc = get_udc_metadata(request)
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            raise HTTPException(
                status_code=403,
                detail="Admin permission required"
            )
        
        from app.main import scheduler
        
        job = scheduler.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_id}' not found"
            )
        
        job.pause()
        
        log.info(
            "scheduler_job_paused",
            job_id=job_id,
            paused_by=f"droplet-{token_data.get('droplet_id')}",
            udc_trace_id=udc.get('trace_id')
        )
        
        # Return plain response - middleware wraps
        return {
            "job_id": job_id,
            "status": "paused",
            "next_run": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("scheduler_job_pause_failed", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pause job: {str(e)}"
        )


@router.post("/scheduler/jobs/{job_id}/resume")
async def resume_scheduler_job(
    job_id: str,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Resume a paused scheduled job
    
    Requires: Admin permission
    REQUEST: UDC envelope (empty payload)
    RESPONSE: UDC envelope with resume confirmation
    """
    try:
        udc = get_udc_metadata(request)
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            raise HTTPException(
                status_code=403,
                detail="Admin permission required"
            )
        
        from app.main import scheduler
        
        job = scheduler.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_id}' not found"
            )
        
        job.resume()
        
        log.info(
            "scheduler_job_resumed",
            job_id=job_id,
            resumed_by=f"droplet-{token_data.get('droplet_id')}",
            udc_trace_id=udc.get('trace_id')
        )
        
        # Return plain response - middleware wraps
        return {
            "job_id": job_id,
            "status": "running",
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("scheduler_job_resume_failed", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume job: {str(e)}"
        )


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

@router.post("/cache/clear")
async def clear_registry_cache(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Clear the Registry droplet directory cache
    
    Forces a fresh sync from Registry on next request
    
    Requires: Admin permission
    REQUEST: UDC envelope (empty payload)
    RESPONSE: UDC envelope with clear confirmation
    """
    try:
        udc = get_udc_metadata(request)
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            raise HTTPException(
                status_code=403,
                detail="Admin permission required"
            )
        
        from app.services.registry_client import registry_client
        
        registry_client.clear_cache()
        
        log.info(
            "registry_cache_cleared",
            cleared_by=f"droplet-{token_data.get('droplet_id')}",
            udc_trace_id=udc.get('trace_id')
        )
        
        # Return plain response - middleware wraps
        return {
            "status": "cleared",
            "cache_type": "registry_droplets",
            "message": "Registry cache cleared successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("cache_clear_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )