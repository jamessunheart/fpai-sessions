"""
Task State Machine
Manages valid state transitions for tasks
"""
from typing import Dict, List, Optional
import structlog

log = structlog.get_logger()

# ============================================================================
# STATE MACHINE DEFINITION
# ============================================================================

# Valid state transitions
# Key = current status, Value = list of allowed next statuses
VALID_TRANSITIONS: Dict[Optional[str], List[str]] = {
    None: ["pending"],  # Task creation
    "pending": ["assigned", "cancelled"],
    "assigned": ["in_progress", "pending", "cancelled"],  # Can unassign back to pending
    "in_progress": ["completed", "failed", "pending"],  # Can reassign on failure
    "completed": [],  # Terminal state - no transitions
    "failed": ["pending"],  # Can retry
    "cancelled": []  # Terminal state - no transitions
}

# Terminal statuses (no further transitions allowed)
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}

# Active statuses (task is being worked on)
ACTIVE_STATUSES = {"pending", "assigned", "in_progress"}


# ============================================================================
# STATE VALIDATION
# ============================================================================

def is_valid_transition(from_status: Optional[str], to_status: str) -> bool:
    """
    Check if state transition is valid
    
    Args:
        from_status: Current status (None for new task)
        to_status: Desired new status
    
    Returns:
        True if transition is valid, False otherwise
    """
    allowed_statuses = VALID_TRANSITIONS.get(from_status, [])
    return to_status in allowed_statuses


def get_allowed_transitions(current_status: str) -> List[str]:
    """
    Get list of allowed transitions from current status
    
    Args:
        current_status: Current task status
    
    Returns:
        List of allowed next statuses
    """
    return VALID_TRANSITIONS.get(current_status, [])


def is_terminal_status(status: str) -> bool:
    """
    Check if status is terminal (no further transitions)
    
    Args:
        status: Task status
    
    Returns:
        True if terminal status
    """
    return status in TERMINAL_STATUSES


def is_active_status(status: str) -> bool:
    """
    Check if status is active (task in progress)
    
    Args:
        status: Task status
    
    Returns:
        True if active status
    """
    return status in ACTIVE_STATUSES


# ============================================================================
# TRANSITION VALIDATION WITH REASONS
# ============================================================================

class TransitionError(Exception):
    """Raised when an invalid state transition is attempted"""
    pass


def validate_transition(
    from_status: Optional[str],
    to_status: str,
    raise_on_invalid: bool = True
) -> tuple[bool, Optional[str]]:
    """
    Validate state transition with detailed reason
    
    Args:
        from_status: Current status
        to_status: Desired new status
        raise_on_invalid: Raise exception if invalid (default True)
    
    Returns:
        Tuple of (is_valid, reason)
    
    Raises:
        TransitionError: If transition is invalid and raise_on_invalid=True
    """
    # Check if to_status is valid
    if to_status not in ["pending", "assigned", "in_progress", "completed", "failed", "cancelled"]:
        reason = f"Invalid status: {to_status}"
        if raise_on_invalid:
            raise TransitionError(reason)
        return False, reason
    
    # Check if current status is terminal
    if from_status and is_terminal_status(from_status):
        reason = f"Cannot transition from terminal status: {from_status}"
        if raise_on_invalid:
            raise TransitionError(reason)
        return False, reason
    
    # Check if transition is allowed
    if not is_valid_transition(from_status, to_status):
        allowed = get_allowed_transitions(from_status)
        reason = f"Invalid transition: {from_status} -> {to_status}. Allowed: {allowed}"
        if raise_on_invalid:
            raise TransitionError(reason)
        return False, reason
    
    return True, None


# ============================================================================
# STATE MACHINE OPERATIONS
# ============================================================================

async def transition_task_status(
    task_id: int,
    current_status: str,
    new_status: str,
    changed_by: str,
    reason: Optional[str] = None,
    db = None
) -> bool:
    """
    Perform task status transition with validation
    
    Args:
        task_id: Task ID
        current_status: Current task status
        new_status: Desired new status
        changed_by: Who/what is making the change (droplet_id or "system")
        reason: Optional reason for the transition
        db: Database connection
    
    Returns:
        True if transition successful
    
    Raises:
        TransitionError: If transition is invalid
    """
    from app.database import db as default_db
    
    if db is None:
        db = default_db
    
    # Validate transition
    is_valid, error_reason = validate_transition(current_status, new_status)
    if not is_valid:
        log.error(
            "invalid_state_transition",
            task_id=task_id,
            from_status=current_status,
            to_status=new_status,
            reason=error_reason
        )
        raise TransitionError(error_reason)
    
    # Update task status
    from datetime import datetime
    
    timestamp_field = None
    if new_status == "assigned":
        timestamp_field = "assigned_at"
    elif new_status == "in_progress":
        timestamp_field = "started_at"
    elif new_status in ["completed", "failed", "cancelled"]:
        timestamp_field = "completed_at"
    
    # Build update query
    if timestamp_field:
        update_query = f"""
            UPDATE tasks
            SET status = $1, {timestamp_field} = $2, updated_at = $2
            WHERE id = $3
        """
        await db.execute(update_query, new_status, datetime.utcnow(), task_id)
    else:
        update_query = """
            UPDATE tasks
            SET status = $1, updated_at = $2
            WHERE id = $3
        """
        await db.execute(update_query, new_status, datetime.utcnow(), task_id)
    
    # Record state history
    await record_state_history(
        task_id=task_id,
        from_status=current_status,
        to_status=new_status,
        changed_by=changed_by,
        reason=reason,
        db=db
    )
    
    log.info(
        "task_status_transitioned",
        task_id=task_id,
        from_status=current_status,
        to_status=new_status,
        changed_by=changed_by
    )
    
    return True


async def record_state_history(
    task_id: int,
    from_status: Optional[str],
    to_status: str,
    changed_by: str,
    reason: Optional[str] = None,
    metadata: Optional[Dict] = None,
    db = None
) -> None:
    """
    Record state transition in audit history
    
    Args:
        task_id: Task ID
        from_status: Previous status
        to_status: New status
        changed_by: Who/what made the change
        reason: Optional reason for change
        metadata: Optional additional metadata
        db: Database connection
    """
    from app.database import db as default_db
    import json
    
    if db is None:
        db = default_db
    
    await db.execute(
        """
        INSERT INTO task_state_history 
        (task_id, from_status, to_status, changed_by, reason, metadata)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        task_id,
        from_status,
        to_status,
        changed_by,
        reason,
        json.dumps(metadata) if metadata else None
    )


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

async def get_tasks_by_status(status: str, db = None) -> List[Dict]:
    """
    Get all tasks with given status
    
    Args:
        status: Task status to filter by
        db: Database connection
    
    Returns:
        List of task dictionaries
    """
    from app.database import db as default_db, records_to_dicts
    
    if db is None:
        db = default_db
    
    records = await db.fetch(
        "SELECT * FROM tasks WHERE status = $1 ORDER BY priority ASC, created_at ASC",
        status
    )
    
    return await records_to_dicts(records)


async def count_tasks_by_status(db = None) -> Dict[str, int]:
    """
    Count tasks by status
    
    Args:
        db: Database connection
    
    Returns:
        Dict mapping status -> count
    """
    from app.database import db as default_db
    
    if db is None:
        db = default_db
    
    records = await db.fetch(
        "SELECT status, COUNT(*) as count FROM tasks GROUP BY status"
    )
    
    return {record['status']: record['count'] for record in records}


# ============================================================================
# AUTOMATIC TRANSITIONS
# ============================================================================

async def auto_retry_failed_task(task_id: int, db = None) -> bool:
    """
    Automatically retry a failed task if retries remaining
    
    Args:
        task_id: Task ID
        db: Database connection
    
    Returns:
        True if task was retried, False if max retries reached
    """
    from app.database import db as default_db
    
    if db is None:
        db = default_db
    
    # Get task details
    task = await db.fetchrow(
        "SELECT * FROM tasks WHERE id = $1",
        task_id
    )
    
    if not task:
        log.error("task_not_found_for_retry", task_id=task_id)
        return False
    
    # Check if retries remaining
    if task['retry_count'] >= task['max_retries']:
        log.info(
            "max_retries_reached",
            task_id=task_id,
            retry_count=task['retry_count'],
            max_retries=task['max_retries']
        )
        return False
    
    # Increment retry count and transition to pending
    await db.execute(
        """
        UPDATE tasks
        SET status = 'pending', retry_count = retry_count + 1, 
            assigned_droplet_id = NULL, error_message = NULL
        WHERE id = $1
        """,
        task_id
    )
    
    await record_state_history(
        task_id=task_id,
        from_status="failed",
        to_status="pending",
        changed_by="system",
        reason=f"Automatic retry ({task['retry_count'] + 1}/{task['max_retries']})",
        db=db
    )
    
    log.info(
        "task_auto_retried",
        task_id=task_id,
        retry_count=task['retry_count'] + 1,
        max_retries=task['max_retries']
    )
    
    return True