#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - SCHEDULER & RELIABILITY
===============================================

Always-on infrastructure with:
- Scheduled actions
- Health checks
- Auto-restart
- Message persistence
- Failover handling
"""

import os
import asyncio
import logging
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
import traceback

logger = logging.getLogger("aria.scheduler")

# ============================================================================
# CONFIGURATION
# ============================================================================

STATE_DIR = Path(os.getenv("ARIA_STATE_DIR", "/tmp/aria-command"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Default schedules
DEFAULT_SCHEDULES = {
    "morning_brief": "07:30",     # Daily at 7:30 AM
    "eod_summary": "18:00",       # Daily at 6:00 PM
    "health_check": "*/15",       # Every 15 minutes
    "cost_report": "0 * * * *",   # Every hour
    "digest_weekly": "09:00 MON", # Monday 9 AM
}


class ScheduleType(str, Enum):
    DAILY = "daily"     # Run at specific time daily
    INTERVAL = "interval"  # Run every N minutes
    CRON = "cron"       # Cron expression
    ONCE = "once"       # Run once


@dataclass
class ScheduledTask:
    """A scheduled task."""
    id: str
    name: str
    schedule_type: ScheduleType
    schedule: str  # Time or interval
    callback: str  # Function name to call
    args: Dict = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class QueuedMessage:
    """A message queued for delivery."""
    id: str
    chat_id: int
    text: str
    voice: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    attempts: int = 0
    delivered: bool = False


class AriaScheduler:
    """
    Task scheduler with reliability features.
    
    Features:
    - Daily/interval/cron scheduling
    - Auto-restart on failure
    - Message queue persistence
    - Health monitoring
    """
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.message_queue: List[QueuedMessage] = []
        self.running = False
        self.callbacks: Dict[str, Callable] = {}
        
        # Load state
        self._load_state()
        
        # Register default schedules
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default scheduled tasks."""
        defaults = [
            ScheduledTask(
                id="morning_brief",
                name="Morning Briefing",
                schedule_type=ScheduleType.DAILY,
                schedule="07:30",
                callback="send_morning_brief"
            ),
            ScheduledTask(
                id="eod_summary",
                name="End of Day Summary",
                schedule_type=ScheduleType.DAILY,
                schedule="18:00",
                callback="send_eod_summary"
            ),
            ScheduledTask(
                id="health_check",
                name="System Health Check",
                schedule_type=ScheduleType.INTERVAL,
                schedule="15",  # Every 15 minutes
                callback="run_health_check"
            ),
            ScheduledTask(
                id="cost_report",
                name="Hourly Cost Report",
                schedule_type=ScheduleType.INTERVAL,
                schedule="60",  # Every hour
                callback="check_costs"
            ),
            ScheduledTask(
                id="agent_heartbeat",
                name="Agent Heartbeat",
                schedule_type=ScheduleType.INTERVAL,
                schedule="5",  # Every 5 minutes
                callback="agent_heartbeat"
            ),
            ScheduledTask(
                id="queue_processor",
                name="Message Queue Processor",
                schedule_type=ScheduleType.INTERVAL,
                schedule="1",  # Every minute
                callback="process_message_queue"
            )
        ]
        
        for task in defaults:
            if task.id not in self.tasks:
                self.tasks[task.id] = task
    
    def register_callback(self, name: str, callback: Callable):
        """Register a callback function."""
        self.callbacks[name] = callback
    
    def add_task(self, task: ScheduledTask):
        """Add a scheduled task."""
        self.tasks[task.id] = task
        self._update_next_run(task)
        self._persist_state()
    
    def remove_task(self, task_id: str):
        """Remove a scheduled task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._persist_state()
    
    def enable_task(self, task_id: str, enabled: bool = True):
        """Enable or disable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = enabled
            self._persist_state()
    
    def _update_next_run(self, task: ScheduledTask):
        """Calculate next run time for a task."""
        now = datetime.now()
        
        if task.schedule_type == ScheduleType.DAILY:
            # Parse HH:MM
            hour, minute = map(int, task.schedule.split(":"))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            task.next_run = next_run
            
        elif task.schedule_type == ScheduleType.INTERVAL:
            # Minutes
            interval = int(task.schedule)
            if task.last_run:
                task.next_run = task.last_run + timedelta(minutes=interval)
            else:
                task.next_run = now + timedelta(minutes=interval)
                
        elif task.schedule_type == ScheduleType.ONCE:
            if task.run_count == 0:
                task.next_run = now
            else:
                task.next_run = None
    
    async def _run_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        if task.callback not in self.callbacks:
            logger.warning(f"No callback registered for {task.callback}")
            return
        
        try:
            logger.info(f"Running scheduled task: {task.name}")
            
            callback = self.callbacks[task.callback]
            
            if asyncio.iscoroutinefunction(callback):
                await callback(**task.args)
            else:
                callback(**task.args)
            
            task.last_run = datetime.now()
            task.run_count += 1
            task.last_error = None
            
            self._update_next_run(task)
            self._persist_state()
            
        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)
            logger.error(f"Task {task.name} failed: {e}\n{traceback.format_exc()}")
            
            # Still update next run to prevent infinite retry
            self._update_next_run(task)
            self._persist_state()
    
    async def run_scheduler_loop(self):
        """Main scheduler loop."""
        self.running = True
        logger.info("Scheduler started")
        
        while self.running:
            try:
                now = datetime.now()
                
                for task in self.tasks.values():
                    if not task.enabled:
                        continue
                    
                    if task.next_run and task.next_run <= now:
                        await self._run_task(task)
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
    
    # ========== MESSAGE QUEUE ==========
    
    def queue_message(self, chat_id: int, text: str, voice: bool = False) -> str:
        """Queue a message for delivery."""
        import hashlib
        
        msg = QueuedMessage(
            id=hashlib.md5(f"{chat_id}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            chat_id=chat_id,
            text=text,
            voice=voice
        )
        
        self.message_queue.append(msg)
        self._persist_state()
        
        return msg.id
    
    async def process_queue(self):
        """Process queued messages."""
        for msg in self.message_queue:
            if msg.delivered or msg.attempts >= 3:
                continue
            
            try:
                msg.attempts += 1
                
                if msg.voice:
                    from ..voice.speak import send_voice
                    success = await send_voice(msg.chat_id, msg.text)
                else:
                    from ..telegram.bot import send_message
                    success = await send_message(msg.chat_id, msg.text)
                
                msg.delivered = success
                
            except Exception as e:
                logger.error(f"Failed to deliver message {msg.id}: {e}")
        
        # Clean up old delivered messages
        self.message_queue = [
            m for m in self.message_queue 
            if not m.delivered or (datetime.now() - m.created_at) < timedelta(hours=1)
        ]
        
        self._persist_state()
    
    # ========== PERSISTENCE ==========
    
    def _persist_state(self):
        """Save state to disk."""
        state = {
            "tasks": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "schedule_type": v.schedule_type.value,
                    "schedule": v.schedule,
                    "callback": v.callback,
                    "args": v.args,
                    "enabled": v.enabled,
                    "last_run": v.last_run.isoformat() if v.last_run else None,
                    "next_run": v.next_run.isoformat() if v.next_run else None,
                    "run_count": v.run_count,
                    "error_count": v.error_count,
                    "last_error": v.last_error
                } for k, v in self.tasks.items()
            },
            "message_queue": [
                {
                    "id": m.id,
                    "chat_id": m.chat_id,
                    "text": m.text,
                    "voice": m.voice,
                    "created_at": m.created_at.isoformat(),
                    "attempts": m.attempts,
                    "delivered": m.delivered
                } for m in self.message_queue
            ]
        }
        
        state_file = STATE_DIR / "scheduler.json"
        state_file.write_text(json.dumps(state, indent=2))
    
    def _load_state(self):
        """Load state from disk."""
        state_file = STATE_DIR / "scheduler.json"
        
        if not state_file.exists():
            return
        
        try:
            state = json.loads(state_file.read_text())
            
            # Load tasks
            for task_id, data in state.get("tasks", {}).items():
                task = ScheduledTask(
                    id=data["id"],
                    name=data["name"],
                    schedule_type=ScheduleType(data["schedule_type"]),
                    schedule=data["schedule"],
                    callback=data["callback"],
                    args=data.get("args", {}),
                    enabled=data.get("enabled", True),
                    last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
                    run_count=data.get("run_count", 0),
                    error_count=data.get("error_count", 0),
                    last_error=data.get("last_error")
                )
                self._update_next_run(task)
                self.tasks[task_id] = task
            
            # Load message queue
            for data in state.get("message_queue", []):
                if not data.get("delivered"):
                    msg = QueuedMessage(
                        id=data["id"],
                        chat_id=data["chat_id"],
                        text=data["text"],
                        voice=data.get("voice", False),
                        created_at=datetime.fromisoformat(data["created_at"]),
                        attempts=data.get("attempts", 0),
                        delivered=data.get("delivered", False)
                    )
                    self.message_queue.append(msg)
                    
        except Exception as e:
            logger.error(f"Failed to load scheduler state: {e}")
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            "running": self.running,
            "tasks": {
                k: {
                    "name": v.name,
                    "enabled": v.enabled,
                    "next_run": v.next_run.isoformat() if v.next_run else None,
                    "last_run": v.last_run.isoformat() if v.last_run else None,
                    "run_count": v.run_count,
                    "error_count": v.error_count,
                    "last_error": v.last_error
                } for k, v in self.tasks.items()
            },
            "queue_size": len([m for m in self.message_queue if not m.delivered])
        }


# ============================================================================
# RELIABILITY WRAPPER
# ============================================================================

class ReliableService:
    """
    Wrapper for reliable service execution.
    
    Features:
    - Auto-restart on crash
    - Error tracking
    - Graceful shutdown
    """
    
    def __init__(self, name: str):
        self.name = name
        self.restart_count = 0
        self.max_restarts = 5
        self.restart_window = timedelta(hours=1)
        self.restart_times: List[datetime] = []
        self.running = False
    
    async def run_with_restart(self, coroutine_func: Callable):
        """Run a coroutine with auto-restart."""
        self.running = True
        
        while self.running:
            try:
                logger.info(f"Starting {self.name}")
                await coroutine_func()
                
            except asyncio.CancelledError:
                logger.info(f"{self.name} cancelled")
                break
                
            except Exception as e:
                logger.error(f"{self.name} crashed: {e}\n{traceback.format_exc()}")
                
                # Check restart limit
                now = datetime.now()
                self.restart_times = [t for t in self.restart_times if now - t < self.restart_window]
                self.restart_times.append(now)
                
                if len(self.restart_times) >= self.max_restarts:
                    logger.critical(f"{self.name} exceeded restart limit, stopping")
                    break
                
                # Wait before restart (exponential backoff)
                wait_time = min(30 * (2 ** len(self.restart_times)), 300)
                logger.info(f"Restarting {self.name} in {wait_time}s")
                await asyncio.sleep(wait_time)
                
                self.restart_count += 1
        
        self.running = False
    
    def stop(self):
        """Stop the service."""
        self.running = False


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_scheduler: Optional[AriaScheduler] = None


def get_scheduler() -> AriaScheduler:
    """Get or create global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AriaScheduler()
    return _scheduler


def schedule_task(
    task_id: str,
    name: str,
    schedule_type: str,
    schedule: str,
    callback: str,
    **kwargs
):
    """Schedule a new task."""
    scheduler = get_scheduler()
    
    task = ScheduledTask(
        id=task_id,
        name=name,
        schedule_type=ScheduleType(schedule_type),
        schedule=schedule,
        callback=callback,
        args=kwargs
    )
    
    scheduler.add_task(task)


def queue_for_delivery(chat_id: int, text: str, voice: bool = False) -> str:
    """Queue a message for reliable delivery."""
    return get_scheduler().queue_message(chat_id, text, voice)


def get_scheduler_status() -> Dict:
    """Get scheduler status."""
    return get_scheduler().get_status()


