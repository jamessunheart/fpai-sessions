#!/usr/bin/env python3
"""
ARIA ASCENSION - DEGRADATION MONITOR
====================================

Monitor for performance degradation:
- Track key metrics in real-time
- If metrics drop > 10% after change → auto-rollback
- Alert James only if repeated failures

Ensures self-improvement doesn't break things.
"""

import os
import json
import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading
import statistics

logger = logging.getLogger("aria.ascension.degradation")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")

# Degradation thresholds
DEGRADATION_THRESHOLD = float(os.getenv("DEGRADATION_THRESHOLD", "0.10"))  # 10%
WINDOW_SIZE_MINUTES = int(os.getenv("DEGRADATION_WINDOW", "30"))
MIN_SAMPLES_FOR_DETECTION = int(os.getenv("DEGRADATION_MIN_SAMPLES", "10"))
ALERT_AFTER_FAILURES = int(os.getenv("ALERT_AFTER_FAILURES", "2"))


class MetricType(str, Enum):
    """Types of metrics to monitor."""
    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    FOLLOWUP_RATE = "followup_rate"


class DegradationSeverity(str, Enum):
    """Severity of detected degradation."""
    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricSnapshot:
    """A snapshot of metrics at a point in time."""
    timestamp: datetime
    response_time_avg: float
    response_time_p95: float
    success_rate: float
    error_rate: float
    sample_count: int
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "response_time_avg": self.response_time_avg,
            "response_time_p95": self.response_time_p95,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "sample_count": self.sample_count
        }


@dataclass
class DegradationAlert:
    """A degradation alert."""
    metric: MetricType
    severity: DegradationSeverity
    baseline_value: float
    current_value: float
    change_percent: float
    detected_at: datetime = field(default_factory=datetime.now)
    related_change_id: str = None
    
    def to_dict(self) -> Dict:
        return {
            "metric": self.metric.value,
            "severity": self.severity.value,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "change_percent": self.change_percent,
            "detected_at": self.detected_at.isoformat(),
            "related_change_id": self.related_change_id
        }


DEGRADATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS metric_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    value REAL NOT NULL,
    change_id TEXT
);

CREATE TABLE IF NOT EXISTS baselines (
    id INTEGER PRIMARY KEY,
    metric_type TEXT UNIQUE NOT NULL,
    baseline_value REAL,
    baseline_stddev REAL,
    sample_count INTEGER,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS degradation_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    severity TEXT NOT NULL,
    baseline_value REAL,
    current_value REAL,
    change_percent REAL,
    detected_at TEXT NOT NULL,
    related_change_id TEXT,
    acknowledged INTEGER DEFAULT 0,
    auto_rollback INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS active_changes (
    id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT,
    can_rollback INTEGER DEFAULT 1,
    rollback_command TEXT
);

CREATE INDEX IF NOT EXISTS idx_ms_timestamp ON metric_samples(timestamp);
CREATE INDEX IF NOT EXISTS idx_ms_type ON metric_samples(metric_type);
CREATE INDEX IF NOT EXISTS idx_da_severity ON degradation_alerts(severity);
"""


# ============================================================================
# DEGRADATION MONITOR
# ============================================================================

class DegradationMonitor:
    """
    Monitors for performance degradation after changes.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._rollback_handlers: Dict[str, Callable] = {}
        self._alert_callback: Optional[Callable[[DegradationAlert], None]] = None
        self._running = False
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_db(self):
        """Initialize database."""
        from pathlib import Path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with self._cursor() as cursor:
            cursor.executescript(DEGRADATION_SCHEMA)
        
        logger.info(f"Degradation monitor initialized: {self.db_path}")
    
    def set_alert_callback(self, callback: Callable[[DegradationAlert], None]):
        """Set callback for alerts."""
        self._alert_callback = callback
    
    def register_rollback(self, change_id: str, handler: Callable):
        """Register a rollback handler for a change."""
        self._rollback_handlers[change_id] = handler
    
    # ========================================================================
    # SAMPLE RECORDING
    # ========================================================================
    
    def record_sample(
        self,
        metric_type: MetricType,
        value: float,
        change_id: str = None
    ):
        """Record a metric sample."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO metric_samples (timestamp, metric_type, value, change_id)
                VALUES (?, ?, ?, ?)
            """, (datetime.now().isoformat(), metric_type.value, value, change_id))
    
    def record_interaction(
        self,
        response_time_ms: float,
        success: bool,
        had_error: bool = False,
        change_id: str = None
    ):
        """Record metrics from an interaction."""
        self.record_sample(MetricType.RESPONSE_TIME, response_time_ms, change_id)
        self.record_sample(MetricType.SUCCESS_RATE, 1.0 if success else 0.0, change_id)
        if had_error:
            self.record_sample(MetricType.ERROR_RATE, 1.0, change_id)
        else:
            self.record_sample(MetricType.ERROR_RATE, 0.0, change_id)
    
    # ========================================================================
    # CHANGE TRACKING
    # ========================================================================
    
    def register_change(
        self,
        change_id: str,
        description: str,
        can_rollback: bool = True,
        rollback_command: str = None
    ):
        """Register a change for monitoring."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO active_changes
                (id, applied_at, description, can_rollback, rollback_command)
                VALUES (?, ?, ?, ?, ?)
            """, (change_id, datetime.now().isoformat(), description, 
                  1 if can_rollback else 0, rollback_command))
        
        logger.info(f"Registered change for monitoring: {change_id}")
    
    def unregister_change(self, change_id: str):
        """Remove a change from monitoring."""
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM active_changes WHERE id = ?", (change_id,))
        
        if change_id in self._rollback_handlers:
            del self._rollback_handlers[change_id]
    
    # ========================================================================
    # BASELINE MANAGEMENT
    # ========================================================================
    
    def update_baselines(self):
        """Update baselines from recent stable data."""
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        
        with self._cursor() as cursor:
            for metric in MetricType:
                cursor.execute("""
                    SELECT value FROM metric_samples
                    WHERE metric_type = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (metric.value, cutoff))
                
                values = [row["value"] for row in cursor.fetchall()]
                
                if len(values) < MIN_SAMPLES_FOR_DETECTION:
                    continue
                
                baseline = statistics.mean(values)
                stddev = statistics.stdev(values) if len(values) > 1 else 0
                
                cursor.execute("""
                    INSERT INTO baselines (id, metric_type, baseline_value, baseline_stddev, sample_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(metric_type) DO UPDATE SET
                        baseline_value = ?, baseline_stddev = ?, sample_count = ?, updated_at = ?
                """, (
                    hash(metric.value) % 1000000,  # Simple ID
                    metric.value, baseline, stddev, len(values), datetime.now().isoformat(),
                    baseline, stddev, len(values), datetime.now().isoformat()
                ))
        
        logger.debug("Updated metric baselines")
    
    def get_baseline(self, metric_type: MetricType) -> Tuple[float, float]:
        """Get baseline value and stddev for a metric."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT baseline_value, baseline_stddev FROM baselines
                WHERE metric_type = ?
            """, (metric_type.value,))
            
            row = cursor.fetchone()
            if row:
                return row["baseline_value"], row["baseline_stddev"]
            return None, None
    
    # ========================================================================
    # DEGRADATION DETECTION
    # ========================================================================
    
    def check_for_degradation(self, change_id: str = None) -> List[DegradationAlert]:
        """
        Check for degradation in all metrics.
        Optionally filter to samples related to a specific change.
        """
        alerts = []
        cutoff = (datetime.now() - timedelta(minutes=WINDOW_SIZE_MINUTES)).isoformat()
        
        for metric in MetricType:
            baseline, stddev = self.get_baseline(metric)
            if baseline is None:
                continue
            
            # Get recent values
            with self._cursor() as cursor:
                if change_id:
                    cursor.execute("""
                        SELECT value FROM metric_samples
                        WHERE metric_type = ? AND timestamp > ? AND change_id = ?
                    """, (metric.value, cutoff, change_id))
                else:
                    cursor.execute("""
                        SELECT value FROM metric_samples
                        WHERE metric_type = ? AND timestamp > ?
                    """, (metric.value, cutoff))
                
                values = [row["value"] for row in cursor.fetchall()]
            
            if len(values) < MIN_SAMPLES_FOR_DETECTION:
                continue
            
            current = statistics.mean(values)
            
            # Calculate change
            if metric == MetricType.RESPONSE_TIME:
                # Higher is worse for response time
                change_pct = (current - baseline) / max(baseline, 1) * 100
                is_degraded = current > baseline * (1 + DEGRADATION_THRESHOLD)
            else:
                # Lower is worse for success rate
                change_pct = (baseline - current) / max(baseline, 0.01) * 100
                is_degraded = current < baseline * (1 - DEGRADATION_THRESHOLD)
            
            if is_degraded:
                severity = DegradationSeverity.CRITICAL if abs(change_pct) > 20 else DegradationSeverity.WARNING
                
                alert = DegradationAlert(
                    metric=metric,
                    severity=severity,
                    baseline_value=baseline,
                    current_value=current,
                    change_percent=change_pct,
                    related_change_id=change_id
                )
                
                alerts.append(alert)
                self._record_alert(alert)
        
        return alerts
    
    def _record_alert(self, alert: DegradationAlert):
        """Record an alert to database."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO degradation_alerts
                (metric, severity, baseline_value, current_value, change_percent, detected_at, related_change_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.metric.value, alert.severity.value,
                alert.baseline_value, alert.current_value,
                alert.change_percent, alert.detected_at.isoformat(),
                alert.related_change_id
            ))
    
    # ========================================================================
    # AUTO-ROLLBACK
    # ========================================================================
    
    async def handle_degradation(self, alerts: List[DegradationAlert]) -> bool:
        """
        Handle detected degradation.
        Returns True if rollback was performed.
        """
        critical_alerts = [a for a in alerts if a.severity == DegradationSeverity.CRITICAL]
        
        if not critical_alerts:
            return False
        
        # Check for related change
        change_ids = set(a.related_change_id for a in critical_alerts if a.related_change_id)
        
        for change_id in change_ids:
            # Check if we should rollback
            recent_alerts = self._get_recent_alerts_for_change(change_id)
            
            if len(recent_alerts) >= ALERT_AFTER_FAILURES:
                # Attempt rollback
                success = await self._perform_rollback(change_id)
                
                if success:
                    logger.warning(f"Auto-rolled back change {change_id} due to degradation")
                    
                    # Notify
                    if self._alert_callback:
                        for alert in critical_alerts:
                            if alert.related_change_id == change_id:
                                alert.severity = DegradationSeverity.CRITICAL
                                self._alert_callback(alert)
                    
                    return True
        
        # Just notify for non-rollbackable alerts
        if self._alert_callback:
            for alert in critical_alerts:
                self._alert_callback(alert)
        
        return False
    
    def _get_recent_alerts_for_change(self, change_id: str) -> List[Dict]:
        """Get recent alerts for a change."""
        cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM degradation_alerts
                WHERE related_change_id = ? AND detected_at > ? AND severity = 'critical'
            """, (change_id, cutoff))
            
            return [dict(row) for row in cursor.fetchall()]
    
    async def _perform_rollback(self, change_id: str) -> bool:
        """Perform rollback for a change."""
        # Check for registered handler
        if change_id in self._rollback_handlers:
            try:
                handler = self._rollback_handlers[change_id]
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
                
                self.unregister_change(change_id)
                
                with self._cursor() as cursor:
                    cursor.execute("""
                        UPDATE degradation_alerts SET auto_rollback = 1
                        WHERE related_change_id = ?
                    """, (change_id,))
                
                return True
            except Exception as e:
                logger.error(f"Rollback failed for {change_id}: {e}")
                return False
        
        # Check for rollback command
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT rollback_command, can_rollback FROM active_changes WHERE id = ?
            """, (change_id,))
            row = cursor.fetchone()
            
            if row and row["can_rollback"] and row["rollback_command"]:
                import subprocess
                try:
                    subprocess.run(row["rollback_command"], shell=True, check=True)
                    self.unregister_change(change_id)
                    return True
                except subprocess.CalledProcessError as e:
                    logger.error(f"Rollback command failed: {e}")
                    return False
        
        return False
    
    # ========================================================================
    # MONITORING LOOP
    # ========================================================================
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """Start the monitoring loop."""
        self._running = True
        logger.info("Degradation monitoring started")
        
        while self._running:
            try:
                # Update baselines periodically
                self.update_baselines()
                
                # Check for degradation
                alerts = self.check_for_degradation()
                
                if alerts:
                    await self.handle_degradation(alerts)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self._running = False
    
    # ========================================================================
    # SNAPSHOT
    # ========================================================================
    
    def get_current_snapshot(self) -> MetricSnapshot:
        """Get current metric snapshot."""
        cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
        
        with self._cursor() as cursor:
            # Response time
            cursor.execute("""
                SELECT AVG(value) as avg_val FROM metric_samples
                WHERE metric_type = 'response_time' AND timestamp > ?
            """, (cutoff,))
            rt_avg = cursor.fetchone()["avg_val"] or 0
            
            cursor.execute("""
                SELECT value FROM metric_samples
                WHERE metric_type = 'response_time' AND timestamp > ?
                ORDER BY value DESC
            """, (cutoff,))
            rt_values = [row["value"] for row in cursor.fetchall()]
            rt_p95 = rt_values[int(len(rt_values) * 0.05)] if rt_values else 0
            
            # Success rate
            cursor.execute("""
                SELECT AVG(value) as avg_val FROM metric_samples
                WHERE metric_type = 'success_rate' AND timestamp > ?
            """, (cutoff,))
            success_rate = cursor.fetchone()["avg_val"] or 0
            
            # Error rate
            cursor.execute("""
                SELECT AVG(value) as avg_val FROM metric_samples
                WHERE metric_type = 'error_rate' AND timestamp > ?
            """, (cutoff,))
            error_rate = cursor.fetchone()["avg_val"] or 0
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM metric_samples WHERE timestamp > ?
            """, (cutoff,))
            sample_count = cursor.fetchone()["count"]
        
        return MetricSnapshot(
            timestamp=datetime.now(),
            response_time_avg=rt_avg,
            response_time_p95=rt_p95,
            success_rate=success_rate,
            error_rate=error_rate,
            sample_count=sample_count
        )
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT severity, COUNT(*) as count
                FROM degradation_alerts
                WHERE detected_at > ?
                GROUP BY severity
            """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
            alerts_24h = {row["severity"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("SELECT COUNT(*) as count FROM active_changes")
            active_changes = cursor.fetchone()["count"]
        
        snapshot = self.get_current_snapshot()
        
        return {
            "current_snapshot": snapshot.to_dict(),
            "alerts_last_24h": alerts_24h,
            "active_changes_monitored": active_changes,
            "degradation_threshold": f"{DEGRADATION_THRESHOLD * 100}%"
        }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_monitor: Optional[DegradationMonitor] = None


def get_degradation_monitor() -> DegradationMonitor:
    """Get global degradation monitor."""
    global _monitor
    if _monitor is None:
        _monitor = DegradationMonitor()
    return _monitor


def record_interaction_metrics(
    response_time_ms: float,
    success: bool,
    change_id: str = None
):
    """Record interaction metrics."""
    get_degradation_monitor().record_interaction(
        response_time_ms, success, change_id=change_id
    )


def register_change_for_monitoring(change_id: str, description: str, **kwargs):
    """Register a change for degradation monitoring."""
    get_degradation_monitor().register_change(change_id, description, **kwargs)


