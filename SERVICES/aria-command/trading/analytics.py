#!/usr/bin/env python3
"""
📊 TRADING ANALYTICS ENGINE
============================

Comprehensive trading performance analytics:
- Win rate tracking
- Profit/loss analysis
- Risk metrics (Sharpe, max drawdown)
- Trade pattern recognition
- Strategy comparison
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import statistics

logger = logging.getLogger("aria.trading.analytics")

# Database path
DATA_DIR = Path(os.getenv("ARIA_DATA_DIR", "/opt/fpai/aria-command/data"))
DB_PATH = DATA_DIR / "trading_analytics.db"


@dataclass
class Trade:
    """A completed trade record."""
    id: str
    symbol: str
    side: str  # long or short
    entry_price: float
    exit_price: float
    size_usd: float
    leverage: int
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    strategy: str
    exit_reason: str  # target, stop, manual, signal
    confidence: float = 0.0
    notes: str = ""


@dataclass 
class PerformanceMetrics:
    """Performance summary metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_percent: float
    average_hold_time: timedelta
    best_symbol: str
    worst_symbol: str
    best_strategy: str
    current_streak: int  # Positive = wins, negative = losses


class TradingAnalytics:
    """
    Trading performance analytics engine.
    """
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                size_usd REAL NOT NULL,
                leverage INTEGER DEFAULT 1,
                entry_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP NOT NULL,
                pnl REAL NOT NULL,
                pnl_percent REAL NOT NULL,
                strategy TEXT DEFAULT 'manual',
                exit_reason TEXT DEFAULT 'manual',
                confidence REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equity_curve (
                timestamp TIMESTAMP PRIMARY KEY,
                equity REAL NOT NULL,
                drawdown REAL DEFAULT 0,
                daily_pnl REAL DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT NOT NULL,
                description TEXT,
                win_rate REAL,
                avg_pnl REAL,
                occurrences INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_trade(self, trade: Trade):
        """Record a completed trade."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO trades 
            (id, symbol, side, entry_price, exit_price, size_usd, leverage,
             entry_time, exit_time, pnl, pnl_percent, strategy, exit_reason,
             confidence, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.id, trade.symbol, trade.side, trade.entry_price,
            trade.exit_price, trade.size_usd, trade.leverage,
            trade.entry_time.isoformat(), trade.exit_time.isoformat(),
            trade.pnl, trade.pnl_percent, trade.strategy, trade.exit_reason,
            trade.confidence, trade.notes
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📊 Recorded trade: {trade.id} - {trade.symbol} ${trade.pnl:+,.2f}")
        
        # Update equity curve
        self._update_equity_curve(trade.pnl)
    
    def _update_equity_curve(self, pnl_change: float):
        """Update equity curve with new trade."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Get current equity
        cursor.execute("SELECT equity FROM equity_curve ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        current_equity = row[0] if row else 10000.0  # Start with $10k
        
        new_equity = current_equity + pnl_change
        
        # Calculate drawdown
        cursor.execute("SELECT MAX(equity) FROM equity_curve")
        row = cursor.fetchone()
        peak_equity = row[0] if row and row[0] else new_equity
        
        drawdown = peak_equity - new_equity if new_equity < peak_equity else 0
        
        cursor.execute("""
            INSERT INTO equity_curve (timestamp, equity, drawdown, daily_pnl)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), new_equity, drawdown, pnl_change))
        
        conn.commit()
        conn.close()
    
    def get_trades(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        days: int = 30,
        limit: int = 100
    ) -> List[Trade]:
        """Get trade history with optional filters."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        query = "SELECT * FROM trades WHERE exit_time > ?"
        params = [(datetime.now() - timedelta(days=days)).isoformat()]
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)
        
        query += " ORDER BY exit_time DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trades.append(Trade(
                id=row[0],
                symbol=row[1],
                side=row[2],
                entry_price=row[3],
                exit_price=row[4],
                size_usd=row[5],
                leverage=row[6],
                entry_time=datetime.fromisoformat(row[7]),
                exit_time=datetime.fromisoformat(row[8]),
                pnl=row[9],
                pnl_percent=row[10],
                strategy=row[11],
                exit_reason=row[12],
                confidence=row[13] or 0,
                notes=row[14] or ""
            ))
        
        return trades
    
    def get_performance(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        days: int = 30
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        trades = self.get_trades(symbol=symbol, strategy=strategy, days=days, limit=1000)
        
        if not trades:
            return PerformanceMetrics(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, total_pnl=0, average_win=0, average_loss=0,
                largest_win=0, largest_loss=0, profit_factor=0,
                sharpe_ratio=0, max_drawdown=0, max_drawdown_percent=0,
                average_hold_time=timedelta(0), best_symbol="N/A",
                worst_symbol="N/A", best_strategy="N/A", current_streak=0
            )
        
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in trades)
        win_pnl = sum(t.pnl for t in wins) if wins else 0
        loss_pnl = abs(sum(t.pnl for t in losses)) if losses else 0
        
        # Symbol performance
        symbol_pnl: Dict[str, float] = {}
        for t in trades:
            symbol_pnl[t.symbol] = symbol_pnl.get(t.symbol, 0) + t.pnl
        
        best_symbol = max(symbol_pnl.items(), key=lambda x: x[1])[0] if symbol_pnl else "N/A"
        worst_symbol = min(symbol_pnl.items(), key=lambda x: x[1])[0] if symbol_pnl else "N/A"
        
        # Strategy performance
        strategy_pnl: Dict[str, float] = {}
        for t in trades:
            strategy_pnl[t.strategy] = strategy_pnl.get(t.strategy, 0) + t.pnl
        
        best_strategy = max(strategy_pnl.items(), key=lambda x: x[1])[0] if strategy_pnl else "N/A"
        
        # Calculate Sharpe ratio (simplified)
        returns = [t.pnl_percent for t in trades]
        sharpe = 0
        if len(returns) > 1 and statistics.stdev(returns) > 0:
            sharpe = (statistics.mean(returns) / statistics.stdev(returns)) * (252 ** 0.5)  # Annualized
        
        # Max drawdown
        equity = 10000.0
        peak = equity
        max_dd = 0
        max_dd_pct = 0
        
        for t in sorted(trades, key=lambda x: x.exit_time):
            equity += t.pnl
            if equity > peak:
                peak = equity
            dd = peak - equity
            dd_pct = dd / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        
        # Current streak
        streak = 0
        for t in trades:  # Already sorted by exit_time DESC
            if streak == 0:
                streak = 1 if t.pnl > 0 else -1
            elif (t.pnl > 0 and streak > 0) or (t.pnl < 0 and streak < 0):
                streak += 1 if streak > 0 else -1
            else:
                break
        
        # Average hold time
        hold_times = [(t.exit_time - t.entry_time) for t in trades]
        avg_hold = sum(hold_times, timedelta(0)) / len(hold_times) if hold_times else timedelta(0)
        
        return PerformanceMetrics(
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=len(wins) / len(trades) * 100 if trades else 0,
            total_pnl=total_pnl,
            average_win=win_pnl / len(wins) if wins else 0,
            average_loss=loss_pnl / len(losses) if losses else 0,
            largest_win=max(t.pnl for t in wins) if wins else 0,
            largest_loss=min(t.pnl for t in losses) if losses else 0,
            profit_factor=win_pnl / loss_pnl if loss_pnl > 0 else float('inf'),
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            max_drawdown_percent=max_dd_pct,
            average_hold_time=avg_hold,
            best_symbol=best_symbol,
            worst_symbol=worst_symbol,
            best_strategy=best_strategy,
            current_streak=streak
        )
    
    def get_equity_curve(self, days: int = 30) -> List[Dict]:
        """Get equity curve data."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, equity, drawdown, daily_pnl
            FROM equity_curve
            WHERE timestamp > ?
            ORDER BY timestamp ASC
        """, ((datetime.now() - timedelta(days=days)).isoformat(),))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "timestamp": row[0],
                "equity": row[1],
                "drawdown": row[2],
                "daily_pnl": row[3]
            }
            for row in rows
        ]
    
    def analyze_patterns(self) -> List[Dict]:
        """Analyze trading patterns and identify what works."""
        trades = self.get_trades(days=90, limit=500)
        
        if not trades:
            return []
        
        patterns = []
        
        # 1. Time of day analysis
        hour_stats: Dict[int, List[float]] = {}
        for t in trades:
            hour = t.entry_time.hour
            if hour not in hour_stats:
                hour_stats[hour] = []
            hour_stats[hour].append(t.pnl)
        
        best_hour = max(hour_stats.items(), key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0)
        patterns.append({
            "name": "Best Trading Hour",
            "description": f"{best_hour[0]}:00 UTC",
            "win_rate": len([p for p in best_hour[1] if p > 0]) / len(best_hour[1]) * 100 if best_hour[1] else 0,
            "avg_pnl": sum(best_hour[1]) / len(best_hour[1]) if best_hour[1] else 0,
            "occurrences": len(best_hour[1])
        })
        
        # 2. Day of week analysis
        dow_stats: Dict[int, List[float]] = {}
        for t in trades:
            dow = t.entry_time.weekday()
            if dow not in dow_stats:
                dow_stats[dow] = []
            dow_stats[dow].append(t.pnl)
        
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        best_dow = max(dow_stats.items(), key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0)
        patterns.append({
            "name": "Best Day of Week",
            "description": days[best_dow[0]],
            "win_rate": len([p for p in best_dow[1] if p > 0]) / len(best_dow[1]) * 100 if best_dow[1] else 0,
            "avg_pnl": sum(best_dow[1]) / len(best_dow[1]) if best_dow[1] else 0,
            "occurrences": len(best_dow[1])
        })
        
        # 3. Confidence correlation
        high_conf = [t for t in trades if t.confidence >= 80]
        low_conf = [t for t in trades if t.confidence < 80 and t.confidence > 0]
        
        if high_conf:
            patterns.append({
                "name": "High Confidence (>80%)",
                "description": "Trades with 80%+ confidence score",
                "win_rate": len([t for t in high_conf if t.pnl > 0]) / len(high_conf) * 100,
                "avg_pnl": sum(t.pnl for t in high_conf) / len(high_conf),
                "occurrences": len(high_conf)
            })
        
        # 4. Hold time analysis
        quick_trades = [t for t in trades if (t.exit_time - t.entry_time).total_seconds() < 3600]
        long_trades = [t for t in trades if (t.exit_time - t.entry_time).total_seconds() >= 3600]
        
        if quick_trades:
            patterns.append({
                "name": "Quick Trades (<1hr)",
                "description": "Trades held less than 1 hour",
                "win_rate": len([t for t in quick_trades if t.pnl > 0]) / len(quick_trades) * 100,
                "avg_pnl": sum(t.pnl for t in quick_trades) / len(quick_trades),
                "occurrences": len(quick_trades)
            })
        
        return patterns
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict:
        """Get summary for a specific day."""
        if date is None:
            date = datetime.now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trades 
            WHERE exit_time >= ? AND exit_time < ?
            ORDER BY exit_time ASC
        """, (start.isoformat(), end.isoformat()))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {
                "date": start.strftime("%Y-%m-%d"),
                "trades": 0,
                "pnl": 0,
                "wins": 0,
                "losses": 0,
                "best_trade": None,
                "worst_trade": None
            }
        
        trades = []
        for row in rows:
            trades.append({
                "symbol": row[1],
                "side": row[2],
                "pnl": row[9],
                "strategy": row[11]
            })
        
        pnls = [t["pnl"] for t in trades]
        
        return {
            "date": start.strftime("%Y-%m-%d"),
            "trades": len(trades),
            "pnl": sum(pnls),
            "wins": len([p for p in pnls if p > 0]),
            "losses": len([p for p in pnls if p < 0]),
            "best_trade": max(trades, key=lambda x: x["pnl"]) if trades else None,
            "worst_trade": min(trades, key=lambda x: x["pnl"]) if trades else None
        }
    
    def format_performance_report(self, days: int = 30) -> str:
        """Generate formatted performance report for Aria."""
        metrics = self.get_performance(days=days)
        patterns = self.analyze_patterns()
        
        if metrics.total_trades == 0:
            return "📊 **No trading data yet**\n\nStart trading to see analytics!"
        
        streak_emoji = "🔥" if metrics.current_streak > 0 else "❄️"
        
        report = f"""📊 **TRADING PERFORMANCE ({days} Days)**

**Overall:**
• Total Trades: **{metrics.total_trades}**
• Win Rate: **{metrics.win_rate:.1f}%** ({metrics.winning_trades}W / {metrics.losing_trades}L)
• Total P&L: **${metrics.total_pnl:+,.2f}**
• {streak_emoji} Current Streak: **{abs(metrics.current_streak)} {'wins' if metrics.current_streak > 0 else 'losses'}**

**Risk Metrics:**
• Profit Factor: **{metrics.profit_factor:.2f}**
• Sharpe Ratio: **{metrics.sharpe_ratio:.2f}**
• Max Drawdown: **${metrics.max_drawdown:,.2f}** ({metrics.max_drawdown_percent:.1f}%)

**Trade Stats:**
• Avg Win: **${metrics.average_win:,.2f}**
• Avg Loss: **${metrics.average_loss:,.2f}**
• Largest Win: **${metrics.largest_win:,.2f}**
• Largest Loss: **${metrics.largest_loss:,.2f}**
• Avg Hold Time: **{str(metrics.average_hold_time).split('.')[0]}**

**Best Performers:**
• Best Symbol: **{metrics.best_symbol}**
• Best Strategy: **{metrics.best_strategy}**"""

        if patterns:
            report += "\n\n**Patterns Detected:**"
            for p in patterns[:3]:
                report += f"\n• {p['name']}: {p['win_rate']:.0f}% win rate"
        
        return report


# Singleton
_analytics: Optional[TradingAnalytics] = None


def get_analytics() -> TradingAnalytics:
    """Get or create global analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = TradingAnalytics()
    return _analytics









