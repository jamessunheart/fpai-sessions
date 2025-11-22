"""
UDC Messaging Endpoints - SPECIAL CASE (Manually Handles UDC)
Inter-droplet communication with full UDC envelope validation

NOTE: This endpoint is EXEMPT from middleware wrapping because it
already handles full UDC envelopes internally. Add "/message" to
middleware SKIP_WRAPPING set.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
import httpx
import structlog

from app.models.udc import UDCMessage
from app.database import db
from app.utils.auth import verify_jwt_token, optional_jwt_token
from app.utils.udc_helpers import udc_wrap, udc_error, validate_udc_envelope
from app.utils.helpers import generate_trace_id
from app.config import settings

log = structlog.get_logger()
router = APIRouter()


# ============================================================================
# RECEIVE MESSAGES - FULL UDC HANDLING (NO MIDDLEWARE)
# ============================================================================

@router.post("/message")
async def receive_message(
    request: Request,
    message: UDCMessage,
    token_data: dict = Depends(optional_jwt_token)
):
    """
    POST /message - UDC standard messaging endpoint
    
    SPECIAL CASE: This endpoint manually handles UDC envelopes
    - Validates incoming UDC envelope structure
    - Processes message payload
    - Returns UDC-wrapped response
    
    Middleware SKIP: Add "/message" to middleware SKIP_WRAPPING
    
    EXPECTS: Full UDC envelope
    RETURNS: Full UDC envelope (manually wrapped)
    """
    try:
        # Validate incoming message is UDC compliant
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            log.warning(
                "invalid_udc_message",
                error=error_msg,
                source=message.source,
                target=message.target
            )
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC message format: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id) if message.trace_id else None
            )
        
        log.info(
            "udc_message_received",
            trace_id=str(message.trace_id),
            source=message.source,
            target=message.target,
            message_type=message.message_type
        )
        
        # Verify target is this orchestrator
        target_matches = (
            message.target == settings.droplet_id or 
            message.target == f"droplet-{settings.droplet_id}" or
            str(message.target) == str(settings.droplet_id)
        )
        
        if not target_matches:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Message target {message.target} does not match this droplet (droplet-{settings.droplet_id})",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Process message based on type
        result = None
        error = None
        
        try:
            if message.message_type == "command":
                result = await process_command(message, token_data)
            elif message.message_type == "query":
                result = await process_query(message, token_data)
            elif message.message_type == "heartbeat":
                result = {"acknowledged": True, "status": "active"}
            else:
                result = {"acknowledged": True, "message": "Message received but not processed"}
                
        except Exception as e:
            error = str(e)
            log.error(
                "message_processing_failed",
                trace_id=str(message.trace_id),
                error=error
            )
        
        # Return UDC-wrapped response (manually)
        return udc_wrap(
            payload={
                "received": True,
                "processed_at": datetime.utcnow().isoformat(),
                "result": result,
                "error": error
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("message_receive_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to receive message: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target="unknown"
        )


async def process_command(message: UDCMessage, token_data: dict) -> dict:
    """Process command messages"""
    command = message.payload.get("command")
    
    if command == "create_task":
        # Create task from message payload
        task_data = message.payload.get("task_data", {})
        
        from app.models.domain import TaskCreate
        import json
        
        try:
            task = TaskCreate(
                task_type=task_data.get("task_type", "custom"),
                title=task_data.get("title", "Task from UDC message"),
                description=task_data.get("description"),
                required_capability=task_data.get("required_capability"),
                priority=task_data.get("priority", 5),
                payload=task_data.get("payload", {}),
                created_by=f"droplet_{message.source}"
            )
            
            # Insert task
            result = await db.fetchrow(
                """
                INSERT INTO tasks 
                (task_type, title, description, required_capability, priority, payload, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, trace_id, status
                """,
                task.task_type, task.title, task.description,
                task.required_capability, task.priority,
                json.dumps(task.payload), task.created_by
            )
            
            log.info(
                "task_created_via_udc_message",
                task_id=result['id'],
                source=message.source,
                udc_trace_id=str(message.trace_id)
            )
            
            return {
                "command": "create_task",
                "task_id": result['id'],
                "trace_id": str(result['trace_id']),
                "status": result['status']
            }
        except Exception as e:
            return {
                "error": f"Failed to create task: {str(e)}",
                "command": "create_task"
            }
    
    elif command == "cancel_task":
        task_id = message.payload.get("task_id")
        
        try:
            # Cancel task
            await db.execute(
                """
                UPDATE tasks
                SET status = 'cancelled', completed_at = NOW()
                WHERE id = $1 AND status NOT IN ('completed', 'failed', 'cancelled')
                """,
                task_id
            )
            
            log.info(
                "task_cancelled_via_udc_message",
                task_id=task_id,
                source=message.source,
                udc_trace_id=str(message.trace_id)
            )
            
            return {
                "command": "cancel_task",
                "task_id": task_id,
                "status": "cancelled"
            }
        except Exception as e:
            return {
                "error": f"Failed to cancel task: {str(e)}",
                "command": "cancel_task"
            }
    
    else:
        return {
            "error": f"Unknown command: {command}",
            "supported_commands": ["create_task", "cancel_task"]
        }


async def process_query(message: UDCMessage, token_data: dict) -> dict:
    """Process query messages"""
    query = message.payload.get("query")
    
    if query == "task_status":
        task_id = message.payload.get("task_id")
        
        task = await db.fetchrow(
            "SELECT id, trace_id, status, created_at, completed_at FROM tasks WHERE id = $1",
            task_id
        )
        
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        log.debug(
            "task_status_queried_via_udc",
            task_id=task_id,
            source=message.source,
            udc_trace_id=str(message.trace_id)
        )
        
        return {
            "query": "task_status",
            "task": {
                "id": task['id'],
                "trace_id": str(task['trace_id']),
                "status": task['status'],
                "created_at": task['created_at'].isoformat(),
                "completed_at": task['completed_at'].isoformat() if task['completed_at'] else None
            }
        }
    
    elif query == "droplet_list":
        droplets = await db.fetch(
            "SELECT droplet_id, name, status FROM droplets WHERE status = 'active'"
        )
        
        log.debug(
            "droplet_list_queried_via_udc",
            source=message.source,
            count=len(droplets),
            udc_trace_id=str(message.trace_id)
        )
        
        return {
            "query": "droplet_list",
            "droplets": [
                {
                    "id": d['droplet_id'],
                    "name": d['name'],
                    "status": d['status']
                }
                for d in droplets
            ]
        }
    
    elif query == "system_status":
        from app.database import check_database_health
        from app.services.websocket_manager import websocket_manager
        
        db_healthy = await check_database_health()
        ws_stats = websocket_manager.get_connection_count()
        
        log.debug(
            "system_status_queried_via_udc",
            source=message.source,
            udc_trace_id=str(message.trace_id)
        )
        
        return {
            "query": "system_status",
            "system": {
                "healthy": db_healthy,
                "database_connected": db_healthy,
                "websocket_connections": ws_stats['total_connections']
            }
        }
    
    else:
        return {
            "error": f"Unknown query: {query}",
            "supported_queries": ["task_status", "droplet_list", "system_status"]
        }


# ============================================================================
# SEND MESSAGES - FULL UDC HANDLING (NO MIDDLEWARE)
# ============================================================================

@router.post("/send")
async def send_message(
    target_droplet_id: int,
    message_type: str,
    payload: dict,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    POST /send - Send UDC message to another droplet
    
    SPECIAL CASE: This endpoint accepts simplified input but
    constructs and sends full UDC envelope.
    
    Middleware processes this endpoint normally (wraps response),
    but we construct outgoing UDC message manually.
    
    REQUEST: UDC envelope with target info and payload
    RESPONSE: UDC envelope with send confirmation
    """
    try:
        # Get target droplet endpoint
        target_droplet = await db.fetchrow(
            "SELECT name, endpoint FROM droplets WHERE droplet_id = $1",
            target_droplet_id
        )
        
        if not target_droplet:
            raise HTTPException(
                status_code=404,
                detail=f"Target droplet {target_droplet_id} not found"
            )
        
        # Generate trace ID
        trace_id = generate_trace_id()
        
        # Build UDC message (FULL COMPLIANCE)
        udc_message = {
            "udc_version": "1.0",
            "trace_id": str(trace_id),
            "source": f"droplet-{settings.droplet_id}",
            "target": f"droplet-{target_droplet_id}",
            "message_type": message_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }
        
        # Send message to target droplet
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{target_droplet['endpoint']}/message",
                    json=udc_message,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail=f"Timeout sending message to {target_droplet['name']}"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Error from {target_droplet['name']}: {e.response.status_code}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send message: {str(e)}"
            )
        
        log.info(
            "udc_message_sent",
            trace_id=str(trace_id),
            target=target_droplet_id,
            target_name=target_droplet['name'],
            message_type=message_type
        )
        
        # Return plain response - middleware wraps
        return {
            "sent": True,
            "target_droplet": target_droplet['name'],
            "target_droplet_id": target_droplet_id,
            "message_delivered_at": datetime.utcnow().isoformat(),
            "trace_id": str(trace_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("message_send_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )


# ============================================================================
# BATCH MESSAGING
# ============================================================================

@router.post("/broadcast")
async def broadcast_message(
    message_type: str,
    payload: dict,
    capability_filter: str = None,
    request: Request = None,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Broadcast a UDC-compliant message to multiple droplets
    
    REQUEST: UDC envelope with broadcast parameters
    RESPONSE: UDC envelope with delivery status
    """
    try:
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            raise HTTPException(
                status_code=403,
                detail="Admin permission required for broadcast"
            )
        
        # Get target droplets
        if capability_filter:
            droplets = await db.fetch(
                """
                SELECT droplet_id, name, endpoint
                FROM droplets
                WHERE status = 'active' AND capabilities @> $1::jsonb
                """,
                f'["{capability_filter}"]'
            )
        else:
            droplets = await db.fetch(
                """
                SELECT droplet_id, name, endpoint
                FROM droplets
                WHERE status = 'active' AND droplet_id != $1
                """,
                settings.droplet_id  # Exclude self
            )
        
        # Send to all droplets
        results = []
        trace_id = generate_trace_id()
        
        for droplet in droplets:
            try:
                # Build UDC message
                udc_message = {
                    "udc_version": "1.0",
                    "trace_id": str(trace_id),
                    "source": f"droplet-{settings.droplet_id}",
                    "target": f"droplet-{droplet['droplet_id']}",
                    "message_type": message_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "payload": payload
                }
                
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"{droplet['endpoint']}/message",
                        json=udc_message,
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    
                results.append({
                    "droplet_id": droplet['droplet_id'],
                    "name": droplet['name'],
                    "status": "sent"
                })
                
            except Exception as e:
                results.append({
                    "droplet_id": droplet['droplet_id'],
                    "name": droplet['name'],
                    "status": "failed",
                    "error": str(e)
                })
        
        log.info(
            "broadcast_completed",
            trace_id=str(trace_id),
            total_droplets=len(droplets),
            successful=len([r for r in results if r['status'] == 'sent'])
        )
        
        # Return plain response - middleware wraps
        return {
            "broadcast": True,
            "total_droplets": len(droplets),
            "successful": len([r for r in results if r['status'] == 'sent']),
            "failed": len([r for r in results if r['status'] == 'failed']),
            "results": results,
            "trace_id": str(trace_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("broadcast_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to broadcast message: {str(e)}"
        )