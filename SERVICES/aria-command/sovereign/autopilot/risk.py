#!/usr/bin/env python3
"""
ARIA ULTRA POWER - RISK ENGINE
===============================

Intelligent risk management:
- Position sizing (Kelly criterion)
- Correlation-aware exposure
- Drawdown limits
- De-risking automation
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("aria.autopilot.risk")


@dataclass
class RiskLimits:
    """Risk management limits."""
    max_position_size_percent: float = 20  # Max single position as % of portfolio
    max_daily_loss_percent: float = 5  # Stop trading if daily loss exceeds this
    max_leverage: float = 3  # Maximum leverage
    max_exposure_percent: float = 100  # Max total exposure as % of equity
    correlation_limit: float = 0.7  # Max allowed correlation between positions
    max_positions: int = 5  # Max concurrent positions
    
    def to_dict(self) -> Dict:
        return {
            "max_position_size_percent": self.max_position_size_percent,
            "max_daily_loss_percent": self.max_daily_loss_percent,
            "max_leverage": self.max_leverage,
            "max_exposure_percent": self.max_exposure_percent,
            "correlation_limit": self.correlation_limit,
            "max_positions": self.max_positions,
        }


class RiskLevel(Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class RiskAssessment:
    """Assessment of current portfolio risk."""
    overall_level: RiskLevel
    risk_score: float  # 0-100
    violations: List[str]
    warnings: List[str]
    recommendations: List[str]
    can_trade: bool
    reason: str
    metrics: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "overall_level": self.overall_level.value,
            "risk_score": self.risk_score,
            "violations": self.violations,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "can_trade": self.can_trade,
            "reason": self.reason,
            "metrics": self.metrics,
        }


# Asset correlations (simplified, would be calculated dynamically)
ASSET_CORRELATIONS = {
    ("SOL", "BTC"): 0.85,
    ("SOL", "ETH"): 0.82,
    ("BTC", "ETH"): 0.90,
    ("SOL", "XRP"): 0.65,
    ("BTC", "XRP"): 0.70,
    ("ETH", "XRP"): 0.68,
}


class RiskEngine:
    """
    Risk management engine.
    
    Features:
    - Position sizing using Kelly criterion
    - Correlation-aware exposure limits
    - Drawdown monitoring
    - Automatic de-risking
    """
    
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self._daily_pnl: Dict[str, float] = {}  # date -> cumulative pnl
        self._daily_trades: Dict[str, int] = {}  # date -> trade count
        
        logger.info("RiskEngine initialized")
    
    async def assess_risk(self) -> RiskAssessment:
        """Assess current portfolio risk."""
        from .portfolio import get_portfolio_manager
        
        manager = get_portfolio_manager()
        state = await manager.get_state()
        
        violations = []
        warnings = []
        recommendations = []
        risk_score = 0
        
        # Check exposure limit
        if state.total_exposure_percent > self.limits.max_exposure_percent:
            violations.append(f"Exposure {state.total_exposure_percent:.1f}% exceeds limit {self.limits.max_exposure_percent}%")
            risk_score += 30
        elif state.total_exposure_percent > self.limits.max_exposure_percent * 0.8:
            warnings.append(f"Exposure approaching limit ({state.total_exposure_percent:.1f}%)")
            risk_score += 15
        
        # Check position count
        if len(state.positions) >= self.limits.max_positions:
            violations.append(f"Max positions reached ({len(state.positions)})")
            risk_score += 20
        elif len(state.positions) >= self.limits.max_positions - 1:
            warnings.append(f"Near max positions ({len(state.positions)}/{self.limits.max_positions})")
            risk_score += 10
        
        # Check individual position sizes
        for pos in state.positions:
            pos_pct = (pos.notional_value / state.equity * 100) if state.equity > 0 else 0
            if pos_pct > self.limits.max_position_size_percent:
                violations.append(f"{pos.symbol} position size {pos_pct:.1f}% exceeds limit")
                risk_score += 20
            
            if pos.leverage > self.limits.max_leverage:
                violations.append(f"{pos.symbol} leverage {pos.leverage}x exceeds limit {self.limits.max_leverage}x")
                risk_score += 15
        
        # Check correlation between positions
        for i, pos1 in enumerate(state.positions):
            for pos2 in state.positions[i+1:]:
                asset1 = pos1.symbol.replace("/USDT", "")
                asset2 = pos2.symbol.replace("/USDT", "")
                
                corr = self._get_correlation(asset1, asset2)
                if corr > self.limits.correlation_limit:
                    warnings.append(f"High correlation ({corr:.2f}) between {asset1} and {asset2}")
                    risk_score += 10
        
        # Check daily loss
        today = datetime.now().strftime("%Y-%m-%d")
        daily_pnl = state.total_unrealized_pnl  # Simplified
        daily_loss_pct = (abs(daily_pnl) / state.total_balance * 100) if state.total_balance > 0 and daily_pnl < 0 else 0
        
        if daily_loss_pct > self.limits.max_daily_loss_percent:
            violations.append(f"Daily loss {daily_loss_pct:.1f}% exceeds limit {self.limits.max_daily_loss_percent}%")
            risk_score += 40
        elif daily_loss_pct > self.limits.max_daily_loss_percent * 0.7:
            warnings.append(f"Approaching daily loss limit ({daily_loss_pct:.1f}%)")
            risk_score += 20
        
        # Generate recommendations
        if risk_score > 70:
            recommendations.append("Consider reducing exposure immediately")
        elif risk_score > 50:
            recommendations.append("Tighten stop losses on existing positions")
        
        if any(pos.stop_loss is None for pos in state.positions):
            recommendations.append("Add stop losses to all positions")
        
        # Determine overall level
        if risk_score >= 70 or violations:
            level = RiskLevel.EXTREME if risk_score >= 80 else RiskLevel.HIGH
            can_trade = False
            reason = "Risk limits violated" if violations else "Risk too high"
        elif risk_score >= 40:
            level = RiskLevel.MEDIUM
            can_trade = True
            reason = "Elevated risk - trade with caution"
        else:
            level = RiskLevel.LOW
            can_trade = True
            reason = "Risk within acceptable limits"
        
        return RiskAssessment(
            overall_level=level,
            risk_score=min(100, risk_score),
            violations=violations,
            warnings=warnings,
            recommendations=recommendations,
            can_trade=can_trade,
            reason=reason,
            metrics={
                "exposure_percent": state.total_exposure_percent,
                "position_count": len(state.positions),
                "daily_pnl_percent": daily_loss_pct * (-1 if daily_pnl < 0 else 1),
            }
        )
    
    def _get_correlation(self, asset1: str, asset2: str) -> float:
        """Get correlation between two assets."""
        key = (min(asset1, asset2), max(asset1, asset2))
        return ASSET_CORRELATIONS.get(key, 0.5)
    
    def calculate_kelly_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        max_kelly_fraction: float = 0.25
    ) -> float:
        """
        Calculate position size using Kelly criterion.
        
        Kelly % = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        """
        if avg_win <= 0 or avg_loss <= 0:
            return 0
        
        # Calculate full Kelly
        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        
        # Use fractional Kelly (more conservative)
        kelly = kelly * max_kelly_fraction
        
        # Clamp to reasonable range
        return max(0, min(kelly, self.limits.max_position_size_percent / 100))
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        risk_percent: float = 1.0,
        leverage: float = 1.0
    ) -> Dict:
        """
        Calculate position size based on risk per trade.
        
        Returns size that risks X% of portfolio if stop is hit.
        """
        from .portfolio import get_portfolio_manager
        import asyncio
        
        async def _get_state():
            manager = get_portfolio_manager()
            return await manager.get_state()
        
        try:
            loop = asyncio.get_event_loop()
            state = loop.run_until_complete(_get_state())
        except:
            return {"error": "Failed to get portfolio state"}
        
        risk_amount = state.total_balance * (risk_percent / 100)
        
        # Calculate distance to stop
        if entry_price <= 0 or stop_loss <= 0:
            return {"error": "Invalid prices"}
        
        stop_distance_pct = abs(entry_price - stop_loss) / entry_price
        
        if stop_distance_pct <= 0:
            return {"error": "Stop loss too close to entry"}
        
        # Position value = risk_amount / stop_distance
        position_value = risk_amount / stop_distance_pct
        
        # Adjust for leverage
        margin_required = position_value / leverage
        
        # Calculate size in units
        size = position_value / entry_price
        
        return {
            "size": size,
            "position_value": position_value,
            "margin_required": margin_required,
            "risk_amount": risk_amount,
            "stop_distance_pct": stop_distance_pct * 100,
        }
    
    async def should_reduce_risk(self) -> Optional[Dict]:
        """Check if we should automatically reduce risk."""
        assessment = await self.assess_risk()
        
        if assessment.overall_level == RiskLevel.EXTREME:
            return {
                "should_reduce": True,
                "urgency": "immediate",
                "actions": [
                    {"action": "close_most_losing", "reason": "Extreme risk level"},
                ],
            }
        elif assessment.overall_level == RiskLevel.HIGH:
            return {
                "should_reduce": True,
                "urgency": "soon",
                "actions": [
                    {"action": "tighten_stops", "reason": "High risk level"},
                ],
            }
        
        return None
    
    def update_limits(self, **kwargs):
        """Update risk limits."""
        for key, value in kwargs.items():
            if hasattr(self.limits, key):
                setattr(self.limits, key, value)
        logger.info(f"Risk limits updated: {kwargs}")
    
    def format_assessment(self, assessment: RiskAssessment) -> str:
        """Format risk assessment for display."""
        emoji_map = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🟠",
            RiskLevel.EXTREME: "🔴",
        }
        
        emoji = emoji_map.get(assessment.overall_level, "⚪")
        
        lines = [
            f"{emoji} **Risk Assessment**",
            "",
            f"Level: {assessment.overall_level.value.upper()}",
            f"Score: {assessment.risk_score}/100",
            f"Can Trade: {'Yes' if assessment.can_trade else 'No'}",
        ]
        
        if assessment.violations:
            lines.append("")
            lines.append("**🚫 Violations:**")
            for v in assessment.violations:
                lines.append(f"• {v}")
        
        if assessment.warnings:
            lines.append("")
            lines.append("**⚠️ Warnings:**")
            for w in assessment.warnings:
                lines.append(f"• {w}")
        
        if assessment.recommendations:
            lines.append("")
            lines.append("**💡 Recommendations:**")
            for r in assessment.recommendations:
                lines.append(f"• {r}")
        
        return "\n".join(lines)


# Singleton instance
_engine: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    """Get global RiskEngine instance."""
    global _engine
    if _engine is None:
        _engine = RiskEngine()
    return _engine


