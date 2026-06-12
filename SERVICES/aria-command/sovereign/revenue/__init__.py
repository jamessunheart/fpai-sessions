#!/usr/bin/env python3
"""
ARIA ASCENSION - REVENUE ENGINE
===============================

Active value generation and tracking:
- Trade Executor: Execute approved trading strategies
- Service Deployer: Deploy revenue-generating features
- ROI Tracker: Track costs and value generated

Revenue Metrics:
- Trading P&L attributed to Aria decisions
- Time saved (hours × James's hourly value)
- Features deployed → usage → revenue
"""

from .trade_executor import (
    TradeExecutor,
    get_trade_executor,
    execute_trade,
    get_position_status
)

from .roi_tracker import (
    ROITracker,
    get_roi_tracker,
    track_cost,
    track_value,
    get_roi_summary
)

__all__ = [
    "TradeExecutor",
    "get_trade_executor",
    "execute_trade",
    "get_position_status",
    "ROITracker",
    "get_roi_tracker",
    "track_cost",
    "track_value",
    "get_roi_summary"
]


