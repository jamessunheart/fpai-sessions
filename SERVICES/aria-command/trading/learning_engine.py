#!/usr/bin/env python3
"""
🧠 TRADE LEARNING ENGINE
=========================

Learns from trade history to improve future decisions:
- Signal source weights (which sources perform better)
- Symbol weights (which assets are more predictable)
- Hour-of-day weights (best times to trade)
- Confidence calibration (reported vs actual win rate)

Continuously adapts based on real trading outcomes.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger("aria.trading.learning")

DATA_DIR = Path(os.getenv("ARIA_DATA_DIR", "/opt/fpai/aria-command/data"))


@dataclass
class TradingInsights:
    """Current learned trading insights."""
    best_hours: List[int]           # Best hours to trade (UTC)
    worst_hours: List[int]          # Worst hours to trade
    best_symbols: List[str]         # Best performing symbols
    best_signal_sources: List[str]  # Most reliable signal sources
    confidence_accuracy: float      # How accurate confidence predictions are
    avg_win_rate: float
    avg_profit_factor: float
    recommendations: List[str]      # Actionable recommendations


@dataclass
class WeightedScore:
    """A score with sample count for weighted averaging."""
    score: float = 1.0
    samples: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    
    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.5
    
    def update(self, is_win: bool, pnl: float, learning_rate: float = 0.1):
        """Update score based on trade outcome."""
        self.samples += 1
        self.total_pnl += pnl
        
        if is_win:
            self.wins += 1
            # Increase weight for winning outcomes
            self.score = self.score * (1 - learning_rate) + 1.2 * learning_rate
        else:
            self.losses += 1
            # Decrease weight for losing outcomes
            self.score = self.score * (1 - learning_rate) + 0.8 * learning_rate
        
        # Clamp to reasonable range
        self.score = max(0.5, min(1.5, self.score))


class TradeLearningEngine:
    """
    Learns from trade history to improve future decisions.
    
    Features:
    - Tracks performance by signal source, symbol, and hour
    - Adjusts confidence based on historical accuracy
    - Provides actionable insights
    - Persists learned weights
    """
    
    def __init__(self):
        self._signal_weights: Dict[str, WeightedScore] = defaultdict(WeightedScore)
        self._symbol_weights: Dict[str, WeightedScore] = defaultdict(WeightedScore)
        self._hour_weights: Dict[int, WeightedScore] = {h: WeightedScore() for h in range(24)}
        self._confidence_calibration: Dict[int, Dict[str, int]] = defaultdict(lambda: {"trades": 0, "wins": 0})
        
        # Learning parameters
        self._learning_rate = 0.1
        self._min_samples = 5  # Minimum samples before using weight
        
        # Load persisted weights
        self._load_weights()
    
    def _weights_file(self) -> Path:
        """Get weights file path."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / "learning_weights.json"
    
    def _load_weights(self):
        """Load persisted weights from file."""
        try:
            path = self._weights_file()
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                
                # Restore signal weights
                for source, w in data.get("signal_weights", {}).items():
                    self._signal_weights[source] = WeightedScore(**w)
                
                # Restore symbol weights
                for symbol, w in data.get("symbol_weights", {}).items():
                    self._symbol_weights[symbol] = WeightedScore(**w)
                
                # Restore hour weights
                for hour_str, w in data.get("hour_weights", {}).items():
                    self._hour_weights[int(hour_str)] = WeightedScore(**w)
                
                # Restore confidence calibration
                self._confidence_calibration = defaultdict(
                    lambda: {"trades": 0, "wins": 0},
                    {int(k): v for k, v in data.get("confidence_calibration", {}).items()}
                )
                
                logger.info("📚 Loaded learning weights from file")
        except Exception as e:
            logger.warning(f"Failed to load weights: {e}")
    
    def _save_weights(self):
        """Persist weights to file."""
        try:
            data = {
                "signal_weights": {k: vars(v) for k, v in self._signal_weights.items()},
                "symbol_weights": {k: vars(v) for k, v in self._symbol_weights.items()},
                "hour_weights": {str(k): vars(v) for k, v in self._hour_weights.items()},
                "confidence_calibration": dict(self._confidence_calibration),
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self._weights_file(), "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save weights: {e}")
    
    async def process_completed_trade(
        self,
        symbol: str,
        entry_time: datetime,
        pnl: float,
        signal_source: str = "signal-shark",
        reported_confidence: float = 0.0
    ):
        """
        Process a completed trade to update weights.
        
        Called after each trade closes.
        """
        is_win = pnl > 0
        hour = entry_time.hour
        
        # 1. Update signal source weight
        self._signal_weights[signal_source].update(is_win, pnl, self._learning_rate)
        
        # 2. Update symbol weight
        self._symbol_weights[symbol].update(is_win, pnl, self._learning_rate)
        
        # 3. Update hour weight
        self._hour_weights[hour].update(is_win, pnl, self._learning_rate)
        
        # 4. Update confidence calibration
        conf_bucket = int(reported_confidence // 10) * 10  # 70%, 80%, 90%, etc.
        self._confidence_calibration[conf_bucket]["trades"] += 1
        if is_win:
            self._confidence_calibration[conf_bucket]["wins"] += 1
        
        # Save updated weights
        self._save_weights()
        
        logger.info(
            f"📊 Learning updated: {symbol} @ {hour}:00 "
            f"| {'WIN' if is_win else 'LOSS'} ${pnl:+,.2f}"
        )
    
    def get_adjusted_confidence(
        self,
        raw_confidence: float,
        symbol: str,
        hour: int,
        signal_source: str
    ) -> float:
        """
        Adjust signal confidence based on learned weights.
        
        Example:
        - Raw confidence: 80%
        - Symbol SOL has 1.2x weight (performs well)
        - Hour 14 has 0.9x weight (afternoon weakness)
        - Signal Shark has 1.1x weight (reliable)
        
        Adjusted: 80% * 1.2 * 0.9 * 1.1 = 95% (capped at 100)
        """
        adjusted = raw_confidence
        
        # Apply signal source weight (if enough samples)
        if self._signal_weights[signal_source].samples >= self._min_samples:
            adjusted *= self._signal_weights[signal_source].score
        
        # Apply symbol weight
        if self._symbol_weights[symbol].samples >= self._min_samples:
            adjusted *= self._symbol_weights[symbol].score
        
        # Apply hour weight
        if self._hour_weights[hour].samples >= self._min_samples:
            adjusted *= self._hour_weights[hour].score
        
        # Apply confidence calibration
        conf_bucket = int(raw_confidence // 10) * 10
        if self._confidence_calibration[conf_bucket]["trades"] >= self._min_samples:
            actual_win_rate = (
                self._confidence_calibration[conf_bucket]["wins"] /
                self._confidence_calibration[conf_bucket]["trades"]
            )
            reported_win_rate = raw_confidence / 100
            
            # Blend toward actual performance
            calibration_factor = actual_win_rate / reported_win_rate if reported_win_rate > 0 else 1
            adjusted *= calibration_factor
        
        # Clamp to valid range
        return max(0, min(100, adjusted))
    
    def get_trading_insights(self) -> TradingInsights:
        """Get current learned insights."""
        
        # Find best/worst hours
        hour_scores = [(h, w.score, w.samples) for h, w in self._hour_weights.items() if w.samples >= self._min_samples]
        hour_scores.sort(key=lambda x: x[1], reverse=True)
        
        best_hours = [h for h, s, n in hour_scores[:3] if s > 1.0]
        worst_hours = [h for h, s, n in sorted(hour_scores, key=lambda x: x[1])[:3] if s < 1.0]
        
        # Find best symbols
        symbol_scores = [(s, w.score, w.samples) for s, w in self._symbol_weights.items() if w.samples >= self._min_samples]
        symbol_scores.sort(key=lambda x: x[1], reverse=True)
        best_symbols = [s for s, score, n in symbol_scores[:3] if score > 1.0]
        
        # Find best signal sources
        source_scores = [(s, w.score, w.samples) for s, w in self._signal_weights.items() if w.samples >= self._min_samples]
        source_scores.sort(key=lambda x: x[1], reverse=True)
        best_sources = [s for s, score, n in source_scores[:3] if score > 1.0]
        
        # Calculate overall stats
        all_weights = list(self._symbol_weights.values()) + list(self._signal_weights.values())
        total_wins = sum(w.wins for w in all_weights)
        total_losses = sum(w.losses for w in all_weights)
        total_pnl = sum(w.total_pnl for w in all_weights)
        
        avg_win_rate = total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0.5
        
        # Calculate confidence accuracy
        conf_data = [
            (bucket, d["wins"] / d["trades"] * 100, d["trades"])
            for bucket, d in self._confidence_calibration.items()
            if d["trades"] >= self._min_samples
        ]
        confidence_accuracy = 0.0
        if conf_data:
            total_samples = sum(n for _, _, n in conf_data)
            weighted_accuracy = sum(
                (100 - abs(bucket - actual)) * n
                for bucket, actual, n in conf_data
            )
            confidence_accuracy = weighted_accuracy / total_samples if total_samples > 0 else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            best_hours, worst_hours, best_symbols, avg_win_rate
        )
        
        return TradingInsights(
            best_hours=best_hours,
            worst_hours=worst_hours,
            best_symbols=best_symbols,
            best_signal_sources=best_sources,
            confidence_accuracy=confidence_accuracy,
            avg_win_rate=avg_win_rate * 100,
            avg_profit_factor=abs(total_pnl) / max(1, total_losses) if total_losses else 0,
            recommendations=recommendations
        )
    
    def _generate_recommendations(
        self,
        best_hours: List[int],
        worst_hours: List[int],
        best_symbols: List[str],
        avg_win_rate: float
    ) -> List[str]:
        """Generate actionable trading recommendations."""
        recs = []
        
        if best_hours:
            recs.append(f"Focus trading during hours: {', '.join(f'{h}:00' for h in best_hours)} UTC")
        
        if worst_hours:
            recs.append(f"Avoid trading during hours: {', '.join(f'{h}:00' for h in worst_hours)} UTC")
        
        if best_symbols:
            recs.append(f"Best performing assets: {', '.join(best_symbols)}")
        
        if avg_win_rate < 0.5:
            recs.append("Consider increasing minimum confidence threshold")
        
        if avg_win_rate > 0.65:
            recs.append("Strong performance - consider slightly larger position sizes")
        
        # Add confidence-based recommendations
        overconfident_buckets = [
            bucket for bucket, d in self._confidence_calibration.items()
            if d["trades"] >= self._min_samples and d["wins"] / d["trades"] < bucket / 100 - 0.1
        ]
        if overconfident_buckets:
            recs.append(f"Signals at {overconfident_buckets[0]}% confidence are overconfident")
        
        return recs
    
    def get_weight_summary(self) -> Dict:
        """Get summary of all weights for debugging."""
        return {
            "signal_sources": {
                k: {
                    "score": round(v.score, 3),
                    "win_rate": round(v.win_rate, 3),
                    "samples": v.samples,
                    "pnl": round(v.total_pnl, 2)
                }
                for k, v in self._signal_weights.items()
            },
            "symbols": {
                k: {
                    "score": round(v.score, 3),
                    "win_rate": round(v.win_rate, 3),
                    "samples": v.samples,
                    "pnl": round(v.total_pnl, 2)
                }
                for k, v in self._symbol_weights.items()
            },
            "hours": {
                k: {
                    "score": round(v.score, 3),
                    "win_rate": round(v.win_rate, 3),
                    "samples": v.samples
                }
                for k, v in self._hour_weights.items()
                if v.samples > 0
            },
            "confidence_calibration": dict(self._confidence_calibration)
        }


# Singleton
_learning_engine: Optional[TradeLearningEngine] = None


def get_learning_engine() -> TradeLearningEngine:
    """Get or create global learning engine."""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = TradeLearningEngine()
    return _learning_engine









