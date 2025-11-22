"""
Task Router Service
Intelligent task routing to capable droplets
"""
from typing import Dict, List, Optional
import structlog

from app.database import db
from app.utils.helpers import capability_matches

log = structlog.get_logger()


# ============================================================================
# TASK ROUTING
# ============================================================================

async def route_task(task_id: int) -> Optional[int]:
    """
    Route task to best available droplet
    
    Algorithm:
    1. Filter droplets by required capability
    2. Filter by status=active (exclude inactive/error)
    3. Sort by current load (fewest active tasks first)
    4. Assign to first available droplet
    
    Args:
        task_id: Task ID to route
    
    Returns:
        Assigned droplet ID or None if no capable droplet available
    """
    # Get task details
    task = await db.fetchrow(
        "SELECT * FROM tasks WHERE id = $1",
        task_id
    )
    
    if not task:
        log.error("task_not_found_for_routing", task_id=task_id)
        return None
    
    required_capability = task['required_capability']
    
    log.info(
        "routing_task",
        task_id=task_id,
        task_type=task['task_type'],
        required_capability=required_capability,
        priority=task['priority']
    )
    
    # Find capable droplet
    droplet_id = await find_capable_droplet(
        required_capability=required_capability,
        task_priority=task['priority']
    )
    
    if droplet_id is None:
        log.warning(
            "no_capable_droplet_found",
            task_id=task_id,
            required_capability=required_capability
        )
        return None
    
    # Assign task to droplet
    from datetime import datetime
    await db.execute(
        """
        UPDATE tasks
        SET assigned_droplet_id = $1, status = 'assigned', assigned_at = $2, updated_at = $2
        WHERE id = $3
        """,
        droplet_id,
        datetime.utcnow(),
        task_id
    )
    
    # Record state history
    from app.services.state_machine import record_state_history
    await record_state_history(
        task_id=task_id,
        from_status='pending',
        to_status='assigned',
        changed_by='orchestrator',
        reason=f'Routed to droplet #{droplet_id}'
    )
    
    log.info(
        "task_routed",
        task_id=task_id,
        droplet_id=droplet_id,
        trace_id=str(task['trace_id'])
    )
    
    return droplet_id


async def find_capable_droplet(
    required_capability: Optional[str],
    task_priority: int = 5
) -> Optional[int]:
    """
    Find best droplet for task based on capability and load
    
    Args:
        required_capability: Required capability string
        task_priority: Task priority (lower = higher priority)
    
    Returns:
        Droplet internal ID or None if no capable droplet
    """
    # Build query based on whether capability is required
    if required_capability:
        # Get active droplets with required capability
        capable_droplets = await db.fetch(
            """
            SELECT d.id, d.droplet_id, d.name, d.capabilities,
                   COUNT(t.id) FILTER (WHERE t.status IN ('assigned', 'in_progress')) as active_tasks
            FROM droplets d
            LEFT JOIN tasks t ON t.assigned_droplet_id = d.id
            WHERE d.status = 'active'
              AND d.capabilities @> $1::jsonb
            GROUP BY d.id, d.droplet_id, d.name, d.capabilities
            ORDER BY active_tasks ASC, d.last_heartbeat DESC
            """,
            f'["{required_capability}"]'
        )
    else:
        # No specific capability required - any active droplet works
        capable_droplets = await db.fetch(
            """
            SELECT d.id, d.droplet_id, d.name, d.capabilities,
                   COUNT(t.id) FILTER (WHERE t.status IN ('assigned', 'in_progress')) as active_tasks
            FROM droplets d
            LEFT JOIN tasks t ON t.assigned_droplet_id = d.id
            WHERE d.status = 'active'
            GROUP BY d.id, d.droplet_id, d.name, d.capabilities
            ORDER BY active_tasks ASC, d.last_heartbeat DESC
            """
        )
    
    if not capable_droplets:
        return None
    
    # Return the droplet with fewest active tasks (already sorted)
    best_droplet = capable_droplets[0]
    
    log.info(
        "droplet_selected",
        droplet_id=best_droplet['droplet_id'],
        droplet_name=best_droplet['name'],
        active_tasks=best_droplet['active_tasks'],
        required_capability=required_capability
    )
    
    return best_droplet['id']  # Return internal ID for FK relationship


# ============================================================================
# BATCH ROUTING
# ============================================================================

async def route_pending_tasks(max_tasks: int = 100) -> int:
    """
    Route all pending tasks (up to max_tasks)
    Called periodically by background scheduler
    
    Args:
        max_tasks: Maximum number of tasks to route in one batch
    
    Returns:
        Number of tasks successfully routed
    """
    # Get pending tasks ordered by priority (1=highest) then FIFO
    pending_tasks = await db.fetch(
        """
        SELECT id FROM tasks
        WHERE status = 'pending'
        ORDER BY priority ASC, created_at ASC
        LIMIT $1
        """,
        max_tasks
    )
    
    if not pending_tasks:
        return 0
    
    routed_count = 0
    
    for task_record in pending_tasks:
        task_id = task_record['id']
        
        try:
            droplet_id = await route_task(task_id)
            if droplet_id:
                routed_count += 1
        except Exception as e:
            log.error(
                "task_routing_failed",
                task_id=task_id,
                error=str(e)
            )
    
    if routed_count > 0:
        log.info(
            "batch_routing_completed",
            total_pending=len(pending_tasks),
            routed=routed_count,
            failed=len(pending_tasks) - routed_count
        )
    
    return routed_count


# ============================================================================
# TASK REASSIGNMENT
# ============================================================================

async def reassign_task(
    task_id: int,
    reason: str = "Reassignment requested"
) -> Optional[int]:
    """
    Reassign task to a different droplet
    
    Args:
        task_id: Task ID to reassign
        reason: Reason for reassignment
    
    Returns:
        New droplet ID or None if reassignment failed
    """
    # Get current task state
    task = await db.fetchrow(
        "SELECT * FROM tasks WHERE id = $1",
        task_id
    )
    
    if not task:
        log.error("task_not_found_for_reassignment", task_id=task_id)
        return None
    
    current_status = task['status']
    current_droplet_id = task['assigned_droplet_id']
    
    # Can only reassign assigned or in_progress tasks
    if current_status not in ['assigned', 'in_progress']:
        log.warning(
            "cannot_reassign_task",
            task_id=task_id,
            status=current_status,
            reason="Only assigned/in_progress tasks can be reassigned"
        )
        return None
    
    # Transition back to pending
    from datetime import datetime
    await db.execute(
        """
        UPDATE tasks
        SET status = 'pending', assigned_droplet_id = NULL, 
            started_at = NULL, updated_at = $1
        WHERE id = $2
        """,
        datetime.utcnow(),
        task_id
    )
    
    # Record state history
    from app.services.state_machine import record_state_history
    await record_state_history(
        task_id=task_id,
        from_status=current_status,
        to_status='pending',
        changed_by='orchestrator',
        reason=reason
    )
    
    log.info(
        "task_unassigned_for_reassignment",
        task_id=task_id,
        previous_droplet_id=current_droplet_id,
        reason=reason
    )
    
    # Route to new droplet
    new_droplet_id = await route_task(task_id)
    
    if new_droplet_id:
        log.info(
            "task_reassigned",
            task_id=task_id,
            old_droplet_id=current_droplet_id,
            new_droplet_id=new_droplet_id
        )
    
    return new_droplet_id


async def reassign_droplet_tasks(droplet_id: int, reason: str = "Droplet unavailable") -> int:
    """
    Reassign all tasks from a specific droplet
    Used when droplet goes offline or fails
    
    Args:
        droplet_id: Droplet internal ID
        reason: Reason for bulk reassignment
    
    Returns:
        Number of tasks reassigned
    """
    # Get all active tasks assigned to this droplet
    tasks = await db.fetch(
        """
        SELECT id FROM tasks
        WHERE assigned_droplet_id = $1
          AND status IN ('assigned', 'in_progress')
        """,
        droplet_id
    )
    
    if not tasks:
        return 0
    
    reassigned_count = 0
    
    for task_record in tasks:
        task_id = task_record['id']
        
        try:
            new_droplet_id = await reassign_task(task_id, reason)
            if new_droplet_id:
                reassigned_count += 1
        except Exception as e:
            log.error(
                "task_reassignment_failed",
                task_id=task_id,
                error=str(e)
            )
    
    log.info(
        "bulk_reassignment_completed",
        droplet_id=droplet_id,
        total_tasks=len(tasks),
        reassigned=reassigned_count,
        reason=reason
    )
    
    return reassigned_count


# ============================================================================
# ROUTING METRICS
# ============================================================================

async def get_routing_metrics() -> Dict:
    """
    Get task routing metrics
    
    Returns:
        Dict with routing statistics
    """
    # Tasks by status
    status_counts = await db.fetch(
        """
        SELECT status, COUNT(*) as count
        FROM tasks
        GROUP BY status
        """
    )
    
    status_dict = {record['status']: record['count'] for record in status_counts}
    
    # Average routing time (pending to assigned)
    avg_routing_time = await db.fetchval(
        """
        SELECT AVG(EXTRACT(EPOCH FROM (assigned_at - created_at)))
        FROM tasks
        WHERE assigned_at IS NOT NULL
          AND created_at > NOW() - INTERVAL '24 hours'
        """
    )
    
    # Droplet load distribution
    droplet_loads = await db.fetch(
        """
        SELECT 
            d.droplet_id,
            d.name,
            COUNT(t.id) FILTER (WHERE t.status IN ('assigned', 'in_progress')) as active_tasks
        FROM droplets d
        LEFT JOIN tasks t ON t.assigned_droplet_id = d.id
        WHERE d.status = 'active'
        GROUP BY d.droplet_id, d.name
        ORDER BY active_tasks DESC
        """
    )
    
    return {
        "tasks_by_status": status_dict,
        "average_routing_time_seconds": round(avg_routing_time or 0, 2),
        "pending_tasks": status_dict.get('pending', 0),
        "active_tasks": status_dict.get('assigned', 0) + status_dict.get('in_progress', 0),
        "droplet_load_distribution": [
            {
                "droplet_id": record['droplet_id'],
                "name": record['name'],
                "active_tasks": record['active_tasks']
            }
            for record in droplet_loads
        ]
    }


# ============================================================================
# CAPABILITY DISCOVERY
# ============================================================================

async def get_droplets_by_capability(capability: str) -> List[Dict]:
    """
    Find all droplets with specific capability
    
    Args:
        capability: Required capability string
    
    Returns:
        List of droplet info dicts
    """
    droplets = await db.fetch(
        """
        SELECT droplet_id, name, steward, endpoint, capabilities, status
        FROM droplets
        WHERE capabilities @> $1::jsonb
        ORDER BY status DESC, name ASC
        """,
        f'["{capability}"]'
    )
    
    return [dict(record) for record in droplets]


async def get_all_capabilities() -> List[str]:
    """
    Get list of all unique capabilities across all droplets
    
    Returns:
        List of capability strings
    """
    result = await db.fetchval(
        """
        SELECT DISTINCT jsonb_array_elements_text(capabilities)
        FROM droplets
        """
    )
    
    return result if result else []