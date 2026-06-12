"""
GIFT COMMAND HANDLER
=====================

Handles the /gift command for sending credits to other users.

Usage: 
  /gift @username amount [message]     - Send to Telegram user
  /gift link amount [message]          - Create shareable link (email/WhatsApp/SMS)
  /giftlinks                           - View your pending gift links

Flow:
1. Verify sender has sufficient balance
2. Look up recipient by username OR create claim link
3. If recipient is member, transfer immediately
4. If not, create pending gift and DM recipient (or return link)
"""

import os
import re
import logging
from typing import Optional, Tuple
import httpx

logger = logging.getLogger("aria.telegram.gift")

# Telegram config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def handle_gift_command(
    message_text: str,
    sender_telegram_id: int,
    chat_id: int
) -> str:
    """
    Handle /gift command.
    
    Args:
        message_text: Full message text (e.g., "/gift @friend 100 Thanks!")
        sender_telegram_id: Sender's Telegram ID
        chat_id: Chat ID to reply to
    
    Returns:
        Response message
    """
    from membership import get_member_db, get_wallet, Member
    
    db = get_member_db()
    
    # Check for link-based gift: /gift link 100 message
    text = message_text.strip()
    if text.startswith("/gift"):
        text = text[5:].strip()
    
    if text.lower().startswith("link "):
        return await handle_gift_link_command(text[5:].strip(), sender_telegram_id)
    
    # Parse command
    parsed = parse_gift_command(message_text)
    if not parsed:
        return (
            "❌ **Invalid format**\n\n"
            "**Send to Telegram user:**\n"
            "`/gift @username amount [message]`\n\n"
            "**Create shareable link (email/WhatsApp):**\n"
            "`/gift link amount [message]`\n\n"
            "Examples:\n"
            "• `/gift @friend 100 Thanks!`\n"
            "• `/gift link 100 Thanks for hosting!`"
        )
    
    recipient_username, amount, gift_message = parsed
    
    # Get sender
    sender = db.get_member_by_telegram(sender_telegram_id)
    if not sender:
        return (
            "❌ You're not a member yet.\n"
            "Start a chat with me first to join the Fellowship."
        )
    
    # Check balance
    wallet = get_wallet(sender.id)
    balance = wallet.get_balance()
    
    if balance["available"] < amount:
        return (
            f"❌ Insufficient balance.\n"
            f"Available: {balance['available']:.2f} UC\n"
            f"Requested: {amount:.2f} UC"
        )
    
    # Look up recipient
    recipient = db.get_member_by_username(recipient_username)
    recipient_telegram_id = None
    
    if recipient:
        # Existing member - direct transfer
        recipient_telegram_id = recipient.telegram_id
        result = wallet.send_gift(
            to_telegram_id=recipient.telegram_id,
            to_username=recipient_username,
            amount=amount,
            message=gift_message
        )
        
        if result.success:
            # Notify recipient
            await notify_gift_received(
                recipient.telegram_id,
                sender.telegram_username or sender.display_name or "Someone",
                amount,
                gift_message
            )
            
            return (
                f"✅ **Gift Sent!**\n\n"
                f"Sent {amount:.2f} UC to @{recipient_username}\n"
                f"Your new balance: {balance['available'] - amount:.2f} UC"
            )
        else:
            return f"❌ {result.message}"
    
    else:
        # Non-member - need to resolve Telegram ID
        # Try to get user ID from username
        recipient_info = await get_telegram_user_info(recipient_username)
        
        if not recipient_info:
            return (
                f"❌ Cannot find @{recipient_username}\n\n"
                "They need to start a chat with me first.\n"
                "Ask them to message @AriaAIBot to join the Fellowship."
            )
        
        recipient_telegram_id = recipient_info.get("id")
        
        # Create pending gift
        result = wallet.send_gift(
            to_telegram_id=recipient_telegram_id,
            to_username=recipient_username,
            amount=amount,
            message=gift_message
        )
        
        if result.success:
            # Notify recipient to accept
            await notify_pending_gift(
                recipient_telegram_id,
                sender.telegram_username or sender.display_name or "A member",
                amount,
                gift_message,
                result.pending_gift_id
            )
            
            return (
                f"🎁 **Gift Pending**\n\n"
                f"{amount:.2f} UC is waiting for @{recipient_username} to accept.\n"
                f"They'll need to join the Fellowship to claim it.\n\n"
                f"I've sent them a message to accept."
            )
        else:
            return f"❌ {result.message}"


def parse_gift_command(text: str) -> Optional[Tuple[str, float, Optional[str]]]:
    """
    Parse gift command text.
    
    Returns:
        (recipient_username, amount, message) or None if invalid
    """
    # Remove /gift prefix
    text = text.strip()
    if text.startswith("/gift"):
        text = text[5:].strip()
    
    # Pattern: @username amount [message]
    pattern = r'^@?(\w+)\s+(\d+(?:\.\d+)?)\s*(.*)$'
    match = re.match(pattern, text)
    
    if not match:
        return None
    
    username = match.group(1)
    amount = float(match.group(2))
    message = match.group(3).strip() or None
    
    if amount <= 0:
        return None
    
    return (username, amount, message)


async def get_telegram_user_info(username: str) -> Optional[dict]:
    """
    Get Telegram user info by username.
    
    Note: Telegram Bot API doesn't directly support username lookup.
    We need to have seen the user before (in our database or a chat).
    
    Returns user info dict or None.
    """
    # This is a limitation - we can't look up arbitrary usernames
    # The user needs to have interacted with the bot first
    from membership import get_member_db
    
    db = get_member_db()
    
    # Check if we have them in pending gifts or previous interactions
    # For now, return None - they'll need to message the bot first
    return None


async def notify_gift_received(
    telegram_id: int,
    from_name: str,
    amount: float,
    message: Optional[str]
):
    """Notify recipient that they received a gift."""
    text = (
        f"🎁 **You received a gift!**\n\n"
        f"**{from_name}** sent you **{amount:.2f} UC**"
    )
    
    if message:
        text += f"\n\n💬 _{message}_"
    
    text += "\n\nType /balance to see your wallet."
    
    await send_telegram_message(telegram_id, text)


async def notify_pending_gift(
    telegram_id: int,
    from_name: str,
    amount: float,
    message: Optional[str],
    gift_id: str
):
    """Notify recipient about a pending gift."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    text = (
        f"🎁 **You have a gift waiting!**\n\n"
        f"**{from_name}** wants to send you **{amount:.2f} UC**"
    )
    
    if message:
        text += f"\n\n💬 _{message}_"
    
    text += (
        "\n\n"
        "To accept this gift, you'll join the **Conscious Wealth Fellowship** "
        "as a Private Membership Association member.\n\n"
        "This means:\n"
        "• You become a member of our private community\n"
        "• You can hold and use UC credits\n"
        "• You can opt into Aria's trading pool\n"
    )
    
    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("📜 View Agreement", callback_data=f"view_pma"),
            InlineKeyboardButton("✅ Accept & Join", callback_data=f"accept_gift:{gift_id}"),
        ],
        [
            InlineKeyboardButton("❌ Decline", callback_data=f"decline_gift:{gift_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_telegram_message_with_buttons(telegram_id, text, reply_markup)


async def send_telegram_message(chat_id: int, text: str):
    """Send a Telegram message."""
    if not TELEGRAM_TOKEN:
        logger.warning("No Telegram token configured")
        return
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                }
            )
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")


async def send_telegram_message_with_buttons(chat_id: int, text: str, reply_markup):
    """Send a Telegram message with inline buttons."""
    if not TELEGRAM_TOKEN:
        logger.warning("No Telegram token configured")
        return
    
    try:
        # Convert reply_markup to dict
        keyboard_dict = {
            "inline_keyboard": [
                [{"text": btn.text, "callback_data": btn.callback_data} for btn in row]
                for row in reply_markup.inline_keyboard
            ]
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard_dict
                }
            )
    except Exception as e:
        logger.error(f"Failed to send Telegram message with buttons: {e}")


# ============================================================================
# LINK-BASED GIFTS (Email, WhatsApp, SMS)
# ============================================================================

async def handle_gift_link_command(args: str, sender_telegram_id: int) -> str:
    """
    Handle /gift link command - create a shareable claim link.
    
    Args:
        args: "amount [message]"
        sender_telegram_id: Sender's Telegram ID
    
    Returns:
        Response with the shareable link
    """
    from membership import get_member_db
    from membership.claim_links import get_claim_manager
    
    db = get_member_db()
    
    # Get sender
    sender = db.get_member_by_telegram(sender_telegram_id)
    if not sender:
        return "❌ You're not a member yet. Start a chat with me first!"
    
    # Parse amount and message
    parts = args.split(maxsplit=1)
    if not parts:
        return (
            "❌ **Invalid format**\n\n"
            "Usage: `/gift link amount [message]`\n"
            "Example: `/gift link 100 Thanks for hosting!`"
        )
    
    try:
        amount = float(parts[0])
    except ValueError:
        return "❌ Invalid amount. Use a number like `100` or `50.5`"
    
    if amount <= 0:
        return "❌ Amount must be positive"
    
    message = parts[1] if len(parts) > 1 else None
    
    # Create claim link
    manager = get_claim_manager()
    claim = manager.create_link(
        from_member_id=sender.id,
        amount=amount,
        message=message
    )
    
    if not claim:
        wallet = db.get_wallet(sender.id)
        return (
            f"❌ Insufficient balance.\n"
            f"Available: {wallet.available_credits:.2f} UC\n"
            f"Requested: {amount:.2f} UC"
        )
    
    # Generate share messages
    messages = manager.format_share_messages(claim)
    
    return (
        f"🔗 **Gift Link Created!**\n\n"
        f"Amount: **{amount:.2f} UC**\n"
        f"Link: `{claim.url}`\n\n"
        f"---\n\n"
        f"**📧 For Email:**\n"
        f"Subject: {messages['email_subject']}\n\n"
        f"**📱 For WhatsApp/SMS:**\n"
        f"{messages['whatsapp']}\n\n"
        f"---\n"
        f"_This link expires in 30 days._\n"
        f"_Use `/giftlinks` to see your pending links._"
    )


async def handle_gift_links_command(sender_telegram_id: int) -> str:
    """
    Handle /giftlinks command - show pending gift links.
    """
    from membership import get_member_db
    from membership.claim_links import get_claim_manager
    
    db = get_member_db()
    
    sender = db.get_member_by_telegram(sender_telegram_id)
    if not sender:
        return "❌ You're not a member yet."
    
    manager = get_claim_manager()
    pending = manager.get_pending_by_sender(sender.id)
    
    if not pending:
        return (
            "📭 **No pending gift links.**\n\n"
            "Create one with: `/gift link 100 message`"
        )
    
    lines = [f"🔗 **Your Pending Gift Links ({len(pending)})**\n"]
    
    total_pending = 0
    for claim in pending:
        status = "⏰ Pending"
        if claim.is_expired:
            status = "❌ Expired"
        
        lines.append(f"**{claim.amount:.2f} UC** - {status}")
        lines.append(f"  Link: `{claim.url}`")
        if claim.message:
            lines.append(f"  Message: _{claim.message[:30]}..._" if len(claim.message) > 30 else f"  Message: _{claim.message}_")
        lines.append(f"  Cancel: `/cancelgift {claim.code}`")
        lines.append("")
        
        if not claim.is_expired:
            total_pending += claim.amount
    
    lines.append(f"**Total pending:** {total_pending:.2f} UC")
    
    return "\n".join(lines)


async def handle_cancel_gift_command(code: str, sender_telegram_id: int) -> str:
    """
    Handle /cancelgift command - cancel a pending gift link.
    """
    from membership import get_member_db
    from membership.claim_links import get_claim_manager
    
    db = get_member_db()
    
    sender = db.get_member_by_telegram(sender_telegram_id)
    if not sender:
        return "❌ You're not a member yet."
    
    manager = get_claim_manager()
    success, message = manager.cancel(code, sender.id)
    
    return f"{'✅' if success else '❌'} {message}"


# ============================================================================
# STEWARD FUNCTIONS
# ============================================================================

async def admin_credit_user(
    admin_telegram_id: int,
    recipient_username: str,
    amount: float,
    reason: str = "Admin credit"
) -> str:
    """
    Admin function to credit a user.
    
    Only stewards can use this.
    """
    from membership import get_member_db, get_wallet, Member, TransactionType
    
    db = get_member_db()
    
    # Verify admin is steward
    admin = db.get_member_by_telegram(admin_telegram_id)
    if not admin or not admin.is_steward:
        return "❌ Only stewards can credit users."
    
    # Find recipient
    recipient = db.get_member_by_username(recipient_username)
    if not recipient:
        return f"❌ User @{recipient_username} not found."
    
    # Credit the user
    if db.add_credits(recipient.id, amount):
        # Record transaction
        from membership.member_db import Transaction, TransactionStatus
        tx = Transaction(
            from_member=admin.id,
            to_member=recipient.id,
            amount=amount,
            type=TransactionType.ADMIN_CREDIT,
            status=TransactionStatus.COMPLETED,
            description=reason
        )
        db.create_transaction(tx)
        
        # Notify recipient
        await send_telegram_message(
            recipient.telegram_id,
            f"✨ You received **{amount:.2f} UC** from the Fellowship.\n\n"
            f"Reason: {reason}\n\n"
            f"Type /balance to see your wallet."
        )
        
        return f"✅ Credited {amount:.2f} UC to @{recipient_username}"
    else:
        return "❌ Failed to credit user."


async def admin_setup_steward(admin_telegram_id: int) -> str:
    """
    Set up the initial steward (James).
    
    This should only be called once during setup.
    """
    from membership import get_member_db, Member
    
    db = get_member_db()
    
    # Check if already a member
    existing = db.get_member_by_telegram(admin_telegram_id)
    if existing:
        if existing.is_steward:
            return "Already set up as steward."
        
        # Make them a steward
        db.update_member(
            existing.id,
            is_steward=True,
            pma_agreed_at=existing.pma_agreed_at or datetime.now().isoformat(),
            trading_agreed_at=existing.trading_agreed_at or datetime.now().isoformat()
        )
        return f"Updated {existing.telegram_username or existing.id} to steward."
    
    # Create new steward
    from datetime import datetime
    member = Member(
        id=None,
        telegram_id=admin_telegram_id,
        telegram_username="jamessunheart",  # Adjust as needed
        display_name="James",
        is_steward=True,
        pma_agreed_at=datetime.now().isoformat(),
        trading_agreed_at=datetime.now().isoformat()
    )
    
    member_id = db.create_member(member)
    
    return f"Created steward account: {member_id}"

