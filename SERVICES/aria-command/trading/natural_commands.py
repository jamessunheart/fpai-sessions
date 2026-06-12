#!/usr/bin/env python3
"""
🗣️ NATURAL LANGUAGE TRADING COMMANDS
=====================================

Allows Aria to understand and execute trading commands in natural language.

Examples:
- "What's the current SOL signal?"
- "Enable auto-trading with $5000"
- "How are my positions doing?"
- "Stop all trading"
- "Go long SOL with $500"
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("aria.trading.natural")


def parse_trading_intent(message: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Parse natural language message for trading intent.
    
    Returns:
        (intent, parameters) or (None, {}) if not a trading message
    
    Intents:
        - get_signals: "What's the signal for SOL?"
        - get_status: "How's my trading?"
        - enable_auto: "Enable auto-trading"
        - disable_auto: "Stop auto-trading"
        - open_position: "Go long SOL with $500"
        - close_position: "Close my SOL position"
        - emergency_stop: "Stop all trading NOW"
        - get_positions: "What positions do I have?"
        - get_balance: "What's my balance?"
        - get_performance: "How am I doing overall?"
    """
    msg_lower = message.lower().strip()
    
    # Emergency stop - highest priority
    if any(phrase in msg_lower for phrase in [
        "stop all trading", "emergency stop", "close everything",
        "panic", "stop everything", "shut it down"
    ]):
        return "emergency_stop", {}
    
    # Signal queries
    if any(word in msg_lower for word in ["signal", "clarity", "opportunity", "setup"]):
        symbol = _extract_symbol(msg_lower)
        return "get_signals", {"symbol": symbol}
    
    # Status queries
    if any(phrase in msg_lower for phrase in [
        "how's my trading", "trading status", "what's happening",
        "how are things", "status update", "trading update"
    ]):
        return "get_status", {}
    
    # Enable auto-trading
    if any(phrase in msg_lower for phrase in [
        "enable auto", "start auto", "turn on auto",
        "enable signal shark", "start signal shark",
        "activate auto", "auto trade on"
    ]):
        capital = _extract_amount(message)
        strategy = _extract_strategy(msg_lower)
        mode = "approval" if "approval" in msg_lower else "automatic"
        return "enable_auto", {
            "capital": capital or 1000.0,
            "strategy": strategy or "signal-shark",
            "mode": mode
        }
    
    # Disable auto-trading
    if any(phrase in msg_lower for phrase in [
        "disable auto", "stop auto", "turn off auto",
        "pause trading", "stop trading", "auto trade off"
    ]) and "emergency" not in msg_lower:
        return "disable_auto", {}
    
    # Open position
    if any(word in msg_lower for word in ["long", "short", "buy", "sell"]):
        direction = "long" if any(w in msg_lower for w in ["long", "buy"]) else "short"
        symbol = _extract_symbol(msg_lower)
        amount = _extract_amount(message)
        leverage = _extract_leverage(msg_lower)
        
        if symbol:
            return "open_position", {
                "symbol": symbol,
                "direction": direction,
                "amount": amount or 100.0,
                "leverage": leverage or 1
            }
    
    # Close position
    if any(phrase in msg_lower for phrase in [
        "close position", "close my", "exit position", "exit my",
        "take profit", "stop loss"
    ]):
        symbol = _extract_symbol(msg_lower)
        return "close_position", {"symbol": symbol}
    
    # Get positions
    if any(phrase in msg_lower for phrase in [
        "positions", "what do i have", "open trades", "my trades"
    ]):
        return "get_positions", {}
    
    # Get balance (unified or trading-specific)
    if any(phrase in msg_lower for phrase in [
        "full balance", "all balance", "unified balance", 
        "show my balance", "my balances", "total balance"
    ]):
        return "get_unified_balance", {}
    
    if any(word in msg_lower for word in ["balance", "equity", "account"]):
        return "get_balance", {}
    
    # Performance
    if any(phrase in msg_lower for phrase in [
        "how am i doing", "performance", "win rate", "pnl", "profit"
    ]):
        return "get_performance", {}
    
    # Connect Hyperliquid
    if "hyperliquid" in msg_lower and any(w in msg_lower for w in ["connect", "setup", "configure"]):
        return "setup_hyperliquid", {}
    
    # Analytics / Performance
    if any(phrase in msg_lower for phrase in [
        "trading performance", "analytics", "how am i doing",
        "win rate", "stats", "statistics", "track record"
    ]):
        days = 30
        if "week" in msg_lower:
            days = 7
        elif "month" in msg_lower:
            days = 30
        elif "year" in msg_lower:
            days = 365
        return "get_analytics", {"days": days}
    
    # Journal / Lessons
    if any(phrase in msg_lower for phrase in [
        "journal", "lessons", "coaching", "insights",
        "what have i learned", "trading lessons"
    ]):
        return "get_journal", {}
    
    # Patterns
    if any(phrase in msg_lower for phrase in [
        "patterns", "what works", "best trades", "worst trades"
    ]):
        return "get_patterns", {}
    
    # Strategy comparison
    if any(phrase in msg_lower for phrase in [
        "compare strategies", "which strategy", "best strategy",
        "strategy comparison", "recommend strategy"
    ]):
        return "compare_strategies", {}
    
    # Strategy optimization
    if any(phrase in msg_lower for phrase in [
        "optimize", "improve strategy", "tune parameters",
        "optimize trading"
    ]):
        return "optimize_strategy", {}
    
    # List strategies
    if any(phrase in msg_lower for phrase in [
        "strategies", "available strategies", "list strategies"
    ]):
        return "list_strategies", {}
    
    # Enable auto-trading
    if any(phrase in msg_lower for phrase in [
        "start auto", "enable auto", "auto trade", "manage my",
        "trade for me", "auto-trade", "autopilot"
    ]):
        # Extract amount if specified
        import re
        amount_match = re.search(r'\$?(\d+)', message)
        max_position = float(amount_match.group(1)) if amount_match else 100.0
        return "start_auto_trading", {"max_position": max_position}
    
    # Stop auto-trading
    if any(phrase in msg_lower for phrase in [
        "stop auto", "disable auto", "stop trading for me",
        "turn off auto", "pause auto"
    ]):
        return "stop_auto_trading", {}
    
    # Emergency stop
    if any(phrase in msg_lower for phrase in [
        "emergency stop", "stop everything", "close all", "panic"
    ]):
        return "emergency_stop", {}
    
    
    return None, {}


def _extract_symbol(text: str) -> Optional[str]:
    """Extract trading symbol from text."""
    symbols = ["sol", "btc", "eth", "xrp", "bnb", "ada", "doge", "sui", "pepe", "wif"]
    text_lower = text.lower()
    
    for sym in symbols:
        if sym in text_lower:
            return sym.upper()
    
    # Try pattern matching
    match = re.search(r'\b([A-Z]{2,5})\b', text)
    if match and match.group(1) in [s.upper() for s in symbols]:
        return match.group(1)
    
    return None


def _extract_amount(text: str) -> Optional[float]:
    """Extract dollar amount from text."""
    # Match patterns like $500, $1000, 500 dollars, 1k, 5000
    patterns = [
        r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',  # $500, $1,000.00
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:dollars?|usd)',  # 500 dollars
        r'(\d+)k\b',  # 5k
        r'(\d+(?:,\d{3})*)\s*(?:with|using|allocate)',  # 500 with
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            amount_str = match.group(1).replace(",", "")
            if 'k' in text.lower() and pattern == patterns[2]:
                return float(amount_str) * 1000
            return float(amount_str)
    
    # Simple number extraction as fallback
    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
    for num in numbers:
        val = float(num)
        if 50 <= val <= 100000:  # Reasonable trading range
            return val
    
    return None


def _extract_leverage(text: str) -> Optional[int]:
    """Extract leverage from text."""
    # Match patterns like 2x, 3x leverage, 5 times
    patterns = [
        r'(\d+)\s*x\b',  # 2x
        r'(\d+)\s*times',  # 3 times
        r'leverage\s*(\d+)',  # leverage 5
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            lev = int(match.group(1))
            return min(lev, 20)  # Cap at 20x
    
    return None


def _extract_strategy(text: str) -> Optional[str]:
    """Extract strategy name from text."""
    strategies = {
        "signal shark max": "signal-shark-max",
        "shark max": "signal-shark-max",
        "signal shark": "signal-shark",
        "shark": "signal-shark",
        "magnet": "magnet-hunter",
        "conservative": "conservative"
    }
    
    for name, code in strategies.items():
        if name in text.lower():
            return code
    
    return None


async def execute_trading_command(intent: str, params: Dict[str, Any]) -> str:
    """
    Execute a parsed trading command.
    
    Returns:
        Response message for the user
    """
    from .live_bridge import get_live_trading_bridge, get_trading_status
    
    bridge = get_live_trading_bridge()
    
    if intent == "emergency_stop":
        result = await bridge.emergency_stop()
        if result.get("success"):
            return "🛑 **EMERGENCY STOP COMPLETE**\n\nAll positions closed and auto-trading disabled."
        else:
            return f"⚠️ Emergency stop had issues: {result.get('message')}"
    
    elif intent == "get_signals":
        signals = await bridge.get_current_signals()
        symbol = params.get("symbol")
        
        if symbol and f"{symbol}/USDT" in signals:
            data = signals[f"{symbol}/USDT"]
            action = data.get("recommended_action", "WAIT")
            emoji = "📈" if action == "LONG" else "📉" if action == "SHORT" else "⏸️"
            
            # Handle None values gracefully
            price = data.get('price') or 0
            target = data.get('primary_target') or 0
            stop = data.get('stop_loss') or 0
            rr = data.get('risk_reward') or 0
            confidence = data.get('clarity_score') or 0
            
            return f"""**{emoji} {symbol} Signal**

• Action: **{action}**
• Price: ${price:,.2f}
• Target: ${target:,.2f}
• Stop: ${stop:,.2f}
• R:R: {rr:.2f}
• Confidence: {confidence:.0f}%"""
        
        else:
            # Return all signals
            lines = ["**📊 Current Signals**\n"]
            for sym, data in signals.items():
                if isinstance(data, dict):
                    action = data.get("recommended_action", "WAIT")
                    emoji = "📈" if action == "LONG" else "📉" if action == "SHORT" else "⏸️"
                    price = data.get('price') or 0
                    lines.append(f"{emoji} **{sym.replace('/USDT', '')}**: {action} @ ${price:,.2f}")
            
            return "\n".join(lines)
    
    elif intent == "get_status":
        # Try live Hyperliquid first
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            if hl.is_connected:
                return hl.format_status()
        except Exception as e:
            pass  # Fall back to paper trading status
        
        # Fallback to paper status
        status = await get_trading_status()
        
        mode_emoji = "🟢" if status.get("live_connected") else "🔴"
        auto_emoji = "🤖" if status.get("auto_trading", {}).get("running") else "💤"
        
        response = f"""**📊 Trading Status**

{mode_emoji} Mode: **{status.get('mode', 'paper').upper()}**
💰 Balance: **${status.get('balance', 0):,.2f}**
{auto_emoji} Auto-Trading: **{'Running' if status.get('auto_trading', {}).get('running') else 'Off'}**"""
        
        if status.get("positions"):
            response += f"\n📈 Positions: **{len(status['positions'])}** open"
        
        if status.get("opportunities"):
            response += f"\n🎯 Opportunities: **{len(status['opportunities'])}** signals"
            for opp in status["opportunities"][:3]:
                response += f"\n   • {opp['symbol']}: {opp['action']}"
        
        return response
    
    elif intent == "enable_auto":
        # Use local AGGRESSIVE auto-trader
        from .auto_trader import start_auto_trading, get_auto_trader
        capital = params.get("capital", 500.0)  # Default to full balance
        
        # AGGRESSIVE MODE: Use most of capital, higher confidence bar
        result = await start_auto_trading(
            max_position=capital,  # Full position
            min_confidence=80.0,   # Higher bar
            symbols=["SOL", "BTC", "ETH"]
        )
        
        if result.get("success"):
            status = result.get("status", {})
            trader = get_auto_trader()
            return f"""🦈 **PROBABILITY HUNTER ACTIVATED**

I'm now actively hunting for high-probability trades!

**Strategy:**
• Only trade **80%+** confidence signals
• Full position commitment on best signals
• Quick rotation to better opportunities
• {status.get('config', {}).get('leverage', 3.0)}x leverage

**Account:**
• Balance: **${status.get('balance', 0):,.2f}**
• Current positions: **{status.get('positions', 0)}**
• Win Rate: **{trader.win_rate:.0f}%**

🎯 Hunting for optimal trades... Say "stop auto trading" to disable."""
        else:
            return f"❌ Could not start auto-trading: {result.get('error')}"
    
    elif intent == "disable_auto":
        from .auto_trader import stop_auto_trading
        result = await stop_auto_trading()
        if result.get("success"):
            return "⏹️ **Auto-Trading Disabled**\n\nI've paused automatic trading. Existing positions remain open."
        else:
            return f"❌ Failed to disable: {result.get('message')}"
    
    elif intent == "open_position":
        symbol = params.get("symbol")
        direction = params.get("direction")
        amount = params.get("amount", 100)
        leverage = params.get("leverage", 1)
        
        if not symbol:
            return "❓ What symbol would you like to trade? (e.g., SOL, BTC, ETH)"
        
        # For now, queue for approval
        return f"""📋 **Trade Confirmation Required**

{("📈" if direction == "long" else "📉")} **{direction.upper()} {symbol}**
💰 Size: ${amount:,.0f}
⚡ Leverage: {leverage}x

To execute this trade, please:
1. Go to the WhaleTrack dashboard
2. Or say "confirm trade" to proceed

Note: For live trading, ensure Hyperliquid is connected."""
    
    elif intent == "close_position":
        symbol = params.get("symbol")
        
        if not symbol:
            # Close all
            result = await bridge.emergency_stop()
            return "🔒 All positions closed."
        else:
            result = await bridge.close_position(symbol)
            if result.get("success"):
                return f"✅ Closed {symbol} position"
            else:
                return f"❌ {result.get('message')}"
    
    elif intent == "get_positions":
        # Try live Hyperliquid first
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            if hl.is_connected:
                positions = hl.get_positions()
                
                if not positions:
                    return "📊 **No open positions**\n\nYou're currently flat on Hyperliquid."
                
                lines = [f"**📊 LIVE Positions ({len(positions)})**\n"]
                total_pnl = 0
                
                for p in positions:
                    pnl = p.get("unrealized_pnl", 0)
                    total_pnl += pnl
                    emoji = "📈" if pnl >= 0 else "📉"
                    side_emoji = "🟢" if p.get("side") == "long" else "🔴"
                    
                    lines.append(f"{side_emoji} **{p.get('symbol')}** {p.get('side', '?').upper()}")
                    lines.append(f"   Size: {p.get('size', 0):.4f} @ ${p.get('entry_price', 0):,.2f}")
                    lines.append(f"   {emoji} uPnL: ${pnl:+,.2f} ({p.get('pnl_percent', 0):+.2f}%)")
                
                lines.append(f"\n**Total uPnL: ${total_pnl:+,.2f}**")
                
                return "\n".join(lines)
        except Exception as e:
            pass  # Fall back
        
        # Fallback to paper positions
        positions = await bridge.get_positions()
        
        if not positions:
            return "📊 **No open positions**\n\nYou're currently flat."
        
        lines = [f"**📊 Open Positions ({len(positions)})**\n"]
        total_pnl = 0
        
        for p in positions:
            pnl = float(p.get("pnl", 0))
            total_pnl += pnl
            emoji = "📈" if pnl >= 0 else "📉"
            side_emoji = "🟢" if p.get("direction") == "long" else "🔴"
            
            lines.append(f"{side_emoji} **{p.get('symbol', '???')}** {p.get('direction', '?').upper()}")
            lines.append(f"   {emoji} P&L: ${pnl:+,.2f}")
        
        lines.append(f"\n**Total P&L: ${total_pnl:+,.2f}**")
        
        return "\n".join(lines)
    
    elif intent == "get_unified_balance":
        # Get unified view across all services
        try:
            from wallet import get_unified_balance_summary
            user_id = params.get("user_id", "default")
            return await get_unified_balance_summary(user_id)
        except Exception as e:
            logger.warning(f"Failed to get unified balance: {e}")
            # Fall back to trading balance
            intent = "get_balance"
    
    elif intent == "get_balance":
        # Trading-specific balance (Hyperliquid)
        try:
            from .hyperliquid_live import get_hyperliquid
            hl = get_hyperliquid()
            
            if hl.is_connected:
                state = hl.get_account_state()
                return f"""💰 **Trading Account Balance**

🟢 **Hyperliquid Connected**
💰 Account Value: **${state.get('account_value', 0):,.2f}**
💵 Withdrawable: **${state.get('withdrawable', 0):,.2f}**
📊 Margin Used: **${state.get('total_margin', 0):,.2f}**

_Use "full balance" for unified view across all services._"""
        except Exception as e:
            pass
        
        # Fallback
        status = await bridge.get_live_status()
        return f"""💰 **Account Balance**

Balance: **${status.get('balance', 0):,.2f}**
Equity: **${status.get('equity', 0):,.2f}**
Withdrawable: **${status.get('withdrawable', 0):,.2f}**
Connected: **{'Yes' if status.get('connected') else 'No'}**

_Use "full balance" for unified view across all services._"""
    
    elif intent == "get_performance":
        # Use local analytics engine
        from .analytics import get_analytics
        analytics = get_analytics()
        metrics = analytics.get_performance(days=30)
        
        if metrics.total_trades == 0:
            return "📊 **No trading data yet**\n\nStart trading to see performance metrics!"
        
        streak_emoji = "🔥" if metrics.current_streak > 0 else "❄️"
        
        return f"""📊 **Trading Performance (30 Days)**

**Overall:**
• Win Rate: **{metrics.win_rate:.1f}%** ({metrics.winning_trades}W / {metrics.losing_trades}L)
• Total P&L: **${metrics.total_pnl:+,.2f}**
• {streak_emoji} Streak: **{abs(metrics.current_streak)} {'wins' if metrics.current_streak > 0 else 'losses'}**

**Risk Metrics:**
• Profit Factor: **{metrics.profit_factor:.2f}**
• Sharpe Ratio: **{metrics.sharpe_ratio:.2f}**
• Max Drawdown: **${metrics.max_drawdown:,.2f}**

**Best:**
• Symbol: **{metrics.best_symbol}**
• Strategy: **{metrics.best_strategy}**"""
    
    elif intent == "setup_hyperliquid":
        return """🔑 **Hyperliquid Setup**

To connect live trading:

1. Go to [Hyperliquid](https://app.hyperliquid.xyz)
2. Connect your wallet
3. Go to Settings → API → Generate Key
4. Copy your API secret (private key)

Then say: "Connect Hyperliquid with key <your-key> account <wallet-address>"

⚠️ Never share your API key publicly!"""
    
    elif intent == "get_analytics":
        from .analytics import get_analytics
        analytics = get_analytics()
        days = params.get("days", 30)
        return analytics.format_performance_report(days=days)
    
    elif intent == "get_journal":
        from .journal import get_journal
        journal = get_journal()
        return journal.get_coaching_insights()
    
    elif intent == "get_patterns":
        from .analytics import get_analytics
        analytics = get_analytics()
        patterns = analytics.analyze_patterns()
        
        if not patterns:
            return "📊 **No patterns detected yet**\n\nNeed more trades to identify patterns."
        
        lines = ["📊 **TRADING PATTERNS**\n"]
        for p in patterns:
            win_pct = p.get("win_rate", 0)
            emoji = "🟢" if win_pct >= 60 else "🟡" if win_pct >= 50 else "🔴"
            lines.append(f"{emoji} **{p['name']}:** {p['description']}")
            lines.append(f"   Win Rate: {win_pct:.0f}% | Avg P&L: ${p.get('avg_pnl', 0):+,.2f} | {p.get('occurrences', 0)} trades")
        
        return "\n".join(lines)
    
    elif intent == "compare_strategies":
        from .optimizer import get_optimizer
        optimizer = get_optimizer()
        comparisons = await optimizer.compare_strategies(days=30)
        recommendation = await optimizer.recommend_strategy()
        
        report = optimizer.format_comparison_report(comparisons)
        report += f"\n\n🎯 **Recommendation:** {recommendation['recommended'].replace('-', ' ').title()}"
        report += f"\n_{recommendation['reason']}_"
        
        return report
    
    elif intent == "optimize_strategy":
        from .optimizer import get_optimizer
        from .analytics import get_analytics
        
        optimizer = get_optimizer()
        analytics = get_analytics()
        
        # Get trade history
        trades = analytics.get_trades(days=30, limit=100)
        trade_dicts = [
            {"symbol": t.symbol, "pnl": t.pnl, "confidence": t.confidence, "strategy": t.strategy}
            for t in trades
        ]
        
        result = optimizer.optimize_parameters("signal-shark", trade_dicts)
        
        if not result.get("optimized"):
            return f"🎯 **No optimizations needed**\n\n{result.get('message')}"
        
        lines = ["🎯 **STRATEGY OPTIMIZATION**\n"]
        for opt in result.get("optimizations", []):
            lines.append(f"• **{opt['parameter']}**: {opt['current']} → {opt['suggested']}")
            lines.append(f"  _{opt['reason']}_")
        
        return "\n".join(lines)
    
    elif intent == "list_strategies":
        from .optimizer import STRATEGIES
        
        lines = ["📋 **AVAILABLE STRATEGIES**\n"]
        for code, config in STRATEGIES.items():
            lines.append(f"**{config.name}** (`{code}`)")
            lines.append(f"   • Confidence: ≥{config.min_confidence}%")
            lines.append(f"   • Leverage: {config.leverage}x")
            lines.append(f"   • Position: {config.position_size_pct}%")
            lines.append(f"   • Symbols: {', '.join(config.symbols)}")
            lines.append("")
        
        return "\n".join(lines)
    
    elif intent == "start_auto_trading":
        from .auto_trader import start_auto_trading, get_auto_trader
        max_pos = params.get("max_position", 500.0)  # Default aggressive
        result = await start_auto_trading(
            max_position=max_pos,
            min_confidence=80.0,  # Higher bar
            symbols=["SOL", "BTC", "ETH"]
        )
        
        if result.get("success"):
            status = result.get("status", {})
            trader = get_auto_trader()
            return f"""🦈 **PROBABILITY HUNTER ACTIVATED**

I'm now actively hunting for high-probability trades!

**Strategy:**
• Only trade **80%+** confidence signals
• Max position: **${max_pos:.0f}**
• {status.get('config', {}).get('leverage', 3.0)}x leverage

**Account:**
• Balance: **${status.get('balance', 0):,.2f}**
• Positions: **{status.get('positions', 0)}**
• Win Rate: **{trader.win_rate:.0f}%**

🎯 Hunting... Say "stop auto trading" to disable."""
        else:
            return f"❌ Could not start auto-trading: {result.get('error')}"
    
    elif intent == "stop_auto_trading":
        from .auto_trader import stop_auto_trading
        result = await stop_auto_trading()
        
        if result.get("success"):
            return "🛑 **Auto-Trading STOPPED**\n\nI've stopped automatic trading. Your positions remain open."
        else:
            return f"❌ Error: {result.get('error')}"
    
    elif intent == "emergency_stop":
        from .auto_trader import emergency_stop
        result = await emergency_stop()
        
        return f"""🚨 **EMERGENCY STOP EXECUTED**

• Auto-trading: **DISABLED**
• Positions closed: **{result.get('closed', 0)}**

All trading activity halted."""
    
    elif intent == "auto_trading_status":
        from .auto_trader import get_auto_trading_status
        status = get_auto_trading_status()
        
        if status.get("running"):
            emoji = "🟢"
            state = "ACTIVE"
        elif status.get("enabled"):
            emoji = "🟡"
            state = "ENABLED (paused)"
        else:
            emoji = "🔴"
            state = "DISABLED"
        
        return f"""{emoji} **Auto-Trading: {state}**

**Account:**
• Balance: **${status.get('balance', 0):,.2f}**
• Open positions: **{status.get('positions', 0)}**
• Daily P&L: **${status.get('daily_pnl', 0):+,.2f}**

**Config:**
• Max position: **${status.get('config', {}).get('max_position_usd', 0):.0f}**
• Min confidence: **{status.get('config', {}).get('min_confidence', 0)}%**"""
    
    return "I didn't understand that trading command. Try asking about signals, positions, or say 'trading status'."


def is_trading_related(message: str) -> bool:
    """Check if message is trading-related."""
    trading_keywords = [
        "trade", "trading", "signal", "position", "long", "short",
        "buy", "sell", "pnl", "profit", "loss", "balance",
        "sol", "btc", "eth", "crypto", "hyperliquid", "auto-trad",
        "signal shark", "stop loss", "take profit", "leverage",
        # Analytics
        "performance", "win rate", "analytics", "stats", "how am i doing",
        # Patterns
        "pattern", "what works",
        # Strategies
        "strateg", "compare", "optimize", "recommend",
        # Journal
        "journal", "lesson", "coaching"
    ]
    
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in trading_keywords)

