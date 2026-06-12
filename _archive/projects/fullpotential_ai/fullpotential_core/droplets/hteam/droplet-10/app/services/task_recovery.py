"""
Task Recovery Service
Automatic task reassignment and recovery from failures
"""
from typing import List, Dict
from datetime import datetime, timedelta
import structlog

from app.database import db
from app.config import settings
from app.services.task_router import reassign_task
from app.services.state_machine import auto_retry_failed_task

log = structlog.get_logger()


# ============================================================================
# TASK RECOVERY
# ============================================================================

async def recover_stalled_tasks() -> Dict:
    """
    Recover tasks that are stalled in in_progress state
    
    Tasks are considered stalled if:
    - Status is 'in_progress' 
    - Started more than 1 hour ago
    - No recent updates
    
    Returns:
        Dict with recovery statistics
    """
    try:
        stall_threshold = datetime.utcnow() - timedelta(hours=1)
        
        # Find stalled tasks
        stalled_tasks = await db.fetch(
            """
            SELECT id, task_type, title, assigned_droplet_id, started_at
            FROM tasks
            WHERE status = 'in_progress'
              AND started_at < $1
              AND updated_at < $1
            """,
            stall_threshold
        )
        
        recovered_count = 0
        failed_count = 0
        
        for task in stalled_tasks:
            try:
                # Attempt to reassign stalled task
                new_droplet_id = await reassign_task(
                    task['id'],
                    reason="Task stalled - no updates for 1+ hour"
                )
                
                if new_droplet_id:
                    recovered_count += 1
                    log.info(
                        "stalled_task_recovered",
                        task_id=task['id'],
                        task_type=task['task_type'],
                        stalled_since=task['started_at']
                    )
                else:
                    failed_count += 1
                    
            except Exception as e:
                log.error(
                    "task_recovery_failed",
                    task_id=task['id'],
                    error=str(e)
                )
                failed_count += 1
        
        result = {
            "stalled_found": len(stalled_tasks),
            "recovered": recovered_count,
            "failed": failed_count,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        if recovered_count > 0:
            log.info("stalled_tasks_recovery_completed", **result)
        
        return result
        
    except Exception as e:
        log.error("recover_stalled_tasks_failed", error=str(e))
        return {
            "stalled_found": 0,
            "recovered": 0,
            "failed": 0,
            "error": str(e)
        }


async def recover_timeout_tasks() -> Dict:
    """
    Recover tasks that have exceeded their deadline
    
    Tasks past deadline are marked as failed with timeout error
    
    Returns:
        Dict with recovery statistics
    """
    try:
        now = datetime.utcnow()
        
        # Find tasks past deadline
        timeout_tasks = await db.fetch(
            """
            SELECT id, task_type, title, deadline
            FROM tasks
            WHERE status IN ('assigned', 'in_progress')
              AND deadline IS NOT NULL
              AND deadline < $1
            """,
            now
        )
        
        failed_count = 0
        
        for task in timeout_tasks:
            try:
                # Mark as failed with timeout message
                await db.execute(
                    """
                    UPDATE tasks
                    SET status = 'failed', 
                        error_message = 'Task exceeded deadline',
                        completed_at = $1,
                        updated_at = $1
                    WHERE id = $2
                    """,
                    now,
                    task['id']
                )
                
                # Record state history
                from app.services.state_machine import record_state_history
                await record_state_history(
                    task_id=task['id'],
                    from_status='in_progress',
                    to_status='failed',
                    changed_by='system',
                    reason=f"Deadline exceeded: {task['deadline']}"
                )
                
                failed_count += 1
                
                log.warning(
                    "task_deadline_exceeded",
                    task_id=task['id'],
                    task_type=task['task_type'],
                    deadline=task['deadline']
                )
                
            except Exception as e:
                log.error(
                    "timeout_task_recovery_failed",
                    task_id=task['id'],
                    error=str(e)
                )
        
        result = {
            "timeout_found": len(timeout_tasks),
            "failed": failed_count,
            "checked_at": now.isoformat()
        }
        
        if failed_count > 0:
            log.info("timeout_tasks_recovery_completed", **result)
        
        return result
        
    except Exception as e:
        log.error("recover_timeout_tasks_failed", error=str(e))
        return {
            "timeout_found": 0,
            "failed": 0,
            "error": str(e)
        }


async def retry_failed_tasks() -> Dict:
    """
    Automatically retry failed tasks that haven't exceeded max_retries
    
    Returns:
        Dict with retry statistics
    """
    try:
        # Find failed tasks eligible for retry
        retry_candidates = await db.fetch(
            """
            SELECT id, task_type, title, retry_count, max_retries
            FROM tasks
            WHERE status = 'failed'
              AND retry_count < max_retries
              AND completed_at > NOW() - INTERVAL '1 hour'
            ORDER BY priority ASC, completed_at ASC
            LIMIT 50
            """
        )
        
        retried_count = 0
        
        for task in retry_candidates:
            try:
                success = await auto_retry_failed_task(task['id'])
                
                if success:
                    retried_count += 1
                    log.info(
                        "task_auto_retried",
                        task_id=task['id'],
                        task_type=task['task_type'],
                        retry_attempt=task['retry_count'] + 1,
                        max_retries=task['max_retries']
                    )
                    
            except Exception as e:
                log.error(
                    "task_retry_failed",
                    task_id=task['id'],
                    error=str(e)
                )
        
        result = {
            "candidates_found": len(retry_candidates),
            "retried": retried_count,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        if retried_count > 0:
            log.info("failed_tasks_retry_completed", **result)
        
        return result
        
    except Exception as e:
        log.error("retry_failed_tasks_failed", error=str(e))
        return {
            "candidates_found": 0,
            "retried": 0,
            "error": str(e)
        }


async def cleanup_orphaned_tasks() -> Dict:
    """
    Clean up tasks assigned to droplets that no longer exist
    
    Returns:
        Dict with cleanup statistics
    """
    try:
        # Find tasks assigned to non-existent droplets
        orphaned_tasks = await db.fetch(
            """
            SELECT t.id, t.task_type, t.title, t.assigned_droplet_id
            FROM tasks t
            WHERE t.status IN ('assigned', 'in_progress')
              AND t.assigned_droplet_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM droplets d
                  WHERE d.id = t.assigned_droplet_id
              )
            """
        )
        
        reassigned_count = 0
        
        for task in orphaned_tasks:
            try:
                # Reassign orphaned task
                new_droplet_id = await reassign_task(
                    task['id'],
                    reason="Assigned droplet no longer exists"
                )
                
                if new_droplet_id:
                    reassigned_count += 1
                    log.info(
                        "orphaned_task_reassigned",
                        task_id=task['id'],
                        task_type=task['task_type'],
                        old_droplet_id=task['assigned_droplet_id']
                    )
                    
            except Exception as e:
                log.error(
                    "orphaned_task_cleanup_failed",
                    task_id=task['id'],
                    error=str(e)
                )
        
        result = {
            "orphaned_found": len(orphaned_tasks),
            "reassigned": reassigned_count,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        if reassigned_count > 0:
            log.info("orphaned_tasks_cleanup_completed", **result)
        
        return result
        
    except Exception as e:
        log.error("cleanup_orphaned_tasks_failed", error=str(e))
        return {
            "orphaned_found": 0,
            "reassigned": 0,
            "error": str(e)
        }


async def run_all_recovery_tasks() -> Dict:
    """
    Run all recovery tasks in sequence
    
    This is the main entry point for the recovery scheduler
    
    Returns:
        Dict with combined recovery statistics
    """
    log.info("starting_task_recovery_cycle")
    
    results = {
        "started_at": datetime.utcnow().isoformat()
    }
    
    # 1. Recover stalled tasks
    if settings.enable_auto_recovery:
        results["stalled"] = await recover_stalled_tasks()
    
    # 2. Handle timeout tasks
    results["timeout"] = await recover_timeout_tasks()
    
    # 3. Retry failed tasks
    results["retry"] = await retry_failed_tasks()
    
    # 4. Clean up orphaned tasks
    if settings.enable_auto_recovery:
        results["orphaned"] = await cleanup_orphaned_tasks()
    
    results["completed_at"] = datetime.utcnow().isoformat()
    
    log.info("task_recovery_cycle_completed", summary=results)
    
    return results