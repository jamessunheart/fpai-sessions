"""
Zend Clerk - POS Chat Agent v1.0
================================

Service: zend-clerk
Port: 8582

Telegram (and future WhatsApp) bot for merchant POS operations.
"Ministry of Flow" - regenerative commerce facilitation.

Commands:
- /start - Register as merchant
- /invoice <amount> <description> - Create payment request
- /link - Get last ZendLink
- /status <code> - Check payment status
- /today - Daily summary
- /balance - Check UC balance

Source of truth:
- docs/protocols/ZEND_REGENERATIVE_SPEC.md Part 8
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from .config import settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================================
# ZEND API CLIENT
# ============================================================

class ZendClient:
    """Client for Zend Payments API."""

    def __init__(self):
        self.payments_url = settings.ZEND_PAYMENTS_URL.rstrip("/")
        self.wallet_url = settings.ZEND_WALLET_URL.rstrip("/")

    async def create_invoice(
        self,
        merchant_id: str,
        amount: float,
        description: str,
        commons_tithe_pct: float = 0.0,
    ) -> Optional[dict]:
        """Create a payment invoice."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.payments_url}/api/invoices",
                    json={
                        "merchant_id": merchant_id,
                        "total": amount,
                        "currency": "USD",
                        "note": description,
                        "commons_tithe_pct": commons_tithe_pct,
                        "expires_in_minutes": settings.DEFAULT_EXPIRY_MINUTES,
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"Invoice creation failed: {e}")
        return None

    async def get_link_status(self, code: str) -> Optional[dict]:
        """Get ZendLink status."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.payments_url}/api/links/{code}")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"Link status fetch failed: {e}")
        return None

    async def get_wallet_balance(self, member_id: str) -> Optional[dict]:
        """Get UC wallet balance."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.wallet_url}/api/zend/wallet/{member_id}")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"Wallet fetch failed: {e}")
        return None


zend = ZendClient()


# ============================================================
# USER STATE
# ============================================================

# Simple in-memory state (would use Redis/DB in production)
user_state: dict = {}


def get_merchant_id(user_id: int) -> str:
    """Get merchant ID for a Telegram user."""
    return f"tg:{user_id}"


def get_last_link(user_id: int) -> Optional[str]:
    """Get last created ZendLink for a user."""
    return user_state.get(f"last_link:{user_id}")


def set_last_link(user_id: int, code: str):
    """Store last created ZendLink for a user."""
    user_state[f"last_link:{user_id}"] = code


# ============================================================
# BOT HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - register merchant."""
    user = update.effective_user
    merchant_id = get_merchant_id(user.id)

    welcome_msg = f"""
🌟 *Welcome to Zend Clerk!*

You are registered as merchant: `{merchant_id}`

*Commands:*
• `/invoice <amount> <description>` - Create payment request
• `/link` - Get your last ZendLink
• `/status <code>` - Check payment status
• `/today` - Daily summary
• `/balance` - Check UC balance

_Ministry of Flow - Zend to Ascend_ ✨
"""
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")


async def create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /invoice command - create payment request.
    Usage: /invoice 23.50 2 lattes + tip
    """
    user = update.effective_user
    merchant_id = get_merchant_id(user.id)

    # Parse arguments
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: `/invoice <amount> <description>`\n"
            "Example: `/invoice 23.50 2 lattes + tip`",
            parse_mode="Markdown"
        )
        return

    # Extract amount
    try:
        amount = float(args[0])
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Use a number like `23.50`", parse_mode="Markdown")
        return

    # Extract description
    description = " ".join(args[1:])

    # Create invoice
    await update.message.reply_text("Creating invoice... 🔄")

    result = await zend.create_invoice(
        merchant_id=merchant_id,
        amount=amount,
        description=description,
        commons_tithe_pct=settings.DEFAULT_COMMONS_TITHE_PCT,
    )

    if not result:
        await update.message.reply_text("❌ Failed to create invoice. Try again.")
        return

    # Store last link
    code = result.get("zend_link", "").split("/")[-1]
    set_last_link(user.id, code)

    # Build response
    zend_link = result.get("zend_link")
    expires_at = result.get("expires_at", "")

    response = f"""
✅ *Invoice Created!*

💰 *Amount:* ${amount:.2f}
📝 *Description:* {description}

🔗 *ZendLink:* `{zend_link}`

_Share this link with your customer to receive payment._

⏰ Expires: {expires_at[:19] if expires_at else 'in 30 minutes'}
"""

    # Add QR code button
    keyboard = [[
        InlineKeyboardButton("📱 Show QR Code", callback_data=f"qr:{code}"),
        InlineKeyboardButton("📊 Check Status", callback_data=f"status:{code}"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(response, parse_mode="Markdown", reply_markup=reply_markup)


async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /link command - get last ZendLink."""
    user = update.effective_user
    code = get_last_link(user.id)

    if not code:
        await update.message.reply_text("No recent ZendLink. Use `/invoice` to create one.", parse_mode="Markdown")
        return

    zend_link = f"https://zend.to/{code}"
    await update.message.reply_text(f"🔗 *Last ZendLink:* `{zend_link}`", parse_mode="Markdown")


async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /status command - check payment status.
    Usage: /status <code>
    """
    args = context.args

    # If no code provided, use last link
    if not args:
        user = update.effective_user
        code = get_last_link(user.id)
        if not code:
            await update.message.reply_text("Usage: `/status <code>`", parse_mode="Markdown")
            return
    else:
        code = args[0]

    # Fetch status
    result = await zend.get_link_status(code)

    if not result:
        await update.message.reply_text("❌ Link not found or expired.")
        return

    status = result.get("status", "unknown")
    amount = result.get("amount", 0)
    recipient = result.get("recipient_id", "unknown")

    emoji_map = {
        "pending": "⏳",
        "settled": "✅",
        "expired": "⌛",
        "cancelled": "❌",
    }
    emoji = emoji_map.get(status, "❓")

    response = f"""
{emoji} *Payment Status: {status.upper()}*

💰 Amount: ${amount:.2f}
🏪 Recipient: {recipient}
🔗 Code: `{code}`
"""
    await update.message.reply_text(response, parse_mode="Markdown")


async def daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /today command - daily summary."""
    user = update.effective_user
    merchant_id = get_merchant_id(user.id)

    # In production, this would fetch from database
    response = f"""
📊 *Daily Summary for {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*

🏪 Merchant: `{merchant_id}`

_Summary feature coming soon!_
_Track your payments in the full dashboard._

_Zend to Ascend_ ✨
"""
    await update.message.reply_text(response, parse_mode="Markdown")


async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command - check UC balance."""
    user = update.effective_user
    merchant_id = get_merchant_id(user.id)

    result = await zend.get_wallet_balance(merchant_id)

    if not result:
        await update.message.reply_text("❌ Could not fetch balance. You may not have a wallet yet.")
        return

    uc_balance = result.get("uc_balance", 0)
    unlocked = result.get("unlocked", [])

    response = f"""
💎 *UC Balance*

🪙 *{uc_balance:.2f} UC*

✨ *Unlocked:*
"""
    if unlocked:
        for u in unlocked:
            response += f"• {u}\n"
    else:
        response += "_None yet - keep Zending!_\n"

    response += "\n_UC Credits are prepaid service credits (not money)._"

    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("qr:"):
        code = data[3:]
        qr_url = f"{settings.ZEND_PAYMENTS_URL}/api/qr/{code}"
        await query.message.reply_text(f"📱 QR Code: {qr_url}")

    elif data.startswith("status:"):
        code = data[7:]
        result = await zend.get_link_status(code)
        if result:
            status = result.get("status", "unknown")
            await query.message.reply_text(f"Status: {status.upper()}")
        else:
            await query.message.reply_text("Could not fetch status.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle plain text messages - natural language invoice creation.
    Example: "23.50 for 2 lattes"
    """
    text = update.message.text.strip()

    # Try to parse as quick invoice
    # Pattern: <amount> [for] <description>
    match = re.match(r"^(\d+(?:\.\d{1,2})?)\s+(?:for\s+)?(.+)$", text, re.IGNORECASE)

    if match:
        amount = float(match.group(1))
        description = match.group(2)

        # Simulate /invoice command
        context.args = [str(amount), description]
        await create_invoice(update, context)
    else:
        # Show help
        await update.message.reply_text(
            "💡 *Quick tip:* Send `<amount> <description>` to create an invoice.\n"
            "Example: `23.50 2 lattes + tip`\n\n"
            "Or use `/invoice <amount> <description>`",
            parse_mode="Markdown"
        )


# ============================================================
# MAIN
# ============================================================

def main():
    """Start the Telegram bot."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("ZEND_CLERK_TELEGRAM_BOT_TOKEN not set")
        return

    # Create application
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("invoice", create_invoice))
    app.add_handler(CommandHandler("link", get_link))
    app.add_handler(CommandHandler("status", check_status))
    app.add_handler(CommandHandler("today", daily_summary))
    app.add_handler(CommandHandler("balance", check_balance))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start polling
    logger.info(f"Starting Zend Clerk bot v{settings.SERVICE_VERSION}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()




