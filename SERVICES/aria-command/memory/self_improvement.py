"""
ARIA SELF-IMPROVEMENT TRACKING
===============================

Tracks how Aria's memory and performance improve over time.

This is meta-cognition - thinking about thinking:
- How is my memory accuracy over time?
- Am I learning from corrections?
- Which types of queries am I getting better at?
- Where do I still struggle?

This module:
1. Tracks performance metrics over time
2. Identifies improvement areas
3. Measures learning velocity
4. Generates self-improvement reports
"""

import os
import sqlite3
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from contextlib import contextmanager
from enum import Enum

logger = logging.getLogger("aria.memory.self_improvement")

# Configuration
IMPROVEMENT_DB_PATH = Path(os.getenv("ARIA_IMPROVEMENT_DB", "/opt/fpai/aria-command/state/improvement.db"))


class InteractionOutcome(str, Enum):
    """Outcome of an interaction."""
    SUCCESS = "success"       # Task completed well
    PARTIAL = "partial"       # Partially successful
    CORRECTION = "correction" # James corrected something
    FAILURE = "failure"       # Something went wrong
    UNKNOWN = "unknown"       # Outcome not clear


class QueryType(str, Enum):
    """Types of queries for performance tracking."""
    TRADING = "trading"
    STATUS = "status"
    BUILDING = "building"
    QUESTION = "question"
    COMMAND = "command"
    MEMORY = "memory"
    OTHER = "other"


@dataclass
class InteractionRecord:
    """Record of a single interaction for performance tracking."""
    id: str
    query_type: QueryType
    outcome: InteractionOutcome
    response_time_ms: float
    memory_used: int  # Number of memories retrieved
    correction_needed: bool
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "query_type": self.query_type.value,
            "outcome": self.outcome.value,
            "response_time_ms": self.response_time_ms,
            "memory_used": self.memory_used,
            "correction_needed": self.correction_needed,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics over a time period."""
    period_start: datetime
    period_end: datetime
    total_interactions: int
    success_rate: float
    correction_rate: float
    avg_response_time_ms: float
    memory_utilization: float
    by_query_type: Dict[str, Dict[str, float]]
    
    def to_dict(self) -> Dict:
        return {
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat()
            },
            "total_interactions": self.total_interactions,
            "success_rate": round(self.success_rate, 3),
            "correction_rate": round(self.correction_rate, 3),
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "memory_utilization": round(self.memory_utilization, 2),
            "by_query_type": self.by_query_type
        }


class SelfImprovementTracker:
    """
    Tracks Aria's performance and improvement over time.
    
    This is the "growth mindset" module - always seeking to improve.
    """
    
    def __init__(self):
        self._ensure_db()
        logger.info("📈 Self-improvement tracker initialized")
    
    def _ensure_db(self):
        """Create database and tables."""
        IMPROVEMENT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id TEXT PRIMARY KEY,
                    query_type TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    response_time_ms REAL,
                    memory_used INTEGER DEFAULT 0,
                    correction_needed INTEGER DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    details TEXT DEFAULT '{}'
                );
                
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    date TEXT PRIMARY KEY,
                    total_interactions INTEGER DEFAULT 0,
                    successes INTEGER DEFAULT 0,
                    corrections INTEGER DEFAULT 0,
                    failures INTEGER DEFAULT 0,
                    avg_response_ms REAL,
                    total_memory_used INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS improvement_goals (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    target_value REAL NOT NULL,
                    current_value REAL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    achieved_at TEXT,
                    active INTEGER DEFAULT 1
                );
                
                CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(query_type);
                CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_interactions_outcome ON interactions(outcome);
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(str(IMPROVEMENT_DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def record_interaction(
        self,
        query_type: QueryType,
        outcome: InteractionOutcome,
        response_time_ms: float = 0,
        memory_used: int = 0,
        details: Dict = None
    ) -> InteractionRecord:
        """
        Record an interaction for performance tracking.
        """
        now = datetime.now(timezone.utc)
        record_id = f"int_{now.timestamp()}"
        
        record = InteractionRecord(
            id=record_id,
            query_type=query_type,
            outcome=outcome,
            response_time_ms=response_time_ms,
            memory_used=memory_used,
            correction_needed=(outcome == InteractionOutcome.CORRECTION),
            timestamp=now,
            details=details or {}
        )
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO interactions
                (id, query_type, outcome, response_time_ms, memory_used, correction_needed, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.query_type.value,
                record.outcome.value,
                record.response_time_ms,
                record.memory_used,
                1 if record.correction_needed else 0,
                now.isoformat(),
                json.dumps(record.details)
            ))
            
            # Update daily metrics
            date_str = now.strftime("%Y-%m-%d")
            conn.execute("""
                INSERT INTO daily_metrics (date, total_interactions, successes, corrections, failures, avg_response_ms, total_memory_used)
                VALUES (?, 1, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_interactions = total_interactions + 1,
                    successes = successes + excluded.successes,
                    corrections = corrections + excluded.corrections,
                    failures = failures + excluded.failures,
                    avg_response_ms = (avg_response_ms * total_interactions + excluded.avg_response_ms) / (total_interactions + 1),
                    total_memory_used = total_memory_used + excluded.total_memory_used
            """, (
                date_str,
                1 if outcome == InteractionOutcome.SUCCESS else 0,
                1 if outcome == InteractionOutcome.CORRECTION else 0,
                1 if outcome == InteractionOutcome.FAILURE else 0,
                response_time_ms,
                memory_used
            ))
        
        return record
    
    def get_metrics(
        self,
        days: int = 7
    ) -> PerformanceMetrics:
        """
        Get performance metrics for the last N days.
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        
        with self._get_connection() as conn:
            # Overall metrics
            overall = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN outcome = 'correction' THEN 1 ELSE 0 END) as corrections,
                    AVG(response_time_ms) as avg_response,
                    AVG(memory_used) as avg_memory
                FROM interactions
                WHERE timestamp >= ?
            """, (start.isoformat(),)).fetchone()
            
            total = overall["total"] or 0
            successes = overall["successes"] or 0
            corrections = overall["corrections"] or 0
            
            # By query type
            by_type = {}
            type_rows = conn.execute("""
                SELECT 
                    query_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN outcome = 'correction' THEN 1 ELSE 0 END) as corrections
                FROM interactions
                WHERE timestamp >= ?
                GROUP BY query_type
            """, (start.isoformat(),)).fetchall()
            
            for row in type_rows:
                type_total = row["total"] or 0
                type_successes = row["successes"] or 0
                type_corrections = row["corrections"] or 0
                by_type[row["query_type"]] = {
                    "total": type_total,
                    "success_rate": type_successes / max(1, type_total),
                    "correction_rate": type_corrections / max(1, type_total)
                }
            
            return PerformanceMetrics(
                period_start=start,
                period_end=end,
                total_interactions=total,
                success_rate=successes / max(1, total),
                correction_rate=corrections / max(1, total),
                avg_response_time_ms=overall["avg_response"] or 0,
                memory_utilization=overall["avg_memory"] or 0,
                by_query_type=by_type
            )
    
    def get_improvement_trend(self, weeks: int = 4) -> Dict[str, Any]:
        """
        Calculate improvement trend over time.
        
        Compares recent performance to past performance.
        """
        now = datetime.now(timezone.utc)
        
        # Recent week
        recent_metrics = self.get_metrics(days=7)
        
        # Previous weeks
        previous_success_rates = []
        for week in range(1, weeks):
            start = now - timedelta(weeks=week + 1)
            end = now - timedelta(weeks=week)
            
            with self._get_connection() as conn:
                result = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes
                    FROM interactions
                    WHERE timestamp >= ? AND timestamp < ?
                """, (start.isoformat(), end.isoformat())).fetchone()
                
                if result["total"] > 0:
                    previous_success_rates.append(result["successes"] / result["total"])
        
        # Calculate trend
        if previous_success_rates:
            avg_previous = sum(previous_success_rates) / len(previous_success_rates)
            improvement = recent_metrics.success_rate - avg_previous
        else:
            avg_previous = 0
            improvement = 0
        
        return {
            "recent_success_rate": recent_metrics.success_rate,
            "previous_avg_success_rate": avg_previous,
            "improvement": improvement,
            "trend": "improving" if improvement > 0.05 else "stable" if improvement > -0.05 else "declining",
            "weeks_analyzed": weeks
        }
    
    def identify_weak_areas(self) -> List[Dict[str, Any]]:
        """
        Identify areas that need improvement.
        """
        metrics = self.get_metrics(days=14)
        weak_areas = []
        
        for query_type, type_metrics in metrics.by_query_type.items():
            if type_metrics["success_rate"] < 0.8:  # Less than 80% success
                weak_areas.append({
                    "area": query_type,
                    "success_rate": type_metrics["success_rate"],
                    "correction_rate": type_metrics["correction_rate"],
                    "total_interactions": type_metrics["total"],
                    "improvement_needed": 0.8 - type_metrics["success_rate"]
                })
        
        # Sort by most improvement needed
        weak_areas.sort(key=lambda x: x["improvement_needed"], reverse=True)
        
        return weak_areas
    
    def set_improvement_goal(
        self,
        goal: str,
        metric: str,
        target_value: float
    ) -> str:
        """
        Set an improvement goal.
        """
        goal_id = f"goal_{datetime.now(timezone.utc).timestamp()}"
        now = datetime.now(timezone.utc)
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO improvement_goals
                (id, goal, metric, target_value, current_value, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
            """, (goal_id, goal, metric, target_value, now.isoformat()))
        
        return goal_id
    
    def get_self_improvement_prompt(self) -> str:
        """
        Get self-improvement context for prompt injection.
        """
        metrics = self.get_metrics(days=7)
        trend = self.get_improvement_trend()
        weak_areas = self.identify_weak_areas()
        
        lines = ["\n## 📈 Self-Improvement Awareness\n"]
        
        # Current performance
        lines.append(f"**This week:** {metrics.total_interactions} interactions, {metrics.success_rate:.0%} success rate")
        
        # Trend
        trend_emoji = "📈" if trend["trend"] == "improving" else "📊" if trend["trend"] == "stable" else "📉"
        lines.append(f"**Trend:** {trend_emoji} {trend['trend'].title()} ({trend['improvement']:+.1%} vs previous)")
        
        # Weak areas
        if weak_areas:
            lines.append("\n**Areas to improve:**")
            for area in weak_areas[:2]:
                lines.append(f"- {area['area']}: {area['success_rate']:.0%} success (target: 80%)")
        
        lines.append("\n---\n")
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get self-improvement statistics."""
        metrics = self.get_metrics(days=30)
        trend = self.get_improvement_trend()
        weak_areas = self.identify_weak_areas()
        
        with self._get_connection() as conn:
            total_all_time = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
            active_goals = conn.execute(
                "SELECT COUNT(*) FROM improvement_goals WHERE active = 1"
            ).fetchone()[0]
        
        return {
            "total_interactions_all_time": total_all_time,
            "last_30_days": metrics.to_dict(),
            "trend": trend,
            "weak_areas": weak_areas,
            "active_goals": active_goals,
            "db_path": str(IMPROVEMENT_DB_PATH)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_tracker: Optional[SelfImprovementTracker] = None


def get_improvement_tracker() -> SelfImprovementTracker:
    """Get or create self-improvement tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = SelfImprovementTracker()
    return _tracker

