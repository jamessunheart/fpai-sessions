#!/usr/bin/env python3
"""
🔗 PORTFOLIO CORRELATION MANAGEMENT
=====================================

Manages portfolio-level correlation risk:
- Tracks correlations between assets
- Adjusts position sizes for correlated exposure
- Prevents over-concentration
- Promotes diversification

Reduces risk from correlated positions moving together.
"""

import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger("aria.trading.correlation")


@dataclass
class Position:
    """An open position."""
    symbol: str
    side: str  # "long" or "short"
    size_usd: float
    entry_price: float
    unrealized_pnl: float = 0.0


@dataclass
class CorrelationCheck:
    """Result of correlation check."""
    allowed: bool
    adjusted_size: float
    reason: str
    correlated_symbols: List[str]
    total_correlated_exposure: float


class CorrelationManager:
    """
    Manages portfolio-level correlation risk.
    
    Features:
    - Pre-defined correlation matrix for crypto pairs
    - Adjusts position sizes based on existing exposure
    - Limits total correlated exposure
    - Suggests diversification
    """
    
    # Pre-computed correlations for major crypto pairs
    # These are approximate and should be updated periodically
    # Values: 0.0 (uncorrelated) to 1.0 (perfectly correlated)
    CORRELATIONS = {
        ("BTC", "ETH"): 0.85,
        ("BTC", "SOL"): 0.75,
        ("BTC", "AVAX"): 0.70,
        ("BTC", "MATIC"): 0.70,
        ("BTC", "LINK"): 0.65,
        ("BTC", "DOGE"): 0.60,
        ("BTC", "XRP"): 0.60,
        
        ("ETH", "SOL"): 0.80,
        ("ETH", "AVAX"): 0.75,
        ("ETH", "MATIC"): 0.75,
        ("ETH", "LINK"): 0.70,
        
        ("SOL", "AVAX"): 0.70,
        ("SOL", "MATIC"): 0.65,
    }
    
    # Maximum exposure to correlated assets
    MAX_CORRELATED_EXPOSURE_PCT = 0.70  # 70% of portfolio
    
    # Correlation threshold for considering assets "correlated"
    CORRELATION_THRESHOLD = 0.60
    
    def __init__(self):
        pass
    
    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Get correlation between two assets.
        
        Returns 0 if no correlation data available.
        """
        if symbol1 == symbol2:
            return 1.0
        
        # Normalize symbols
        s1, s2 = symbol1.upper(), symbol2.upper()
        
        # Try both orderings
        corr = self.CORRELATIONS.get((s1, s2))
        if corr is not None:
            return corr
        
        corr = self.CORRELATIONS.get((s2, s1))
        if corr is not None:
            return corr
        
        # Default to moderate correlation for unknown pairs
        return 0.40
    
    def check_portfolio_risk(
        self,
        current_positions: List[Position],
        proposed_symbol: str,
        proposed_side: str,
        proposed_size: float,
        portfolio_value: float
    ) -> CorrelationCheck:
        """
        Check if proposed trade would create too much correlated exposure.
        
        Rules:
        - Max 70% exposure to correlated assets
        - Reduce size if adding to correlated exposure
        - Prefer uncorrelated diversification
        """
        if not current_positions:
            # No existing positions, allow full size
            return CorrelationCheck(
                allowed=True,
                adjusted_size=proposed_size,
                reason="No existing positions",
                correlated_symbols=[],
                total_correlated_exposure=proposed_size / portfolio_value * 100 if portfolio_value else 0
            )
        
        # Find correlated positions
        correlated = []
        total_correlated_usd = 0.0
        
        for pos in current_positions:
            correlation = self.get_correlation(proposed_symbol, pos.symbol)
            
            if correlation >= self.CORRELATION_THRESHOLD:
                # Same direction adds correlation, opposite direction reduces
                if pos.side == proposed_side:
                    # Same direction = adds to correlated exposure
                    correlated.append(pos.symbol)
                    total_correlated_usd += pos.size_usd * correlation
                else:
                    # Opposite direction = hedge, reduces correlation
                    total_correlated_usd -= pos.size_usd * correlation * 0.5
        
        # Calculate what proposed trade would add
        new_correlated = total_correlated_usd + proposed_size
        new_correlated_pct = new_correlated / portfolio_value * 100 if portfolio_value else 0
        
        # Check limits
        max_allowed_usd = portfolio_value * self.MAX_CORRELATED_EXPOSURE_PCT
        
        if new_correlated <= max_allowed_usd:
            # Within limits
            return CorrelationCheck(
                allowed=True,
                adjusted_size=proposed_size,
                reason=f"Correlated exposure {new_correlated_pct:.1f}% within limit",
                correlated_symbols=correlated,
                total_correlated_exposure=new_correlated_pct
            )
        
        # Need to reduce size
        available_room = max_allowed_usd - total_correlated_usd
        
        if available_room <= 0:
            return CorrelationCheck(
                allowed=False,
                adjusted_size=0,
                reason=f"Maximum correlated exposure already reached ({total_correlated_usd/portfolio_value*100:.1f}%)",
                correlated_symbols=correlated,
                total_correlated_exposure=total_correlated_usd / portfolio_value * 100 if portfolio_value else 0
            )
        
        # Reduce to fit within limits
        adjusted_size = min(proposed_size, available_room)
        
        return CorrelationCheck(
            allowed=True,
            adjusted_size=adjusted_size,
            reason=f"Reduced from ${proposed_size:.0f} to ${adjusted_size:.0f} for correlation limit",
            correlated_symbols=correlated,
            total_correlated_exposure=new_correlated_pct
        )
    
    def get_adjusted_size(
        self,
        proposed_size: float,
        symbol: str,
        side: str,
        current_positions: List[Position],
        portfolio_value: float
    ) -> float:
        """
        Get adjusted position size based on existing correlated exposure.
        
        Convenience method for quick size adjustment.
        """
        check = self.check_portfolio_risk(
            current_positions=current_positions,
            proposed_symbol=symbol,
            proposed_side=side,
            proposed_size=proposed_size,
            portfolio_value=portfolio_value
        )
        
        return check.adjusted_size
    
    def get_diversification_score(
        self,
        positions: List[Position]
    ) -> Tuple[float, str]:
        """
        Calculate diversification score for current portfolio.
        
        Returns:
            (score 0-100, description)
        """
        if not positions:
            return 100.0, "No positions"
        
        if len(positions) == 1:
            return 50.0, "Single position - no diversification"
        
        # Calculate average correlation between all positions
        total_corr = 0.0
        pairs = 0
        
        for i, pos1 in enumerate(positions):
            for pos2 in positions[i+1:]:
                corr = self.get_correlation(pos1.symbol, pos2.symbol)
                total_corr += corr
                pairs += 1
        
        avg_corr = total_corr / pairs if pairs > 0 else 0
        
        # Higher correlation = lower diversification score
        score = (1 - avg_corr) * 100
        
        if score >= 70:
            desc = "Well diversified portfolio"
        elif score >= 50:
            desc = "Moderately diversified"
        elif score >= 30:
            desc = "Low diversification - high correlation risk"
        else:
            desc = "Poor diversification - very high correlation risk"
        
        return round(score, 1), desc
    
    def get_hedge_suggestions(
        self,
        positions: List[Position]
    ) -> List[str]:
        """
        Get suggestions for hedging or diversifying.
        """
        suggestions = []
        
        if not positions:
            return suggestions
        
        # Check if all positions are same direction
        longs = [p for p in positions if p.side == "long"]
        shorts = [p for p in positions if p.side == "short"]
        
        if len(longs) > 0 and len(shorts) == 0:
            suggestions.append("Consider a short position for hedging")
        elif len(shorts) > 0 and len(longs) == 0:
            suggestions.append("Consider a long position for hedging")
        
        # Check for highly correlated positions
        for i, pos1 in enumerate(positions):
            for pos2 in positions[i+1:]:
                corr = self.get_correlation(pos1.symbol, pos2.symbol)
                if corr >= 0.80 and pos1.side == pos2.side:
                    suggestions.append(
                        f"{pos1.symbol} and {pos2.symbol} highly correlated ({corr:.0%}) - "
                        "consider closing one"
                    )
        
        # Suggest uncorrelated assets
        current_symbols = {p.symbol for p in positions}
        
        uncorrelated_options = []
        for symbol in ["BTC", "ETH", "SOL", "AVAX", "LINK", "XRP"]:
            if symbol in current_symbols:
                continue
            
            max_corr = max(
                self.get_correlation(symbol, p.symbol)
                for p in positions
            )
            
            if max_corr < 0.50:
                uncorrelated_options.append((symbol, max_corr))
        
        if uncorrelated_options:
            best = min(uncorrelated_options, key=lambda x: x[1])
            suggestions.append(f"Consider {best[0]} for diversification (low correlation)")
        
        return suggestions
    
    def get_portfolio_summary(self, positions: List[Position], portfolio_value: float) -> Dict:
        """Get portfolio correlation summary."""
        div_score, div_desc = self.get_diversification_score(positions)
        
        return {
            "diversification_score": div_score,
            "diversification_description": div_desc,
            "positions_count": len(positions),
            "hedge_suggestions": self.get_hedge_suggestions(positions),
            "max_correlated_exposure_pct": self.MAX_CORRELATED_EXPOSURE_PCT * 100,
            "correlations": [
                {
                    "pair": f"{pos1.symbol}/{pos2.symbol}",
                    "correlation": self.get_correlation(pos1.symbol, pos2.symbol)
                }
                for i, pos1 in enumerate(positions)
                for pos2 in positions[i+1:]
            ]
        }


# Singleton
_correlation_manager: Optional[CorrelationManager] = None


def get_correlation_manager() -> CorrelationManager:
    """Get or create global correlation manager."""
    global _correlation_manager
    if _correlation_manager is None:
        _correlation_manager = CorrelationManager()
    return _correlation_manager









