#!/usr/bin/env python3
"""
ARIA Trading Module - Level 10 Trading System
===============================================

A comprehensive, institutional-grade trading system with:
- Persistent state and recovery
- Exchange-native stop orders
- Trailing stops and profit taking
- Kelly criterion position sizing
- Drawdown protection
- Learning and adaptation
- Pattern recognition
- Market regime detection

Provides trading capabilities for Aria:
- Live trading via Hyperliquid
- Auto-trading with Signal Shark
- Natural language trading commands
- Position monitoring and PnL tracking
"""

# Core trading components
from .executor import get_executor, TradingExecutor
from .live_bridge import get_live_trading_bridge, LiveTradingBridge, get_trading_status
from .natural_commands import (
    parse_trading_intent,
    execute_trading_command,
    is_trading_related
)
from .notifications import (
    get_trading_notifier,
    TradingNotifier,
    start_signal_monitoring,
    stop_signal_monitoring
)
from .analytics import get_analytics, TradingAnalytics, Trade, PerformanceMetrics
from .voice_alerts import get_voice_alerts, TradingVoiceAlerts
from .journal import get_journal, TradingJournal
from .optimizer import get_optimizer, StrategyOptimizer, STRATEGIES
from .hyperliquid_live import get_hyperliquid, HyperliquidLive, get_live_status, get_live_positions, get_live_balance
from .auto_trader import (
    get_auto_trader, AriaAutoTrader, AutoTraderConfig,
    start_auto_trading, stop_auto_trading, emergency_stop,
    get_auto_trading_status
)

# ========== LEVEL 10 COMPONENTS ==========

# Phase 1: Foundation
from .persistence import (
    get_persistence, TradePersistence, 
    TradeRecord, AutoTraderState, DailyStats, SignalRecord
)
from .order_manager import get_order_manager, OrderManager
from .trailing_stop import (
    get_trailing_manager, TrailingStopManager,
    TrailingStopConfig, start_trailing_for_position
)
from .recovery import get_recovery, TradingRecovery, run_recovery

# Phase 2: Smart Execution
from .scaled_entry import get_scaled_entry_manager, ScaledEntryManager, ScaleConfig
from .profit_taker import get_profit_taker, ProfitTaker, ProfitTakeConfig
from .time_rules import get_time_exit_manager, TimeBasedExitManager, TimeRules

# Phase 3: Adaptive Intelligence
from .learning_engine import get_learning_engine, TradeLearningEngine
from .regime_detector import get_regime_detector, RegimeDetector, MarketRegime
from .pattern_learner import (
    get_pattern_learner, PatternLearner, 
    TradePattern, MarketConditions
)

# Phase 4: Money Management
from .position_sizer import get_position_sizer, KellyPositionSizer, PerformanceStats as SizingStats
from .drawdown_protector import get_drawdown_protector, DrawdownProtector, DrawdownConfig
from .capital_manager import get_capital_manager, CapitalManager, CapitalRules
from .correlation_manager import get_correlation_manager, CorrelationManager

# Phase 5: Master Controller
from .trade_controller import (
    get_trade_controller, MasterTradeController,
    TradingSignal, TradeDecision, process_signal
)

# ========== TRUE LEVEL 10 ENHANCEMENTS ==========

# Real-Time Execution
from .websocket_feed import (
    get_websocket_feed, HyperliquidWebSocket,
    start_websocket_feed, stop_websocket_feed,
    PriceUpdate, OrderUpdate, FillEvent
)
from .realtime_executor import (
    get_realtime_executor, RealTimeExecutor,
    start_realtime_executor, stop_realtime_executor,
    PendingExecution, ExecutionResult
)

# Order Management
from .order_lifecycle import (
    get_order_manager as get_lifecycle_manager, OrderLifecycleManager,
    start_order_manager, stop_order_manager,
    ManagedOrder, OrderState, OrderFill, OrderResult
)
from .resilient_client import (
    get_resilient_client, ResilientExchangeClient,
    start_exchange_monitoring, stop_exchange_monitoring,
    get_exchange_health, ConnectionState, HealthStatus
)

# Risk & Slippage
from .slippage_tracker import (
    get_slippage_tracker, SlippageTracker,
    record_slippage, SlippageRecord
)
from .risk_metrics import (
    get_risk_calculator, RiskMetricsCalculator,
    calculate_risk_metrics, generate_risk_report, RiskMetrics
)
from .equity_tracker import (
    get_equity_tracker, EquityTracker,
    record_equity_snapshot, record_daily_equity,
    get_equity_curve, EquitySnapshot
)

# Backtesting
from .backtest import (
    get_data_manager, HistoricalDataManager, OHLCV,
    get_backtest_engine, BacktestEngine, BacktestConfig, BacktestResult,
    get_strategy_tester, StrategyTester
)

__all__ = [
    # Executor
    "get_executor",
    "TradingExecutor",
    # Live Bridge
    "get_live_trading_bridge",
    "LiveTradingBridge",
    "get_trading_status",
    # Natural Commands
    "parse_trading_intent",
    "execute_trading_command",
    "is_trading_related",
    # Notifications
    "get_trading_notifier",
    "TradingNotifier",
    "start_signal_monitoring",
    "stop_signal_monitoring",
    # Analytics
    "get_analytics",
    "TradingAnalytics",
    "Trade",
    "PerformanceMetrics",
    # Voice Alerts
    "get_voice_alerts",
    "TradingVoiceAlerts",
    # Journal
    "get_journal",
    "TradingJournal",
    # Optimizer
    "get_optimizer",
    "StrategyOptimizer",
    "STRATEGIES",
    # Hyperliquid Live
    "get_hyperliquid",
    "HyperliquidLive",
    "get_live_status",
    "get_live_positions",
    "get_live_balance",
    # Auto Trader
    "get_auto_trader",
    "AriaAutoTrader",
    "AutoTraderConfig",
    "start_auto_trading",
    "stop_auto_trading",
    "emergency_stop",
    "get_auto_trading_status",
    
    # ========== LEVEL 10 COMPONENTS ==========
    
    # Phase 1: Foundation
    "get_persistence", "TradePersistence", 
    "TradeRecord", "AutoTraderState", "DailyStats", "SignalRecord",
    "get_order_manager", "OrderManager",
    "get_trailing_manager", "TrailingStopManager", 
    "TrailingStopConfig", "start_trailing_for_position",
    "get_recovery", "TradingRecovery", "run_recovery",
    
    # Phase 2: Smart Execution
    "get_scaled_entry_manager", "ScaledEntryManager", "ScaleConfig",
    "get_profit_taker", "ProfitTaker", "ProfitTakeConfig",
    "get_time_exit_manager", "TimeBasedExitManager", "TimeRules",
    
    # Phase 3: Adaptive Intelligence
    "get_learning_engine", "TradeLearningEngine",
    "get_regime_detector", "RegimeDetector", "MarketRegime",
    "get_pattern_learner", "PatternLearner", "TradePattern", "MarketConditions",
    
    # Phase 4: Money Management
    "get_position_sizer", "KellyPositionSizer", "SizingStats",
    "get_drawdown_protector", "DrawdownProtector", "DrawdownConfig",
    "get_capital_manager", "CapitalManager", "CapitalRules",
    "get_correlation_manager", "CorrelationManager",
    
    # Phase 5: Master Controller
    "get_trade_controller", "MasterTradeController",
    "TradingSignal", "TradeDecision", "process_signal",
    
    # ========== TRUE LEVEL 10 ENHANCEMENTS ==========
    
    # Real-Time Execution
    "get_websocket_feed", "HyperliquidWebSocket",
    "start_websocket_feed", "stop_websocket_feed",
    "PriceUpdate", "OrderUpdate", "FillEvent",
    "get_realtime_executor", "RealTimeExecutor",
    "start_realtime_executor", "stop_realtime_executor",
    "PendingExecution", "ExecutionResult",
    
    # Order Management
    "get_lifecycle_manager", "OrderLifecycleManager",
    "start_order_manager", "stop_order_manager",
    "ManagedOrder", "OrderState", "OrderFill", "OrderResult",
    "get_resilient_client", "ResilientExchangeClient",
    "start_exchange_monitoring", "stop_exchange_monitoring",
    "get_exchange_health", "ConnectionState", "HealthStatus",
    
    # Risk & Slippage
    "get_slippage_tracker", "SlippageTracker",
    "record_slippage", "SlippageRecord",
    "get_risk_calculator", "RiskMetricsCalculator",
    "calculate_risk_metrics", "generate_risk_report", "RiskMetrics",
    "get_equity_tracker", "EquityTracker",
    "record_equity_snapshot", "record_daily_equity",
    "get_equity_curve", "EquitySnapshot",
    
    # Backtesting
    "get_data_manager", "HistoricalDataManager", "OHLCV",
    "get_backtest_engine", "BacktestEngine", "BacktestConfig", "BacktestResult",
    "get_strategy_tester", "StrategyTester",
]


async def get_trading_context_for_prompt() -> str:
    """
    Get trading context to inject into Aria's system prompt.
    
    Returns:
        Trading context string with current status and opportunities
    """
    try:
        status = await get_trading_status()
        
        if not status:
            return ""
        
        # Build context
        lines = ["\n\n## 📊 TRADING CONTEXT (Real-Time)"]
        
        # Connection status
        if status.get("live_connected"):
            lines.append(f"✅ **LIVE TRADING CONNECTED** - Balance: ${status.get('balance', 0):,.2f}")
        else:
            lines.append("⚠️ Paper trading mode (Hyperliquid not connected)")
        
        # Auto-trading status
        auto = status.get("auto_trading", {})
        if auto.get("running"):
            lines.append(f"🤖 Auto-trading: **RUNNING** ({auto.get('strategy')})")
        else:
            lines.append("💤 Auto-trading: **OFF**")
        
        # Current positions
        positions = status.get("positions", [])
        if positions:
            lines.append(f"\n**Open Positions ({len(positions)}):**")
            for p in positions[:3]:  # Limit to 3
                pnl = float(p.get("pnl", 0))
                emoji = "📈" if pnl >= 0 else "📉"
                lines.append(f"  • {p.get('symbol')}: {p.get('direction', 'long').upper()} {emoji} ${pnl:+,.2f}")
        
        # Current opportunities
        opps = status.get("opportunities", [])
        if opps:
            lines.append(f"\n**Active Signals ({len(opps)}):**")
            for o in opps[:3]:
                lines.append(f"  • {o.get('symbol')}: **{o.get('action')}** ({o.get('confidence')}% confidence)")
        
        lines.append("\n*You can execute trades, check signals, enable auto-trading, and manage positions.*")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"\n\n## 📊 Trading Context\n⚠️ Trading status unavailable: {e}"


async def handle_trading_message(message: str) -> str:
    """
    Handle a trading-related message.
    
    Returns:
        Response message or empty string if not trading-related
    """
    if not is_trading_related(message):
        return ""
    
    intent, params = parse_trading_intent(message)
    
    if intent:
        return await execute_trading_command(intent, params)
    
    return ""

# ========== ADAPTIVE INTELLIGENCE ==========
from .adaptive_intelligence import (
    get_adaptive_intelligence,
    AdaptiveIntelligence,
    AdaptiveConfig,
    start_adaptive_trading,
    stop_adaptive_trading
)

from .probability_scalper import (
    get_scalper,
    ProbabilityScalper,
    ScalperConfig,
    start_probability_scalping,
    stop_probability_scalping,
    get_scalper_status
)


