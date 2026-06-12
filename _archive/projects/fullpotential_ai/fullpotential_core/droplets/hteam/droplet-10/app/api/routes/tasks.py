"""
Task Management Endpoints - WORKING UDC SOLUTION
Uses dependency-based approach to unwrap UDC envelopes

This approach:
1. Manually parses request body
2. Unwraps UDC envelope
3. Validates with Pydantic manually
4. Wraps response

It's more verbose but actually works!
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from typing import Optional
import json
import structlog
# Add missing import
from datetime import datetime, timezone

from app.models.domain import TaskCreate, TaskUpdate, TaskStatus
from app.database import db
from app.utils.auth import verify_jwt_token, get_droplet_id_from_token
from app.utils.udc_deps import parse_udc_request, wrap_udc_response, get_udc_metadata
from app.services.state_machine import transition_task_status, TransitionError
from app.services.websocket_manager import websocket_manager
from app.utils.helpers import paginate_params
from app.config import settings

log = structlog.get_logger()
router = APIRouter()


# ============================================================================
# TASK ENDPOINTS
# ============================================================================

@router.post("", status_code=201)
async def create_task(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Create a new task
    
    REQUEST: UDC envelope with TaskCreate in payload
    RESPONSE: UDC envelope with task creation result
    """
    try:
        # Parse and unwrap UDC request
        payload = await parse_udc_request(request)
        
        # Manually validate with Pydantic
        try:
            task = TaskCreate(**payload)
        except ValidationError as e:
            log.warning("task_validation_failed", errors=e.errors())
            raise HTTPException(status_code=422, detail=e.errors())
        
        # Get UDC metadata
        udc = get_udc_metadata(request)
        if task.deadline:
            if task.deadline.tzinfo is None:
                deadline_db = task.deadline  # already naive, leave it
            else:
                deadline_db = task.deadline.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            deadline_db = None
        deadline_aware = deadline_db
        # Insert task into database
        result = await db.fetchrow(
            """
            INSERT INTO tasks 
            (task_type, title, description, required_capability, priority, 
             payload, created_by, max_retries, deadline)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id, trace_id, status, created_at
            """,
            task.task_type,
            task.title,
            task.description,
            task.required_capability,
            task.priority,
            json.dumps(task.payload),  # Use task_payload
            task.created_by or f"droplet_{token_data.get('droplet_id')}",
            task.max_retries,
            deadline_aware
        )
        
        # Record initial state
        from app.services.state_machine import record_state_history
        await record_state_history(
            task_id=result['id'],
            from_status=None,
            to_status='pending',
            changed_by=f"droplet_{token_data.get('droplet_id')}"
        )
        
        # Broadcast WebSocket event
        from app.utils.udc_helpers import udc_wrap
        await websocket_manager.broadcast_task_created(
            udc_wrap(
                payload={
                    "event": "task_created",
                    "task": {
                        "id": result['id'],
                        "trace_id": str(result['trace_id']),
                        "task_type": task.task_type,
                        "title": task.title,
                        "priority": task.priority,
                        "status": result['status'],
                        "created_at": result['created_at'].isoformat()
                    }
                },
                source=f"droplet-{settings.droplet_id}",
                target="broadcast",
                message_type="event",
                trace_id=udc.get('trace_id') or str(result['trace_id'])
            )
        )
        
        log.info(
            "task_created",
            task_id=result['id'],
            trace_id=str(result['trace_id']),
            task_type=task.task_type,
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "task_id": result['id'],
                "trace_id": str(result['trace_id']),
                "status": result['status'],
                "created_at": result['created_at'].isoformat(),
                "estimated_assignment_seconds": 10
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("task_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("")
async def list_tasks(
    request: Request,
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    priority_min: Optional[int] = Query(None, ge=1, le=10),
    priority_max: Optional[int] = Query(None, ge=1, le=10),
    assigned_droplet_id: Optional[int] = Query(None),
    limit: Optional[int] = Query(50, ge=1, le=500),
    offset: Optional[int] = Query(0, ge=0),
    token_data: dict = Depends(verify_jwt_token)
):
    """
    List tasks with optional filters
    
    GET requests don't need UDC wrapping in request
    Response automatically wrapped
    """
    try:
        # Validate pagination
        limit, offset = paginate_params(limit, offset)
        
        # Build query conditions
        conditions = []
        params = []
        param_count = 1
        
        if status:
            conditions.append(f"t.status = ${param_count}")
            params.append(status)
            param_count += 1
        
        if task_type:
            conditions.append(f"t.task_type = ${param_count}")
            params.append(task_type)
            param_count += 1
        
        if priority_min:
            conditions.append(f"t.priority >= ${param_count}")
            params.append(priority_min)
            param_count += 1
        
        if priority_max:
            conditions.append(f"t.priority <= ${param_count}")
            params.append(priority_max)
            param_count += 1
        
        if assigned_droplet_id:
            droplet = await db.fetchrow(
                "SELECT id FROM droplets WHERE droplet_id = $1",
                assigned_droplet_id
            )
            if droplet:
                conditions.append(f"t.assigned_droplet_id = ${param_count}")
                params.append(droplet['id'])
                param_count += 1
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM tasks t {where_clause}"
        total = await db.fetchval(count_query, *params)
        
        # Get tasks
        tasks_query = f"""
            SELECT 
                t.*,
                d.droplet_id as assigned_droplet_droplet_id,
                d.name as assigned_droplet_name
            FROM tasks t
            LEFT JOIN droplets d ON t.assigned_droplet_id = d.id
            {where_clause}
            ORDER BY t.priority ASC, t.created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([limit, offset])
        
        tasks = await db.fetch(tasks_query, *params)
        
        # Convert to response format
        task_list = []
        for task in tasks:
            task_dict = dict(task)
            task_list.append({
                "id": task_dict['id'],
                "trace_id": str(task_dict['trace_id']),
                "task_type": task_dict['task_type'],
                "title": task_dict['title'],
                "description": task_dict['description'],
                "status": task_dict['status'],
                "priority": task_dict['priority'],
                "assigned_droplet_id": task_dict.get('assigned_droplet_droplet_id'),
                "assigned_droplet_name": task_dict.get('assigned_droplet_name'),
                "created_at": task_dict['created_at'].isoformat() if task_dict['created_at'] else None,
                "completed_at": task_dict['completed_at'].isoformat() if task_dict.get('completed_at') else None
            })
        
        # Wrap response
        return wrap_udc_response(
            {
                "tasks": task_list,
                "total": total,
                "limit": limit,
                "offset": offset
            },
            request
        )
        
    except Exception as e:
        log.error("task_list_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Get detailed task information"""
    try:
        # Get task details
        task = await db.fetchrow(
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
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Get state history
        history = await db.fetch(
            """
            SELECT from_status, to_status, changed_by, reason, changed_at
            FROM task_state_history
            WHERE task_id = $1
            ORDER BY changed_at ASC
            """,
            task_id
        )
        
        # Build response
        task_dict = dict(task)
        
        # Wrap response
        return wrap_udc_response(
            {
                "task": {
                    "id": task_dict['id'],
                    "trace_id": str(task_dict['trace_id']),
                    "task_type": task_dict['task_type'],
                    "title": task_dict['title'],
                    "description": task_dict['description'],
                    "payload": task_dict['payload'],
                    "status": task_dict['status'],
                    "priority": task_dict['priority'],
                    "assigned_droplet_id": task_dict.get('assigned_droplet_droplet_id'),
                    "assigned_droplet_name": task_dict.get('assigned_droplet_name'),
                    "created_at": task_dict['created_at'].isoformat() if task_dict['created_at'] else None,
                    "assigned_at": task_dict['assigned_at'].isoformat() if task_dict.get('assigned_at') else None,
                    "started_at": task_dict['started_at'].isoformat() if task_dict.get('started_at') else None,
                    "completed_at": task_dict['completed_at'].isoformat() if task_dict.get('completed_at') else None,
                    "result": task_dict.get('result'),
                    "error_message": task_dict.get('error_message'),
                    "state_history": [
                        {
                            "from_status": h['from_status'],
                            "to_status": h['to_status'],
                            "changed_by": h['changed_by'],
                            "reason": h['reason'],
                            "changed_at": h['changed_at'].isoformat()
                        }
                        for h in history
                    ]
                }
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("task_fetch_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch task: {str(e)}")


@router.patch("/{task_id}")
async def update_task(
    task_id: int,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Update task status"""
    try:
        # Parse and unwrap UDC request
        payload = await parse_udc_request(request)
        
        # Manually validate
        try:
            update = TaskUpdate(**payload)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
        
        # Get UDC metadata
        udc = get_udc_metadata(request)
        
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
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Verify permission
        requester_droplet_id = token_data.get('droplet_id')
        if task['assigned_droplet_droplet_id'] != requester_droplet_id:
            raise HTTPException(status_code=403, detail="Only assigned droplet can update task status")
        
        current_status = task['status']
        new_status = update.status.value
        
        # Transition state
        try:
            await transition_task_status(
                task_id=task_id,
                current_status=current_status,
                new_status=new_status,
                changed_by=f"droplet_{requester_droplet_id}"
            )
        except TransitionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Update result and error message if provided
        if update.result is not None or update.error_message is not None:
            await db.execute(
                """
                UPDATE tasks
                SET result = $1, error_message = $2
                WHERE id = $3
                """,
                json.dumps(update.result) if update.result else None,
                update.error_message,
                task_id
            )
        
        log.info("task_updated", task_id=task_id, new_status=new_status, udc_trace_id=udc.get('trace_id'))
        
        # Wrap response
        return wrap_udc_response(
            {
                "task_id": task_id,
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("task_update_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.delete("/{task_id}")
async def cancel_task(
    task_id: int,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Cancel a task"""
    try:
        # Get UDC metadata
        udc = get_udc_metadata(request)
        
        # Check permissions
        permissions = token_data.get('permissions', [])
        is_admin = 'admin' in permissions
        
        # Get current task
        task = await db.fetchrow(
            "SELECT * FROM tasks WHERE id = $1",
            task_id
        )
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Check permission
        created_by = task['created_by']
        requester = f"droplet_{token_data.get('droplet_id')}"
        
        if not is_admin and created_by != requester:
            raise HTTPException(status_code=403, detail="Only task creator or admin can cancel tasks")
        
        current_status = task['status']
        
        # Check if task can be cancelled
        from app.services.state_machine import is_terminal_status
        if is_terminal_status(current_status):
            raise HTTPException(status_code=400, detail=f"Cannot cancel task in terminal state: {current_status}")
        
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
            raise HTTPException(status_code=400, detail=str(e))
        
        log.info("task_cancelled", task_id=task_id, cancelled_by=requester, udc_trace_id=udc.get('trace_id'))
        
        # Wrap response
        return wrap_udc_response(
            {
                "task_id": task_id,
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).isoformat()
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("task_cancellation_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")

