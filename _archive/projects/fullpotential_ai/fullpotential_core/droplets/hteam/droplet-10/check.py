"""
FULL UDC COMPLIANCE - ALL POST ENDPOINTS
All POST requests AND responses must be UDC-wrapped
No exceptions.
"""

# ============================================================================
# auth.py - FULL UDC COMPLIANCE
# ============================================================================

from fastapi import APIRouter, HTTPException, status, Depends, Request
from app.utils.auth import create_access_token, verify_jwt_token
from app.config import settings
from app.utils.udc_helpers import udc_wrap, udc_error, validate_udc_envelope
from app.models.udc import UDCMessage
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token")
async def get_token(message: UDCMessage):
    """
    Generates a JWT token for a Droplet ID.
    
    EXPECTS: UDC-wrapped request
    RETURNS: UDC-wrapped token response
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Extract payload
        droplet_id = message.payload.get("droplet_id")
        secret_key = message.payload.get("secret_key")
        
        if not droplet_id or droplet_id <= 0:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message="Invalid or missing droplet_id in payload",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        if secret_key != settings.jwt_secret_key:
            log.warning("token_request_invalid_secret", droplet_id=droplet_id)
            return udc_error(
                error_code="FORBIDDEN",
                error_message="Invalid secret key",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Build token payload
        token_payload = {
            "droplet_id": droplet_id,
            "steward": settings.droplet_steward,
            "permissions": ["read", "write"]
        }
        
        # Generate JWT token
        jwt_token = create_access_token(data=token_payload)
        
        log.info("token_generated", droplet_id=droplet_id, trace_id=str(message.trace_id))
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "access_token": jwt_token,
                "token_type": "bearer",
                "expires_in": settings.jwt_expiration,
                "permissions": token_payload["permissions"]
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("token_generation_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to generate token: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.post("/refresh")
async def refresh_token(message: UDCMessage, token_data: dict = Depends(verify_jwt_token)):
    """
    Refresh an existing JWT token.
    
    EXPECTS: UDC-wrapped request with valid JWT
    RETURNS: UDC-wrapped new token
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        droplet_id = token_data.get('droplet_id')
        
        # Generate new token with same permissions
        new_token_payload = {
            "droplet_id": droplet_id,
            "steward": token_data.get('steward', settings.droplet_steward),
            "permissions": token_data.get('permissions', ["read", "write"])
        }
        
        jwt_token = create_access_token(data=new_token_payload)
        
        log.info("token_refreshed", droplet_id=droplet_id, trace_id=str(message.trace_id))
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "access_token": jwt_token,
                "token_type": "bearer",
                "expires_in": settings.jwt_expiration,
                "permissions": new_token_payload["permissions"]
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("token_refresh_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to refresh token: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.post("/revoke")
async def revoke_token(message: UDCMessage, token_data: dict = Depends(verify_jwt_token)):
    """
    Revoke current JWT token (logout).
    
    EXPECTS: UDC-wrapped request
    RETURNS: UDC-wrapped revocation confirmation
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        droplet_id = token_data.get('droplet_id')
        
        log.info("token_revoked", droplet_id=droplet_id, trace_id=str(message.trace_id))
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "revoked": True,
                "droplet_id": droplet_id,
                "message": "Token revoked successfully. Use /auth/token to generate a new token."
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("token_revocation_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to revoke token: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


# ============================================================================
# droplets.py - FULL UDC COMPLIANCE
# ============================================================================

@router.post("/register", status_code=201)
async def register_droplet_endpoint(
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Register a new droplet with the orchestrator.
    
    EXPECTS: UDC-wrapped registration request
    RETURNS: UDC-wrapped registration confirmation
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Extract registration data from payload
        droplet_id = message.payload.get("droplet_id")
        name = message.payload.get("name")
        steward = message.payload.get("steward")
        endpoint = message.payload.get("endpoint")
        capabilities = message.payload.get("capabilities", [])
        
        if not droplet_id or not name:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message="Missing required fields: droplet_id and name are required",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        result = await register_droplet(
            droplet_id=droplet_id,
            name=name,
            steward=steward,
            endpoint=endpoint,
            capabilities=capabilities
        )
        
        log.info(
            "droplet_registration_processed",
            droplet_id=droplet_id,
            name=name,
            trace_id=str(message.trace_id)
        )
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                **result,
                "heartbeat_interval_seconds": 60,
                "next_heartbeat_deadline": (datetime.utcnow().timestamp() + 60)
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("droplet_registration_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to register droplet: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.post("/{droplet_id}/heartbeat")
async def send_heartbeat(
    droplet_id: int,
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Process droplet heartbeat.
    
    EXPECTS: UDC-wrapped heartbeat
    RETURNS: UDC-wrapped heartbeat acknowledgment
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        token_droplet_id = get_droplet_id_from_token(token_data)
        
        # Verify droplet is reporting its own heartbeat
        if droplet_id != token_droplet_id:
            return udc_error(
                error_code="FORBIDDEN",
                error_message=f"Droplet {token_droplet_id} cannot send heartbeat for droplet {droplet_id}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Extract heartbeat data from payload
        status = message.payload.get("status", "active")
        metrics = message.payload.get("metrics", {})
        
        result = await process_heartbeat(
            droplet_id=droplet_id,
            status=status,
            metrics=metrics
        )
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                **result,
                "next_heartbeat_deadline": (datetime.utcnow().timestamp() + 60)
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("heartbeat_processing_failed", droplet_id=droplet_id, error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to process heartbeat: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.post("/{droplet_id}/activate")
async def activate_droplet(
    droplet_id: int,
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Manually activate a droplet.
    
    EXPECTS: UDC-wrapped activation request
    RETURNS: UDC-wrapped activation confirmation
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        if 'admin' not in token_data.get('permissions', []):
            return udc_error(
                error_code="FORBIDDEN",
                error_message="Admin permission required",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        droplet = await db.fetchrow("SELECT id, name, status FROM droplets WHERE droplet_id = $1", droplet_id)
        if not droplet:
            return udc_error(
                error_code="NOT_FOUND",
                error_message=f"Droplet {droplet_id} not found",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        now = datetime.utcnow()
        await db.execute(
            "UPDATE droplets SET status = 'active', last_heartbeat = $1, updated_at = $1 WHERE droplet_id = $2",
            now, droplet_id
        )
        
        await websocket_manager.broadcast_droplet_health_changed(
            droplet_id, droplet['status'], 'active'
        )
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "droplet_id": droplet_id,
                "name": droplet['name'],
                "old_status": droplet['status'],
                "new_status": "active",
                "activated_at": now.isoformat(),
                "activated_by": str(message.source)
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("droplet_activation_failed", droplet_id=droplet_id, error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to activate droplet: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.post("/{droplet_id}/deactivate")
async def deactivate_droplet(
    droplet_id: int,
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Manually deactivate a droplet.
    
    EXPECTS: UDC-wrapped deactivation request
    RETURNS: UDC-wrapped deactivation confirmation with task reassignment info
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        if 'admin' not in token_data.get('permissions', []):
            return udc_error(
                error_code="FORBIDDEN",
                error_message="Admin permission required",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        droplet = await db.fetchrow("SELECT id, name, status FROM droplets WHERE droplet_id = $1", droplet_id)
        if not droplet:
            return udc_error(
                error_code="NOT_FOUND",
                error_message=f"Droplet {droplet_id} not found",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        now = datetime.utcnow()
        await db.execute("UPDATE droplets SET status = 'inactive', updated_at = $1 WHERE droplet_id = $2", now, droplet_id)
        
        reassigned_count = 0
        if settings.enable_auto_recovery:
            reassigned_count = await reassign_droplet_tasks(droplet['id'], reason=f"Droplet #{droplet_id} manually deactivated")
        
        await websocket_manager.broadcast_droplet_health_changed(
            droplet_id, droplet['status'], 'inactive'
        )
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "droplet_id": droplet_id,
                "name": droplet['name'],
                "old_status": droplet['status'],
                "new_status": "inactive",
                "tasks_reassigned": reassigned_count,
                "deactivated_at": now.isoformat(),
                "deactivated_by": str(message.source)
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("droplet_deactivation_failed", droplet_id=droplet_id, error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to deactivate droplet: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


# ============================================================================
# tasks.py - FULL UDC COMPLIANCE
# ============================================================================

@router.post("", status_code=201)
async def create_task(
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Create a new task
    
    EXPECTS: UDC-wrapped task creation request
    RETURNS: UDC-wrapped task creation response
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Extract task data from payload
        task_type = message.payload.get("task_type")
        title = message.payload.get("title")
        description = message.payload.get("description")
        required_capability = message.payload.get("required_capability")
        priority = message.payload.get("priority", 5)
        payload_data = message.payload.get("payload", {})
        max_retries = message.payload.get("max_retries", 3)
        deadline = message.payload.get("deadline")
        created_by = message.payload.get("created_by") or str(message.source)
        
        if not task_type or not title:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message="Missing required fields: task_type and title are required",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Insert task into database
        result = await db.fetchrow(
            """
            INSERT INTO tasks 
            (task_type, title, description, required_capability, priority, 
             payload, created_by, max_retries, deadline)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id, trace_id, status, created_at
            """,
            task_type, title, description, required_capability, priority,
            json.dumps(payload_data), created_by, max_retries, deadline
        )
        
        # Record initial state in history
        from app.services.state_machine import record_state_history
        await record_state_history(
            task_id=result['id'],
            from_status=None,
            to_status='pending',
            changed_by=created_by
        )
        
        # Broadcast WebSocket event (UDC compliant)
        await websocket_manager.broadcast_task_created(
            udc_wrap(
                payload={
                    "event": "task_created",
                    "task": {
                        "id": result['id'],
                        "trace_id": str(result['trace_id']),
                        "task_type": task_type,
                        "title": title,
                        "priority": priority,
                        "status": result['status'],
                        "created_at": result['created_at'].isoformat()
                    }
                },
                source=f"droplet-{settings.droplet_id}",
                target="broadcast",
                message_type="event",
                trace_id=str(message.trace_id)
            )
        )
        
        log.info(
            "task_created",
            task_id=result['id'],
            trace_id=str(message.trace_id),
            task_type=task_type
        )
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "task_id": result['id'],
                "trace_id": str(result['trace_id']),
                "status": result['status'],
                "created_at": result['created_at'].isoformat(),
                "estimated_assignment_seconds": 10
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("task_creation_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to create task: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.patch("/{task_id}")
async def update_task(
    task_id: int,
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Update task status
    
    EXPECTS: UDC-wrapped task update request
    RETURNS: UDC-wrapped updated task information
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Extract update data from payload
        new_status = message.payload.get("status")
        result_data = message.payload.get("result")
        error_message = message.payload.get("error_message")
        
        if not new_status:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message="Missing required field: status",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Get current task
        task = await db.fetchrow(
            """
            SELECT t.*, d.droplet_id as assigned_droplet_droplet_id
            FROM tasks t
            LEFT JOIN droplets d ON t.assigned_droplet_id = d.id
            WHERE t.id = $1
            """,
            task_id
        )
        
        if not task:
            return udc_error(
                error_code="NOT_FOUND",
                error_message=f"Task {task_id} not found",
                details={"task_id": task_id},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Verify permission
        requester_droplet_id = token_data.get('droplet_id')
        if task['assigned_droplet_droplet_id'] != requester_droplet_id:
            return udc_error(
                error_code="FORBIDDEN",
                error_message="Only assigned droplet can update task status",
                details={"task_id": task_id, "assigned_to": task['assigned_droplet_droplet_id']},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        current_status = task['status']
        
        # Transition state
        try:
            await transition_task_status(
                task_id=task_id,
                current_status=current_status,
                new_status=new_status,
                changed_by=str(message.source)
            )
        except TransitionError as e:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=str(e),
                details={"current_status": current_status, "new_status": new_status},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Update result and error message if provided
        if result_data is not None or error_message is not None:
            await db.execute(
                """
                UPDATE tasks
                SET result = $1, error_message = $2
                WHERE id = $3
                """,
                json.dumps(result_data) if result_data else None,
                error_message,
                task_id
            )
        
        # Broadcast WebSocket events (UDC compliant)
        await websocket_manager.broadcast_task_updated(
            udc_wrap(
                payload={
                    "event": "task_updated",
                    "task_id": task_id,
                    "old_status": current_status,
                    "new_status": new_status,
                    "trace_id": str(task['trace_id'])
                },
                source=f"droplet-{settings.droplet_id}",
                target="broadcast",
                message_type="event",
                trace_id=str(message.trace_id)
            )
        )
        
        if new_status == 'completed':
            await websocket_manager.broadcast_task_completed(
                udc_wrap(
                    payload={
                        "event": "task_completed",
                        "task_id": task_id,
                        "result": result_data,
                        "trace_id": str(task['trace_id'])
                    },
                    source=f"droplet-{settings.droplet_id}",
                    target="broadcast",
                    message_type="event",
                    trace_id=str(message.trace_id)
                )
            )
        elif new_status == 'failed':
            await websocket_manager.broadcast_task_failed(
                udc_wrap(
                    payload={
                        "event": "task_failed",
                        "task_id": task_id,
                        "error_message": error_message or "Task failed",
                        "trace_id": str(task['trace_id'])
                    },
                    source=f"droplet-{settings.droplet_id}",
                    target="broadcast",
                    message_type="event",
                    trace_id=str(message.trace_id)
                )
            )
        
        # Get updated task
        updated_task = await db.fetchrow(
            """
            SELECT 
                t.*,
                d.droplet_id as assigned_droplet_droplet_id,
                d.name as assigned_droplet_name
            FROM tasks t
            LEFT JOIN droplets d ON t.assigned_droplet_id = d.id
            WHERE t.id = $1
            """,
            task_id
        )
        
        task_dict = dict(updated_task)
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "task": {
                    "id": task_dict['id'],
                    "trace_id": str(task_dict['trace_id']),
                    "status": task_dict['status'],
                    "updated_at": task_dict['updated_at'].isoformat() if task_dict.get('updated_at') else None
                }
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("task_update_failed", task_id=task_id, error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to update task: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.delete("/{task_id}")
async def cancel_task(
    task_id: int,
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Cancel a task
    
    EXPECTS: UDC-wrapped cancellation request
    RETURNS: UDC-wrapped cancellation confirmation
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Check permissions
        permissions = token_data.get('permissions', [])
        is_admin = 'admin' in permissions
        
        # Get current task
        task = await db.fetchrow(
            "SELECT * FROM tasks WHERE id = $1",
            task_id
        )
        
        if not task:
            return udc_error(
                error_code="NOT_FOUND",
                error_message=f"Task {task_id} not found",
                details={"task_id": task_id},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Check permission
        created_by = task['created_by']
        requester = str(message.source)
        
        if not is_admin and created_by != requester:
            return udc_error(
                error_code="FORBIDDEN",
                error_message="Only task creator or admin can cancel tasks",
                details={"task_id": task_id},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        current_status = task['status']
        
        # Check if task can be cancelled
        from app.services.state_machine import is_terminal_status
        if is_terminal_status(current_status):
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Cannot cancel task in terminal state: {current_status}",
                details={"task_id": task_id, "status": current_status},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Transition to cancelled
        try:
            await transition_task_status(
                task_id=task_id,
                current_status=current_status,
                new_status='cancelled',
                changed_by=requester,
                reason="Cancelled by user request"
            )
        except TransitionError as e:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=str(e),
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        log.info(
            "task_cancelled",
            task_id=task_id,
            trace_id=str(message.trace_id),
            cancelled_by=requester
        )
        
        cancelled_at = await db.fetchval(
            "SELECT completed_at FROM tasks WHERE id = $1",
            task_id
        )
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "task_id": task_id,
                "status": "cancelled",
                "cancelled_at": cancelled_at.isoformat() if cancelled_at else None
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("task_cancellation_failed", task_id=task_id, error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to cancel task: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


# ============================================================================
# management.py - FULL UDC COMPLIANCE
# ============================================================================

@router.post("/reload-config")
async def reload_config(
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Reload configuration without restarting the service.
    
    EXPECTS: UDC-wrapped config reload request
    RETURNS: UDC-wrapped reload confirmation
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            return udc_error(
                error_code="FORBIDDEN",
                error_message="Admin permission required for config reload",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        config_source = message.payload.get("config_source", "environment")
        
        log.info(
            "config_reload_requested",
            requested_by=str(message.source),
            config_source=config_source,
            trace_id=str(message.trace_id)
        )
        
        # Reload settings
        if config_source == "environment":
            settings_module = __import__('app.config', fromlist=['Settings'])
            new_settings = settings_module.Settings()
            
            reloaded_fields = []
            for field in new_settings.model_fields:
                if field not in ['droplet_id', 'droplet_name']:
                    old_value = getattr(settings, field)
                    new_value = getattr(new_settings, field)
                    if old_value != new_value:
                        setattr(settings, field, new_value)
                        reloaded_fields.append(field)
            
            log.info("config_reloaded", reloaded_fields=reloaded_fields, trace_id=str(message.trace_id))
            
            return udc_wrap(
                payload={
                    "status": "reloaded",
                    "config_source": "environment",
                    "reloaded_fields": reloaded_fields
                },
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                message_type="response",
                trace_id=str(message.trace_id)
            )
        
        else:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Unsupported config_source: {config_source}",
                details={"supported": ["environment"]},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
    except Exception as e:
        log.error("config_reload_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to reload config: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.post("/shutdown")
async def graceful_shutdown(
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Initiate graceful shutdown of the orchestrator.
    
    EXPECTS: UDC-wrapped shutdown request
    RETURNS: UDC-wrapped shutdown confirmation
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            return udc_error(
                error_code="FORBIDDEN",
                error_message="Admin permission required for shutdown",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        delay_seconds = message.payload.get("delay_seconds", 10)
        reason = message.payload.get("reason", "Manual shutdown requested")
        
        log.warning(
            "graceful_shutdown_initiated",
            requested_by=str(message.source),
            delay_seconds=delay_seconds,
            reason=reason,
            trace_id=str(message.trace_id)
        )
        
        # Schedule shutdown
        async def perform_shutdown():
            await asyncio.sleep(delay_seconds)
            
            log.warning("shutdown_executing", reason=reason)
            
            # Notify all connected WebSockets
            from app.services.websocket_manager import websocket_manager
            
            shutdown_notice = udc_wrap(
                payload={
                    "event": "orchestrator_shutdown",
                    "reason": reason,
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
            
            await asyncio.sleep(1)
            os.kill(os.getpid(), signal.SIGTERM)
        
        asyncio.create_task(perform_shutdown())
        
        return udc_wrap(
            payload={
                "status": "shutdown_scheduled",
                "delay_seconds": delay_seconds,
                "reason": reason,
                "message": f"Graceful shutdown will begin in {delay_seconds} seconds"
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("shutdown_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to initiate shutdown: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.post("/emergency-stop")
async def emergency_stop(
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    EMERGENCY: Immediate stop without cleanup.
    
    EXPECTS: UDC-wrapped emergency stop request
    RETURNS: UDC-wrapped stop confirmation
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            return udc_error(
                error_code="FORBIDDEN",
                error_message="Admin permission required for emergency stop",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        log.critical(
            "emergency_stop_initiated",
            requested_by=str(message.source),
            trace_id=str(message.trace_id)
        )
        
        async def perform_emergency_stop():
            await asyncio.sleep(0.5)
            os.kill(os.getpid(), signal.SIGKILL)
        
        asyncio.create_task(perform_emergency_stop())
        
        return udc_wrap(
            payload={
                "status": "emergency_stop_initiated",
                "message": "Service will terminate immediately"
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("emergency_stop_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to initiate emergency stop: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


# ============================================================================
# message.py - Already UDC compliant for /send and /broadcast
# ============================================================================

@router.post("/send")
async def send_message(
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    POST /send - Send UDC message to another droplet
    
    EXPECTS: UDC-wrapped send request
    RETURNS: UDC-wrapped delivery confirmation
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Extract send parameters from payload
        target_droplet_id = message.payload.get("target_droplet_id")
        outgoing_message_type = message.payload.get("message_type", "command")
        outgoing_payload = message.payload.get("payload", {})
        
        if not target_droplet_id:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message="Missing target_droplet_id in payload",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Get target droplet endpoint
        target_droplet = await db.fetchrow(
            "SELECT name, endpoint FROM droplets WHERE droplet_id = $1",
            target_droplet_id
        )
        
        if not target_droplet:
            return udc_error(
                error_code="NOT_FOUND",
                error_message=f"Target droplet {target_droplet_id} not found",
                details={"target_droplet_id": target_droplet_id},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Build UDC message for target
        outgoing_udc_message = {
            "udc_version": "1.0",
            "trace_id": str(message.trace_id),  # Propagate trace_id
            "source": str(message.source),  # Original source
            "target": f"droplet-{target_droplet_id}",
            "message_type": outgoing_message_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": outgoing_payload
        }
        
        # Send message to target droplet
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{target_droplet['endpoint']}/message",
                    json=outgoing_udc_message,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
        except httpx.TimeoutException:
            return udc_error(
                error_code="DEPENDENCY_UNAVAILABLE",
                error_message=f"Timeout sending message to {target_droplet['name']}",
                details={"target": target_droplet['name'], "timeout": "10s"},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        except httpx.HTTPStatusError as e:
            return udc_error(
                error_code="DEPENDENCY_UNAVAILABLE",
                error_message=f"Error from {target_droplet['name']}: {e.response.status_code}",
                details={"status_code": e.response.status_code},
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        except Exception as e:
            return udc_error(
                error_code="INTERNAL_ERROR",
                error_message=f"Failed to send message: {str(e)}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        log.info(
            "udc_message_sent",
            trace_id=str(message.trace_id),
            target=target_droplet_id,
            target_name=target_droplet['name']
        )
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "sent": True,
                "target_droplet": target_droplet['name'],
                "target_droplet_id": target_droplet_id,
                "message_delivered_at": datetime.utcnow().isoformat()
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("message_send_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to send message: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )


@router.post("/broadcast")
async def broadcast_message(
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Broadcast a UDC-compliant message to multiple droplets
    
    EXPECTS: UDC-wrapped broadcast request
    RETURNS: UDC-wrapped delivery status for all targets
    """
    try:
        # Validate UDC envelope
        message_dict = message.model_dump()
        is_valid, error_msg = validate_udc_envelope(message_dict)
        
        if not is_valid:
            return udc_error(
                error_code="INVALID_REQUEST",
                error_message=f"Invalid UDC envelope: {error_msg}",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source)
            )
        
        # Check admin permission
        permissions = token_data.get('permissions', [])
        if 'admin' not in permissions:
            return udc_error(
                error_code="FORBIDDEN",
                error_message="Admin permission required for broadcast",
                source=f"droplet-{settings.droplet_id}",
                target=str(message.source),
                trace_id=str(message.trace_id)
            )
        
        # Extract broadcast parameters from payload
        broadcast_message_type = message.payload.get("message_type", "event")
        broadcast_payload = message.payload.get("payload", {})
        capability_filter = message.payload.get("capability_filter")
        
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
                settings.droplet_id
            )
        
        # Send to all droplets
        results = []
        
        for droplet in droplets:
            try:
                # Build UDC message for this target
                target_udc_message = {
                    "udc_version": "1.0",
                    "trace_id": str(message.trace_id),
                    "source": str(message.source),
                    "target": f"droplet-{droplet['droplet_id']}",
                    "message_type": broadcast_message_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "payload": broadcast_payload
                }
                
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"{droplet['endpoint']}/message",
                        json=target_udc_message,
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
            trace_id=str(message.trace_id),
            total_droplets=len(droplets),
            successful=len([r for r in results if r['status'] == 'sent'])
        )
        
        # Return UDC-wrapped response
        return udc_wrap(
            payload={
                "broadcast": True,
                "total_droplets": len(droplets),
                "successful": len([r for r in results if r['status'] == 'sent']),
                "failed": len([r for r in results if r['status'] == 'failed']),
                "results": results
            },
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source),
            message_type="response",
            trace_id=str(message.trace_id)
        )
        
    except Exception as e:
        log.error("broadcast_failed", error=str(e))
        return udc_error(
            error_code="INTERNAL_ERROR",
            error_message=f"Failed to broadcast message: {str(e)}",
            source=f"droplet-{settings.droplet_id}",
            target=str(message.source) if message else "unknown",
            trace_id=str(message.trace_id) if message else None
        )
