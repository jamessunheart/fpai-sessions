"""
Droplet Management Endpoints - WORKING UDC SOLUTION
Uses dependency-based approach to unwrap UDC envelopes
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from typing import Optional
import structlog
from datetime import datetime

from app.models.domain import (
    DropletRegister, DropletHeartbeat
)
from app.services.health_monitor import (
    register_droplet, process_heartbeat, get_droplet_info
)
from app.database import db
from app.utils.auth import verify_jwt_token, get_droplet_id_from_token
from app.utils.udc_deps import parse_udc_request, wrap_udc_response, get_udc_metadata
from app.services.websocket_manager import websocket_manager
from app.services.task_router import reassign_droplet_tasks
from app.config import settings

log = structlog.get_logger()
router = APIRouter()


# ============================================================================
# DROPLET REGISTRATION
# ============================================================================

@router.post("/register", status_code=201)
async def register_droplet_endpoint(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Register a new droplet with the orchestrator.
    
    REQUEST: UDC envelope with DropletRegister in payload
    RESPONSE: UDC envelope with registration confirmation
    """
    try:
        # Parse and unwrap UDC request
        payload = await parse_udc_request(request)
        
        # Manually validate with Pydantic
        try:
            droplet = DropletRegister(**payload)
        except ValidationError as e:
            log.warning("droplet_validation_failed", errors=e.errors())
            raise HTTPException(status_code=422, detail=e.errors())
        
        # Get UDC metadata
        udc = get_udc_metadata(request)
        token_droplet_id = get_droplet_id_from_token(token_data)
        
        # Validate droplet data
        if not droplet.droplet_id or not droplet.name:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: droplet_id and name are required"
            )
        
        result = await register_droplet(
            droplet_id=droplet.droplet_id,
            name=droplet.name,
            steward=droplet.steward,
            endpoint=droplet.endpoint,
            capabilities=droplet.capabilities
        )
        
        log.info(
            "droplet_registration_processed",
            droplet_id=droplet.droplet_id,
            name=droplet.name,
            status=result.get('status'),
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                **result,
                "heartbeat_interval_seconds": 60,
                "next_heartbeat_deadline": (datetime.utcnow().timestamp() + 60)
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("droplet_registration_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register droplet: {str(e)}"
        )


# ============================================================================
# HEARTBEAT
# ============================================================================

@router.post("/{droplet_id}/heartbeat")
async def send_heartbeat(
    droplet_id: int,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Process droplet heartbeat.
    
    REQUEST: UDC envelope with DropletHeartbeat in payload
    RESPONSE: UDC envelope with heartbeat acknowledgment
    """
    try:
        # Parse and unwrap UDC request
        payload = await parse_udc_request(request)
        
        # Manually validate with Pydantic
        try:
            heartbeat = DropletHeartbeat(**payload)
        except ValidationError as e:
            log.warning("heartbeat_validation_failed", errors=e.errors())
            raise HTTPException(status_code=422, detail=e.errors())
        
        # Get UDC metadata
        udc = get_udc_metadata(request)
        token_droplet_id = get_droplet_id_from_token(token_data)
        
        # Verify droplet is reporting its own heartbeat
        if droplet_id != token_droplet_id and token_droplet_id not in [1,"droplet-1"]:
            raise HTTPException(
                status_code=403,
                detail=f"Droplet {token_droplet_id} cannot send heartbeat for droplet {droplet_id}"
            )
        
        result = await process_heartbeat(
            droplet_id=droplet_id,
            status=heartbeat.status,
            metrics=heartbeat.metrics
        )
        
        log.debug(
            "heartbeat_processed",
            droplet_id=droplet_id,
            status=heartbeat.status,
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                **result,
                "next_heartbeat_deadline": (datetime.utcnow().timestamp() + 60)
            },
            request
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        log.error("heartbeat_processing_failed", droplet_id=droplet_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process heartbeat: {str(e)}"
        )


# ============================================================================
# DROPLET DIRECTORY
# ============================================================================

@router.get("")
async def list_droplets(
    request: Request,
    status: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
    token_data: dict = Depends(verify_jwt_token)
):
    """
    List all registered droplets with optional filters.
    
    RESPONSE: UDC envelope with droplet directory
    """
    try:
        conditions = []
        params = []
        param_count = 1
        
        if status:
            conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1
        if capability:
            conditions.append(f"capabilities @> ${param_count}::jsonb")
            params.append(f'["{capability}"]')
            param_count += 1
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        total = await db.fetchval(f"SELECT COUNT(*) FROM droplets {where_clause}", *params)
        droplets_query = f"""
            SELECT 
                droplet_id, name, steward, endpoint, capabilities, status,
                last_heartbeat, registered_at,
                EXTRACT(EPOCH FROM (NOW() - last_heartbeat)) as seconds_since_heartbeat
            FROM droplets
            {where_clause}
            ORDER BY droplet_id ASC
        """
        droplets = await db.fetch(droplets_query, *params)
        
        # Convert to serializable format
        droplet_list = []
        for d in droplets:
            droplet_dict = dict(d)
            droplet_list.append({
                "droplet_id": droplet_dict['droplet_id'],
                "name": droplet_dict['name'],
                "steward": droplet_dict['steward'],
                "endpoint": droplet_dict['endpoint'],
                "capabilities": droplet_dict['capabilities'],
                "status": droplet_dict['status'],
                "last_heartbeat": droplet_dict['last_heartbeat'].isoformat() if droplet_dict.get('last_heartbeat') else None,
                "registered_at": droplet_dict['registered_at'].isoformat() if droplet_dict.get('registered_at') else None,
                "seconds_since_heartbeat": droplet_dict.get('seconds_since_heartbeat')
            })
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "droplets": droplet_list,
                "total": total,
                "filters": {
                    "status": status,
                    "capability": capability
                }
            },
            request
        )
        
    except Exception as e:
        log.error("droplet_list_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list droplets: {str(e)}"
        )


@router.get("/{droplet_id}")
async def get_droplet_details(
    droplet_id: int,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Get detailed information about a specific droplet.
    
    RESPONSE: UDC envelope with droplet details
    """
    try:
        droplet = await get_droplet_info(droplet_id)
        if not droplet:
            raise HTTPException(
                status_code=404,
                detail=f"Droplet {droplet_id} not found"
            )
        
        # Wrap and return response
        return wrap_udc_response({"droplet": droplet}, request)
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("droplet_fetch_failed", droplet_id=droplet_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch droplet details: {str(e)}"
        )


# ============================================================================
# DROPLET STATUS MANAGEMENT
# ============================================================================

@router.post("/{droplet_id}/activate")
async def activate_droplet(
    droplet_id: int,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Manually activate a droplet.
    
    Requires admin permission.
    REQUEST: UDC envelope (empty or minimal payload)
    RESPONSE: UDC envelope with activation confirmation
    """
    try:
        udc = get_udc_metadata(request)
        
        if 'admin' not in token_data.get('permissions', []) and droplet_id != token_data.get('droplet_id'):
            raise HTTPException(
                status_code=403,
                detail="Admin permission required to activate another droplet"
            )
        
        droplet = await db.fetchrow(
            "SELECT id, name, status FROM droplets WHERE droplet_id = $1",
            droplet_id
        )
        if not droplet:
            raise HTTPException(
                status_code=404,
                detail=f"Droplet {droplet_id} not found"
            )
        
        now = datetime.utcnow()
        await db.execute(
            "UPDATE droplets SET status = 'active', last_heartbeat = $1, updated_at = $1 WHERE droplet_id = $2",
            now, droplet_id
        )
        
        await websocket_manager.broadcast_droplet_health_changed(
            droplet_id, droplet['status'], 'active'
        )
        
        log.info(
            "droplet_activated",
            droplet_id=droplet_id,
            old_status=droplet['status'],
            activated_by=f"droplet-{token_data.get('droplet_id')}",
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "droplet_id": droplet_id,
                "name": droplet['name'],
                "old_status": droplet['status'],
                "new_status": "active",
                "activated_at": now.isoformat(),
                "activated_by": f"droplet-{token_data.get('droplet_id')}"
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("droplet_activation_failed", droplet_id=droplet_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate droplet: {str(e)}"
        )


@router.post("/{droplet_id}/deactivate")
async def deactivate_droplet(
    droplet_id: int,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Manually deactivate a droplet.
    
    Requires admin permission.
    REQUEST: UDC envelope (empty or minimal payload)
    RESPONSE: UDC envelope with deactivation confirmation
    """
    try:
        udc = get_udc_metadata(request)
        
        if 'admin' not in token_data.get('permissions', []) and droplet_id != token_data.get('droplet_id'):
            raise HTTPException(
                status_code=403,
                detail="Admin permission required"
            )
        
        droplet = await db.fetchrow(
            "SELECT id, name, status FROM droplets WHERE droplet_id = $1",
            droplet_id
        )
        if not droplet:
            raise HTTPException(
                status_code=404,
                detail=f"Droplet {droplet_id} not found"
            )
        
        now = datetime.utcnow()
        await db.execute(
            "UPDATE droplets SET status = 'inactive', updated_at = $1 WHERE droplet_id = $2",
            now, droplet_id
        )
        
        reassigned_count = 0
        if settings.enable_auto_recovery:
            reassigned_count = await reassign_droplet_tasks(
                droplet['id'],
                reason=f"Droplet #{droplet_id} manually deactivated"
            )
        
        await websocket_manager.broadcast_droplet_health_changed(
            droplet_id, droplet['status'], 'inactive'
        )
        
        log.info(
            "droplet_deactivated",
            droplet_id=droplet_id,
            old_status=droplet['status'],
            tasks_reassigned=reassigned_count,
            deactivated_by=f"droplet-{token_data.get('droplet_id')}",
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "droplet_id": droplet_id,
                "name": droplet['name'],
                "old_status": droplet['status'],
                "new_status": "inactive",
                "tasks_reassigned": reassigned_count,
                "deactivated_at": now.isoformat(),
                "deactivated_by": f"droplet-{token_data.get('droplet_id')}"
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("droplet_deactivation_failed", droplet_id=droplet_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate droplet: {str(e)}"
        )


# ============================================================================
# DROPLET CAPABILITIES
# ============================================================================

@router.get("/{droplet_id}/capabilities")
async def get_droplet_capabilities(
    droplet_id: int,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Get droplet capabilities.
    
    RESPONSE: UDC envelope with capabilities list
    """
    try:
        droplet = await db.fetchrow(
            "SELECT name, capabilities FROM droplets WHERE droplet_id = $1",
            droplet_id
        )
        if not droplet:
            raise HTTPException(
                status_code=404,
                detail=f"Droplet {droplet_id} not found"
            )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "droplet_id": droplet_id,
                "name": droplet['name'],
                "capabilities": droplet['capabilities']
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("droplet_capabilities_fetch_failed", droplet_id=droplet_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch capabilities: {str(e)}"
        )