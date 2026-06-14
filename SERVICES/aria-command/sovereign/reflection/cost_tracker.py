#!/usr/bin/env python3
"""
ARIA REFLECTION COST TRACKER
============================

Tracks costs for the reflection system:
- Per-cycle costs (summarizer, dialogue, spec, build)
- Daily/weekly/monthly totals
- ROI estimation (improvements per dollar)
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.reflection.cost_tracker")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("REFLECTION_DB", "/opt/fpai/aria-command/state/reflection.db")

# Model costs (per 1K tokens, input/output)
MODEL_COSTS = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
}


@dataclass
class CycleCost:
    """Cost breakdown for a reflection cycle."""
    cycle_id: str
    summarizer_cost: float = 0.0
    dialogue_cost: float = 0.0
    spec_generation_cost: float = 0.0
    build_cost: float = 0.0
    total_cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Outcomes
    proposals_generated: int = 0
    specs_generated: int = 0
    builds_completed: int = 0
    builds_failed: int = 0
    
    def calculate_total(self):
        self.total_cost = (
            self.summarizer_cost +
            self.dialogue_cost +
            self.spec_generation_cost +
            self.build_cost
        )
    
    def to_dict(self) -> Dict:
        return {
            "cycle_id": self.cycle_id,
            "summarizer_cost": self.summarizer_cost,
            "dialogue_cost": self.dialogue_cost,
            "spec_generation_cost": self.spec_generation_cost,
            "build_cost": self.build_cost,
            "total_cost": self.total_cost,
            "timestamp": self.timestamp.isoformat(),
            "proposals_generated": self.proposals_generated,
            "specs_generated": self.specs_generated,
            "builds_completed": self.builds_completed,
            "builds_failed": self.builds_failed
        }


COST_SCHEMA = """
CREATE TABLE IF NOT EXISTS cycle_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT UNIQUE NOT NULL,
    summarizer_cost REAL DEFAULT 0,
    dialogue_cost REAL DEFAULT 0,
    spec_generation_cost REAL DEFAULT 0,
    build_cost REAL DEFAULT 0,
    total_cost REAL DEFAULT 0,
    timestamp TEXT NOT NULL,
    proposals_generated INTEGER DEFAULT 0,
    specs_generated INTEGER DEFAULT 0,
    builds_completed INTEGER DEFAULT 0,
    builds_failed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT,
    model TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost REAL,
    component TEXT,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cc_timestamp ON cycle_costs(timestamp);
CREATE INDEX IF NOT EXISTS idx_ac_cycle ON api_calls(cycle_id);
CREATE INDEX IF NOT EXISTS idx_ac_timestamp ON api_calls(timestamp);
"""


# ============================================================================
# COST TRACKER
# ============================================================================

class ReflectionCostTracker:
    """
    Tracks costs for reflection cycles.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._current_cycle: Optional[CycleCost] = None
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
            cursor.executescript(COST_SCHEMA)
        
        logger.info(f"Cost tracker initialized: {self.db_path}")
    
    # ========================================================================
    # CYCLE MANAGEMENT
    # ========================================================================
    
    def start_cycle(self, cycle_id: str) -> CycleCost:
        """Start tracking a new cycle."""
        self._current_cycle = CycleCost(cycle_id=cycle_id)
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO cycle_costs (cycle_id, timestamp)
                VALUES (?, ?)
            """, (cycle_id, self._current_cycle.timestamp.isoformat()))
        
        logger.info(f"Started tracking cycle: {cycle_id}")
        return self._current_cycle
    
    def end_cycle(self) -> Optional[CycleCost]:
        """End current cycle and finalize costs."""
        if not self._current_cycle:
            return None
        
        cycle = self._current_cycle
        cycle.calculate_total()
        
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE cycle_costs SET
                    summarizer_cost = ?,
                    dialogue_cost = ?,
                    spec_generation_cost = ?,
                    build_cost = ?,
                    total_cost = ?,
                    proposals_generated = ?,
                    specs_generated = ?,
                    builds_completed = ?,
                    builds_failed = ?
                WHERE cycle_id = ?
            """, (
                cycle.summarizer_cost,
                cycle.dialogue_cost,
                cycle.spec_generation_cost,
                cycle.build_cost,
                cycle.total_cost,
                cycle.proposals_generated,
                cycle.specs_generated,
                cycle.builds_completed,
                cycle.builds_failed,
                cycle.cycle_id
            ))
        
        logger.info(f"Cycle {cycle.cycle_id} ended: ${cycle.total_cost:.4f}")
        
        self._current_cycle = None
        return cycle
    
    # ========================================================================
    # COST RECORDING
    # ========================================================================
    
    def record_api_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        component: str,
        cycle_id: str = None
    ) -> float:
        """Record an API call and return the cost."""
        costs = MODEL_COSTS.get(model, {"input": 0.003, "output": 0.015})
        cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000
        
        if cycle_id is None and self._current_cycle:
            cycle_id = self._current_cycle.cycle_id
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO api_calls (cycle_id, model, input_tokens, output_tokens, cost, component, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cycle_id, model, input_tokens, output_tokens, cost, component, datetime.now().isoformat()))
        
        # Update current cycle
        if self._current_cycle and cycle_id == self._current_cycle.cycle_id:
            if component == "summarizer":
                self._current_cycle.summarizer_cost += cost
            elif component == "dialogue":
                self._current_cycle.dialogue_cost += cost
            elif component == "spec_generation":
                self._current_cycle.spec_generation_cost += cost
            elif component == "build":
                self._current_cycle.build_cost += cost
        
        return cost
    
    def record_summarizer_cost(self, cost: float):
        """Record summarizer cost directly."""
        if self._current_cycle:
            self._current_cycle.summarizer_cost += cost
    
    def record_dialogue_cost(self, cost: float):
        """Record dialogue cost directly."""
        if self._current_cycle:
            self._current_cycle.dialogue_cost += cost
    
    def record_spec_cost(self, cost: float):
        """Record spec generation cost directly."""
        if self._current_cycle:
            self._current_cycle.spec_generation_cost += cost
    
    def record_build_cost(self, cost: float):
        """Record build cost directly."""
        if self._current_cycle:
            self._current_cycle.build_cost += cost
    
    def record_outcomes(
        self,
        proposals: int = 0,
        specs: int = 0,
        builds_completed: int = 0,
        builds_failed: int = 0
    ):
        """Record outcomes for current cycle."""
        if self._current_cycle:
            self._current_cycle.proposals_generated += proposals
            self._current_cycle.specs_generated += specs
            self._current_cycle.builds_completed += builds_completed
            self._current_cycle.builds_failed += builds_failed
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def get_daily_cost(self, date: datetime = None) -> Dict[str, Any]:
        """Get cost for a specific day."""
        if date is None:
            date = datetime.now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    SUM(total_cost) as total,
                    SUM(summarizer_cost) as summarizer,
                    SUM(dialogue_cost) as dialogue,
                    SUM(spec_generation_cost) as spec,
                    SUM(build_cost) as build,
                    COUNT(*) as cycles,
                    SUM(proposals_generated) as proposals,
                    SUM(specs_generated) as specs,
                    SUM(builds_completed) as builds_ok,
                    SUM(builds_failed) as builds_fail
                FROM cycle_costs
                WHERE timestamp >= ? AND timestamp < ?
            """, (start.isoformat(), end.isoformat()))
            
            row = cursor.fetchone()
        
        return {
            "date": date.date().isoformat(),
            "total_cost": row["total"] or 0,
            "by_component": {
                "summarizer": row["summarizer"] or 0,
                "dialogue": row["dialogue"] or 0,
                "spec_generation": row["spec"] or 0,
                "build": row["build"] or 0
            },
            "cycles": row["cycles"] or 0,
            "outcomes": {
                "proposals": row["proposals"] or 0,
                "specs": row["specs"] or 0,
                "builds_completed": row["builds_ok"] or 0,
                "builds_failed": row["builds_fail"] or 0
            }
        }
    
    def get_weekly_cost(self, weeks_ago: int = 0) -> Dict[str, Any]:
        """Get cost for a specific week."""
        now = datetime.now()
        start = now - timedelta(days=now.weekday() + 7 * weeks_ago)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    SUM(total_cost) as total,
                    COUNT(*) as cycles,
                    SUM(builds_completed) as builds_ok
                FROM cycle_costs
                WHERE timestamp >= ? AND timestamp < ?
            """, (start.isoformat(), end.isoformat()))
            
            row = cursor.fetchone()
        
        return {
            "week_start": start.date().isoformat(),
            "week_end": end.date().isoformat(),
            "total_cost": row["total"] or 0,
            "cycles": row["cycles"] or 0,
            "builds_completed": row["builds_ok"] or 0
        }
    
    def get_monthly_cost(self, months_ago: int = 0) -> Dict[str, Any]:
        """Get cost for a specific month."""
        now = datetime.now()
        year = now.year
        month = now.month - months_ago
        
        while month < 1:
            month += 12
            year -= 1
        
        start = datetime(year, month, 1)
        
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    SUM(total_cost) as total,
                    COUNT(*) as cycles,
                    SUM(builds_completed) as builds_ok
                FROM cycle_costs
                WHERE timestamp >= ? AND timestamp < ?
            """, (start.isoformat(), end.isoformat()))
            
            row = cursor.fetchone()
        
        return {
            "month": start.strftime("%Y-%m"),
            "total_cost": row["total"] or 0,
            "cycles": row["cycles"] or 0,
            "builds_completed": row["builds_ok"] or 0
        }
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get overall cost summary."""
        daily = self.get_daily_cost()
        weekly = self.get_weekly_cost()
        monthly = self.get_monthly_cost()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    SUM(total_cost) as total,
                    COUNT(*) as cycles,
                    SUM(builds_completed) as builds_ok
                FROM cycle_costs
            """)
            all_time = cursor.fetchone()
        
        # Calculate ROI metrics
        total_cost = all_time["total"] or 0.01  # Avoid division by zero
        total_builds = all_time["builds_ok"] or 0
        cost_per_build = total_cost / max(total_builds, 1)
        
        return {
            "today": daily,
            "this_week": weekly,
            "this_month": monthly,
            "all_time": {
                "total_cost": all_time["total"] or 0,
                "cycles": all_time["cycles"] or 0,
                "builds_completed": total_builds
            },
            "roi_metrics": {
                "cost_per_improvement": cost_per_build,
                "estimated_monthly": daily.get("total_cost", 0) * 30
            }
        }
    
    def get_recent_cycles(self, limit: int = 10) -> List[Dict]:
        """Get recent cycle costs."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM cycle_costs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ============================================================================

_tracker: Optional[ReflectionCostTracker] = None


def get_cost_tracker() -> ReflectionCostTracker:
    """Get global cost tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = ReflectionCostTracker()
    return _tracker


def start_cycle(cycle_id: str) -> CycleCost:
    """Start tracking a cycle."""
    return get_cost_tracker().start_cycle(cycle_id)


def end_cycle() -> Optional[CycleCost]:
    """End current cycle."""
    return get_cost_tracker().end_cycle()


def record_cost(component: str, cost: float):
    """Record cost for a component."""
    tracker = get_cost_tracker()
    if component == "summarizer":
        tracker.record_summarizer_cost(cost)
    elif component == "dialogue":
        tracker.record_dialogue_cost(cost)
    elif component == "spec":
        tracker.record_spec_cost(cost)
    elif component == "build":
        tracker.record_build_cost(cost)


def get_cost_summary() -> Dict[str, Any]:
    """Get cost summary."""
    return get_cost_tracker().get_cost_summary()


