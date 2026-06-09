#!/usr/bin/env python3
"""
Intelligent Trader
==================
Wraps the Level 10 trader with learning intelligence.

Intelligence Features:
1. Pre-trade: Check if we SHOULD trade based on history
2. Sizing: Adjust position size based on edge
3. Post-trade: Learn from every closed trade
4. Reporting: Generate intelligence reports

This makes the trader SMARTER over time.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import requests

from .trade_learning_engine import (
    get_learning_engine, 
    should_trade, 
    get_size_multiplier,
    get_intelligence_report
)

logger = logging.getLogger("intelligent_trader")


class IntelligentTrader:
    """
    Intelligent wrapper for trading decisions.
    """
    
    def __init__(self):
        self.learning = get_learning_engine()
        self.last_sync = None
        self.decisions_today = []
        
    def pre_trade_check(self, symbol: str, side: str, signal_strength: float = 1.0) -> Dict:
        """
        Check if we should take this trade based on intelligence.
        
        Args:
            symbol: Asset to trade
            side: 'long' or 'short'
            signal_strength: 0-1, how strong is the signal
        
        Returns:
            {
                "should_trade": bool,
                "size_multiplier": float,
                "reason": str,
                "confidence": str
            }
        """
        should, reason, multiplier = should_trade(symbol, side)
        
        # Adjust for signal strength
        if signal_strength < 0.5:
            multiplier *= 0.5
            reason += " (weak signal)"
        elif signal_strength > 0.8:
            multiplier *= 1.2
            reason += " (strong signal)"
        
        # Cap multiplier
        multiplier = min(multiplier, 2.0)
        
        decision = {
            "should_trade": should and multiplier > 0,
            "size_multiplier": multiplier,
            "reason": reason,
            "confidence": "high" if self.learning.get_asset_profile(symbol) and self.learning.get_asset_profile(symbol).total_trades > 20 else "low",
            "timestamp": datetime.now().isoformat()
        }
        
        self.decisions_today.append({
            "symbol": symbol,
            "side": side,
            **decision
        })
        
        return decision
    
    def get_optimal_size(self, symbol: str, base_size: float) -> float:
        """
        Get optimal position size based on learned edge.
        
        Args:
            symbol: Asset
            base_size: Base position size (without intelligence)
        
        Returns:
            Adjusted size
        """
        multiplier = get_size_multiplier(symbol)
        return base_size * multiplier
    
    def post_trade_learn(self):
        """Sync trades and update learning."""
        self.learning.sync_trades()
        self.learning.analyze_patterns()
        self.last_sync = datetime.now()
        logger.info("Learning updated from latest trades")
    
    def get_recommendations(self) -> Dict[str, Dict]:
        """
        Get trading recommendations for all assets.
        
        Returns:
            {
                "SOL": {"action": "trade", "size": 1.5, "edge": 0.05},
                "BTC": {"action": "avoid", "size": 0, "edge": -0.02},
                ...
            }
        """
        recommendations = {}
        
        for symbol in ["SOL", "ETH", "BTC"]:
            profile = self.learning.get_asset_profile(symbol)
            
            if profile:
                recommendations[symbol] = {
                    "action": profile.recommendation,
                    "size_multiplier": self.learning.get_position_size_multiplier(symbol),
                    "edge": profile.edge,
                    "win_rate": profile.win_rate,
                    "total_trades": profile.total_trades,
                    "best_hours": profile.best_hours,
                    "worst_hours": profile.worst_hours
                }
            else:
                recommendations[symbol] = {
                    "action": "trade",
                    "size_multiplier": 0.5,
                    "edge": 0,
                    "win_rate": 0,
                    "total_trades": 0,
                    "note": "No history - trading with caution"
                }
        
        return recommendations
    
    def get_report(self) -> str:
        """Get intelligence report."""
        return get_intelligence_report()
    
    def should_be_active(self) -> Tuple[bool, str]:
        """
        Check if trading should be active based on overall performance.
        
        Returns:
            (should_trade, reason)
        """
        # Check if we're in heavy drawdown
        if self.learning._is_in_drawdown():
            return False, "In drawdown - pausing new trades"
        
        # Check overall edge
        patterns = self.learning.analyze_patterns()
        total_edge = sum(p.edge for p in patterns.values() if p.pattern.startswith("asset:"))
        
        if total_edge < -10:
            return False, f"Negative overall edge (${total_edge:.2f}) - reconsidering strategy"
        
        return True, "System healthy"


# Integration with existing trader

def create_intelligent_config(base_config: Dict) -> Dict:
    """
    Create an intelligent config that adjusts parameters based on learning.
    """
    trader = IntelligentTrader()
    recommendations = trader.get_recommendations()
    
    config = base_config.copy()
    
    # Adjust per-asset settings based on learning
    asset_configs = {}
    for symbol, rec in recommendations.items():
        asset_configs[symbol] = {
            "enabled": rec["action"] != "avoid",
            "size_multiplier": rec["size_multiplier"],
            "edge": rec["edge"]
        }
    
    config["asset_intelligence"] = asset_configs
    config["intelligence_enabled"] = True
    
    return config


async def run_intelligent_cycle(trader_instance):
    """
    Run one intelligent trading cycle.
    
    This should be called from the main trader loop.
    """
    intelligent = IntelligentTrader()
    
    # Check if we should be trading at all
    should_trade, reason = intelligent.should_be_active()
    if not should_trade:
        logger.warning(f"Trading paused: {reason}")
        return {"action": "pause", "reason": reason}
    
    # Get recommendations
    recommendations = intelligent.get_recommendations()
    
    # Log intelligence
    for symbol, rec in recommendations.items():
        if rec["action"] == "avoid":
            logger.info(f"🔴 {symbol}: AVOID (edge: ${rec['edge']:.2f})")
        elif rec["action"] == "reduce":
            logger.info(f"🟡 {symbol}: REDUCE to {rec['size_multiplier']:.1f}x")
        else:
            logger.info(f"🟢 {symbol}: TRADE at {rec['size_multiplier']:.1f}x (edge: ${rec['edge']:.2f})")
    
    return {
        "action": "continue",
        "recommendations": recommendations
    }


# Singleton
_intelligent_trader: Optional[IntelligentTrader] = None

def get_intelligent_trader() -> IntelligentTrader:
    global _intelligent_trader
    if _intelligent_trader is None:
        _intelligent_trader = IntelligentTrader()
    return _intelligent_trader







