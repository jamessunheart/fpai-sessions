"""
CALLBACK HANDLER
=================

Handles inline button callbacks from Telegram.

Callback data patterns:
- pma_accept:{gift_id} - Accept PMA agreement
- pma_decline:{gift_id} - Decline gift
- trading_accept - Accept trading terms
- trading_decline - Decline trading
- accept_gift:{gift_id} - Accept a pending gift
- decline_gift:{gift_id} - Decline a pending gift
- view_pma - View PMA agreement (just a link)
"""

import os
import logging
from typing import Optional, Tuple
import httpx

logger = logging.getLogger("aria.telegram.callback")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def handle_callback(
    callback_query_id: str,
    callback_data: str,
    telegram_id: int,
    telegram_username: Optional[str] = None,
    chat_id: int = None,
    message_id: int = None
) -> Tuple[str, Optional[str]]:
    """
    Handle an inline button callback.
    
    Args:
        callback_query_id: Telegram callback query ID
        callback_data: The callback data from the button
        telegram_id: User's Telegram ID
        telegram_username: User's username
        chat_id: Chat ID for editing message
        message_id: Message ID for editing
    
    Returns:
        (answer_text, new_message_text)
        - answer_text: Text for callback answer popup
        - new_message_text: New text to replace message (or None)
    """
    from membership.onboarding import get_onboarding
    
    onboarding = get_onboarding()
    
    # Parse callback data
    parts = callback_data.split(":", 1)
    action = parts[0]
    param = parts[1] if len(parts) > 1 else None
    
    logger.info(f"Callback from {telegram_id}: {action} ({param})")
    
    if action == "pma_accept":
        # Accept PMA agreement
        new_text = await onboarding.handle_pma_accept(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            gift_id=param
        )
        
        # Send trading buttons
        await send_message_with_buttons(
            chat_id,
            new_text,
            onboarding.get_trading_buttons()
        )
        
        return ("Welcome to the Fellowship! 🎉", None)
    
    elif action == "pma_decline":
        if param and param != "none":
            new_text = await onboarding.handle_gift_decline(telegram_id, param)
        else:
            new_text = "No problem! You can join anytime by messaging me."
        
        return ("Got it!", new_text)
    
    elif action == "trading_accept":
        new_text = await onboarding.handle_trading_accept(telegram_id)
        return ("You're all set! ✨", new_text)
    
    elif action == "trading_decline":
        new_text = await onboarding.handle_trading_decline(telegram_id)
        return ("No problem!", new_text)
    
    elif action == "accept_gift":
        # Accept a pending gift (for existing members or after onboarding)
        from membership import get_member_db, get_wallet
        
        db = get_member_db()
        member = db.get_member_by_telegram(telegram_id)
        
        if not member:
            # Start onboarding
            new_text = await onboarding.start_onboarding(
                telegram_id=telegram_id,
                telegram_username=telegram_username,
                pending_gift_id=param
            )
            
            await send_message_with_buttons(
                chat_id,
                new_text,
                onboarding.get_pma_buttons(param)
            )
            
            return ("Please accept the membership agreement first.", None)
        
        # Already a member, accept gift directly
        wallet = get_wallet(member.id)
        result = wallet.accept_pending_gift(param)
        
        return (
            "Gift accepted! 🎁" if result.success else result.message,
            f"{'✅' if result.success else '❌'} {result.message}"
        )
    
    elif action == "decline_gift":
        new_text = await onboarding.handle_gift_decline(telegram_id, param)
        return ("Gift declined.", new_text)
    
    elif action == "view_pma":
        # Just acknowledge, the button has a URL
        return ("Opening agreement...", None)
    
    else:
        logger.warning(f"Unknown callback action: {action}")
        return ("Unknown action", None)


async def send_message_with_buttons(chat_id: int, text: str, buttons: list):
    """Send a message with inline buttons."""
    if not TELEGRAM_TOKEN:
        return
    
    keyboard = {"inline_keyboard": buttons}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard
                }
            )
    except Exception as e:
        logger.error(f"Failed to send message: {e}")


async def edit_message(chat_id: int, message_id: int, text: str, buttons: list = None):
    """Edit a message."""
    if not TELEGRAM_TOKEN:
        return
    
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                json=payload
            )
    except Exception as e:
        logger.error(f"Failed to edit message: {e}")


async def answer_callback_query(callback_query_id: str, text: str):
    """Answer a callback query (shows popup)."""
    if not TELEGRAM_TOKEN:
        return
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                json={
                    "callback_query_id": callback_query_id,
                    "text": text
                }
            )
    except Exception as e:
        logger.error(f"Failed to answer callback: {e}")








