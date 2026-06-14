#!/usr/bin/env python3
"""
ARIA STRUCTURED LOGGING SYSTEM
==============================

Captures all Aria interactions with structured metadata for AI analysis.
Stores in SQLite for queryable history and pattern detection.

Features:
- Log all interactions, errors, tool calls, and outcomes
- Track response times, error rates, user satisfaction signals
- Queryable history for self-improvement analysis
- Retention and cleanup policies
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.logging.structured")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ARIA_LOG_DB", "/opt/fpai/aria-command/state/aria_logs.db")
RETENTION_DAYS = int(os.getenv("ARIA_LOG_RETENTION_DAYS", "30"))


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(str, Enum):
    INTERACTION = "interaction"      # User messages and responses
    TOOL_CALL = "tool_call"          # Tool/function executions
    ERROR = "error"                   # Errors and exceptions
    METRIC = "metric"                 # Performance metrics
    DECISION = "decision"             # AI decision points
    IMPROVEMENT = "improvement"       # Self-improvement events
    SYSTEM = "system"                 # System events


@dataclass
class LogEntry:
    """A structured log entry."""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    level: LogLevel = LogLevel.INFO
    category: LogCategory = LogCategory.SYSTEM
    
    # Context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Content
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Metrics
    duration_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    
    # Outcome
    success: Optional[bool] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        d["level"] = self.level.value
        d["category"] = self.category.value
        d["details"] = json.dumps(self.details)
        return d


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    user_id TEXT,
    session_id TEXT,
    request_id TEXT,
    message TEXT,
    details TEXT,
    duration_ms REAL,
    tokens_used INTEGER,
    cost_usd REAL,
    success INTEGER,
    error_type TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_category ON logs(category);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_success ON logs(success);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);

CREATE TABLE IF NOT EXISTS improvement_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    risk_level INTEGER,
    problem TEXT,
    solution TEXT,
    file_path TEXT,
    diff TEXT,
    estimated_impact TEXT,
    approved_at TEXT,
    applied_at TEXT,
    outcome TEXT
);

CREATE INDEX IF NOT EXISTS idx_proposals_status ON improvement_proposals(status);
"""


# ============================================================================
# STRUCTURED LOGGER
# ============================================================================

class StructuredLogger:
    """
    Thread-safe structured logging with SQLite storage.
    
    Features:
    - Async-friendly logging
    - Queryable log history
    - Automatic cleanup
    - Metrics aggregation
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Get a cursor with automatic commit."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def _init_db(self):
        """Initialize database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._cursor() as cursor:
            cursor.executescript(SCHEMA)
        logger.info(f"Structured logger initialized: {self.db_path}")
    
    def log(self, entry: LogEntry) -> int:
        """
        Log a structured entry.
        
        Returns:
            The ID of the inserted log entry.
        """
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO logs (
                    timestamp, level, category, user_id, session_id, request_id,
                    message, details, duration_ms, tokens_used, cost_usd,
                    success, error_type, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.timestamp.isoformat(),
                entry.level.value,
                entry.category.value,
                entry.user_id,
                entry.session_id,
                entry.request_id,
                entry.message,
                json.dumps(entry.details),
                entry.duration_ms,
                entry.tokens_used,
                entry.cost_usd,
                1 if entry.success else (0 if entry.success is False else None),
                entry.error_type,
                entry.error_message
            ))
            return cursor.lastrowid
    
    def log_interaction(
        self,
        user_id: str,
        message: str,
        response: str,
        duration_ms: float,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        success: bool = True,
        details: Dict[str, Any] = None
    ) -> int:
        """Log a user interaction."""
        return self.log(LogEntry(
            level=LogLevel.INFO,
            category=LogCategory.INTERACTION,
            user_id=user_id,
            message=message[:500],  # Truncate
            details={
                "response_preview": response[:500],
                **(details or {})
            },
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            success=success
        ))
    
    def log_error(
        self,
        error: Exception,
        context: str = "",
        user_id: Optional[str] = None,
        details: Dict[str, Any] = None
    ) -> int:
        """Log an error."""
        return self.log(LogEntry(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            user_id=user_id,
            message=context,
            details=details or {},
            success=False,
            error_type=type(error).__name__,
            error_message=str(error)[:1000]
        ))
    
    def log_tool_call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        result: Any,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> int:
        """Log a tool/function call."""
        return self.log(LogEntry(
            level=LogLevel.INFO if success else LogLevel.WARNING,
            category=LogCategory.TOOL_CALL,
            user_id=user_id,
            message=f"Tool: {tool_name}",
            details={
                "tool": tool_name,
                "params": params,
                "result_preview": str(result)[:500] if result else None
            },
            duration_ms=duration_ms,
            success=success,
            error_message=error
        ))
    
    def log_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> int:
        """Log a metric value."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO metrics (timestamp, name, value, tags)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                name,
                value,
                json.dumps(tags or {})
            ))
            return cursor.lastrowid
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    def get_logs(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        category: Optional[LogCategory] = None,
        level: Optional[LogLevel] = None,
        user_id: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query logs with filters."""
        query = "SELECT * FROM logs WHERE 1=1"
        params = []
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())
        if until:
            query += " AND timestamp <= ?"
            params.append(until.isoformat())
        if category:
            query += " AND category = ?"
            params.append(category.value)
        if level:
            query += " AND level = ?"
            params.append(level.value)
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if success is not None:
            query += " AND success = ?"
            params.append(1 if success else 0)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self._cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_errors(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent errors."""
        since = datetime.now() - timedelta(hours=hours)
        return self.get_logs(
            since=since,
            category=LogCategory.ERROR,
            limit=limit
        )
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for analysis."""
        since = datetime.now() - timedelta(hours=hours)
        
        with self._cursor() as cursor:
            # Error counts by type
            cursor.execute("""
                SELECT error_type, COUNT(*) as count
                FROM logs
                WHERE category = 'error' AND timestamp >= ?
                GROUP BY error_type
                ORDER BY count DESC
            """, (since.isoformat(),))
            by_type = {row["error_type"]: row["count"] for row in cursor.fetchall()}
            
            # Total errors
            cursor.execute("""
                SELECT COUNT(*) as count FROM logs
                WHERE category = 'error' AND timestamp >= ?
            """, (since.isoformat(),))
            total = cursor.fetchone()["count"]
            
            # Sample error messages
            cursor.execute("""
                SELECT error_type, error_message, message, timestamp
                FROM logs
                WHERE category = 'error' AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (since.isoformat(),))
            samples = [dict(row) for row in cursor.fetchall()]
        
        return {
            "total_errors": total,
            "by_type": by_type,
            "samples": samples,
            "period_hours": hours
        }
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for analysis."""
        since = datetime.now() - timedelta(hours=hours)
        
        with self._cursor() as cursor:
            # Average response times
            cursor.execute("""
                SELECT 
                    AVG(duration_ms) as avg_duration,
                    MIN(duration_ms) as min_duration,
                    MAX(duration_ms) as max_duration,
                    COUNT(*) as count
                FROM logs
                WHERE category = 'interaction' AND timestamp >= ? AND duration_ms IS NOT NULL
            """, (since.isoformat(),))
            timing = dict(cursor.fetchone())
            
            # Success rate
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
                    COUNT(*) as total
                FROM logs
                WHERE timestamp >= ? AND success IS NOT NULL
            """, (since.isoformat(),))
            success = dict(cursor.fetchone())
            
            # Costs
            cursor.execute("""
                SELECT SUM(cost_usd) as total_cost, SUM(tokens_used) as total_tokens
                FROM logs
                WHERE timestamp >= ?
            """, (since.isoformat(),))
            costs = dict(cursor.fetchone())
        
        success_rate = 0
        if success["total"] > 0:
            success_rate = success["successes"] / success["total"] * 100
        
        return {
            "period_hours": hours,
            "response_times": timing,
            "success_rate": success_rate,
            "total_interactions": success["total"],
            "total_cost_usd": costs["total_cost"] or 0,
            "total_tokens": costs["total_tokens"] or 0
        }
    
    def get_improvement_data(self, hours: int = 24) -> Dict[str, Any]:
        """Get data needed for self-improvement analysis."""
        return {
            "errors": self.get_error_summary(hours),
            "performance": self.get_performance_metrics(hours),
            "recent_logs": self.get_logs(
                since=datetime.now() - timedelta(hours=hours),
                limit=500
            )
        }
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    def cleanup_old_logs(self, days: int = RETENTION_DAYS) -> int:
        """Remove logs older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM logs WHERE timestamp < ?",
                (cutoff.isoformat(),)
            )
            deleted_logs = cursor.rowcount
            
            cursor.execute(
                "DELETE FROM metrics WHERE timestamp < ?",
                (cutoff.isoformat(),)
            )
            deleted_metrics = cursor.rowcount
        
        logger.info(f"Cleanup: removed {deleted_logs} logs and {deleted_metrics} metrics")
        return deleted_logs + deleted_metrics
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# ============================================================================

_logger: Optional[StructuredLogger] = None


def get_logger() -> StructuredLogger:
    """Get or create global structured logger."""
    global _logger
    if _logger is None:
        _logger = StructuredLogger()
    return _logger


def log_interaction(
    user_id: str,
    message: str,
    response: str,
    duration_ms: float,
    **kwargs
) -> int:
    """Log a user interaction."""
    return get_logger().log_interaction(user_id, message, response, duration_ms, **kwargs)


def log_error(error: Exception, context: str = "", **kwargs) -> int:
    """Log an error."""
    return get_logger().log_error(error, context, **kwargs)


def log_tool_call(tool_name: str, params: Dict, result: Any, duration_ms: float, **kwargs) -> int:
    """Log a tool call."""
    return get_logger().log_tool_call(tool_name, params, result, duration_ms, **kwargs)


def log_metric(name: str, value: float, tags: Dict[str, str] = None) -> int:
    """Log a metric."""
    return get_logger().log_metric(name, value, tags)

