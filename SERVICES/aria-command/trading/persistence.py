#!/usr/bin/env python3
"""
💾 TRADE PERSISTENCE LAYER
===========================

Persistent storage for all trading state:
- Active trades with entry data
- Trade history with full details
- Auto-trader state (config, enabled status)
- Daily stats and performance metrics
- Signal history for analysis

Ensures no data loss on service restart.
"""

import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
from contextlib import contextmanager
import shutil

logger = logging.getLogger("aria.trading.persistence")

# Database path
DATA_DIR = Path(os.getenv("ARIA_DATA_DIR", "/opt/fpai/aria-command/data"))
DB_PATH = DATA_DIR / "trading_state.db"
BACKUP_DIR = DATA_DIR / "backups"


@dataclass
class TradeRecord:
    """A trade record with full details."""
    id: str
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    entry_time: datetime
    size: float
    size_usd: float
    leverage: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.0
    signal_source: str = "signal-shark"
    
    # Exit data (filled when closed)
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    
    # Order tracking
    entry_order_id: Optional[str] = None
    stop_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None
    
    # Status
    status: str = "open"  # open, closed, cancelled
    
    # Metadata
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutoTraderState:
    """Persisted state of the auto-trader."""
    enabled: bool = False
    running: bool = False
    
    # Configuration
    max_position_usd: float = 500.0
    min_confidence: float = 80.0
    max_daily_loss: float = 150.0
    leverage: float = 3.0
    symbols: List[str] = field(default_factory=lambda: ["SOL", "BTC", "ETH"])
    
    # Performance tracking
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    
    # State
    daily_reset_date: Optional[str] = None
    peak_equity: float = 0.0
    
    # Timestamps
    last_updated: Optional[str] = None
    started_at: Optional[str] = None


@dataclass
class DailyStats:
    """Daily trading statistics."""
    date: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    pnl: float = 0.0
    peak_equity: float = 0.0
    drawdown: float = 0.0
    best_trade_pnl: float = 0.0
    worst_trade_pnl: float = 0.0


@dataclass
class SignalRecord:
    """Record of a received signal for analysis."""
    id: str
    timestamp: datetime
    symbol: str
    action: str  # LONG, SHORT, WAIT
    confidence: float
    risk_reward: float
    price: float
    target: Optional[float]
    stop: Optional[float]
    
    # Was it acted upon?
    traded: bool = False
    trade_id: Optional[str] = None
    
    # Outcome (filled later if traded)
    outcome: Optional[str] = None  # win, loss, breakeven


class TradePersistence:
    """
    Persistent storage for all trading state.
    
    Features:
    - SQLite-based storage
    - Transaction-safe writes
    - Automatic backup before writes
    - Auto-restore on startup
    """
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """Initialize database and tables."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Active and historical trades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    size REAL NOT NULL,
                    size_usd REAL NOT NULL,
                    leverage REAL DEFAULT 1.0,
                    stop_loss REAL,
                    take_profit REAL,
                    confidence REAL DEFAULT 0,
                    signal_source TEXT DEFAULT 'signal-shark',
                    exit_price REAL,
                    exit_time TIMESTAMP,
                    exit_reason TEXT,
                    pnl REAL,
                    pnl_percent REAL,
                    entry_order_id TEXT,
                    stop_order_id TEXT,
                    tp_order_id TEXT,
                    status TEXT DEFAULT 'open',
                    notes TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Auto-trader state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auto_trader_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled BOOLEAN DEFAULT FALSE,
                    running BOOLEAN DEFAULT FALSE,
                    max_position_usd REAL DEFAULT 500.0,
                    min_confidence REAL DEFAULT 80.0,
                    max_daily_loss REAL DEFAULT 150.0,
                    leverage REAL DEFAULT 3.0,
                    symbols TEXT DEFAULT '["SOL","BTC","ETH"]',
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0.0,
                    daily_pnl REAL DEFAULT 0.0,
                    consecutive_losses INTEGER DEFAULT 0,
                    daily_reset_date TEXT,
                    peak_equity REAL DEFAULT 0.0,
                    last_updated TIMESTAMP,
                    started_at TIMESTAMP
                )
            """)
            
            # Daily statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    trades INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    pnl REAL DEFAULT 0.0,
                    peak_equity REAL DEFAULT 0.0,
                    drawdown REAL DEFAULT 0.0,
                    best_trade_pnl REAL DEFAULT 0.0,
                    worst_trade_pnl REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Signal history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    risk_reward REAL DEFAULT 0.0,
                    price REAL NOT NULL,
                    target REAL,
                    stop REAL,
                    traded BOOLEAN DEFAULT FALSE,
                    trade_id TEXT,
                    outcome TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Ensure auto_trader_state has one row
            cursor.execute("INSERT OR IGNORE INTO auto_trader_state (id) VALUES (1)")
            
            conn.commit()
            
        logger.info(f"📦 Trade persistence initialized at {DB_PATH}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(str(DB_PATH), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _backup_db(self):
        """Create backup before important operations."""
        if not DB_PATH.exists():
            return
        
        backup_name = f"trading_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = BACKUP_DIR / backup_name
        
        try:
            shutil.copy2(DB_PATH, backup_path)
            
            # Keep only last 10 backups
            backups = sorted(BACKUP_DIR.glob("trading_state_*.db"))
            for old_backup in backups[:-10]:
                old_backup.unlink()
                
            logger.debug(f"Created backup: {backup_name}")
        except Exception as e:
            logger.warning(f"Backup failed: {e}")
    
    # ==================== TRADE OPERATIONS ====================
    
    def save_trade(self, trade: TradeRecord):
        """Save or update a trade record."""
        self._backup_db()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO trades (
                    id, symbol, side, entry_price, entry_time, size, size_usd,
                    leverage, stop_loss, take_profit, confidence, signal_source,
                    exit_price, exit_time, exit_reason, pnl, pnl_percent,
                    entry_order_id, stop_order_id, tp_order_id, status, notes,
                    metadata, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.id, trade.symbol, trade.side, trade.entry_price,
                trade.entry_time.isoformat() if trade.entry_time else None,
                trade.size, trade.size_usd, trade.leverage, trade.stop_loss,
                trade.take_profit, trade.confidence, trade.signal_source,
                trade.exit_price,
                trade.exit_time.isoformat() if trade.exit_time else None,
                trade.exit_reason, trade.pnl, trade.pnl_percent,
                trade.entry_order_id, trade.stop_order_id, trade.tp_order_id,
                trade.status, trade.notes, json.dumps(trade.metadata),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            
        logger.info(f"💾 Saved trade: {trade.id} ({trade.symbol} {trade.side})")
    
    def get_trade(self, trade_id: str) -> Optional[TradeRecord]:
        """Get a specific trade by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_trade(row)
        return None
    
    def get_active_trades(self) -> List[TradeRecord]:
        """Get all currently open trades."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY entry_time DESC")
            rows = cursor.fetchall()
            return [self._row_to_trade(row) for row in rows]
    
    def get_trades(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        days: int = 30,
        limit: int = 100
    ) -> List[TradeRecord]:
        """Get trades with optional filters."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if days:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                query += " AND entry_time > ?"
                params.append(cutoff)
            
            query += " ORDER BY entry_time DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_trade(row) for row in rows]
    
    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        pnl_percent: float
    ):
        """Mark a trade as closed with exit data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades SET
                    exit_price = ?,
                    exit_time = ?,
                    exit_reason = ?,
                    pnl = ?,
                    pnl_percent = ?,
                    status = 'closed',
                    updated_at = ?
                WHERE id = ?
            """, (
                exit_price,
                datetime.now().isoformat(),
                exit_reason,
                pnl,
                pnl_percent,
                datetime.now().isoformat(),
                trade_id
            ))
            conn.commit()
            
        logger.info(f"📊 Closed trade: {trade_id} - ${pnl:+,.2f} ({pnl_percent:+.1f}%)")
    
    def _row_to_trade(self, row: sqlite3.Row) -> TradeRecord:
        """Convert database row to TradeRecord."""
        return TradeRecord(
            id=row["id"],
            symbol=row["symbol"],
            side=row["side"],
            entry_price=row["entry_price"],
            entry_time=datetime.fromisoformat(row["entry_time"]) if row["entry_time"] else None,
            size=row["size"],
            size_usd=row["size_usd"],
            leverage=row["leverage"] or 1.0,
            stop_loss=row["stop_loss"],
            take_profit=row["take_profit"],
            confidence=row["confidence"] or 0.0,
            signal_source=row["signal_source"] or "signal-shark",
            exit_price=row["exit_price"],
            exit_time=datetime.fromisoformat(row["exit_time"]) if row["exit_time"] else None,
            exit_reason=row["exit_reason"],
            pnl=row["pnl"],
            pnl_percent=row["pnl_percent"],
            entry_order_id=row["entry_order_id"],
            stop_order_id=row["stop_order_id"],
            tp_order_id=row["tp_order_id"],
            status=row["status"],
            notes=row["notes"] or "",
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
    
    # ==================== AUTO-TRADER STATE ====================
    
    def save_auto_trader_state(self, state: AutoTraderState):
        """Save auto-trader state."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE auto_trader_state SET
                    enabled = ?,
                    running = ?,
                    max_position_usd = ?,
                    min_confidence = ?,
                    max_daily_loss = ?,
                    leverage = ?,
                    symbols = ?,
                    total_trades = ?,
                    winning_trades = ?,
                    total_pnl = ?,
                    daily_pnl = ?,
                    consecutive_losses = ?,
                    daily_reset_date = ?,
                    peak_equity = ?,
                    last_updated = ?,
                    started_at = ?
                WHERE id = 1
            """, (
                state.enabled,
                state.running,
                state.max_position_usd,
                state.min_confidence,
                state.max_daily_loss,
                state.leverage,
                json.dumps(state.symbols),
                state.total_trades,
                state.winning_trades,
                state.total_pnl,
                state.daily_pnl,
                state.consecutive_losses,
                state.daily_reset_date,
                state.peak_equity,
                datetime.now().isoformat(),
                state.started_at
            ))
            conn.commit()
            
        logger.debug("💾 Saved auto-trader state")
    
    def restore_auto_trader_state(self) -> AutoTraderState:
        """Restore auto-trader state from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM auto_trader_state WHERE id = 1")
            row = cursor.fetchone()
            
            if not row:
                return AutoTraderState()
            
            return AutoTraderState(
                enabled=bool(row["enabled"]),
                running=False,  # Always start as not running
                max_position_usd=row["max_position_usd"] or 500.0,
                min_confidence=row["min_confidence"] or 80.0,
                max_daily_loss=row["max_daily_loss"] or 150.0,
                leverage=row["leverage"] or 3.0,
                symbols=json.loads(row["symbols"]) if row["symbols"] else ["SOL", "BTC", "ETH"],
                total_trades=row["total_trades"] or 0,
                winning_trades=row["winning_trades"] or 0,
                total_pnl=row["total_pnl"] or 0.0,
                daily_pnl=row["daily_pnl"] or 0.0,
                consecutive_losses=row["consecutive_losses"] or 0,
                daily_reset_date=row["daily_reset_date"],
                peak_equity=row["peak_equity"] or 0.0,
                last_updated=row["last_updated"],
                started_at=row["started_at"]
            )
    
    # ==================== DAILY STATS ====================
    
    def update_daily_stats(
        self,
        pnl: float,
        is_win: bool,
        equity: float
    ):
        """Update today's statistics."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get existing stats
            cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
            row = cursor.fetchone()
            
            if row:
                trades = row["trades"] + 1
                wins = row["wins"] + (1 if is_win else 0)
                losses = row["losses"] + (0 if is_win else 1)
                total_pnl = row["pnl"] + pnl
                peak = max(row["peak_equity"], equity)
                drawdown = peak - equity if equity < peak else 0
                best = max(row["best_trade_pnl"], pnl)
                worst = min(row["worst_trade_pnl"], pnl)
                
                cursor.execute("""
                    UPDATE daily_stats SET
                        trades = ?, wins = ?, losses = ?, pnl = ?,
                        peak_equity = ?, drawdown = ?,
                        best_trade_pnl = ?, worst_trade_pnl = ?
                    WHERE date = ?
                """, (trades, wins, losses, total_pnl, peak, drawdown, best, worst, today))
            else:
                cursor.execute("""
                    INSERT INTO daily_stats
                        (date, trades, wins, losses, pnl, peak_equity, drawdown,
                         best_trade_pnl, worst_trade_pnl)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    today, 1, 1 if is_win else 0, 0 if is_win else 1,
                    pnl, equity, 0, pnl if pnl > 0 else 0, pnl if pnl < 0 else 0
                ))
            
            conn.commit()
    
    def get_daily_stats(self, date: Optional[str] = None) -> Optional[DailyStats]:
        """Get stats for a specific date."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (date,))
            row = cursor.fetchone()
            
            if row:
                return DailyStats(
                    date=row["date"],
                    trades=row["trades"],
                    wins=row["wins"],
                    losses=row["losses"],
                    pnl=row["pnl"],
                    peak_equity=row["peak_equity"],
                    drawdown=row["drawdown"],
                    best_trade_pnl=row["best_trade_pnl"],
                    worst_trade_pnl=row["worst_trade_pnl"]
                )
        return None
    
    def get_stats_range(self, days: int = 30) -> List[DailyStats]:
        """Get daily stats for a range of days."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM daily_stats WHERE date > ? ORDER BY date DESC",
                (cutoff,)
            )
            rows = cursor.fetchall()
            
            return [
                DailyStats(
                    date=row["date"],
                    trades=row["trades"],
                    wins=row["wins"],
                    losses=row["losses"],
                    pnl=row["pnl"],
                    peak_equity=row["peak_equity"],
                    drawdown=row["drawdown"],
                    best_trade_pnl=row["best_trade_pnl"],
                    worst_trade_pnl=row["worst_trade_pnl"]
                )
                for row in rows
            ]
    
    # ==================== SIGNAL HISTORY ====================
    
    def save_signal(self, signal: SignalRecord):
        """Save a signal record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO signals
                    (id, timestamp, symbol, action, confidence, risk_reward,
                     price, target, stop, traded, trade_id, outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.id,
                signal.timestamp.isoformat(),
                signal.symbol,
                signal.action,
                signal.confidence,
                signal.risk_reward,
                signal.price,
                signal.target,
                signal.stop,
                signal.traded,
                signal.trade_id,
                signal.outcome
            ))
            conn.commit()
    
    def get_signals(
        self,
        symbol: Optional[str] = None,
        traded: Optional[bool] = None,
        days: int = 7
    ) -> List[SignalRecord]:
        """Get signal history."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM signals WHERE timestamp > ?"
            params = [cutoff]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if traded is not None:
                query += " AND traded = ?"
                params.append(traded)
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                SignalRecord(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    symbol=row["symbol"],
                    action=row["action"],
                    confidence=row["confidence"],
                    risk_reward=row["risk_reward"] or 0.0,
                    price=row["price"],
                    target=row["target"],
                    stop=row["stop"],
                    traded=bool(row["traded"]),
                    trade_id=row["trade_id"],
                    outcome=row["outcome"]
                )
                for row in rows
            ]
    
    def update_signal_outcome(self, signal_id: str, outcome: str):
        """Update signal outcome after trade closes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE signals SET outcome = ? WHERE id = ?",
                (outcome, signal_id)
            )
            conn.commit()
    
    # ==================== PERFORMANCE STATS ====================
    
    def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        trades = self.get_trades(status="closed", days=days, limit=1000)
        
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "avg_hold_time_hours": 0.0
            }
        
        wins = [t for t in trades if t.pnl and t.pnl > 0]
        losses = [t for t in trades if t.pnl and t.pnl < 0]
        
        total_win_pnl = sum(t.pnl for t in wins) if wins else 0
        total_loss_pnl = abs(sum(t.pnl for t in losses)) if losses else 0
        
        # Calculate average hold time
        hold_times = []
        for t in trades:
            if t.entry_time and t.exit_time:
                hold_times.append((t.exit_time - t.entry_time).total_seconds() / 3600)
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": len(wins) / len(trades) * 100 if trades else 0,
            "total_pnl": sum(t.pnl for t in trades if t.pnl) or 0,
            "avg_win": total_win_pnl / len(wins) if wins else 0,
            "avg_loss": total_loss_pnl / len(losses) if losses else 0,
            "profit_factor": total_win_pnl / total_loss_pnl if total_loss_pnl > 0 else float('inf'),
            "largest_win": max(t.pnl for t in wins) if wins else 0,
            "largest_loss": min(t.pnl for t in losses) if losses else 0,
            "avg_hold_time_hours": sum(hold_times) / len(hold_times) if hold_times else 0
        }


# Singleton
_persistence: Optional[TradePersistence] = None


def get_persistence() -> TradePersistence:
    """Get or create global persistence instance."""
    global _persistence
    if _persistence is None:
        _persistence = TradePersistence()
    return _persistence









