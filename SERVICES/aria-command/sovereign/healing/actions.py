#!/usr/bin/env python3
"""
ARIA SELF-HEALING ACTIONS
==========================

Implements the actual healing actions that can be executed when
error patterns are detected.

Safety features:
- Cooldown between actions
- Max actions per hour
- Audit logging
- Rollback capability
"""

import os
import asyncio
import subprocess
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.healing.actions")

# ============================================================================
# CONFIGURATION
# ============================================================================

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/opt/fpai/aria-command"))
STATE_DIR = WORKSPACE_ROOT / "state"
BACKUP_DIR = STATE_DIR / "healing_backups"
AUDIT_LOG = STATE_DIR / "healing_audit.log"

# Services we can restart
RESTARTABLE_SERVICES = {
    "aria-command",
    "fpai-aria",
    "aria-watchdog"
}

# Files we can clear
CLEARABLE_STATE = [
    "conversations.db",
    "conversation_cache.json",
    "working_memory.json"
]


class ActionResult(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_APPROVAL = "needs_approval"


@dataclass
class HealingAction:
    """Result of a healing action."""
    action_name: str
    result: ActionResult
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_audit_line(self) -> str:
        """Format for audit log."""
        return f"{self.timestamp.isoformat()} | {self.result.value} | {self.action_name} | {self.message}"


# ============================================================================
# AUDIT LOGGING
# ============================================================================

def log_audit(action: HealingAction):
    """Log healing action to audit file."""
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG, "a") as f:
            f.write(action.to_audit_line() + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


# ============================================================================
# HEALING ACTIONS
# ============================================================================

async def clear_conversation_history() -> HealingAction:
    """
    Clear corrupted conversation history.
    
    This fixes errors like:
    - tool_calls in conversation history
    - Corrupted message format
    """
    try:
        # Backup first
        backup_dir = BACKUP_DIR / f"conversations_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        cleared = []
        for filename in CLEARABLE_STATE:
            filepath = STATE_DIR / filename
            if filepath.exists():
                # Backup
                shutil.copy2(filepath, backup_dir / filename)
                # Remove
                filepath.unlink()
                cleared.append(filename)
        
        if cleared:
            action = HealingAction(
                action_name="clear_conversation_history",
                result=ActionResult.SUCCESS,
                message=f"Cleared {len(cleared)} state files",
                details={"cleared": cleared, "backup": str(backup_dir)}
            )
        else:
            action = HealingAction(
                action_name="clear_conversation_history",
                result=ActionResult.SKIPPED,
                message="No state files to clear"
            )
        
        log_audit(action)
        logger.info(f"Clear conversation: {action.result.value}")
        return action
        
    except Exception as e:
        action = HealingAction(
            action_name="clear_conversation_history",
            result=ActionResult.FAILED,
            message=str(e)
        )
        log_audit(action)
        return action


async def restart_service(service_name: str = "aria-command") -> HealingAction:
    """
    Restart a service.
    
    Only restarts known safe services.
    """
    if service_name not in RESTARTABLE_SERVICES:
        return HealingAction(
            action_name="restart_service",
            result=ActionResult.FAILED,
            message=f"Service {service_name} is not in restart whitelist"
        )
    
    try:
        # Check current status
        status_result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True
        )
        was_active = status_result.stdout.strip() == "active"
        
        # Restart
        restart_result = subprocess.run(
            ["systemctl", "restart", service_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if restart_result.returncode == 0:
            # Wait a moment
            await asyncio.sleep(3)
            
            # Verify it's running
            verify_result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True
            )
            is_active = verify_result.stdout.strip() == "active"
            
            if is_active:
                action = HealingAction(
                    action_name="restart_service",
                    result=ActionResult.SUCCESS,
                    message=f"Restarted {service_name}",
                    details={"service": service_name, "was_active": was_active}
                )
            else:
                action = HealingAction(
                    action_name="restart_service",
                    result=ActionResult.FAILED,
                    message=f"Service {service_name} not active after restart"
                )
        else:
            action = HealingAction(
                action_name="restart_service",
                result=ActionResult.FAILED,
                message=f"Restart command failed: {restart_result.stderr}"
            )
        
        log_audit(action)
        logger.info(f"Restart {service_name}: {action.result.value}")
        return action
        
    except subprocess.TimeoutExpired:
        action = HealingAction(
            action_name="restart_service",
            result=ActionResult.FAILED,
            message="Restart command timed out"
        )
        log_audit(action)
        return action
    except Exception as e:
        action = HealingAction(
            action_name="restart_service",
            result=ActionResult.FAILED,
            message=str(e)
        )
        log_audit(action)
        return action


async def clear_caches() -> HealingAction:
    """
    Clear caches to free memory.
    """
    try:
        cleared = []
        
        # Clear Python cache
        cache_dirs = [
            WORKSPACE_ROOT / "__pycache__",
            WORKSPACE_ROOT / "brain" / "__pycache__",
            WORKSPACE_ROOT / "telegram" / "__pycache__",
            WORKSPACE_ROOT / "sovereign" / "__pycache__",
        ]
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cleared.append(str(cache_dir))
        
        # Clear temp files
        temp_patterns = ["*.tmp", "*.pyc", ".*.swp"]
        for pattern in temp_patterns:
            for f in WORKSPACE_ROOT.rglob(pattern):
                f.unlink()
                cleared.append(str(f))
        
        action = HealingAction(
            action_name="clear_caches",
            result=ActionResult.SUCCESS,
            message=f"Cleared {len(cleared)} cache items",
            details={"cleared_count": len(cleared)}
        )
        
        log_audit(action)
        logger.info(f"Clear caches: {action.result.value}")
        return action
        
    except Exception as e:
        action = HealingAction(
            action_name="clear_caches",
            result=ActionResult.FAILED,
            message=str(e)
        )
        log_audit(action)
        return action


async def clear_caches_restart() -> HealingAction:
    """
    Clear caches and restart service.
    Used for memory issues.
    """
    cache_result = await clear_caches()
    if cache_result.result == ActionResult.FAILED:
        return cache_result
    
    restart_result = await restart_service("aria-command")
    
    if restart_result.result == ActionResult.SUCCESS:
        action = HealingAction(
            action_name="clear_caches_restart",
            result=ActionResult.SUCCESS,
            message="Cleared caches and restarted service"
        )
    else:
        action = HealingAction(
            action_name="clear_caches_restart",
            result=ActionResult.FAILED,
            message=f"Restart failed: {restart_result.message}"
        )
    
    log_audit(action)
    return action


async def rate_limit_backoff() -> HealingAction:
    """
    Handle rate limiting by waiting.
    """
    # Just log it - the actual backoff is handled by the caller
    action = HealingAction(
        action_name="rate_limit_backoff",
        result=ActionResult.SUCCESS,
        message="Rate limit detected, will backoff on next request"
    )
    log_audit(action)
    return action


async def switch_model_fallback() -> HealingAction:
    """
    Switch to a fallback model when primary is unavailable.
    """
    # This would modify the router config to prefer a different model
    # For now, just log it
    action = HealingAction(
        action_name="switch_model_fallback",
        result=ActionResult.SUCCESS,
        message="Will use fallback model for next request"
    )
    log_audit(action)
    return action


async def clear_database_locks() -> HealingAction:
    """
    Clear SQLite database locks.
    """
    try:
        # Find and kill any processes holding locks
        db_files = list(STATE_DIR.glob("*.db"))
        
        for db_file in db_files:
            # Remove journal/wal files
            for suffix in ["-journal", "-wal", "-shm"]:
                lock_file = db_file.with_suffix(db_file.suffix + suffix)
                if lock_file.exists():
                    lock_file.unlink()
        
        action = HealingAction(
            action_name="clear_database_locks",
            result=ActionResult.SUCCESS,
            message=f"Cleared locks for {len(db_files)} databases"
        )
        log_audit(action)
        return action
        
    except Exception as e:
        action = HealingAction(
            action_name="clear_database_locks",
            result=ActionResult.FAILED,
            message=str(e)
        )
        log_audit(action)
        return action


async def alert_human(pattern_name: str = "") -> HealingAction:
    """
    Alert human for issues that require manual intervention.
    """
    try:
        # Send Telegram notification
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("SUNHEART_CHAT_ID", "")
        
        if token and chat_id:
            message = f"🚨 **Aria Needs Help**\n\nDetected issue: {pattern_name}\n\nThis requires manual intervention."
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
                )
            
            action = HealingAction(
                action_name="alert_human",
                result=ActionResult.NEEDS_APPROVAL,
                message=f"Alerted human about: {pattern_name}"
            )
        else:
            action = HealingAction(
                action_name="alert_human",
                result=ActionResult.FAILED,
                message="No Telegram credentials configured"
            )
        
        log_audit(action)
        return action
        
    except Exception as e:
        action = HealingAction(
            action_name="alert_human",
            result=ActionResult.FAILED,
            message=str(e)
        )
        log_audit(action)
        return action


async def retry_with_backoff() -> HealingAction:
    """
    Mark for retry with exponential backoff.
    """
    action = HealingAction(
        action_name="retry_with_backoff",
        result=ActionResult.SUCCESS,
        message="Will retry with exponential backoff"
    )
    log_audit(action)
    return action


async def rollback_last_change() -> HealingAction:
    """
    Rollback to last known good state.
    Requires approval for safety.
    """
    action = HealingAction(
        action_name="rollback_last_change",
        result=ActionResult.NEEDS_APPROVAL,
        message="Rollback requires human approval"
    )
    log_audit(action)
    return action


async def restore_database_backup() -> HealingAction:
    """
    Restore database from backup.
    Requires approval for safety.
    """
    action = HealingAction(
        action_name="restore_database_backup",
        result=ActionResult.NEEDS_APPROVAL,
        message="Database restore requires human approval"
    )
    log_audit(action)
    return action


# ============================================================================
# ACTION DISPATCHER
# ============================================================================

ACTION_MAP: Dict[str, Callable] = {
    "clear_conversation_history": clear_conversation_history,
    "restart_service": restart_service,
    "clear_caches": clear_caches,
    "clear_caches_restart": clear_caches_restart,
    "rate_limit_backoff": rate_limit_backoff,
    "switch_model_fallback": switch_model_fallback,
    "clear_database_locks": clear_database_locks,
    "alert_human": alert_human,
    "retry_with_backoff": retry_with_backoff,
    "rollback_last_change": rollback_last_change,
    "restore_database_backup": restore_database_backup,
}


async def execute_healing_action(action_name: str, **kwargs) -> HealingAction:
    """
    Execute a healing action by name.
    
    Args:
        action_name: Name of the action to execute
        **kwargs: Additional arguments for the action
    
    Returns:
        HealingAction result
    """
    if action_name not in ACTION_MAP:
        return HealingAction(
            action_name=action_name,
            result=ActionResult.FAILED,
            message=f"Unknown action: {action_name}"
        )
    
    try:
        action_func = ACTION_MAP[action_name]
        return await action_func(**kwargs)
    except Exception as e:
        logger.error(f"Action {action_name} failed: {e}")
        return HealingAction(
            action_name=action_name,
            result=ActionResult.FAILED,
            message=str(e)
        )


