#!/usr/bin/env python3
"""
🔍 PATTERN RECOGNITION ENGINE
==============================

Discovers and tracks winning patterns from trade history:
- Time-based patterns (best hours, days)
- Symbol-based patterns
- Signal combinations
- Market condition patterns

Uses pattern matching to boost confidence on
similar setups that have historically performed well.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger("aria.trading.patterns")

DATA_DIR = Path(os.getenv("ARIA_DATA_DIR", "/opt/fpai/aria-command/data"))


@dataclass
class TradePattern:
    """A discovered trading pattern."""
    name: str
    conditions: Dict[str, Any]    # What defines this pattern
    win_rate: float              # Historical win rate
    avg_return: float            # Average return
    profit_factor: float         # Gross profit / gross loss
    occurrences: int             # How many times seen
    wins: int
    losses: int
    total_pnl: float
    last_seen: datetime = field(default_factory=datetime.now)
    
    @property
    def is_significant(self) -> bool:
        """Check if pattern has enough data to be significant."""
        return self.occurrences >= 5 and self.win_rate > 0.5
    
    def matches(self, conditions: Dict[str, Any]) -> float:
        """
        Check how well conditions match this pattern.
        Returns match score 0-1.
        """
        if not self.conditions:
            return 0.0
        
        matches = 0
        total = len(self.conditions)
        
        for key, value in self.conditions.items():
            if key in conditions:
                if isinstance(value, tuple):
                    # Range match
                    if value[0] <= conditions[key] <= value[1]:
                        matches += 1
                elif isinstance(value, list):
                    # List membership
                    if conditions[key] in value:
                        matches += 1
                else:
                    # Exact match
                    if conditions[key] == value:
                        matches += 1
        
        return matches / total if total > 0 else 0.0


@dataclass
class MarketConditions:
    """Current market conditions for pattern matching."""
    symbol: str
    side: str  # long/short
    hour: int  # 0-23 UTC
    day_of_week: int  # 0-6, Monday=0
    confidence: float
    regime: str = "unknown"
    volume_ratio: float = 1.0  # Current vs average volume
    price_change_1h: float = 0.0
    price_change_24h: float = 0.0


class PatternLearner:
    """
    Discovers and tracks winning patterns from trade history.
    
    Features:
    - Automatic pattern discovery
    - Pattern scoring for new signals
    - Continuous pattern updates
    - Pattern persistence
    """
    
    def __init__(self):
        self._patterns: List[TradePattern] = []
        self._trade_buffer: List[Dict] = []  # Recent trades for analysis
        
        # Pre-defined pattern templates
        self._pattern_templates = [
            # Time-based patterns
            {
                "name": "Morning {symbol} {side}",
                "condition_keys": ["symbol", "side", "hour"],
                "hour_range": (6, 10)
            },
            {
                "name": "Afternoon {symbol} {side}",
                "condition_keys": ["symbol", "side", "hour"],
                "hour_range": (12, 16)
            },
            {
                "name": "Evening {symbol} {side}",
                "condition_keys": ["symbol", "side", "hour"],
                "hour_range": (18, 22)
            },
            # Weekday patterns
            {
                "name": "{day} {symbol}",
                "condition_keys": ["symbol", "day_of_week"]
            },
            # High confidence patterns
            {
                "name": "High Conf {symbol} {side}",
                "condition_keys": ["symbol", "side", "confidence"],
                "confidence_range": (85, 100)
            },
        ]
        
        # Load persisted patterns
        self._load_patterns()
    
    def _patterns_file(self) -> Path:
        """Get patterns file path."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / "trading_patterns.json"
    
    def _load_patterns(self):
        """Load patterns from file."""
        try:
            path = self._patterns_file()
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                
                self._patterns = [
                    TradePattern(
                        name=p["name"],
                        conditions=p["conditions"],
                        win_rate=p["win_rate"],
                        avg_return=p["avg_return"],
                        profit_factor=p.get("profit_factor", 1.0),
                        occurrences=p["occurrences"],
                        wins=p["wins"],
                        losses=p["losses"],
                        total_pnl=p.get("total_pnl", 0),
                        last_seen=datetime.fromisoformat(p["last_seen"])
                    )
                    for p in data.get("patterns", [])
                ]
                
                logger.info(f"📚 Loaded {len(self._patterns)} trading patterns")
        except Exception as e:
            logger.warning(f"Failed to load patterns: {e}")
    
    def _save_patterns(self):
        """Save patterns to file."""
        try:
            data = {
                "patterns": [
                    {
                        "name": p.name,
                        "conditions": p.conditions,
                        "win_rate": p.win_rate,
                        "avg_return": p.avg_return,
                        "profit_factor": p.profit_factor,
                        "occurrences": p.occurrences,
                        "wins": p.wins,
                        "losses": p.losses,
                        "total_pnl": p.total_pnl,
                        "last_seen": p.last_seen.isoformat()
                    }
                    for p in self._patterns
                ],
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self._patterns_file(), "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
    
    async def record_trade(
        self,
        symbol: str,
        side: str,
        entry_time: datetime,
        pnl: float,
        pnl_percent: float,
        confidence: float,
        regime: str = "unknown"
    ):
        """
        Record a completed trade for pattern analysis.
        """
        trade = {
            "symbol": symbol,
            "side": side,
            "hour": entry_time.hour,
            "day_of_week": entry_time.weekday(),
            "confidence": confidence,
            "regime": regime,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "is_win": pnl > 0,
            "timestamp": entry_time
        }
        
        self._trade_buffer.append(trade)
        
        # Keep buffer manageable
        if len(self._trade_buffer) > 1000:
            self._trade_buffer = self._trade_buffer[-500:]
        
        # Update patterns
        await self._update_patterns(trade)
        
        # Try to discover new patterns periodically
        if len(self._trade_buffer) % 10 == 0:
            await self._discover_patterns()
    
    async def _update_patterns(self, trade: Dict):
        """Update existing patterns with new trade data."""
        conditions = self._extract_conditions(trade)
        
        for pattern in self._patterns:
            match_score = pattern.matches(conditions)
            
            if match_score >= 0.8:  # Good match
                # Update pattern stats
                pattern.occurrences += 1
                pattern.last_seen = datetime.now()
                
                if trade["is_win"]:
                    pattern.wins += 1
                else:
                    pattern.losses += 1
                
                pattern.total_pnl += trade["pnl"]
                
                # Recalculate metrics
                total = pattern.wins + pattern.losses
                pattern.win_rate = pattern.wins / total if total > 0 else 0.5
                pattern.avg_return = pattern.total_pnl / pattern.occurrences
        
        self._save_patterns()
    
    async def _discover_patterns(self):
        """
        Discover new patterns from trade history.
        """
        if len(self._trade_buffer) < 10:
            return
        
        # Group trades by various dimensions
        by_hour_symbol = defaultdict(list)
        by_day_symbol = defaultdict(list)
        by_confidence_symbol = defaultdict(list)
        
        for trade in self._trade_buffer:
            key1 = (trade["symbol"], trade["side"], trade["hour"] // 4)  # 6-hour blocks
            by_hour_symbol[key1].append(trade)
            
            key2 = (trade["symbol"], trade["day_of_week"])
            by_day_symbol[key2].append(trade)
            
            conf_bucket = int(trade["confidence"] // 10) * 10
            key3 = (trade["symbol"], trade["side"], conf_bucket)
            by_confidence_symbol[key3].append(trade)
        
        # Analyze groups for significant patterns
        new_patterns = []
        
        for key, trades in by_hour_symbol.items():
            if len(trades) >= 5:
                pattern = self._analyze_group(
                    f"{key[1].upper()} {key[0]} Block {key[2]}",
                    trades,
                    {"symbol": key[0], "side": key[1], "hour": (key[2]*4, key[2]*4+3)}
                )
                if pattern and pattern.is_significant:
                    new_patterns.append(pattern)
        
        # Add new patterns that don't duplicate existing ones
        for new_pattern in new_patterns:
            is_duplicate = any(
                p.name == new_pattern.name or
                p.conditions == new_pattern.conditions
                for p in self._patterns
            )
            if not is_duplicate:
                self._patterns.append(new_pattern)
                logger.info(f"🔍 Discovered pattern: {new_pattern.name} (win rate: {new_pattern.win_rate:.1%})")
        
        self._save_patterns()
    
    def _extract_conditions(self, trade: Dict) -> Dict[str, Any]:
        """Extract condition dict from trade."""
        return {
            "symbol": trade["symbol"],
            "side": trade["side"],
            "hour": trade["hour"],
            "day_of_week": trade["day_of_week"],
            "confidence": trade["confidence"],
            "regime": trade.get("regime", "unknown")
        }
    
    def _analyze_group(
        self,
        name: str,
        trades: List[Dict],
        conditions: Dict
    ) -> Optional[TradePattern]:
        """Analyze a group of trades to create a pattern."""
        if not trades:
            return None
        
        wins = sum(1 for t in trades if t["is_win"])
        losses = len(trades) - wins
        total_pnl = sum(t["pnl"] for t in trades)
        
        win_pnl = sum(t["pnl"] for t in trades if t["is_win"])
        loss_pnl = abs(sum(t["pnl"] for t in trades if not t["is_win"]))
        
        return TradePattern(
            name=name,
            conditions=conditions,
            win_rate=wins / len(trades),
            avg_return=total_pnl / len(trades),
            profit_factor=win_pnl / loss_pnl if loss_pnl > 0 else float('inf'),
            occurrences=len(trades),
            wins=wins,
            losses=losses,
            total_pnl=total_pnl,
            last_seen=max(t["timestamp"] for t in trades)
        )
    
    def get_pattern_score(
        self,
        conditions: MarketConditions
    ) -> Tuple[float, List[TradePattern]]:
        """
        Score how well current setup matches known winning patterns.
        
        Returns:
            (score 0-100, list of matching patterns)
        """
        condition_dict = {
            "symbol": conditions.symbol,
            "side": conditions.side,
            "hour": conditions.hour,
            "day_of_week": conditions.day_of_week,
            "confidence": conditions.confidence,
            "regime": conditions.regime
        }
        
        matching_patterns = []
        total_score = 0.0
        
        for pattern in self._patterns:
            if not pattern.is_significant:
                continue
            
            match_score = pattern.matches(condition_dict)
            
            if match_score >= 0.5:  # Partial match
                # Weight by win rate and match quality
                pattern_score = match_score * pattern.win_rate * 100
                total_score += pattern_score
                matching_patterns.append(pattern)
        
        # Average score across matching patterns
        if matching_patterns:
            avg_score = total_score / len(matching_patterns)
        else:
            avg_score = 50.0  # Neutral if no patterns match
        
        return min(100, avg_score), matching_patterns
    
    def get_best_patterns(self, min_occurrences: int = 5, top_n: int = 10) -> List[Dict]:
        """Get best performing patterns."""
        significant = [
            p for p in self._patterns
            if p.occurrences >= min_occurrences
        ]
        
        # Sort by profit factor (most important metric)
        sorted_patterns = sorted(
            significant,
            key=lambda p: p.profit_factor if p.profit_factor != float('inf') else 999,
            reverse=True
        )
        
        return [
            {
                "name": p.name,
                "win_rate": round(p.win_rate * 100, 1),
                "profit_factor": round(p.profit_factor, 2) if p.profit_factor != float('inf') else "∞",
                "avg_return": round(p.avg_return, 2),
                "occurrences": p.occurrences,
                "total_pnl": round(p.total_pnl, 2)
            }
            for p in sorted_patterns[:top_n]
        ]
    
    def get_patterns_for_symbol(self, symbol: str) -> List[TradePattern]:
        """Get all patterns related to a symbol."""
        return [
            p for p in self._patterns
            if p.conditions.get("symbol") == symbol
        ]
    
    def get_summary(self) -> Dict:
        """Get pattern summary."""
        significant = [p for p in self._patterns if p.is_significant]
        
        return {
            "total_patterns": len(self._patterns),
            "significant_patterns": len(significant),
            "total_trades_analyzed": len(self._trade_buffer),
            "best_patterns": self.get_best_patterns(top_n=5),
            "worst_patterns": sorted(
                [p for p in significant],
                key=lambda p: p.win_rate
            )[:3] if significant else []
        }


# Singleton
_pattern_learner: Optional[PatternLearner] = None


def get_pattern_learner() -> PatternLearner:
    """Get or create global pattern learner."""
    global _pattern_learner
    if _pattern_learner is None:
        _pattern_learner = PatternLearner()
    return _pattern_learner









