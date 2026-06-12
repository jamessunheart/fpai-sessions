#!/usr/bin/env python3
"""
ARIA TELEGRAM TRADING COMMANDS
==============================

Trading execution commands for Telegram.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("aria.telegram.trading")


@dataclass
class TradingCommandResult:
    """Result of a trading command."""
    text: str
    success: bool = True
    needs_approval: bool = False
    approval_id: Optional[str] = None


async def handle_trade(args: str) -> TradingCommandResult:
    """
    Handle /trade command.
    
    Usage:
        /trade long BTC 100      - Long BTC with $100
        /trade short ETH 50 2x   - Short ETH with $50 at 2x leverage
    """
    try:
        from trading.executor import get_executor, MAX_POSITION_SIZE_USD, MAX_LEVERAGE
    except ImportError:
        from ..trading.executor import get_executor, MAX_POSITION_SIZE_USD, MAX_LEVERAGE
    
    if not args:
        return TradingCommandResult(
            text=f"""**📈 Trade Command**

Usage:
`/trade <side> <symbol> <amount> [leverage]`

Examples:
• `/trade long BTC 100` - Long BTC with $100
• `/trade short ETH 50` - Short ETH with $50
• `/trade long SOL 100 3x` - Long SOL $100 at 3x

Limits:
• Max position: ${MAX_POSITION_SIZE_USD}
• Max leverage: {MAX_LEVERAGE}x

⚠️ All trades require approval.""",
            success=True
        )
    
    parts = args.split()
    if len(parts) < 3:
        return TradingCommandResult(
            text="❌ Usage: `/trade <side> <symbol> <amount> [leverage]`\n\nExample: `/trade long BTC 100`",
            success=False
        )
    
    side = parts[0].lower()
    symbol = parts[1].upper()
    
    try:
        amount = float(parts[2].replace("$", ""))
    except ValueError:
        return TradingCommandResult(
            text=f"❌ Invalid amount: {parts[2]}",
            success=False
        )
    
    leverage = 1
    if len(parts) > 3:
        try:
            leverage = int(parts[3].replace("x", "").replace("X", ""))
        except ValueError:
            pass
    
    if side not in ["long", "short"]:
        return TradingCommandResult(
            text=f"❌ Side must be 'long' or 'short', got: {side}",
            success=False
        )
    
    # Request the trade (requires approval)
    executor = get_executor()
    
    # Check safety first
    safety = await executor.check_trade_safety(symbol, amount, leverage)
    
    if not safety["safe"]:
        issues = "\n".join(f"• {i}" for i in safety["issues"])
        return TradingCommandResult(
            text=f"❌ **Trade Blocked**\n\n{issues}",
            success=False
        )
    
    trade = await executor.request_trade(symbol, side, amount, leverage)
    
    warnings = ""
    if safety["warnings"]:
        warnings = "\n\n⚠️ Warnings:\n" + "\n".join(f"• {w}" for w in safety["warnings"])
    
    side_emoji = "📈" if side == "long" else "📉"
    
    return TradingCommandResult(
        text=f"""**📋 Trade Pending Approval**

{side_emoji} **{side.upper()} {symbol}**
💰 Size: ${amount:.2f}
⚡ Leverage: {leverage}x

Current exposure: ${safety["current_exposure"]:.2f}{warnings}

To execute: `/approve {trade.id}`
To cancel: `/cancel_trade {trade.id}`""",
        success=True,
        needs_approval=True,
        approval_id=trade.id
    )


async def handle_close(args: str) -> TradingCommandResult:
    """
    Handle /close command.
    
    Usage:
        /close BTC     - Close BTC position
        /close all     - Close all positions (EMERGENCY)
    """
    try:
        from trading.executor import get_executor
    except ImportError:
        from ..trading.executor import get_executor
    
    if not args:
        return TradingCommandResult(
            text="""**🔒 Close Position**

Usage:
• `/close BTC` - Close BTC position
• `/close ETH` - Close ETH position
• `/close all` - Emergency close ALL positions

Use `/positions` to see open positions.""",
            success=True
        )
    
    symbol = args.strip().upper()
    executor = get_executor()
    
    if symbol == "ALL":
        # Emergency stop
        result = await executor.emergency_stop()
        if result["success"]:
            return TradingCommandResult(
                text=f"🛑 **Emergency Stop Complete**\n\nClosed {result['closed']} position(s)",
                success=True
            )
        else:
            errors = "\n".join(f"• {e}" for e in result["errors"])
            return TradingCommandResult(
                text=f"⚠️ **Partial Close**\n\nClosed: {result['closed']}\nErrors:\n{errors}",
                success=False
            )
    
    result = await executor.close_position(symbol)
    
    if result.success:
        return TradingCommandResult(
            text=f"✅ **Position Closed**\n\n{symbol} position has been closed.",
            success=True
        )
    else:
        return TradingCommandResult(
            text=f"❌ **Close Failed**\n\n{result.error}",
            success=False
        )


async def handle_positions(args: str) -> TradingCommandResult:
    """Handle /positions command."""
    try:
        from trading.executor import get_executor
    except ImportError:
        from ..trading.executor import get_executor
    
    executor = get_executor()
    positions = await executor.get_positions()
    balance = await executor.get_balance()
    
    if not positions:
        return TradingCommandResult(
            text=f"""**📊 No Open Positions**

Balance: ${balance:.2f}

Use `/trade long BTC 100` to open a position.""",
            success=True
        )
    
    lines = [f"**📊 Open Positions** ({len(positions)})\n"]
    
    total_pnl = 0
    for p in positions:
        symbol = p.get("symbol", "???")
        side = p.get("side", "?")
        size = float(p.get("size", 0))
        entry = float(p.get("entry_price", 0))
        pnl = float(p.get("pnl", 0))
        pnl_pct = float(p.get("pnl_percent", 0))
        total_pnl += pnl
        
        emoji = "📈" if pnl >= 0 else "📉"
        side_emoji = "🟢" if side == "long" else "🔴"
        
        lines.append(
            f"{side_emoji} **{symbol}** {side.upper()}\n"
            f"   Size: {size:.4f} @ ${entry:.2f}\n"
            f"   {emoji} P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)"
        )
    
    lines.append(f"\n**Total P&L:** ${total_pnl:+.2f}")
    lines.append(f"**Balance:** ${balance:.2f}")
    
    return TradingCommandResult(
        text="\n".join(lines),
        success=True
    )


async def handle_balance(args: str) -> TradingCommandResult:
    """Handle /balance command."""
    try:
        from trading.executor import get_executor
    except ImportError:
        from ..trading.executor import get_executor
    
    executor = get_executor()
    summary = await executor.get_account_summary()
    
    return TradingCommandResult(
        text=f"""**💰 Account Summary**

Balance: **${summary["balance"]:.2f}**
Positions: {summary["positions"]}
Exposure: ${summary["exposure"]:.2f}
Available: ${summary["available"]:.2f}

Total P&L: ${summary["total_pnl"]:+.2f}""",
        success=True
    )


async def handle_cancel_trade(trade_id: str) -> TradingCommandResult:
    """Cancel a pending trade."""
    try:
        from trading.executor import get_executor
    except ImportError:
        from ..trading.executor import get_executor
    
    if not trade_id:
        return TradingCommandResult(
            text="Usage: `/cancel_trade <id>`",
            success=False
        )
    
    executor = get_executor()
    if executor.cancel_trade(trade_id):
        return TradingCommandResult(
            text=f"✅ Trade `{trade_id}` cancelled.",
            success=True
        )
    else:
        return TradingCommandResult(
            text=f"❌ Trade `{trade_id}` not found.",
            success=False
        )


