#!/usr/bin/env python3
"""
Trade Learning Engine
=====================
Learns from every trade to improve future performance.

Intelligence Layers:
1. Pattern Recognition - What setups work?
2. Asset Edge - Which assets have edge?
3. Time Edge - Best trading hours/days?
4. Regime Awareness - Trend vs Range vs Volatile?
5. Kelly Sizing - Optimal position sizes
6. Drawdown Protection - Scale down during losses

The trader becomes SMARTER with every trade.
"""
import sqlite3
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import math

logger = logging.getLogger("trade_learning")


@dataclass
class TradeInsight:
    """Insight about a trading pattern."""
    pattern: str
    win_rate: float
    avg_profit: float
    avg_loss: float
    edge: float  # Expected value per trade
    kelly_fraction: float  # Optimal bet size
    sample_size: int
    confidence: str  # low, medium, high
    recommendation: str  # trade, reduce, avoid


@dataclass
class AssetProfile:
    """Learned profile for an asset."""
    symbol: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_winner: float
    avg_loser: float
    edge: float
    kelly_fraction: float
    best_hours: List[int]
    worst_hours: List[int]
    recommendation: str


class TradeLearningEngine:
    """
    Learns from trades and provides intelligent recommendations.
    """
    
    def __init__(self, db_path: str = "/opt/fpai/aria/trade_learning.db"):
        self.db_path = db_path
        self.account = "0xefbfead1189f32bc1000d3740445d0227286b77b"
        self._ensure_tables()
        
        # Learning parameters
        self.min_trades_for_confidence = 10
        self.min_trades_for_high_confidence = 30
        self.kelly_fraction_cap = 0.25  # Max 25% of account per trade
        self.drawdown_threshold = 0.10  # 10% drawdown triggers protection
    
    def _ensure_tables(self):
        """Create learning tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trade history with analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                size REAL,
                pnl REAL,
                pnl_percent REAL,
                hold_time_hours REAL,
                hour_of_day INTEGER,
                day_of_week INTEGER,
                market_regime TEXT,
                signal_type TEXT,
                was_winner INTEGER
            )
        """)
        
        # Learned patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id TEXT PRIMARY KEY,
                pattern_key TEXT UNIQUE,
                pattern_type TEXT,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                avg_winner REAL DEFAULT 0,
                avg_loser REAL DEFAULT 0,
                edge REAL DEFAULT 0,
                kelly_fraction REAL DEFAULT 0,
                last_updated TEXT,
                recommendation TEXT DEFAULT 'trade'
            )
        """)
        
        # Performance tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                account_value REAL,
                daily_pnl REAL,
                trades_today INTEGER,
                win_rate_today REAL,
                cumulative_pnl REAL,
                max_drawdown REAL
            )
        """)
        
        # Current state
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    # === Data Fetching ===
    
    def fetch_trade_history(self) -> List[Dict]:
        """Fetch all trades from Hyperliquid."""
        try:
            r = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "userFills", "user": self.account}, timeout=15)
            return r.json()
        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            return []
    
    def sync_trades(self):
        """Sync trades from exchange to local database."""
        fills = self.fetch_trade_history()
        if not fills:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Group fills into trades (entries and exits)
        for fill in fills:
            pnl = float(fill.get("closedPnl", 0))
            if pnl == 0:
                continue  # Skip entries, only track closed trades
            
            ts = datetime.fromtimestamp(fill["time"] / 1000)
            trade_id = f"{fill['oid']}_{fill['time']}"
            
            cursor.execute("SELECT id FROM trade_history WHERE id = ?", (trade_id,))
            if cursor.fetchone():
                continue  # Already synced
            
            cursor.execute("""
                INSERT INTO trade_history 
                (id, timestamp, symbol, side, exit_price, size, pnl, hour_of_day, day_of_week, was_winner)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                ts.isoformat(),
                fill["coin"],
                fill["side"],
                float(fill["px"]),
                float(fill["sz"]),
                pnl,
                ts.hour,
                ts.weekday(),
                1 if pnl > 0 else 0
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Synced {len(fills)} fills")
    
    # === Pattern Analysis ===
    
    def analyze_patterns(self) -> Dict[str, TradeInsight]:
        """Analyze all trading patterns."""
        self.sync_trades()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        patterns = {}
        
        # By asset
        cursor.execute("""
            SELECT symbol, 
                   COUNT(*) as total,
                   SUM(was_winner) as wins,
                   SUM(pnl) as total_pnl,
                   AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                   AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
            FROM trade_history
            GROUP BY symbol
        """)
        
        for row in cursor.fetchall():
            symbol, total, wins, total_pnl, avg_win, avg_loss = row
            if total == 0:
                continue
            
            losses = total - wins
            win_rate = wins / total if total > 0 else 0
            avg_win = avg_win or 0
            avg_loss = avg_loss or 0
            
            # Calculate edge (expected value)
            edge = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
            
            # Kelly criterion
            if avg_loss != 0 and win_rate > 0:
                b = avg_win / abs(avg_loss)  # Win/loss ratio
                kelly = (win_rate * b - (1 - win_rate)) / b
                kelly = max(0, min(kelly, self.kelly_fraction_cap))
            else:
                kelly = 0
            
            # Confidence
            if total >= self.min_trades_for_high_confidence:
                confidence = "high"
            elif total >= self.min_trades_for_confidence:
                confidence = "medium"
            else:
                confidence = "low"
            
            # Recommendation
            if edge > 0 and kelly > 0.05:
                recommendation = "trade"
            elif edge > 0:
                recommendation = "reduce"
            else:
                recommendation = "avoid"
            
            patterns[f"asset:{symbol}"] = TradeInsight(
                pattern=f"asset:{symbol}",
                win_rate=win_rate,
                avg_profit=avg_win,
                avg_loss=avg_loss,
                edge=edge,
                kelly_fraction=kelly,
                sample_size=total,
                confidence=confidence,
                recommendation=recommendation
            )
            
            # Save to database
            self._save_pattern(f"asset:{symbol}", "asset", wins, losses, total_pnl, avg_win, avg_loss, edge, kelly, recommendation)
        
        # By hour
        cursor.execute("""
            SELECT hour_of_day,
                   COUNT(*) as total,
                   SUM(was_winner) as wins,
                   SUM(pnl) as total_pnl
            FROM trade_history
            GROUP BY hour_of_day
        """)
        
        for row in cursor.fetchall():
            hour, total, wins, total_pnl = row
            if total < 3:
                continue
            
            win_rate = wins / total if total > 0 else 0
            patterns[f"hour:{hour}"] = TradeInsight(
                pattern=f"hour:{hour}",
                win_rate=win_rate,
                avg_profit=0,
                avg_loss=0,
                edge=total_pnl / total if total > 0 else 0,
                kelly_fraction=0,
                sample_size=total,
                confidence="low" if total < 10 else "medium",
                recommendation="trade" if win_rate > 0.5 else "caution"
            )
        
        conn.close()
        return patterns
    
    def _save_pattern(self, key, ptype, wins, losses, pnl, avg_win, avg_loss, edge, kelly, rec):
        """Save pattern to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO learned_patterns 
            (id, pattern_key, pattern_type, wins, losses, total_pnl, avg_winner, avg_loser, edge, kelly_fraction, last_updated, recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (key, key, ptype, wins, losses, pnl, avg_win, avg_loss, edge, kelly, datetime.now().isoformat(), rec))
        
        conn.commit()
        conn.close()
    
    # === Intelligence Queries ===
    
    def get_asset_profile(self, symbol: str) -> Optional[AssetProfile]:
        """Get learned profile for an asset."""
        patterns = self.analyze_patterns()
        key = f"asset:{symbol}"
        
        if key not in patterns:
            return None
        
        insight = patterns[key]
        
        # Get best/worst hours
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT hour_of_day, SUM(pnl) as hour_pnl
            FROM trade_history WHERE symbol = ?
            GROUP BY hour_of_day
            ORDER BY hour_pnl DESC
        """, (symbol,))
        
        hours = cursor.fetchall()
        best_hours = [h[0] for h in hours[:3] if h[1] > 0]
        worst_hours = [h[0] for h in hours[-3:] if h[1] < 0]
        
        conn.close()
        
        return AssetProfile(
            symbol=symbol,
            total_trades=insight.sample_size,
            wins=int(insight.win_rate * insight.sample_size),
            losses=insight.sample_size - int(insight.win_rate * insight.sample_size),
            win_rate=insight.win_rate,
            total_pnl=insight.avg_profit * int(insight.win_rate * insight.sample_size) + insight.avg_loss * (insight.sample_size - int(insight.win_rate * insight.sample_size)),
            avg_winner=insight.avg_profit,
            avg_loser=insight.avg_loss,
            edge=insight.edge,
            kelly_fraction=insight.kelly_fraction,
            best_hours=best_hours,
            worst_hours=worst_hours,
            recommendation=insight.recommendation
        )
    
    def get_position_size_multiplier(self, symbol: str) -> float:
        """
        Get position size multiplier based on learned edge.
        
        Returns:
            0.0 = Don't trade
            0.5 = Half size
            1.0 = Normal size
            2.0 = Double size (high edge)
        """
        profile = self.get_asset_profile(symbol)
        
        if not profile:
            return 1.0  # No data, trade normal
        
        if profile.recommendation == "avoid":
            return 0.0
        
        if profile.recommendation == "reduce":
            return 0.5
        
        # Scale by Kelly fraction (capped at 2x)
        if profile.kelly_fraction > 0.15:
            return min(2.0, 1.0 + profile.kelly_fraction)
        
        return 1.0
    
    def should_trade(self, symbol: str, side: str) -> Tuple[bool, str, float]:
        """
        Should we take this trade?
        
        Returns:
            (should_trade, reason, size_multiplier)
        """
        profile = self.get_asset_profile(symbol)
        
        if not profile:
            return True, "No history - trading with caution", 0.5
        
        # Check recommendation
        if profile.recommendation == "avoid":
            return False, f"{symbol} has negative edge ({profile.edge:.2f}), avoiding", 0.0
        
        # Check current hour
        hour = datetime.now().hour
        if hour in profile.worst_hours:
            return True, f"Worst hour for {symbol}, reducing size", 0.5
        
        # Check drawdown protection
        if self._is_in_drawdown():
            return True, "In drawdown, reducing size", 0.5
        
        # Good to trade
        multiplier = self.get_position_size_multiplier(symbol)
        
        if multiplier >= 1.5:
            return True, f"{symbol} has strong edge ({profile.win_rate:.0%} WR), increasing size", multiplier
        
        return True, f"{symbol} edge: {profile.edge:.2f}", multiplier
    
    def _is_in_drawdown(self) -> bool:
        """Check if we're in drawdown mode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check recent performance
        cursor.execute("""
            SELECT SUM(pnl) FROM trade_history
            WHERE timestamp > datetime('now', '-7 days')
        """)
        
        row = cursor.fetchone()
        recent_pnl = row[0] if row and row[0] else 0
        
        conn.close()
        
        return recent_pnl < -50  # More than $50 loss in past week
    
    # === Reporting ===
    
    def get_intelligence_report(self) -> str:
        """Get a human-readable intelligence report."""
        patterns = self.analyze_patterns()
        
        lines = ["📊 TRADE INTELLIGENCE REPORT", "=" * 40, ""]
        
        # Asset insights
        lines.append("🎯 ASSET INSIGHTS:")
        for key, insight in patterns.items():
            if not key.startswith("asset:"):
                continue
            
            symbol = key.replace("asset:", "")
            emoji = "🟢" if insight.recommendation == "trade" else "🟡" if insight.recommendation == "reduce" else "🔴"
            
            lines.append(f"\n{emoji} {symbol}:")
            lines.append(f"   Win Rate: {insight.win_rate:.0%} ({insight.sample_size} trades)")
            lines.append(f"   Edge: ${insight.edge:.2f}/trade")
            lines.append(f"   Kelly: {insight.kelly_fraction:.1%} of account")
            lines.append(f"   → {insight.recommendation.upper()}")
        
        # Get best/worst patterns
        sorted_patterns = sorted(patterns.values(), key=lambda x: x.edge, reverse=True)
        
        if sorted_patterns:
            lines.append("\n" + "=" * 40)
            lines.append("💡 RECOMMENDATIONS:")
            
            best = sorted_patterns[0]
            lines.append(f"   Best: {best.pattern} (edge ${best.edge:.2f})")
            
            worst = sorted_patterns[-1]
            if worst.edge < 0:
                lines.append(f"   Avoid: {worst.pattern} (edge ${worst.edge:.2f})")
        
        return "\n".join(lines)
    
    def get_sizing_recommendations(self) -> Dict[str, float]:
        """Get sizing recommendations for all assets."""
        patterns = self.analyze_patterns()
        
        recommendations = {}
        for key, insight in patterns.items():
            if key.startswith("asset:"):
                symbol = key.replace("asset:", "")
                recommendations[symbol] = self.get_position_size_multiplier(symbol)
        
        return recommendations


# Singleton
_engine: Optional[TradeLearningEngine] = None

def get_learning_engine() -> TradeLearningEngine:
    global _engine
    if _engine is None:
        _engine = TradeLearningEngine()
    return _engine


# Convenience functions
def should_trade(symbol: str, side: str = "long") -> Tuple[bool, str, float]:
    return get_learning_engine().should_trade(symbol, side)

def get_size_multiplier(symbol: str) -> float:
    return get_learning_engine().get_position_size_multiplier(symbol)

def get_intelligence_report() -> str:
    return get_learning_engine().get_intelligence_report()







