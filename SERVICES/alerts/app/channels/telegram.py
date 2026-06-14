"""
Telegram notification channel
"""
import httpx
import logging
from typing import Optional

from app.channels.base import BaseChannel
from app.config import settings

logger = logging.getLogger(__name__)


class TelegramChannel(BaseChannel):
    """Telegram Bot API channel handler"""

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def is_configured(self) -> bool:
        """Check if Telegram is configured"""
        return bool(self.bot_token)

    async def send(self, recipient: str, message: str) -> bool:
        """
        Send a Telegram message

        Args:
            recipient: Telegram chat ID or "default" for steward chat
            message: Message text

        Returns:
            True if sent successfully

        Raises:
            Exception: If API call fails
        """
        if not self.is_configured():
            raise ValueError("Telegram bot token not configured")

        # Handle "default" recipient
        if recipient == "default":
            if not settings.TELEGRAM_STEWARD_CHAT_ID:
                raise ValueError("Steward chat ID not configured")
            recipient = settings.TELEGRAM_STEWARD_CHAT_ID

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": recipient,
            "text": message,
            "parse_mode": "Markdown",  # Changed from HTML to Markdown for better formatting
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                result = response.json()

                if result.get("ok"):
                    logger.info(f"Telegram message sent to {recipient}")
                    return True
                else:
                    error = result.get("description", "Unknown error")
                    raise Exception(f"Telegram API error: {error}")

            except httpx.HTTPStatusError as e:
                logger.error(f"Telegram HTTP error: {e}")
                raise
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")
                raise

    async def test(self) -> bool:
        """
        Test Telegram connectivity by getting bot info

        Returns:
            True if bot is accessible
        """
        if not self.is_configured():
            return False

        url = f"{self.base_url}/getMe"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=5.0)
                response.raise_for_status()
                result = response.json()
                return result.get("ok", False)
            except Exception as e:
                logger.error(f"Telegram test failed: {e}")
                return False

    async def send_to_steward(self, message: str) -> bool:
        """
        Send a message to the configured steward chat

        Args:
            message: Message text

        Returns:
            True if sent successfully
        """
        if not settings.TELEGRAM_STEWARD_CHAT_ID:
            raise ValueError("Steward chat ID not configured")

        return await self.send(settings.TELEGRAM_STEWARD_CHAT_ID, message)

    async def send_with_buttons(self, recipient: str, message: str, buttons: list) -> bool:
        """
        Send a Telegram message with inline keyboard buttons

        Args:
            recipient: Telegram chat ID or "default" for steward chat
            message: Message text
            buttons: List of button rows, e.g.:
                     [[{"text": "✅ Yes", "callback_data": "confirm:123"}],
                      [{"text": "❌ No", "callback_data": "reject:123"}]]

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            raise ValueError("Telegram bot token not configured")

        # Handle "default" recipient
        if recipient == "default":
            if not settings.TELEGRAM_STEWARD_CHAT_ID:
                raise ValueError("Steward chat ID not configured")
            recipient = settings.TELEGRAM_STEWARD_CHAT_ID

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": recipient,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": buttons
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                result = response.json()

                if result.get("ok"):
                    logger.info(f"Telegram message with buttons sent to {recipient}")
                    return True
                else:
                    error = result.get("description", "Unknown error")
                    raise Exception(f"Telegram API error: {error}")

            except httpx.HTTPStatusError as e:
                logger.error(f"Telegram HTTP error: {e}")
                raise
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")
                raise

    async def answer_callback(self, callback_query_id: str, text: str = None) -> bool:
        """
        Answer a callback query (acknowledge button click)

        Args:
            callback_query_id: The callback query ID from Telegram
            text: Optional text to show as notification

        Returns:
            True if acknowledged successfully
        """
        if not self.is_configured():
            raise ValueError("Telegram bot token not configured")

        url = f"{self.base_url}/answerCallbackQuery"
        payload = {
            "callback_query_id": callback_query_id
        }
        if text:
            payload["text"] = text

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=5.0)
                response.raise_for_status()
                result = response.json()
                return result.get("ok", False)
            except Exception as e:
                logger.error(f"Callback answer failed: {e}")
                return False
