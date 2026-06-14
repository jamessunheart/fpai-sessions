"""
Health Monitor Service
Background monitoring of droplet health and automatic recovery
"""
from datetime import datetime, timedelta
from typing import Dict, List
import structlog

from app.config import settings
from app.database import db
from app.services.task_router import reassign_droplet_tasks

log = structlog.get_logger()


# ============================================================================
# HEARTBEAT MONITORING
# ============================================================================

async def check_droplet_health() -> Dict:
    """
    Check all droplet health and mark inactive if heartbeat missed
    Called every 60 seconds by scheduler
    
    Returns:
        Dict with monitoring results
    """
    threshold = datetime.utcnow() - timedelta(seconds=settings.heartbeat_timeout)
    
    # Find droplets with stale heartbeats
    stale_droplets = await db.fetch(
        """
        SELECT id, droplet_id, name, last_heartbeat, status
        FROM droplets
        WHERE status = 'active'
          AND (last_heartbeat IS NULL OR last_heartbeat < $1)
        """,
        threshold
    )
    
    results = {
        "checked_at": datetime.utcnow().isoformat(),
        "stale_droplets_found": len(stale_droplets),
        "droplets_marked_inactive": 0,
        "tasks_reassigned": 0
    }
    
    if not stale_droplets:
        log.debug("health_check_completed", active_droplets="all_healthy")
        return results
    
    # Mark stale droplets as inactive and reassign tasks
    for droplet in stale_droplets:
        try:
            # Mark droplet inactive
            await db.execute(
                """
                UPDATE droplets
                SET status = 'inactive', updated_at = $1
                WHERE id = $2
                """,
                datetime.utcnow(),
                droplet['id']
            )
            
            results["droplets_marked_inactive"] += 1
            
            log.warning(
                "droplet_marked_inactive",
                droplet_id=droplet['droplet_id'],
                droplet_name=droplet['name'],
                last_heartbeat=droplet['last_heartbeat'],
                seconds_since_heartbeat=(
                    (datetime.utcnow() - droplet['last_heartbeat']).total_seconds()
                    if droplet['last_heartbeat'] else None
                )
            )
            
            # Reassign tasks from this droplet
            if settings.enable_auto_recovery:
                reassigned = await reassign_droplet_tasks(
                    droplet['id'],
                    reason=f"Droplet #{droplet['droplet_id']} heartbeat timeout"
                )
                results["tasks_reassigned"] += reassigned
            
            # Broadcast WebSocket event
            from app.services.websocket_manager import websocket_manager
            await websocket_manager.broadcast_droplet_health_changed(
                droplet['droplet_id'],
                'active',
                'inactive'
            )
            
        except Exception as e:
            log.error(
                "health_check_failed_for_droplet",
                droplet_id=droplet['droplet_id'],
                error=str(e)
            )
    
    log.info(
        "health_check_completed",
        **results
    )
    
    return results


# ============================================================================
# DROPLET REGISTRATION
# ============================================================================

async def register_droplet(
    droplet_id: int,
    name: str,
    steward: str,
    endpoint: str,
    capabilities: List[str]
) -> Dict:
    """
    Register or update droplet in directory
    
    Args:
        droplet_id: Unique droplet ID
        name: Droplet name
        steward: Droplet steward
        endpoint: Droplet endpoint URL
        capabilities: List of capabilities
    
    Returns:
        Registration result dict
    """
    import json
    
    # Check if droplet already exists
    existing = await db.fetchrow(
        "SELECT id, status FROM droplets WHERE droplet_id = $1",
        droplet_id
    )
    
    now = datetime.utcnow()
    
    if existing:
        # Update existing droplet
        await db.execute(
            """
            UPDATE droplets
            SET name = $1, steward = $2, endpoint = $3, capabilities = $4,
                status = 'active', last_heartbeat = $5, updated_at = $5
            WHERE droplet_id = $6
            """,
            name,
            steward,
            endpoint,
            json.dumps(capabilities),
            now,
            droplet_id
        )
        
        log.info(
            "droplet_re_registered",
            droplet_id=droplet_id,
            name=name,
            previous_status=existing['status']
        )
        
        return {
            "registered": True,
            "droplet_id": droplet_id,
            "registered_at": now.isoformat(),
            "heartbeat_required_every_seconds": settings.heartbeat_check_interval,
            "status": "updated"
        }
    else:
        # Insert new droplet
        await db.execute(
            """
            INSERT INTO droplets 
            (droplet_id, name, steward, endpoint, capabilities, status, last_heartbeat, registered_at)
            VALUES ($1, $2, $3, $4, $5, 'active', $6, $6)
            """,
            droplet_id,
            name,
            steward,
            endpoint,
            json.dumps(capabilities),
            now
        )
        
        log.info(
            "droplet_registered",
            droplet_id=droplet_id,
            name=name,
            steward=steward,
            capabilities=capabilities
        )
        
        # Broadcast WebSocket event
        from app.services.websocket_manager import websocket_manager
        await websocket_manager.broadcast_droplet_registered(droplet_id, name)
        
        return {
            "registered": True,
            "droplet_id": droplet_id,
            "registered_at": now.isoformat(),
            "heartbeat_required_every_seconds": settings.heartbeat_check_interval,
            "status": "new"
        }


# ============================================================================
# HEARTBEAT PROCESSING
# ============================================================================

async def process_heartbeat(
    droplet_id: int,
    status: str,
    metrics: Dict = None
) -> Dict:
    """
    Process heartbeat from droplet
    
    Args:
        droplet_id: Droplet ID
        status: Current droplet status
        metrics: Optional performance metrics
    
    Returns:
        Heartbeat acknowledgment dict
    """
    import json
    
    # Get droplet
    droplet = await db.fetchrow(
        "SELECT id, name, status as current_status FROM droplets WHERE droplet_id = $1",
        droplet_id
    )
    
    if not droplet:
        log.warning("heartbeat_from_unregistered_droplet", droplet_id=droplet_id)
        raise ValueError(f"Droplet {droplet_id} not registered")
    
    now = datetime.utcnow()
    
    # Update droplet last_heartbeat
    await db.execute(
        """
        UPDATE droplets
        SET last_heartbeat = $1, status = $2, updated_at = $1
        WHERE id = $3
        """,
        now,
        status,
        droplet['id']
    )
    
    # Record heartbeat in history
    await db.execute(
        """
        INSERT INTO heartbeats (droplet_id, status, metrics, received_at)
        VALUES ($1, $2, $3, $4)
        """,
        droplet['id'],
        status,
        json.dumps(metrics) if metrics else None,
        now
    )
    
    # If status changed from inactive to active, log recovery
    if droplet['current_status'] == 'inactive' and status == 'active':
        log.info(
            "droplet_recovered",
            droplet_id=droplet_id,
            droplet_name=droplet['name']
        )
        
        # Broadcast WebSocket event
        from app.services.websocket_manager import websocket_manager
        await websocket_manager.broadcast_droplet_health_changed(
            droplet_id,
            'inactive',
            'active'
        )
    
    # Calculate next heartbeat deadline
    next_deadline = now + timedelta(seconds=settings.heartbeat_check_interval)
    
    return {
        "received": True,
        "next_heartbeat_deadline": next_deadline.isoformat()
    }


# ============================================================================
# CLEANUP OPERATIONS
# ============================================================================

async def cleanup_old_heartbeats() -> int:
    """
    Remove heartbeat records older than retention period
    Called periodically by scheduler
    
    Returns:
        Number of records deleted
    """
    threshold = datetime.utcnow() - timedelta(seconds=settings.heartbeat_retention)
    
    result = await db.fetchval(
        """
        WITH deleted AS (
            DELETE FROM heartbeats
            WHERE received_at < $1
            RETURNING *
        )
        SELECT COUNT(*) FROM deleted
        """,
        threshold
    )
    
    if result and result > 0:
        log.info("old_heartbeats_cleaned_up", deleted_count=result)
    
    return result or 0


# ============================================================================
# DROPLET QUERIES
# ============================================================================

async def get_active_droplets() -> List[Dict]:
    """
    Get all active droplets
    
    Returns:
        List of active droplet dicts
    """
    droplets = await db.fetch(
        """
        SELECT droplet_id, name, steward, endpoint, capabilities, 
               last_heartbeat, registered_at,
               EXTRACT(EPOCH FROM (NOW() - last_heartbeat)) as seconds_since_heartbeat
        FROM droplets
        WHERE status = 'active'
        ORDER BY droplet_id ASC
        """
    )
    
    return [dict(record) for record in droplets]


async def get_droplet_info(droplet_id: int) -> Dict:
    """
    Get detailed droplet information
    
    Args:
        droplet_id: Droplet ID
    
    Returns:
        Droplet info dict with task history
    """
    # Get droplet details
    droplet = await db.fetchrow(
        """
        SELECT d.*, 
               EXTRACT(EPOCH FROM (NOW() - d.last_heartbeat)) as seconds_since_heartbeat,
               COUNT(t.id) FILTER (WHERE t.status IN ('assigned', 'in_progress')) as active_tasks,
               COUNT(t.id) FILTER (WHERE t.status = 'completed') as completed_tasks,
               COUNT(t.id) FILTER (WHERE t.status = 'failed') as failed_tasks
        FROM droplets d
        LEFT JOIN tasks t ON t.assigned_droplet_id = d.id
        WHERE d.droplet_id = $1
        GROUP BY d.id
        """,
        droplet_id
    )
    
    if not droplet:
        return None
    
    # Get recent tasks
    recent_tasks = await db.fetch(
        """
        SELECT t.id, t.status, t.task_type, t.created_at, t.completed_at
        FROM tasks t
        JOIN droplets d ON t.assigned_droplet_id = d.id
        WHERE d.droplet_id = $1
        ORDER BY t.created_at DESC
        LIMIT 10
        """,
        droplet_id
    )
    
    # Get 24h health history
    health_history = await db.fetch(
        """
        SELECT received_at as time, status
        FROM heartbeats h
        JOIN droplets d ON h.droplet_id = d.id
        WHERE d.droplet_id = $1
          AND received_at > NOW() - INTERVAL '24 hours'
        ORDER BY received_at DESC
        LIMIT 100
        """,
        droplet_id
    )
    
    droplet_dict = dict(droplet)
    droplet_dict['recent_tasks'] = [dict(t) for t in recent_tasks]
    droplet_dict['health_history_24h'] = [
        {"time": h['time'].isoformat(), "status": h['status']}
        for h in health_history
    ]
    
    return droplet_dict


async def get_droplet_health_summary() -> Dict:
    """
    Get system-wide droplet health summary
    
    Returns:
        Health summary dict
    """
    summary = await db.fetchrow(
        """
        SELECT 
            COUNT(*) as total_droplets,
            COUNT(*) FILTER (WHERE status = 'active') as active_droplets,
            COUNT(*) FILTER (WHERE status = 'inactive') as inactive_droplets,
            COUNT(*) FILTER (WHERE status = 'error') as error_droplets
        FROM droplets
        """
    )
    
    return dict(summary) if summary else {}