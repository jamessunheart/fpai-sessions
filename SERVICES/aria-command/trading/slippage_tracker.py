#!/usr/bin/env python3
"""
📉 SLIPPAGE TRACKER
=====================

Tracks execution quality via slippage analysis.

Features:
- Record slippage for every trade
- Calculate rolling averages
- Alert on excessive slippage
- Generate execution quality reports
"""

import sqlite3
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger("aria.trading.slippage")

# Data directory
DATA_DIR = Path("/opt/fpai/aria-command/data/trading")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "slippage.db"


@dataclass
class SlippageRecord:
    """Record of slippage for a trade."""
    trade_id: str
    symbol: str
    side: str
    intended_price: float      # Price when we decided to trade
    order_price: float         # Price we sent to exchange
    fill_price: float          # Actual execution price
    size: float
    timestamp: datetime
    
    @property
    def slippage_bps(self) -> float:
        """Slippage in basis points (relative to intended price)."""
        if self.intended_price == 0:
            return 0.0
        
        # For buys, positive slippage is bad (paid more)
        # For sells, negative slippage is bad (received less)
        if self.side.lower() == "buy":
            return ((self.fill_price - self.intended_price) / self.intended_price) * 10000
        else:
            return ((self.intended_price - self.fill_price) / self.intended_price) * 10000
    
    @property
    def slippage_usd(self) -> float:
        """Slippage in USD."""
        return abs(self.fill_price - self.intended_price) * self.size
    
    @property
    def is_favorable(self) -> bool:
        """Check if slippage was in our favor."""
        return self.slippage_bps < 0
    
    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side,
            "intended_price": self.intended_price,
            "order_price": self.order_price,
            "fill_price": self.fill_price,
            "size": self.size,
            "slippage_bps": round(self.slippage_bps, 2),
            "slippage_usd": round(self.slippage_usd, 4),
            "is_favorable": self.is_favorable,
            "timestamp": self.timestamp.isoformat()
        }


class SlippageTracker:
    """
    Tracks execution quality via slippage analysis.
    
    Features:
    - Record slippage for every trade
    - Calculate rolling averages
    - Alert on excessive slippage
    - Generate execution quality reports
    """
    
    def __init__(self):
        self._db_path = DB_PATH
        self._init_db()
        
        # Alert threshold (basis points)
        self._alert_threshold_bps = 50  # Alert if > 0.5% slippage
    
    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS slippage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    symbol TEXT,
                    side TEXT,
                    intended_price REAL,
                    order_price REAL,
                    fill_price REAL,
                    size REAL,
                    slippage_bps REAL,
                    slippage_usd REAL,
                    timestamp TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_slippage_time
                ON slippage_records(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_slippage_symbol
                ON slippage_records(symbol)
            """)
    
    def record_execution(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        intended_price: float,
        fill_price: float,
        size: float,
        order_price: Optional[float] = None
    ) -> SlippageRecord:
        """Record slippage for a trade."""
        if order_price is None:
            order_price = intended_price
        
        record = SlippageRecord(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            intended_price=intended_price,
            order_price=order_price,
            fill_price=fill_price,
            size=size,
            timestamp=datetime.now()
        )
        
        # Store in database
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO slippage_records
                (trade_id, symbol, side, intended_price, order_price, fill_price,
                 size, slippage_bps, slippage_usd, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.trade_id,
                record.symbol,
                record.side,
                record.intended_price,
                record.order_price,
                record.fill_price,
                record.size,
                record.slippage_bps,
                record.slippage_usd,
                record.timestamp.isoformat()
            ))
        
        logger.info(
            f"📉 Recorded slippage: {symbol} {side} - "
            f"{record.slippage_bps:.1f} bps (${record.slippage_usd:.2f})"
        )
        
        return record
    
    def get_average_slippage(
        self,
        symbol: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """
        Get average slippage statistics.
        
        Returns:
        {
            "avg_slippage_bps": 12.5,
            "max_slippage_bps": 45.0,
            "total_slippage_usd": 23.50,
            "trades_analyzed": 50,
            "excessive_slippage_count": 2
        }
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self._db_path) as conn:
            if symbol:
                cursor = conn.execute("""
                    SELECT 
                        AVG(slippage_bps) as avg_bps,
                        MAX(slippage_bps) as max_bps,
                        MIN(slippage_bps) as min_bps,
                        SUM(slippage_usd) as total_usd,
                        COUNT(*) as trades,
                        SUM(CASE WHEN ABS(slippage_bps) > ? THEN 1 ELSE 0 END) as excessive
                    FROM slippage_records
                    WHERE symbol = ? AND timestamp >= ?
                """, (self._alert_threshold_bps, symbol, cutoff))
            else:
                cursor = conn.execute("""
                    SELECT 
                        AVG(slippage_bps) as avg_bps,
                        MAX(slippage_bps) as max_bps,
                        MIN(slippage_bps) as min_bps,
                        SUM(slippage_usd) as total_usd,
                        COUNT(*) as trades,
                        SUM(CASE WHEN ABS(slippage_bps) > ? THEN 1 ELSE 0 END) as excessive
                    FROM slippage_records
                    WHERE timestamp >= ?
                """, (self._alert_threshold_bps, cutoff))
            
            row = cursor.fetchone()
            
            return {
                "avg_slippage_bps": round(row[0] or 0, 2),
                "max_slippage_bps": round(row[1] or 0, 2),
                "min_slippage_bps": round(row[2] or 0, 2),
                "total_slippage_usd": round(row[3] or 0, 2),
                "trades_analyzed": row[4] or 0,
                "excessive_slippage_count": row[5] or 0,
                "days_analyzed": days,
                "symbol": symbol
            }
    
    def get_slippage_by_hour(self, days: int = 30) -> Dict[int, float]:
        """Get slippage broken down by hour of day."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                    AVG(slippage_bps) as avg_bps
                FROM slippage_records
                WHERE timestamp >= ?
                GROUP BY hour
                ORDER BY hour
            """, (cutoff,))
            
            return {row[0]: round(row[1], 2) for row in cursor.fetchall()}
    
    def get_slippage_by_symbol(self, days: int = 30) -> Dict[str, Dict]:
        """Get slippage statistics by symbol."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    symbol,
                    AVG(slippage_bps) as avg_bps,
                    COUNT(*) as trades,
                    SUM(slippage_usd) as total_usd
                FROM slippage_records
                WHERE timestamp >= ?
                GROUP BY symbol
                ORDER BY avg_bps DESC
            """, (cutoff,))
            
            return {
                row[0]: {
                    "avg_slippage_bps": round(row[1], 2),
                    "trades": row[2],
                    "total_slippage_usd": round(row[3], 2)
                }
                for row in cursor.fetchall()
            }
    
    def get_recent_slippage(self, limit: int = 20) -> List[Dict]:
        """Get recent slippage records."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT trade_id, symbol, side, intended_price, order_price,
                       fill_price, size, slippage_bps, slippage_usd, timestamp
                FROM slippage_records
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    "trade_id": row[0],
                    "symbol": row[1],
                    "side": row[2],
                    "intended_price": row[3],
                    "order_price": row[4],
                    "fill_price": row[5],
                    "size": row[6],
                    "slippage_bps": round(row[7], 2),
                    "slippage_usd": round(row[8], 4),
                    "timestamp": row[9]
                })
            
            return records
    
    async def alert_if_excessive(self, record: SlippageRecord):
        """Alert steward if slippage exceeds threshold."""
        if abs(record.slippage_bps) > self._alert_threshold_bps:
            await self._send_alert(record)
    
    async def _send_alert(self, record: SlippageRecord):
        """Send slippage alert."""
        try:
            from telegram.bot import get_bot
            
            emoji = "📈" if record.is_favorable else "📉"
            
            bot = await get_bot()
            steward_id = 1087024913
            
            await bot.send_message(
                chat_id=steward_id,
                text=(
                    f"{emoji} **High Slippage Alert**\n\n"
                    f"Symbol: {record.symbol}\n"
                    f"Side: {record.side}\n"
                    f"Intended: ${record.intended_price:,.2f}\n"
                    f"Filled: ${record.fill_price:,.2f}\n"
                    f"Slippage: {record.slippage_bps:.0f} bps (${record.slippage_usd:.2f})\n"
                    f"{'✅ In your favor!' if record.is_favorable else '⚠️ Against you'}"
                )
            )
        except Exception as e:
            logger.error(f"Failed to send slippage alert: {e}")
    
    def generate_report(self, days: int = 30) -> str:
        """Generate slippage report."""
        stats = self.get_average_slippage(days=days)
        by_hour = self.get_slippage_by_hour(days)
        by_symbol = self.get_slippage_by_symbol(days)
        
        lines = [
            "📉 **SLIPPAGE REPORT**",
            "=" * 40,
            "",
            f"📅 Period: Last {days} days",
            f"📊 Trades Analyzed: {stats['trades_analyzed']}",
            "",
            "**📈 Overall Statistics**",
            f"  Avg Slippage: {stats['avg_slippage_bps']:.1f} bps",
            f"  Max Slippage: {stats['max_slippage_bps']:.1f} bps",
            f"  Min Slippage: {stats['min_slippage_bps']:.1f} bps",
            f"  Total Cost: ${stats['total_slippage_usd']:.2f}",
            f"  Excessive (>{self._alert_threshold_bps} bps): {stats['excessive_slippage_count']}",
            ""
        ]
        
        if by_symbol:
            lines.append("**📊 By Symbol**")
            for symbol, data in sorted(by_symbol.items(), key=lambda x: x[1]["avg_slippage_bps"], reverse=True)[:5]:
                lines.append(
                    f"  {symbol}: {data['avg_slippage_bps']:.1f} bps "
                    f"({data['trades']} trades, ${data['total_slippage_usd']:.2f})"
                )
            lines.append("")
        
        if by_hour:
            # Find best and worst hours
            best_hour = min(by_hour.items(), key=lambda x: x[1])
            worst_hour = max(by_hour.items(), key=lambda x: x[1])
            
            lines.append("**⏰ By Hour**")
            lines.append(f"  Best Hour: {best_hour[0]:02d}:00 ({best_hour[1]:.1f} bps)")
            lines.append(f"  Worst Hour: {worst_hour[0]:02d}:00 ({worst_hour[1]:.1f} bps)")
        
        return "\n".join(lines)


# Singleton
_slippage_tracker: Optional[SlippageTracker] = None


def get_slippage_tracker() -> SlippageTracker:
    """Get or create global slippage tracker."""
    global _slippage_tracker
    if _slippage_tracker is None:
        _slippage_tracker = SlippageTracker()
    return _slippage_tracker


def record_slippage(
    trade_id: str,
    symbol: str,
    side: str,
    intended_price: float,
    fill_price: float,
    size: float
) -> SlippageRecord:
    """Record slippage for a trade."""
    tracker = get_slippage_tracker()
    return tracker.record_execution(
        trade_id, symbol, side, intended_price, fill_price, size
    )









