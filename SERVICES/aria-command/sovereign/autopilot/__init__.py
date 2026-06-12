#!/usr/bin/env python3
"""
ARIA ULTRA POWER - PORTFOLIO AUTOPILOT
=======================================

Full autonomous trading with intelligent risk management:
- Portfolio tracking and management
- Risk engine with limits
- Strategy execution
- Confidence-based autonomy
"""

from .portfolio import (
    PortfolioManager,
    get_portfolio_manager,
    Position,
    PortfolioState,
)

from .risk import (
    RiskEngine,
    get_risk_engine,
    RiskLimits,
    RiskAssessment,
)

from .strategy import (
    StrategyExecutor,
    get_strategy_executor,
    TradingStrategy,
    StrategySignal,
)

from .loop import (
    AutopilotLoop,
    get_autopilot,
    AutopilotMode,
    AutopilotState,
)

__all__ = [
    # Portfolio
    "PortfolioManager",
    "get_portfolio_manager",
    "Position",
    "PortfolioState",
    # Risk
    "RiskEngine",
    "get_risk_engine",
    "RiskLimits",
    "RiskAssessment",
    # Strategy
    "StrategyExecutor",
    "get_strategy_executor",
    "TradingStrategy",
    "StrategySignal",
    # Loop
    "AutopilotLoop",
    "get_autopilot",
    "AutopilotMode",
    "AutopilotState",
]


