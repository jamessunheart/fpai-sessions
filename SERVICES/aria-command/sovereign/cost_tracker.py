#!/usr/bin/env python3
"""
ARIA SELF-IMPROVEMENT COST TRACKER
===================================

Tracks costs associated with the self-improvement system:
- Claude Opus API calls for analysis
- Token usage
- Daily/weekly/monthly spending
- Budget enforcement

Features:
- Real-time cost tracking
- Daily spend limits
- Cost alerts via Telegram
- Historical cost analysis
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.sovereign.cost_tracker")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ARIA_COST_DB", "/opt/fpai/aria-command/state/improvement_costs.db")
DAILY_LIMIT_USD = float(os.getenv("ARIA_DAILY_COST_LIMIT", "5.0"))

# Claude pricing (approximate, update as needed)
CLAUDE_PRICING = {
    "claude-3-opus": {"input": 0.015, "output": 0.075},  # per 1K tokens
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-sonnet-4": {"input": 0.003, "output": 0.015},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}


@dataclass
class CostEvent:
    """A cost event."""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    category: str = "review"  # review, execution, analysis
    model: str = "claude-3-opus"
    
    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    
    # Calculated cost
    cost_usd: float = 0.0
    
    # Context
    description: str = ""
    improvement_id: Optional[str] = None


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    category TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL NOT NULL,
    description TEXT,
    improvement_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_costs_timestamp ON costs(timestamp);
CREATE INDEX IF NOT EXISTS idx_costs_category ON costs(category);

CREATE TABLE IF NOT EXISTS daily_summaries (
    date TEXT PRIMARY KEY,
    total_cost_usd REAL,
    total_input_tokens INTEGER,
    total_output_tokens INTEGER,
    review_count INTEGER,
    improvements_made INTEGER
);

CREATE TABLE IF NOT EXISTS budget_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT,
    acknowledged INTEGER DEFAULT 0
);
"""


class CostTracker:
    """
    Track and manage self-improvement costs.
    
    Features:
    - Log all API costs
    - Enforce daily spending limits
    - Generate cost reports
    - Alert on budget issues
    """
    
    def __init__(self, db_path: str = DB_PATH, daily_limit: float = DAILY_LIMIT_USD):
        self.db_path = db_path
        self.daily_limit = daily_limit
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
        logger.info(f"Cost tracker initialized: {self.db_path}")
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for a model call."""
        pricing = CLAUDE_PRICING.get(model, CLAUDE_PRICING["claude-3-opus"])
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    
    def log_cost(
        self,
        category: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        description: str = "",
        improvement_id: Optional[str] = None
    ) -> CostEvent:
        """
        Log a cost event.
        
        Returns the CostEvent with calculated cost.
        """
        cost_usd = self.calculate_cost(model, input_tokens, output_tokens)
        
        event = CostEvent(
            category=category,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            description=description,
            improvement_id=improvement_id
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO costs (
                    timestamp, category, model, input_tokens, output_tokens,
                    cost_usd, description, improvement_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp.isoformat(),
                event.category,
                event.model,
                event.input_tokens,
                event.output_tokens,
                event.cost_usd,
                event.description,
                event.improvement_id
            ))
            event.id = cursor.lastrowid
        
        logger.info(f"Cost logged: ${cost_usd:.4f} ({model}, {category})")
        
        # Check budget
        self._check_budget()
        
        return event
    
    def _check_budget(self):
        """Check if daily budget is exceeded."""
        today_cost = self.get_today_cost()
        
        if today_cost >= self.daily_limit:
            self._create_alert(
                "budget_exceeded",
                f"Daily budget of ${self.daily_limit:.2f} exceeded! Current: ${today_cost:.2f}"
            )
        elif today_cost >= self.daily_limit * 0.8:
            self._create_alert(
                "budget_warning",
                f"Approaching daily budget: ${today_cost:.2f} / ${self.daily_limit:.2f}"
            )
    
    def _create_alert(self, alert_type: str, message: str):
        """Create a budget alert."""
        with self._cursor() as cursor:
            # Check if we already have this alert today
            cursor.execute("""
                SELECT id FROM budget_alerts
                WHERE alert_type = ? AND timestamp >= ?
            """, (alert_type, datetime.now().date().isoformat()))
            
            if cursor.fetchone():
                return  # Already alerted today
            
            cursor.execute("""
                INSERT INTO budget_alerts (timestamp, alert_type, message)
                VALUES (?, ?, ?)
            """, (datetime.now().isoformat(), alert_type, message))
        
        logger.warning(f"Budget alert: {message}")
    
    def get_today_cost(self) -> float:
        """Get total cost for today."""
        today = datetime.now().date().isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(SUM(cost_usd), 0) as total
                FROM costs
                WHERE timestamp >= ?
            """, (today,))
            return cursor.fetchone()["total"]
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget for today."""
        return max(0, self.daily_limit - self.get_today_cost())
    
    def can_spend(self, estimated_cost: float) -> bool:
        """Check if we can afford an operation."""
        return self.get_remaining_budget() >= estimated_cost
    
    def get_cost_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get cost summary for the specified period."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._cursor() as cursor:
            # Total costs
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(cost_usd), 0) as total_cost,
                    COALESCE(SUM(input_tokens), 0) as total_input,
                    COALESCE(SUM(output_tokens), 0) as total_output,
                    COUNT(*) as call_count
                FROM costs
                WHERE timestamp >= ?
            """, (since,))
            totals = dict(cursor.fetchone())
            
            # By category
            cursor.execute("""
                SELECT category, SUM(cost_usd) as cost
                FROM costs
                WHERE timestamp >= ?
                GROUP BY category
            """, (since,))
            by_category = {row["category"]: row["cost"] for row in cursor.fetchall()}
            
            # By model
            cursor.execute("""
                SELECT model, SUM(cost_usd) as cost, COUNT(*) as calls
                FROM costs
                WHERE timestamp >= ?
                GROUP BY model
            """, (since,))
            by_model = {row["model"]: {"cost": row["cost"], "calls": row["calls"]} 
                       for row in cursor.fetchall()}
            
            # Daily breakdown
            cursor.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    SUM(cost_usd) as cost
                FROM costs
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (since,))
            daily = [{"date": row["date"], "cost": row["cost"]} 
                    for row in cursor.fetchall()]
        
        return {
            "period_days": days,
            "total_cost_usd": totals["total_cost"],
            "total_input_tokens": totals["total_input"],
            "total_output_tokens": totals["total_output"],
            "total_calls": totals["call_count"],
            "avg_cost_per_call": totals["total_cost"] / max(1, totals["call_count"]),
            "by_category": by_category,
            "by_model": by_model,
            "daily_breakdown": daily,
            "today_cost": self.get_today_cost(),
            "remaining_budget": self.get_remaining_budget()
        }
    
    def get_unacknowledged_alerts(self) -> List[Dict[str, Any]]:
        """Get unacknowledged budget alerts."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM budget_alerts
                WHERE acknowledged = 0
                ORDER BY timestamp DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def acknowledge_alert(self, alert_id: int):
        """Acknowledge a budget alert."""
        with self._cursor() as cursor:
            cursor.execute(
                "UPDATE budget_alerts SET acknowledged = 1 WHERE id = ?",
                (alert_id,)
            )
    
    def format_report(self, days: int = 7) -> str:
        """Format a human-readable cost report."""
        summary = self.get_cost_summary(days)
        
        lines = [
            f"**Cost Report ({days} days)**",
            "",
            f"Total: ${summary['total_cost_usd']:.2f}",
            f"Calls: {summary['total_calls']}",
            f"Avg/call: ${summary['avg_cost_per_call']:.4f}",
            "",
            f"Today: ${summary['today_cost']:.2f} / ${self.daily_limit:.2f}",
            f"Remaining: ${summary['remaining_budget']:.2f}",
            "",
            "**By Category:**"
        ]
        
        for cat, cost in summary["by_category"].items():
            lines.append(f"  {cat}: ${cost:.2f}")
        
        lines.append("")
        lines.append("**By Model:**")
        for model, data in summary["by_model"].items():
            lines.append(f"  {model}: ${data['cost']:.2f} ({data['calls']} calls)")
        
        return "\n".join(lines)
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get or create global cost tracker."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker


def log_cost(category: str, model: str, input_tokens: int, output_tokens: int, **kwargs) -> CostEvent:
    """Log a cost event."""
    return get_cost_tracker().log_cost(category, model, input_tokens, output_tokens, **kwargs)


def can_spend(estimated_cost: float) -> bool:
    """Check if we can afford an operation."""
    return get_cost_tracker().can_spend(estimated_cost)


def get_remaining_budget() -> float:
    """Get remaining budget for today."""
    return get_cost_tracker().get_remaining_budget()


