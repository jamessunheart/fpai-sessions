#!/usr/bin/env python3
"""
📈 EQUITY CURVE TRACKER
=========================

Tracks equity curve for risk calculations.

Features:
- Daily equity snapshots
- Intraday snapshots for real-time tracking
- Integration with risk metrics calculator
"""

import sqlite3
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("aria.trading.equity")

# Data directory
DATA_DIR = Path("/opt/fpai/aria-command/data/trading")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "equity.db"


@dataclass
class EquitySnapshot:
    """A snapshot of account equity."""
    timestamp: datetime
    account_value: float
    open_positions_value: float
    unrealized_pnl: float
    realized_pnl_daily: float
    
    @property
    def total_value(self) -> float:
        """Total equity value."""
        return self.account_value
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "account_value": round(self.account_value, 2),
            "open_positions_value": round(self.open_positions_value, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "realized_pnl_daily": round(self.realized_pnl_daily, 2)
        }


class EquityTracker:
    """
    Tracks equity curve for risk calculations.
    
    Records daily and intraday snapshots of:
    - Account value
    - Open positions value
    - Realized P&L
    """
    
    def __init__(self):
        self._db_path = DB_PATH
        self._init_db()
        
        # Cache for current day
        self._today_snapshots: List[EquitySnapshot] = []
        self._last_snapshot: Optional[EquitySnapshot] = None
    
    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self._db_path) as conn:
            # Daily snapshots (end of day)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_equity (
                    date TEXT PRIMARY KEY,
                    account_value REAL,
                    open_positions_value REAL,
                    unrealized_pnl REAL,
                    realized_pnl REAL,
                    timestamp TEXT
                )
            """)
            
            # Intraday snapshots (more granular)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intraday_equity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    account_value REAL,
                    open_positions_value REAL,
                    unrealized_pnl REAL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_intraday_time
                ON intraday_equity(timestamp)
            """)
    
    async def record_snapshot(self) -> Optional[EquitySnapshot]:
        """Record current equity snapshot."""
        try:
            from .hyperliquid_live import get_hyperliquid
            
            hl = get_hyperliquid()
            
            if not hl.is_connected:
                return None
            
            state = hl.get_account_state()
            positions = hl.get_positions()
            
            if state.get("error"):
                return None
            
            # Calculate position values
            positions_value = sum(p.get("size_usd", 0) for p in positions)
            unrealized_pnl = sum(p.get("unrealized_pnl", 0) for p in positions)
            
            snapshot = EquitySnapshot(
                timestamp=datetime.now(),
                account_value=state.get("account_value", 0),
                open_positions_value=positions_value,
                unrealized_pnl=unrealized_pnl,
                realized_pnl_daily=0  # Would need to track this separately
            )
            
            # Store intraday
            self._store_intraday(snapshot)
            
            # Update cache
            self._last_snapshot = snapshot
            self._today_snapshots.append(snapshot)
            
            logger.debug(f"📈 Equity snapshot: ${snapshot.account_value:,.2f}")
            
            return snapshot
        
        except Exception as e:
            logger.error(f"Failed to record equity snapshot: {e}")
            return None
    
    def _store_intraday(self, snapshot: EquitySnapshot):
        """Store intraday snapshot."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT INTO intraday_equity
                (timestamp, account_value, open_positions_value, unrealized_pnl)
                VALUES (?, ?, ?, ?)
            """, (
                snapshot.timestamp.isoformat(),
                snapshot.account_value,
                snapshot.open_positions_value,
                snapshot.unrealized_pnl
            ))
    
    async def record_daily_snapshot(self):
        """Record end-of-day equity snapshot."""
        snapshot = await self.record_snapshot()
        
        if snapshot:
            today = date.today().isoformat()
            
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO daily_equity
                    (date, account_value, open_positions_value, 
                     unrealized_pnl, realized_pnl, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    today,
                    snapshot.account_value,
                    snapshot.open_positions_value,
                    snapshot.unrealized_pnl,
                    snapshot.realized_pnl_daily,
                    snapshot.timestamp.isoformat()
                ))
            
            logger.info(f"📅 Daily equity recorded: ${snapshot.account_value:,.2f}")
    
    def get_equity_curve(self, days: int = 30) -> List[float]:
        """Get equity values for risk calculations."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT account_value
                FROM daily_equity
                WHERE date >= ?
                ORDER BY date
            """, (cutoff,))
            
            return [row[0] for row in cursor.fetchall()]
    
    def get_daily_returns(self, days: int = 30) -> List[float]:
        """Calculate daily percentage returns."""
        equity_curve = self.get_equity_curve(days)
        
        if len(equity_curve) < 2:
            return []
        
        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] != 0:
                ret = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                returns.append(ret * 100)  # As percentage
        
        return returns
    
    def get_daily_snapshots(self, days: int = 30) -> List[Dict]:
        """Get daily equity snapshots."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT date, account_value, open_positions_value,
                       unrealized_pnl, realized_pnl
                FROM daily_equity
                WHERE date >= ?
                ORDER BY date DESC
            """, (cutoff,))
            
            return [
                {
                    "date": row[0],
                    "account_value": row[1],
                    "open_positions_value": row[2],
                    "unrealized_pnl": row[3],
                    "realized_pnl": row[4]
                }
                for row in cursor.fetchall()
            ]
    
    def get_intraday_curve(self, hours: int = 24) -> List[Tuple[datetime, float]]:
        """Get intraday equity curve."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, account_value
                FROM intraday_equity
                WHERE timestamp >= ?
                ORDER BY timestamp
            """, (cutoff,))
            
            return [
                (datetime.fromisoformat(row[0]), row[1])
                for row in cursor.fetchall()
            ]
    
    def get_current_equity(self) -> float:
        """Get most recent equity value."""
        if self._last_snapshot:
            return self._last_snapshot.account_value
        
        # Try from database
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT account_value FROM intraday_equity
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            return row[0] if row else 0.0
    
    def get_today_pnl(self) -> float:
        """Get today's P&L."""
        # Get yesterday's close
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT account_value FROM daily_equity
                WHERE date = ?
            """, (yesterday,))
            row = cursor.fetchone()
            
            if row:
                yesterday_close = row[0]
                current = self.get_current_equity()
                return current - yesterday_close
        
        return 0.0
    
    def get_statistics(self, days: int = 30) -> Dict:
        """Get equity statistics."""
        curve = self.get_equity_curve(days)
        
        if not curve:
            return {
                "current": 0,
                "high": 0,
                "low": 0,
                "change_pct": 0,
                "days": 0
            }
        
        return {
            "current": curve[-1] if curve else 0,
            "high": max(curve),
            "low": min(curve),
            "start": curve[0],
            "change_pct": ((curve[-1] - curve[0]) / curve[0] * 100) if curve[0] else 0,
            "days": len(curve)
        }
    
    def cleanup_old_data(self, keep_daily_days: int = 365, keep_intraday_days: int = 7):
        """Clean up old data to save space."""
        daily_cutoff = (date.today() - timedelta(days=keep_daily_days)).isoformat()
        intraday_cutoff = (datetime.now() - timedelta(days=keep_intraday_days)).isoformat()
        
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM daily_equity WHERE date < ?", (daily_cutoff,))
            conn.execute("DELETE FROM intraday_equity WHERE timestamp < ?", (intraday_cutoff,))
            conn.execute("VACUUM")


# Singleton
_equity_tracker: Optional[EquityTracker] = None


def get_equity_tracker() -> EquityTracker:
    """Get or create global equity tracker."""
    global _equity_tracker
    if _equity_tracker is None:
        _equity_tracker = EquityTracker()
    return _equity_tracker


async def record_equity_snapshot():
    """Record current equity snapshot."""
    tracker = get_equity_tracker()
    return await tracker.record_snapshot()


async def record_daily_equity():
    """Record daily equity snapshot."""
    tracker = get_equity_tracker()
    await tracker.record_daily_snapshot()


def get_equity_curve(days: int = 30) -> List[float]:
    """Get equity curve."""
    tracker = get_equity_tracker()
    return tracker.get_equity_curve(days)









