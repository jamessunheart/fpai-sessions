#!/usr/bin/env python3
"""
ARIA ASCENSION - ROI TRACKER
============================

Track costs and value generated:
- Cost: API calls, compute, time
- Value: Trades executed, time saved, revenue generated
- Net ROI per improvement
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.revenue.roi")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")

# Value estimates
JAMES_HOURLY_VALUE = float(os.getenv("JAMES_HOURLY_VALUE", "200"))  # $/hr
INTERACTION_TIME_SAVED = float(os.getenv("INTERACTION_TIME_SAVED", "2"))  # minutes per interaction


class CostCategory(str, Enum):
    """Categories of costs."""
    API_CALLS = "api_calls"
    COMPUTE = "compute"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    THIRD_PARTY = "third_party"


class ValueCategory(str, Enum):
    """Categories of value generated."""
    TRADING_PNL = "trading_pnl"
    TIME_SAVED = "time_saved"
    REVENUE = "revenue"
    AUTOMATION = "automation"
    IMPROVEMENT = "improvement"


@dataclass
class CostEntry:
    """A cost entry."""
    id: str
    category: CostCategory
    amount: float
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "amount": self.amount,
            "description": self.description,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ValueEntry:
    """A value entry."""
    id: str
    category: ValueCategory
    amount: float
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "amount": self.amount,
            "description": self.description,
            "timestamp": self.timestamp.isoformat()
        }


ROI_SCHEMA = """
CREATE TABLE IF NOT EXISTS costs (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    timestamp TEXT NOT NULL,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS value_generated (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    timestamp TEXT NOT NULL,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS daily_summary (
    date TEXT PRIMARY KEY,
    total_cost REAL DEFAULT 0,
    total_value REAL DEFAULT 0,
    net_roi REAL DEFAULT 0,
    interactions INTEGER DEFAULT 0,
    trades_executed INTEGER DEFAULT 0,
    improvements_applied INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS feature_roi (
    feature_name TEXT PRIMARY KEY,
    development_cost REAL DEFAULT 0,
    operational_cost REAL DEFAULT 0,
    value_generated REAL DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    first_used TEXT,
    last_used TEXT
);

CREATE INDEX IF NOT EXISTS idx_costs_cat ON costs(category);
CREATE INDEX IF NOT EXISTS idx_costs_ts ON costs(timestamp);
CREATE INDEX IF NOT EXISTS idx_value_cat ON value_generated(category);
CREATE INDEX IF NOT EXISTS idx_value_ts ON value_generated(timestamp);
"""


# ============================================================================
# ROI TRACKER
# ============================================================================

class ROITracker:
    """
    Tracks costs and value for ROI calculation.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
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
            cursor.executescript(ROI_SCHEMA)
        
        logger.info(f"ROI tracker initialized: {self.db_path}")
    
    # ========================================================================
    # COST TRACKING
    # ========================================================================
    
    def track_cost(
        self,
        category: CostCategory,
        amount: float,
        description: str,
        metadata: Dict = None
    ) -> CostEntry:
        """Track a cost."""
        entry = CostEntry(
            id=f"cost-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            category=category,
            amount=amount,
            description=description,
            metadata=metadata or {}
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO costs (id, category, amount, description, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry.id, entry.category.value, entry.amount,
                entry.description, entry.timestamp.isoformat(),
                json.dumps(entry.metadata)
            ))
            
            # Update daily summary
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO daily_summary (date, total_cost)
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET total_cost = total_cost + ?
            """, (today, amount, amount))
        
        logger.debug(f"Cost tracked: ${amount:.4f} - {description}")
        return entry
    
    def track_api_cost(self, provider: str, tokens: int, cost_per_1k: float = 0.01):
        """Track API call cost."""
        cost = (tokens / 1000) * cost_per_1k
        return self.track_cost(
            CostCategory.API_CALLS,
            cost,
            f"{provider} API call ({tokens} tokens)",
            {"provider": provider, "tokens": tokens}
        )
    
    # ========================================================================
    # VALUE TRACKING
    # ========================================================================
    
    def track_value(
        self,
        category: ValueCategory,
        amount: float,
        description: str,
        metadata: Dict = None
    ) -> ValueEntry:
        """Track value generated."""
        entry = ValueEntry(
            id=f"value-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            category=category,
            amount=amount,
            description=description,
            metadata=metadata or {}
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO value_generated (id, category, amount, description, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry.id, entry.category.value, entry.amount,
                entry.description, entry.timestamp.isoformat(),
                json.dumps(entry.metadata)
            ))
            
            # Update daily summary
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO daily_summary (date, total_value)
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET total_value = total_value + ?
            """, (today, amount, amount))
        
        logger.debug(f"Value tracked: ${amount:.2f} - {description}")
        return entry
    
    def track_trading_pnl(self, pnl: float, symbol: str = ""):
        """Track trading P&L."""
        return self.track_value(
            ValueCategory.TRADING_PNL,
            pnl,
            f"Trading P&L{' (' + symbol + ')' if symbol else ''}",
            {"symbol": symbol, "pnl": pnl}
        )
    
    def track_time_saved(self, minutes: float, task: str = ""):
        """Track time saved."""
        value = (minutes / 60) * JAMES_HOURLY_VALUE
        return self.track_value(
            ValueCategory.TIME_SAVED,
            value,
            f"Time saved: {minutes:.1f} minutes{' (' + task + ')' if task else ''}",
            {"minutes": minutes, "task": task}
        )
    
    def track_interaction(self):
        """Track an interaction (auto-calculated time saved)."""
        return self.track_time_saved(INTERACTION_TIME_SAVED, "Interaction handled")
    
    # ========================================================================
    # FEATURE ROI
    # ========================================================================
    
    def track_feature_usage(self, feature_name: str):
        """Track usage of a feature."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO feature_roi (feature_name, usage_count, first_used, last_used)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(feature_name) DO UPDATE SET
                    usage_count = usage_count + 1,
                    last_used = ?
            """, (
                feature_name,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
    
    def track_feature_cost(self, feature_name: str, cost: float, cost_type: str = "operational"):
        """Track cost of a feature."""
        with self._cursor() as cursor:
            if cost_type == "development":
                cursor.execute("""
                    INSERT INTO feature_roi (feature_name, development_cost)
                    VALUES (?, ?)
                    ON CONFLICT(feature_name) DO UPDATE SET
                        development_cost = development_cost + ?
                """, (feature_name, cost, cost))
            else:
                cursor.execute("""
                    INSERT INTO feature_roi (feature_name, operational_cost)
                    VALUES (?, ?)
                    ON CONFLICT(feature_name) DO UPDATE SET
                        operational_cost = operational_cost + ?
                """, (feature_name, cost, cost))
    
    def track_feature_value(self, feature_name: str, value: float):
        """Track value generated by a feature."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO feature_roi (feature_name, value_generated)
                VALUES (?, ?)
                ON CONFLICT(feature_name) DO UPDATE SET
                    value_generated = value_generated + ?
            """, (feature_name, value, value))
    
    # ========================================================================
    # SUMMARIES
    # ========================================================================
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """Get summary for a specific day."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM daily_summary WHERE date = ?
            """, (date,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "date": row["date"],
                    "total_cost": row["total_cost"],
                    "total_value": row["total_value"],
                    "net_roi": row["total_value"] - row["total_cost"],
                    "roi_pct": ((row["total_value"] - row["total_cost"]) / max(row["total_cost"], 0.01)) * 100
                }
            
            return {
                "date": date,
                "total_cost": 0,
                "total_value": 0,
                "net_roi": 0,
                "roi_pct": 0
            }
    
    def get_period_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary for a period."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    SUM(total_cost) as cost,
                    SUM(total_value) as value,
                    COUNT(*) as days
                FROM daily_summary
                WHERE date >= ?
            """, (cutoff,))
            row = cursor.fetchone()
            
            cost = row["cost"] or 0
            value = row["value"] or 0
            
            return {
                "period_days": days,
                "total_cost": cost,
                "total_value": value,
                "net_roi": value - cost,
                "roi_pct": ((value - cost) / max(cost, 0.01)) * 100,
                "avg_daily_cost": cost / max(row["days"] or 1, 1),
                "avg_daily_value": value / max(row["days"] or 1, 1)
            }
    
    def get_category_breakdown(self, days: int = 7) -> Dict[str, Any]:
        """Get breakdown by category."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._cursor() as cursor:
            # Costs by category
            cursor.execute("""
                SELECT category, SUM(amount) as total
                FROM costs
                WHERE timestamp >= ?
                GROUP BY category
            """, (cutoff,))
            costs = {row["category"]: row["total"] for row in cursor.fetchall()}
            
            # Value by category
            cursor.execute("""
                SELECT category, SUM(amount) as total
                FROM value_generated
                WHERE timestamp >= ?
                GROUP BY category
            """, (cutoff,))
            value = {row["category"]: row["total"] for row in cursor.fetchall()}
        
        return {
            "period_days": days,
            "costs_by_category": costs,
            "value_by_category": value
        }
    
    def get_feature_roi(self) -> List[Dict]:
        """Get ROI for all features."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    feature_name,
                    development_cost,
                    operational_cost,
                    value_generated,
                    usage_count,
                    (value_generated - development_cost - operational_cost) as net_roi
                FROM feature_roi
                ORDER BY net_roi DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_roi_dashboard(self) -> Dict[str, Any]:
        """Get complete ROI dashboard data."""
        return {
            "today": self.get_daily_summary(),
            "last_7_days": self.get_period_summary(7),
            "last_30_days": self.get_period_summary(30),
            "category_breakdown": self.get_category_breakdown(7),
            "top_features": self.get_feature_roi()[:10],
            "generated_at": datetime.now().isoformat()
        }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_tracker: Optional[ROITracker] = None


def get_roi_tracker() -> ROITracker:
    """Get global ROI tracker."""
    global _tracker
    if _tracker is None:
        _tracker = ROITracker()
    return _tracker


def track_cost(category: str, amount: float, description: str) -> CostEntry:
    """Track a cost."""
    return get_roi_tracker().track_cost(CostCategory(category), amount, description)


def track_value(category: str, amount: float, description: str) -> ValueEntry:
    """Track value."""
    return get_roi_tracker().track_value(ValueCategory(category), amount, description)


def get_roi_summary(days: int = 7) -> Dict:
    """Get ROI summary."""
    return get_roi_tracker().get_period_summary(days)


