#!/usr/bin/env python3
"""
ARIA ROLLING WINDOW METRICS
============================

Real-time metrics tracking with configurable rolling windows.

Tracks:
- Error rate (last 10 interactions)
- Average response time (last hour)
- Correction rate (last 24h)
- Model cost (current session)
- Success rate trends
- Tool usage patterns

These metrics trigger Tier 2 evolution (event-driven) when thresholds are crossed.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
from collections import deque
from enum import Enum

logger = logging.getLogger("aria.evolution.metrics")

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")


class MetricType(str, Enum):
    """Types of metrics tracked."""
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    CORRECTION_RATE = "correction_rate"
    SUCCESS_RATE = "success_rate"
    COST = "cost"
    TOOL_USAGE = "tool_usage"
    CACHE_HIT_RATE = "cache_hit_rate"
    TOKEN_USAGE = "tokens"


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ============================================================================
# THRESHOLDS
# ============================================================================

THRESHOLDS = {
    MetricType.ERROR_RATE: {
        AlertLevel.WARNING: 0.2,    # 20% errors
        AlertLevel.CRITICAL: 0.3    # 30% errors
    },
    MetricType.RESPONSE_TIME: {
        AlertLevel.WARNING: 20000,   # 20s - complex queries can take 10-15s
        AlertLevel.CRITICAL: 60000   # 60s - only alert for very slow responses
    },
    MetricType.CORRECTION_RATE: {
        AlertLevel.WARNING: 0.1,    # 10% corrections
        AlertLevel.CRITICAL: 0.2    # 20% corrections
    },
    MetricType.SUCCESS_RATE: {
        AlertLevel.WARNING: 0.8,    # Below 80%
        AlertLevel.CRITICAL: 0.6    # Below 60%
    },
    MetricType.COST: {
        AlertLevel.WARNING: 1.0,    # $1/hour
        AlertLevel.CRITICAL: 5.0    # $5/hour
    }
}


@dataclass
class MetricPoint:
    """A single metric measurement."""
    timestamp: datetime
    value: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WindowStats:
    """Statistics for a rolling window."""
    metric_type: MetricType
    window_minutes: int
    current_value: float
    min_value: float
    max_value: float
    avg_value: float
    sample_count: int
    trend: str  # "improving", "stable", "degrading"
    alert_level: Optional[AlertLevel] = None


@dataclass
class MetricAlert:
    """An alert triggered by metric threshold."""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metric_type: MetricType = MetricType.ERROR_RATE
    alert_level: AlertLevel = AlertLevel.WARNING
    current_value: float = 0.0
    threshold_value: float = 0.0
    message: str = ""
    acknowledged: bool = False


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

METRICS_SCHEMA = """
-- Raw metric points
CREATE TABLE IF NOT EXISTS metric_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    value REAL NOT NULL,
    context TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrics_time ON metric_points(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON metric_points(metric_type);

-- Aggregated windows (hourly summaries)
CREATE TABLE IF NOT EXISTS metric_windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    min_value REAL,
    max_value REAL,
    avg_value REAL,
    sum_value REAL,
    sample_count INTEGER,
    UNIQUE(window_start, metric_type)
);

CREATE INDEX IF NOT EXISTS idx_windows_time ON metric_windows(window_start DESC);
CREATE INDEX IF NOT EXISTS idx_windows_type ON metric_windows(metric_type);

-- Alerts history
CREATE TABLE IF NOT EXISTS metric_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    alert_level TEXT NOT NULL,
    current_value REAL,
    threshold_value REAL,
    message TEXT,
    acknowledged INTEGER DEFAULT 0,
    acknowledged_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_time ON metric_alerts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_level ON metric_alerts(alert_level);
CREATE INDEX IF NOT EXISTS idx_alerts_ack ON metric_alerts(acknowledged);

-- Trends
CREATE TABLE IF NOT EXISTS metric_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    daily_avg REAL,
    trend_direction TEXT,
    change_percent REAL,
    UNIQUE(date, metric_type)
);

CREATE INDEX IF NOT EXISTS idx_trends_date ON metric_trends(date DESC);
"""


# ============================================================================
# ROLLING WINDOW
# ============================================================================

class RollingWindow:
    """In-memory rolling window for fast access."""
    
    def __init__(self, max_size: int = 100, max_age_minutes: int = 60):
        self.max_size = max_size
        self.max_age_minutes = max_age_minutes
        self._data: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()
    
    def add(self, value: float, context: Dict = None):
        """Add a data point."""
        with self._lock:
            self._data.append(MetricPoint(
                timestamp=datetime.now(),
                value=value,
                context=context or {}
            ))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current window statistics."""
        with self._lock:
            # Filter by age
            cutoff = datetime.now() - timedelta(minutes=self.max_age_minutes)
            recent = [p for p in self._data if p.timestamp > cutoff]
            
            if not recent:
                return {
                    "count": 0,
                    "avg": 0,
                    "min": 0,
                    "max": 0,
                    "current": 0,
                    "trend": "stable"
                }
            
            values = [p.value for p in recent]
            
            # Calculate trend
            trend = "stable"
            if len(values) >= 5:
                first_half = sum(values[:len(values)//2]) / (len(values)//2)
                second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
                if second_half > first_half * 1.1:
                    trend = "increasing"
                elif second_half < first_half * 0.9:
                    trend = "decreasing"
            
            return {
                "count": len(recent),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "current": values[-1] if values else 0,
                "trend": trend
            }
    
    def get_recent(self, count: int = 10) -> List[MetricPoint]:
        """Get recent data points."""
        with self._lock:
            return list(self._data)[-count:]


# ============================================================================
# METRICS TRACKER
# ============================================================================

class MetricsWindow:
    """
    Real-time metrics tracking with rolling windows.
    
    Provides:
    - Fast in-memory access for recent metrics
    - Persistent storage for historical analysis
    - Automatic alert generation
    - Trend detection
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        
        # In-memory rolling windows
        self._windows: Dict[MetricType, RollingWindow] = {
            MetricType.ERROR_RATE: RollingWindow(100, 10),        # Last 10 interactions (fast)
            MetricType.RESPONSE_TIME: RollingWindow(200, 60),     # Last hour
            MetricType.CORRECTION_RATE: RollingWindow(500, 1440), # Last 24h
            MetricType.SUCCESS_RATE: RollingWindow(100, 60),      # Last hour
            MetricType.COST: RollingWindow(200, 60),              # Last hour
            MetricType.TOKEN_USAGE: RollingWindow(200, 60),       # Last hour
            MetricType.CACHE_HIT_RATE: RollingWindow(100, 60),    # Last hour
            MetricType.TOOL_USAGE: RollingWindow(200, 60),        # Last hour
        }
        
        # Alert callbacks
        self._alert_callbacks: List[callable] = []
        
        self._init_db()
    
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
            cursor.executescript(METRICS_SCHEMA)
        logger.info("Metrics window initialized")
    
    # ========================================================================
    # RECORDING
    # ========================================================================
    
    def record(
        self,
        metric_type: MetricType,
        value: float,
        context: Dict = None
    ):
        """
        Record a metric data point.
        
        This:
        1. Adds to in-memory rolling window
        2. Persists to database
        3. Checks thresholds and triggers alerts
        """
        # Add to rolling window
        self._windows[metric_type].add(value, context)
        
        # Persist to database
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO metric_points (timestamp, metric_type, value, context)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                metric_type.value,
                value,
                json.dumps(context) if context else None
            ))
        
        # Check thresholds
        self._check_thresholds(metric_type, value)
    
    def record_interaction(
        self,
        success: bool,
        response_time_ms: float,
        was_correction: bool,
        was_cached: bool,
        cost_usd: float,
        tokens: int,
        tools_used: int
    ):
        """
        Record metrics from a single interaction.
        
        Convenience method that updates all relevant metrics at once.
        """
        # Error/success rate (1.0 for error, 0.0 for success)
        self.record(MetricType.ERROR_RATE, 0.0 if success else 1.0)
        self.record(MetricType.SUCCESS_RATE, 1.0 if success else 0.0)
        
        # Response time
        self.record(MetricType.RESPONSE_TIME, response_time_ms)
        
        # Correction rate
        self.record(MetricType.CORRECTION_RATE, 1.0 if was_correction else 0.0)
        
        # Cache hit rate
        self.record(MetricType.CACHE_HIT_RATE, 1.0 if was_cached else 0.0)
        
        # Cost
        self.record(MetricType.COST, cost_usd)
        
        # Token usage
        self.record(MetricType.TOKEN_USAGE, float(tokens))
        
        # Tool usage
        self.record(MetricType.TOOL_USAGE, float(tools_used))
    
    def _check_thresholds(self, metric_type: MetricType, value: float):
        """Check if value crosses any thresholds."""
        if metric_type not in THRESHOLDS:
            return
        
        thresholds = THRESHOLDS[metric_type]
        stats = self._windows[metric_type].get_stats()
        avg_value = stats["avg"]
        
        # Determine alert level based on metric type
        alert_level = None
        
        if metric_type in [MetricType.ERROR_RATE, MetricType.CORRECTION_RATE, 
                          MetricType.RESPONSE_TIME, MetricType.COST]:
            # Higher is worse
            if avg_value >= thresholds.get(AlertLevel.CRITICAL, float('inf')):
                alert_level = AlertLevel.CRITICAL
            elif avg_value >= thresholds.get(AlertLevel.WARNING, float('inf')):
                alert_level = AlertLevel.WARNING
        
        elif metric_type == MetricType.SUCCESS_RATE:
            # Lower is worse
            if avg_value <= thresholds.get(AlertLevel.CRITICAL, 0):
                alert_level = AlertLevel.CRITICAL
            elif avg_value <= thresholds.get(AlertLevel.WARNING, 0):
                alert_level = AlertLevel.WARNING
        
        if alert_level:
            self._create_alert(metric_type, alert_level, avg_value, thresholds[alert_level])
    
    def _create_alert(
        self,
        metric_type: MetricType,
        level: AlertLevel,
        current_value: float,
        threshold_value: float
    ):
        """Create and persist an alert."""
        # Check if we already have a recent alert for this
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT id FROM metric_alerts
                WHERE metric_type = ? AND alert_level = ?
                AND timestamp >= datetime('now', '-15 minutes')
                AND acknowledged = 0
            """, (metric_type.value, level.value))
            
            if cursor.fetchone():
                return  # Already have recent unacknowledged alert
        
        message = f"{metric_type.value} is {level.value}: {current_value:.2f} (threshold: {threshold_value:.2f})"
        
        alert = MetricAlert(
            timestamp=datetime.now(),
            metric_type=metric_type,
            alert_level=level,
            current_value=current_value,
            threshold_value=threshold_value,
            message=message
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO metric_alerts (
                    timestamp, metric_type, alert_level, current_value,
                    threshold_value, message, acknowledged
                ) VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (
                alert.timestamp.isoformat(),
                alert.metric_type.value,
                alert.alert_level.value,
                alert.current_value,
                alert.threshold_value,
                alert.message
            ))
            alert.id = cursor.lastrowid
        
        logger.warning(f"Alert: {message}")
        
        # Notify callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    # ========================================================================
    # QUERYING
    # ========================================================================
    
    def get_current(self, metric_type: MetricType) -> Dict[str, Any]:
        """Get current rolling window stats for a metric."""
        return self._windows[metric_type].get_stats()
    
    def get_all_current(self) -> Dict[str, Dict[str, Any]]:
        """Get current stats for all metrics."""
        return {
            mt.value: self._windows[mt].get_stats()
            for mt in MetricType
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics for display."""
        all_stats = self.get_all_current()
        
        # Get any active alerts
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT metric_type, alert_level, message
                FROM metric_alerts
                WHERE acknowledged = 0
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            alerts = [dict(row) for row in cursor.fetchall()]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "error_rate": {
                    "value": all_stats[MetricType.ERROR_RATE.value]["avg"],
                    "trend": all_stats[MetricType.ERROR_RATE.value]["trend"],
                    "status": "good" if all_stats[MetricType.ERROR_RATE.value]["avg"] < 0.1 else "warning"
                },
                "response_time_ms": {
                    "value": all_stats[MetricType.RESPONSE_TIME.value]["avg"],
                    "trend": all_stats[MetricType.RESPONSE_TIME.value]["trend"],
                    "status": "good" if all_stats[MetricType.RESPONSE_TIME.value]["avg"] < 5000 else "warning"
                },
                "correction_rate": {
                    "value": all_stats[MetricType.CORRECTION_RATE.value]["avg"],
                    "trend": all_stats[MetricType.CORRECTION_RATE.value]["trend"],
                    "status": "good" if all_stats[MetricType.CORRECTION_RATE.value]["avg"] < 0.1 else "warning"
                },
                "success_rate": {
                    "value": all_stats[MetricType.SUCCESS_RATE.value]["avg"],
                    "trend": all_stats[MetricType.SUCCESS_RATE.value]["trend"],
                    "status": "good" if all_stats[MetricType.SUCCESS_RATE.value]["avg"] > 0.9 else "warning"
                },
                "cache_hit_rate": {
                    "value": all_stats[MetricType.CACHE_HIT_RATE.value]["avg"],
                    "trend": all_stats[MetricType.CACHE_HIT_RATE.value]["trend"],
                    "status": "good" if all_stats[MetricType.CACHE_HIT_RATE.value]["avg"] > 0.3 else "info"
                },
                "cost_per_hour": {
                    "value": all_stats[MetricType.COST.value]["avg"] * 60,  # Per hour
                    "trend": all_stats[MetricType.COST.value]["trend"],
                    "status": "good" if all_stats[MetricType.COST.value]["avg"] * 60 < 1.0 else "warning"
                }
            },
            "active_alerts": alerts,
            "overall_health": self._calculate_health_score(all_stats)
        }
    
    def _calculate_health_score(self, stats: Dict) -> Dict[str, Any]:
        """Calculate overall health score from metrics."""
        scores = []
        
        # Error rate (inverted, lower is better)
        error_score = max(0, 1 - stats[MetricType.ERROR_RATE.value]["avg"] * 5)
        scores.append(error_score)
        
        # Success rate (direct)
        success_score = stats[MetricType.SUCCESS_RATE.value]["avg"]
        scores.append(success_score)
        
        # Correction rate (inverted)
        correction_score = max(0, 1 - stats[MetricType.CORRECTION_RATE.value]["avg"] * 5)
        scores.append(correction_score)
        
        # Response time (scaled)
        avg_time = stats[MetricType.RESPONSE_TIME.value]["avg"]
        time_score = max(0, 1 - (avg_time / 15000))  # 15s = 0
        scores.append(time_score)
        
        overall = sum(scores) / len(scores) if scores else 0
        
        status = "excellent" if overall > 0.9 else "good" if overall > 0.7 else "warning" if overall > 0.5 else "critical"
        
        return {
            "score": overall,
            "status": status,
            "components": {
                "error_score": error_score,
                "success_score": success_score,
                "correction_score": correction_score,
                "time_score": time_score
            }
        }
    
    def get_historical(
        self,
        metric_type: MetricType,
        hours: int = 24
    ) -> List[Dict]:
        """Get historical metric data."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT timestamp, value, context
                FROM metric_points
                WHERE metric_type = ? AND timestamp >= ?
                ORDER BY timestamp
            """, (metric_type.value, since))
            
            return [
                {
                    "timestamp": row["timestamp"],
                    "value": row["value"],
                    "context": json.loads(row["context"]) if row["context"] else {}
                }
                for row in cursor.fetchall()
            ]
    
    def get_alerts(self, include_acknowledged: bool = False) -> List[Dict]:
        """Get alerts."""
        with self._cursor() as cursor:
            if include_acknowledged:
                cursor.execute("""
                    SELECT * FROM metric_alerts
                    ORDER BY timestamp DESC
                    LIMIT 50
                """)
            else:
                cursor.execute("""
                    SELECT * FROM metric_alerts
                    WHERE acknowledged = 0
                    ORDER BY timestamp DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def acknowledge_alert(self, alert_id: int):
        """Acknowledge an alert."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE metric_alerts
                SET acknowledged = 1, acknowledged_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), alert_id))
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def on_alert(self, callback: callable):
        """Register a callback for alerts."""
        self._alert_callbacks.append(callback)
    
    # ========================================================================
    # AGGREGATION
    # ========================================================================
    
    def aggregate_hourly(self):
        """Aggregate metrics into hourly windows (run periodically)."""
        now = datetime.now()
        window_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        window_end = window_start + timedelta(hours=1)
        
        with self._cursor() as cursor:
            for metric_type in MetricType:
                cursor.execute("""
                    SELECT 
                        MIN(value) as min_val,
                        MAX(value) as max_val,
                        AVG(value) as avg_val,
                        SUM(value) as sum_val,
                        COUNT(*) as cnt
                    FROM metric_points
                    WHERE metric_type = ? AND timestamp >= ? AND timestamp < ?
                """, (metric_type.value, window_start.isoformat(), window_end.isoformat()))
                
                row = cursor.fetchone()
                if row and row["cnt"] > 0:
                    cursor.execute("""
                        INSERT INTO metric_windows (
                            window_start, window_end, metric_type,
                            min_value, max_value, avg_value, sum_value, sample_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(window_start, metric_type) DO UPDATE SET
                            min_value = excluded.min_value,
                            max_value = excluded.max_value,
                            avg_value = excluded.avg_value,
                            sum_value = excluded.sum_value,
                            sample_count = excluded.sample_count
                    """, (
                        window_start.isoformat(),
                        window_end.isoformat(),
                        metric_type.value,
                        row["min_val"],
                        row["max_val"],
                        row["avg_val"],
                        row["sum_val"],
                        row["cnt"]
                    ))
        
        logger.info(f"Aggregated metrics for window: {window_start}")
    
    def cleanup_old_points(self, days: int = 7):
        """Clean up old raw metric points (keep aggregates)."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                DELETE FROM metric_points WHERE timestamp < ?
            """, (cutoff,))
            deleted = cursor.rowcount
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old metric points")
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_metrics: Optional[MetricsWindow] = None


def get_metrics_window() -> MetricsWindow:
    """Get or create global metrics window."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsWindow()
    return _metrics


def record_metric(metric_type: MetricType, value: float, context: Dict = None):
    """Record a metric."""
    get_metrics_window().record(metric_type, value, context)


def record_interaction(**kwargs):
    """Record all metrics from an interaction."""
    get_metrics_window().record_interaction(**kwargs)


def get_metrics_summary() -> Dict[str, Any]:
    """Get current metrics summary."""
    return get_metrics_window().get_summary()

