"""
WALLET COMMANDS
================

Telegram command handlers for wallet and pool operations.

Commands:
- /balance - Check wallet balance
- /pool - See pool status
- /poolopt [in/out] - Opt in/out of trading pool
- /returns - See trading return history
- /gift @user amount - Send credits
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger("aria.telegram.wallet")

# Telegram config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
JAMES_TELEGRAM_ID = int(os.getenv("SUNHEART_CHAT_ID", "1759822075"))


async def handle_balance_command(telegram_id: int) -> str:
    """
    Handle /balance command.
    
    Shows user's wallet balance and pool status.
    """
    from membership import get_member_db, get_wallet
    
    db = get_member_db()
    member = db.get_member_by_telegram(telegram_id)
    
    if not member:
        return (
            "❌ You're not a member yet.\n\n"
            "Start a conversation with me to join the Fellowship!"
        )
    
    wallet = get_wallet(member.id)
    balance = wallet.get_balance()
    
    lines = [
        "💳 **Your Wallet**\n",
        f"Available: **{balance['available']:.2f} UC**",
    ]
    
    if balance['pool'] > 0:
        lines.append(f"In Pool: **{balance['pool']:.2f} UC** ({balance['pool_share']:.1%} share)")
        lines.append(f"\n**Total: {balance['total']:.2f} UC**")
    else:
        lines.append("\n_Not in trading pool. Use `/poolopt in` to join._")
    
    return "\n".join(lines)


async def handle_pool_command(telegram_id: int) -> str:
    """
    Handle /pool command.
    
    Shows pool status and user's share.
    """
    from membership import get_member_db
    from trading.pool_manager import get_pool_manager
    
    db = get_member_db()
    member = db.get_member_by_telegram(telegram_id)
    
    if not member:
        return "❌ You're not a member yet."
    
    manager = get_pool_manager()
    
    # Get pool status
    pool_status = await manager.get_pool_status()
    
    # Get member's status
    member_status = await manager.get_member_status(member.id)
    
    lines = [
        "💰 **Conscious Wealth Pool**\n",
        f"Total Pool: {pool_status.total_credits:.2f} UC",
        f"Members: {pool_status.member_count}",
        f"Cumulative P&L: {pool_status.cumulative_pnl:+.2f} UC",
    ]
    
    if pool_status.aria_balance > 0:
        lines.append(f"Aria's Balance: {pool_status.aria_balance:.2f} UC")
    
    lines.append("\n---\n")
    
    if member_status.pool_credits > 0:
        lines.extend([
            "**Your Share:**",
            f"Credits: {member_status.pool_credits:.2f} UC",
            f"Share: {member_status.pool_share:.1%}",
            f"Total Earned: {member_status.total_earned:+.2f} UC",
        ])
        
        if member_status.share_value != member_status.pool_credits:
            diff = member_status.share_value - member_status.pool_credits
            emoji = "📈" if diff > 0 else "📉"
            lines.append(f"Current Value: {member_status.share_value:.2f} UC ({emoji})")
    else:
        lines.append("_You're not in the pool yet._\n")
        lines.append("Use `/poolopt in` to join!")
    
    return "\n".join(lines)


async def handle_poolopt_command(telegram_id: int, action: str, amount: Optional[float] = None) -> str:
    """
    Handle /poolopt command.
    
    Args:
        telegram_id: User's Telegram ID
        action: "in" or "out"
        amount: Optional amount (defaults to all)
    """
    from membership import get_member_db, get_wallet
    from membership.onboarding import get_onboarding, TRADING_SUMMARY
    
    db = get_member_db()
    member = db.get_member_by_telegram(telegram_id)
    
    if not member:
        return "❌ You're not a member yet."
    
    wallet_obj = get_wallet(member.id)
    balance = wallet_obj.get_balance()
    
    action = action.lower().strip()
    
    if action == "in":
        # Check if agreed to trading
        if not member.trading_agreed_at:
            # Show trading agreement
            return (
                "To join the trading pool, please review and accept the terms:\n\n"
                + TRADING_SUMMARY +
                "\n\nReply with `/poolopt accept` to agree and join."
            )
        
        # Opt in
        if amount is None:
            amount = balance["available"]
        
        if amount <= 0:
            return "❌ You have no available credits to add."
        
        if amount > balance["available"]:
            return f"❌ You only have {balance['available']:.2f} UC available."
        
        result = wallet_obj.opt_into_pool(amount)
        return f"{'✅' if result.success else '❌'} {result.message}"
    
    elif action == "out":
        if balance["pool"] <= 0:
            return "❌ You have no credits in the pool."
        
        if amount is None:
            amount = balance["pool"]
        
        if amount > balance["pool"]:
            return f"❌ You only have {balance['pool']:.2f} UC in the pool."
        
        result = wallet_obj.opt_out_of_pool(amount)
        return f"{'✅' if result.success else '❌'} {result.message}"
    
    elif action == "accept":
        # Accept trading terms
        db.agree_to_trading(member.id)
        
        # Then opt in
        amount = balance["available"]
        if amount > 0:
            result = wallet_obj.opt_into_pool(amount)
            return (
                f"✅ Trading terms accepted!\n\n"
                f"{result.message}"
            )
        else:
            return (
                "✅ Trading terms accepted!\n\n"
                "You have no credits to add yet. When you receive credits, "
                "use `/poolopt in` to add them to the pool."
            )
    
    else:
        return (
            "❌ Invalid action.\n\n"
            "Usage:\n"
            "• `/poolopt in [amount]` - Add credits to pool\n"
            "• `/poolopt out [amount]` - Withdraw from pool\n"
            "• `/poolopt accept` - Accept trading terms"
        )


async def handle_returns_command(telegram_id: int) -> str:
    """
    Handle /returns command.
    
    Shows trading return history.
    """
    from membership import get_member_db, get_wallet
    from membership.member_db import TransactionType
    
    db = get_member_db()
    member = db.get_member_by_telegram(telegram_id)
    
    if not member:
        return "❌ You're not a member yet."
    
    wallet = get_wallet(member.id)
    returns = wallet.get_pool_returns(limit=10)
    
    if not returns:
        return (
            "📊 **Trading Returns**\n\n"
            "_No returns yet._\n\n"
            "Returns are distributed daily when there's trading activity."
        )
    
    lines = ["📊 **Trading Returns**\n"]
    
    total_returns = 0
    for tx in returns:
        dt = datetime.fromisoformat(tx.created_at)
        date_str = dt.strftime("%m/%d")
        emoji = "📈" if tx.amount > 0 else "📉"
        lines.append(f"{date_str}: {emoji} {tx.amount:+.2f} UC")
        total_returns += tx.amount
    
    lines.append(f"\n**Total: {total_returns:+.2f} UC**")
    
    return "\n".join(lines)


async def handle_transactions_command(telegram_id: int) -> str:
    """
    Handle /transactions command.
    
    Shows recent transaction history.
    """
    from membership import get_member_db, get_wallet
    
    db = get_member_db()
    member = db.get_member_by_telegram(telegram_id)
    
    if not member:
        return "❌ You're not a member yet."
    
    wallet = get_wallet(member.id)
    transactions = wallet.get_transactions(limit=10)
    
    if not transactions:
        return (
            "📜 **Transaction History**\n\n"
            "_No transactions yet._"
        )
    
    lines = ["📜 **Transaction History**\n"]
    
    for tx in transactions:
        dt = datetime.fromisoformat(tx.created_at)
        date_str = dt.strftime("%m/%d %H:%M")
        
        # Determine direction
        if tx.to_member == member.id:
            direction = "+"
            other = tx.from_member
        else:
            direction = "-"
            other = tx.to_member
        
        # Format based on type
        type_emoji = {
            "gift": "🎁",
            "pool_contribution": "💰",
            "pool_withdrawal": "💳",
            "pool_return": "📊",
            "admin_credit": "✨",
            "purchase": "🛒",
        }.get(tx.type.value, "💵")
        
        lines.append(f"{date_str} {type_emoji} {direction}{tx.amount:.2f} UC")
    
    return "\n".join(lines)


# ============================================================================
# STEWARD COMMANDS
# ============================================================================

async def handle_admin_credit_command(
    admin_telegram_id: int,
    recipient_username: str,
    amount: float,
    reason: str = "Admin credit"
) -> str:
    """
    Handle /credit command (steward only).
    
    Credits UC to a user.
    """
    from telegram.gift_handler import admin_credit_user
    
    return await admin_credit_user(admin_telegram_id, recipient_username, amount, reason)


async def handle_setup_steward_command(admin_telegram_id: int) -> str:
    """
    Handle /setupsteward command.
    
    Sets up James as the initial steward.
    """
    if admin_telegram_id != JAMES_TELEGRAM_ID:
        return "❌ Only James can run this command."
    
    from telegram.gift_handler import admin_setup_steward
    
    return await admin_setup_steward(admin_telegram_id)


async def handle_pool_stats_command(telegram_id: int) -> str:
    """
    Handle /poolstats command (steward only).
    
    Shows detailed pool statistics.
    """
    from membership import get_member_db
    from trading.pool_manager import get_pool_manager
    
    db = get_member_db()
    member = db.get_member_by_telegram(telegram_id)
    
    if not member or not member.is_steward:
        return "❌ Steward access required."
    
    manager = get_pool_manager()
    pool_status = await manager.get_pool_status()
    stats = db.get_stats()
    
    lines = [
        "📊 **Pool Statistics (Steward)**\n",
        f"Total Members: {stats['total_members']}",
        f"PMA Members: {stats['pma_members']}",
        f"Trading Members: {stats['trading_members']}",
        f"\n**Pool:**",
        f"Total Credits: {pool_status.total_credits:.2f} UC",
        f"Members in Pool: {pool_status.member_count}",
        f"Cumulative P&L: {pool_status.cumulative_pnl:+.2f} UC",
        f"Aria Balance: {pool_status.aria_balance:.2f} UC",
        f"\n**System:**",
        f"Credits in System: {stats['total_credits_in_system']:.2f} UC",
    ]
    
    if pool_status.last_distribution:
        dt = datetime.fromisoformat(pool_status.last_distribution)
        lines.append(f"Last Distribution: {dt.strftime('%Y-%m-%d %H:%M')}")
    
    return "\n".join(lines)


# ============================================================================
# COMMAND ROUTER
# ============================================================================

async def route_command(
    command: str,
    telegram_id: int,
    args: str = ""
) -> Optional[str]:
    """
    Route a command to the appropriate handler.
    
    Returns response message or None if command not recognized.
    """
    command = command.lower().strip("/")
    args = args.strip()
    
    if command == "balance":
        return await handle_balance_command(telegram_id)
    
    elif command == "pool":
        return await handle_pool_command(telegram_id)
    
    elif command == "poolopt":
        # Parse action and optional amount
        parts = args.split()
        action = parts[0] if parts else ""
        amount = None
        if len(parts) > 1:
            try:
                amount = float(parts[1])
            except ValueError:
                pass
        return await handle_poolopt_command(telegram_id, action, amount)
    
    elif command == "returns":
        return await handle_returns_command(telegram_id)
    
    elif command == "transactions" or command == "tx":
        return await handle_transactions_command(telegram_id)
    
    elif command == "gift":
        from telegram.gift_handler import handle_gift_command
        return await handle_gift_command(f"/gift {args}", telegram_id, telegram_id)
    
    elif command == "credit":
        # Admin credit: /credit @user amount reason
        parts = args.split(maxsplit=2)
        if len(parts) < 2:
            return "Usage: /credit @username amount [reason]"
        username = parts[0].lstrip("@")
        try:
            amount = float(parts[1])
        except ValueError:
            return "Invalid amount"
        reason = parts[2] if len(parts) > 2 else "Admin credit"
        return await handle_admin_credit_command(telegram_id, username, amount, reason)
    
    elif command == "setupsteward":
        return await handle_setup_steward_command(telegram_id)
    
    elif command == "poolstats":
        return await handle_pool_stats_command(telegram_id)
    
    return None  # Command not recognized








