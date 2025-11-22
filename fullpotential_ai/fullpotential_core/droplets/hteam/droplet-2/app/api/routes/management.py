from fastapi import APIRouter, Depends
from typing import Dict, Any
from ...models.domain import ReloadConfigRequest, ShutdownRequest
from ...utils.auth import verify_jwt_token
from ...utils.logging import get_logger
from ...config import settings

router = APIRouter(tags=["UDC Management"])
log = get_logger(__name__)


@router.post("/reload-config")
async def reload_config(
    request: ReloadConfigRequest,
    token_data: Dict[str, Any] = Depends(verify_jwt_token)
):
    """Reload configuration without restart"""
    
    log.info(f"Config reload requested - Path: {request.config_path}, By: {token_data.get('droplet_id')}")
    
    # In production: actually reload configuration
    # For demo: just return success
    
    return {
        "reloaded": True,
        "config_path": request.config_path,
        "timestamp": "2025-11-08T03:00:00Z"
    }


@router.post("/shutdown")
async def shutdown(
    request: ShutdownRequest,
    token_data: Dict[str, Any] = Depends(verify_jwt_token)
):
    """Graceful shutdown with cleanup"""
    
    log.warning(f"Shutdown requested - Delay: {request.delay_seconds}s, Reason: {request.reason}, By: {token_data.get('droplet_id')}")
    
    # In production: actually schedule shutdown
    # For demo: just return acknowledgment
    
    return {
        "shutdown_scheduled": True,
        "delay_seconds": request.delay_seconds,
        "reason": request.reason,
        "scheduled_at": "2025-11-08T03:00:00Z"
    }


@router.get("/version")
async def version(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Build and deployment information"""
    return {
        "version": "1.0.0",
        "build_date": "2025-11-08",
        "commit_hash": "dev",
        "environment": settings.environment,
        "deployed_by": settings.droplet_steward
    }