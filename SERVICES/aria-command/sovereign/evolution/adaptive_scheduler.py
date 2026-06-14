#!/usr/bin/env python3
"""
ARIA ADAPTIVE SCHEDULER
========================

Dynamic scheduling that learns from user patterns.

Features:
- Learns James's activity patterns
- Schedules heavy analysis during quiet periods
- Pre-warms caches before expected usage
- Adjusts proactive message timing
- Optimizes resource allocation

The schedule itself learns:
- If James uses Aria mostly 9-5, do analysis at 6 AM
- If James is nocturnal, shift accordingly
- If there's a quiet period > 2 hours, use it for analysis
"""

import os
import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("aria.evolution.scheduler")

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")


class TaskType(str, Enum):
    """Types of scheduled tasks."""
    ANALYSIS = "analysis"           # Daily deep analysis
    DIGEST = "digest"               # Send digest to user
    CLEANUP = "cleanup"             # Database cleanup
    CACHE_WARMUP = "cache_warmup"   # Pre-warm caches
    METRICS_AGGREGATE = "metrics"   # Aggregate metrics
    EVOLUTION_CYCLE = "evolution"   # Full evolution cycle
    PROACTIVE_CHECK = "proactive"   # Check for proactive opportunities
    HEALTH_CHECK = "health"         # System health check


class TaskPriority(str, Enum):
    """Task priorities."""
    CRITICAL = "critical"   # Must run, interrupt if needed
    HIGH = "high"           # Run ASAP but don't interrupt
    NORMAL = "normal"       # Run when convenient
    LOW = "low"             # Run only during idle


@dataclass
class ScheduledTask:
    """A scheduled task."""
    id: Optional[int] = None
    task_type: TaskType = TaskType.ANALYSIS
    priority: TaskPriority = TaskPriority.NORMAL
    
    # Schedule
    scheduled_hour: int = 6         # Preferred hour (24h)
    scheduled_minute: int = 0
    interval_hours: int = 24        # How often to run
    
    # Flexibility
    earliest_hour: int = 4          # Can run as early as
    latest_hour: int = 10           # Must run by
    
    # State
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    avg_duration_ms: float = 0
    
    # Handler
    handler: Optional[Callable] = None


@dataclass
class UserActivityPattern:
    """Learned user activity pattern."""
    user_id: str = ""
    
    # Hourly activity distribution (0-23 -> activity score)
    hourly_activity: Dict[int, float] = field(default_factory=dict)
    
    # Day of week activity (0-6 -> activity score)
    daily_activity: Dict[int, float] = field(default_factory=dict)
    
    # Detected patterns
    peak_hours: List[int] = field(default_factory=list)
    quiet_hours: List[int] = field(default_factory=list)
    typical_start_hour: int = 9
    typical_end_hour: int = 17
    
    # Last activity
    last_activity: Optional[datetime] = None


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

SCHEDULER_SCHEMA = """
-- Scheduled tasks
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    priority TEXT DEFAULT 'normal',
    scheduled_hour INTEGER DEFAULT 6,
    scheduled_minute INTEGER DEFAULT 0,
    interval_hours INTEGER DEFAULT 24,
    earliest_hour INTEGER DEFAULT 4,
    latest_hour INTEGER DEFAULT 10,
    last_run TEXT,
    next_run TEXT,
    run_count INTEGER DEFAULT 0,
    avg_duration_ms REAL DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    UNIQUE(task_type)
);

CREATE INDEX IF NOT EXISTS idx_task_next ON scheduled_tasks(next_run);
CREATE INDEX IF NOT EXISTS idx_task_enabled ON scheduled_tasks(enabled);

-- Task execution history
CREATE TABLE IF NOT EXISTS task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms REAL,
    success INTEGER DEFAULT 1,
    result TEXT,
    context TEXT
);

CREATE INDEX IF NOT EXISTS idx_history_time ON task_history(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_type ON task_history(task_type);

-- User activity patterns
CREATE TABLE IF NOT EXISTS user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    hour INTEGER,
    day_of_week INTEGER,
    interaction_type TEXT
);

CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_time ON user_activity(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_activity_hour ON user_activity(hour);

-- Learned patterns
CREATE TABLE IF NOT EXISTS learned_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    hourly_activity TEXT,
    daily_activity TEXT,
    peak_hours TEXT,
    quiet_hours TEXT,
    typical_start_hour INTEGER,
    typical_end_hour INTEGER,
    last_updated TEXT
);

CREATE INDEX IF NOT EXISTS idx_patterns_user ON learned_patterns(user_id);
"""


# ============================================================================
# ADAPTIVE SCHEDULER
# ============================================================================

class AdaptiveScheduler:
    """
    Adaptive task scheduler that learns from user patterns.
    
    Features:
    - Schedules heavy tasks during user inactivity
    - Pre-warms caches before expected activity
    - Sends proactive messages at optimal times
    - Aggregates metrics during off-hours
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        
        # Task handlers
        self._handlers: Dict[TaskType, Callable] = {}
        
        # Running state
        self._running = False
        self._check_interval = 60  # seconds
        
        # Activity tracking
        self._recent_activity: List[datetime] = []
        self._activity_lock = threading.Lock()
        
        self._init_db()
        self._register_default_tasks()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Get cursor with auto-commit."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def _init_db(self):
        """Initialize database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._cursor() as cursor:
            cursor.executescript(SCHEDULER_SCHEMA)
        logger.info("Adaptive scheduler initialized")
    
    def _register_default_tasks(self):
        """Register default scheduled tasks."""
        default_tasks = [
            ScheduledTask(
                task_type=TaskType.ANALYSIS,
                priority=TaskPriority.HIGH,
                scheduled_hour=6,
                interval_hours=24,
                earliest_hour=4,
                latest_hour=10
            ),
            ScheduledTask(
                task_type=TaskType.DIGEST,
                priority=TaskPriority.NORMAL,
                scheduled_hour=8,
                interval_hours=24,
                earliest_hour=7,
                latest_hour=12
            ),
            ScheduledTask(
                task_type=TaskType.CLEANUP,
                priority=TaskPriority.LOW,
                scheduled_hour=3,
                interval_hours=24,
                earliest_hour=2,
                latest_hour=6
            ),
            ScheduledTask(
                task_type=TaskType.METRICS_AGGREGATE,
                priority=TaskPriority.NORMAL,
                scheduled_hour=0,
                scheduled_minute=5,
                interval_hours=1,
                earliest_hour=0,
                latest_hour=23
            ),
            ScheduledTask(
                task_type=TaskType.HEALTH_CHECK,
                priority=TaskPriority.HIGH,
                scheduled_hour=0,
                interval_hours=1,
                earliest_hour=0,
                latest_hour=23
            ),
            ScheduledTask(
                task_type=TaskType.CACHE_WARMUP,
                priority=TaskPriority.LOW,
                scheduled_hour=8,
                interval_hours=4,
                earliest_hour=6,
                latest_hour=22
            )
        ]
        
        for task in default_tasks:
            self._upsert_task(task)
    
    def _upsert_task(self, task: ScheduledTask):
        """Insert or update a task."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO scheduled_tasks (
                    task_type, priority, scheduled_hour, scheduled_minute,
                    interval_hours, earliest_hour, latest_hour, run_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(task_type) DO UPDATE SET
                    priority = excluded.priority,
                    scheduled_hour = excluded.scheduled_hour,
                    scheduled_minute = excluded.scheduled_minute,
                    interval_hours = excluded.interval_hours,
                    earliest_hour = excluded.earliest_hour,
                    latest_hour = excluded.latest_hour
            """, (
                task.task_type.value,
                task.priority.value,
                task.scheduled_hour,
                task.scheduled_minute,
                task.interval_hours,
                task.earliest_hour,
                task.latest_hour
            ))
    
    # ========================================================================
    # TASK REGISTRATION
    # ========================================================================
    
    def register_handler(self, task_type: TaskType, handler: Callable):
        """Register a handler for a task type."""
        self._handlers[task_type] = handler
        logger.info(f"Registered handler for {task_type.value}")
    
    # ========================================================================
    # ACTIVITY TRACKING
    # ========================================================================
    
    def record_activity(self, user_id: str, interaction_type: str = "chat"):
        """Record user activity for pattern learning."""
        now = datetime.now()
        
        # Track in memory
        with self._activity_lock:
            self._recent_activity.append(now)
            # Keep last 2 hours
            cutoff = now - timedelta(hours=2)
            self._recent_activity = [a for a in self._recent_activity if a > cutoff]
        
        # Persist
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_activity (
                    user_id, timestamp, hour, day_of_week, interaction_type
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                now.isoformat(),
                now.hour,
                now.weekday(),
                interaction_type
            ))
    
    def is_user_active(self, minutes: int = 30) -> bool:
        """Check if user has been active recently."""
        with self._activity_lock:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            return any(a > cutoff for a in self._recent_activity)
    
    def get_quiet_period_length(self) -> timedelta:
        """Get how long since last activity."""
        with self._activity_lock:
            if not self._recent_activity:
                return timedelta(hours=24)  # Assume long quiet period
            
            last = max(self._recent_activity)
            return datetime.now() - last
    
    # ========================================================================
    # PATTERN LEARNING
    # ========================================================================
    
    def learn_patterns(self, user_id: str = "james") -> UserActivityPattern:
        """Learn activity patterns from historical data."""
        pattern = UserActivityPattern(user_id=user_id)
        
        # Get activity data from last 30 days
        since = (datetime.now() - timedelta(days=30)).isoformat()
        
        with self._cursor() as cursor:
            # Hourly distribution
            cursor.execute("""
                SELECT hour, COUNT(*) as count
                FROM user_activity
                WHERE user_id = ? AND timestamp >= ?
                GROUP BY hour
            """, (user_id, since))
            
            hourly = {row["hour"]: row["count"] for row in cursor.fetchall()}
            total = sum(hourly.values()) or 1
            pattern.hourly_activity = {h: c/total for h, c in hourly.items()}
            
            # Daily distribution
            cursor.execute("""
                SELECT day_of_week, COUNT(*) as count
                FROM user_activity
                WHERE user_id = ? AND timestamp >= ?
                GROUP BY day_of_week
            """, (user_id, since))
            
            daily = {row["day_of_week"]: row["count"] for row in cursor.fetchall()}
            total = sum(daily.values()) or 1
            pattern.daily_activity = {d: c/total for d, c in daily.items()}
        
        # Identify peak and quiet hours
        if pattern.hourly_activity:
            sorted_hours = sorted(
                pattern.hourly_activity.items(),
                key=lambda x: x[1],
                reverse=True
            )
            pattern.peak_hours = [h for h, _ in sorted_hours[:5]]
            pattern.quiet_hours = [h for h, _ in sorted_hours[-5:]]
            
            # Find typical start and end
            active_hours = [h for h, c in pattern.hourly_activity.items() if c > 0.05]
            if active_hours:
                pattern.typical_start_hour = min(active_hours)
                pattern.typical_end_hour = max(active_hours)
        
        # Save pattern
        self._save_pattern(pattern)
        
        return pattern
    
    def _save_pattern(self, pattern: UserActivityPattern):
        """Save learned pattern to database."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO learned_patterns (
                    user_id, hourly_activity, daily_activity,
                    peak_hours, quiet_hours, typical_start_hour,
                    typical_end_hour, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    hourly_activity = excluded.hourly_activity,
                    daily_activity = excluded.daily_activity,
                    peak_hours = excluded.peak_hours,
                    quiet_hours = excluded.quiet_hours,
                    typical_start_hour = excluded.typical_start_hour,
                    typical_end_hour = excluded.typical_end_hour,
                    last_updated = excluded.last_updated
            """, (
                pattern.user_id,
                json.dumps(pattern.hourly_activity),
                json.dumps(pattern.daily_activity),
                json.dumps(pattern.peak_hours),
                json.dumps(pattern.quiet_hours),
                pattern.typical_start_hour,
                pattern.typical_end_hour,
                datetime.now().isoformat()
            ))
    
    def get_pattern(self, user_id: str = "james") -> Optional[UserActivityPattern]:
        """Get learned pattern for a user."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM learned_patterns WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return UserActivityPattern(
                user_id=row["user_id"],
                hourly_activity=json.loads(row["hourly_activity"] or "{}"),
                daily_activity=json.loads(row["daily_activity"] or "{}"),
                peak_hours=json.loads(row["peak_hours"] or "[]"),
                quiet_hours=json.loads(row["quiet_hours"] or "[]"),
                typical_start_hour=row["typical_start_hour"],
                typical_end_hour=row["typical_end_hour"]
            )
    
    # ========================================================================
    # ADAPTIVE SCHEDULING
    # ========================================================================
    
    def get_optimal_time(self, task_type: TaskType) -> datetime:
        """Get optimal time to run a task based on learned patterns."""
        # Get task config
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM scheduled_tasks WHERE task_type = ?
            """, (task_type.value,))
            row = cursor.fetchone()
            
            if not row:
                return datetime.now() + timedelta(hours=1)
        
        scheduled_hour = row["scheduled_hour"]
        earliest = row["earliest_hour"]
        latest = row["latest_hour"]
        
        # Get user pattern
        pattern = self.get_pattern()
        
        if pattern and pattern.quiet_hours:
            # Find a quiet hour within the task's window
            for hour in pattern.quiet_hours:
                if earliest <= hour <= latest:
                    scheduled_hour = hour
                    break
        
        # Calculate next run time
        now = datetime.now()
        next_run = now.replace(
            hour=scheduled_hour,
            minute=row["scheduled_minute"],
            second=0,
            microsecond=0
        )
        
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return next_run
    
    def should_run_now(self, task_type: TaskType) -> Tuple[bool, str]:
        """Check if a task should run now."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM scheduled_tasks
                WHERE task_type = ? AND enabled = 1
            """, (task_type.value,))
            row = cursor.fetchone()
            
            if not row:
                return False, "Task not found or disabled"
        
        now = datetime.now()
        
        # Check if already ran today (for daily tasks)
        if row["interval_hours"] >= 24 and row["last_run"]:
            last_run = datetime.fromisoformat(row["last_run"])
            if (now - last_run).total_seconds() < row["interval_hours"] * 3600:
                return False, "Already ran within interval"
        
        # Check if within window
        if not (row["earliest_hour"] <= now.hour <= row["latest_hour"]):
            return False, "Outside task window"
        
        # Check priority vs user activity
        priority = TaskPriority(row["priority"])
        
        if priority == TaskPriority.LOW:
            # Only run during quiet periods
            quiet_length = self.get_quiet_period_length()
            if quiet_length < timedelta(hours=2):
                return False, "User active, task is low priority"
        
        elif priority == TaskPriority.NORMAL:
            # Can run if user not currently active
            if self.is_user_active(30):
                return False, "User currently active"
        
        # CRITICAL and HIGH can always run
        
        return True, "OK to run"
    
    # ========================================================================
    # TASK EXECUTION
    # ========================================================================
    
    async def run_task(self, task_type: TaskType) -> Dict[str, Any]:
        """Run a task and record results."""
        handler = self._handlers.get(task_type)
        if not handler:
            return {"success": False, "error": "No handler registered"}
        
        start_time = datetime.now()
        
        # Record start
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO task_history (task_type, started_at)
                VALUES (?, ?)
            """, (task_type.value, start_time.isoformat()))
            history_id = cursor.lastrowid
        
        try:
            # Run handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler()
            else:
                result = handler()
            
            success = True
            
        except Exception as e:
            logger.error(f"Task {task_type.value} failed: {e}")
            result = str(e)
            success = False
        
        # Record completion
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE task_history SET
                    completed_at = ?,
                    duration_ms = ?,
                    success = ?,
                    result = ?
                WHERE id = ?
            """, (
                end_time.isoformat(),
                duration_ms,
                1 if success else 0,
                json.dumps(result) if isinstance(result, dict) else str(result),
                history_id
            ))
            
            # Update task stats
            cursor.execute("""
                UPDATE scheduled_tasks SET
                    last_run = ?,
                    run_count = run_count + 1,
                    avg_duration_ms = (avg_duration_ms * run_count + ?) / (run_count + 1)
                WHERE task_type = ?
            """, (
                end_time.isoformat(),
                duration_ms,
                task_type.value
            ))
        
        return {
            "task_type": task_type.value,
            "success": success,
            "duration_ms": duration_ms,
            "result": result
        }
    
    # ========================================================================
    # MAIN LOOP
    # ========================================================================
    
    async def run(self):
        """Run the scheduler loop."""
        logger.info("Adaptive scheduler starting...")
        self._running = True
        
        while self._running:
            try:
                # Check each task type
                for task_type in TaskType:
                    should_run, reason = self.should_run_now(task_type)
                    
                    if should_run and task_type in self._handlers:
                        logger.info(f"Running scheduled task: {task_type.value}")
                        result = await self.run_task(task_type)
                        logger.info(f"Task {task_type.value} completed: {result}")
                
                # Update patterns periodically (every 6 hours)
                now = datetime.now()
                if now.hour % 6 == 0 and now.minute == 0:
                    self.learn_patterns()
                
                await asyncio.sleep(self._check_interval)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(self._check_interval * 2)
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        logger.info("Adaptive scheduler stopping...")
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    def get_schedule(self) -> List[Dict]:
        """Get current schedule."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM scheduled_tasks WHERE enabled = 1
                ORDER BY scheduled_hour, scheduled_minute
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_task_history(self, task_type: TaskType = None, limit: int = 50) -> List[Dict]:
        """Get task execution history."""
        with self._cursor() as cursor:
            if task_type:
                cursor.execute("""
                    SELECT * FROM task_history
                    WHERE task_type = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (task_type.value, limit))
            else:
                cursor.execute("""
                    SELECT * FROM task_history
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        pattern = self.get_pattern()
        
        return {
            "running": self._running,
            "check_interval_seconds": self._check_interval,
            "user_active": self.is_user_active(),
            "quiet_period_minutes": self.get_quiet_period_length().total_seconds() / 60,
            "registered_handlers": list(self._handlers.keys()),
            "pattern": {
                "peak_hours": pattern.peak_hours if pattern else [],
                "quiet_hours": pattern.quiet_hours if pattern else [],
                "typical_hours": f"{pattern.typical_start_hour}:00-{pattern.typical_end_hour}:00" if pattern else "unknown"
            } if pattern else None
        }
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_scheduler: Optional[AdaptiveScheduler] = None


def get_adaptive_scheduler() -> AdaptiveScheduler:
    """Get or create global adaptive scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AdaptiveScheduler()
    return _scheduler


async def start_scheduler():
    """Start the scheduler loop."""
    scheduler = get_adaptive_scheduler()
    await scheduler.run()


def stop_scheduler():
    """Stop the scheduler."""
    if _scheduler:
        _scheduler.stop()


def record_user_activity(user_id: str = "james", interaction_type: str = "chat"):
    """Record user activity."""
    get_adaptive_scheduler().record_activity(user_id, interaction_type)


