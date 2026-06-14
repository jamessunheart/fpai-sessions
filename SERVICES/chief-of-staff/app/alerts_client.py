"""
Client for sending notifications via alerts service
"""
import httpx
import logging
from typing import Optional

from app.config import settings
from app.models import Signal, SignalCategory

logger = logging.getLogger(__name__)


class AlertsClient:
    """Client for alerts service integration"""

    def __init__(self):
        self.base_url = settings.ALERTS_SERVICE_URL

    async def send_urgent_alert(self, signal: Signal) -> bool:
        """
        Send urgent alert via Telegram

        Format:
        🔴 URGENT - [Title]

        [Description]

        Impact: [What's affected]
        Action: [What to do]
        """
        message = self._format_urgent_message(signal)

        return await self._send_telegram(message)

    async def send_digest(self, digest_text: str) -> bool:
        """Send daily digest via Telegram"""
        return await self._send_telegram(digest_text)

    async def send_summary(self, summary_text: str) -> bool:
        """Send weekly summary via Telegram"""
        return await self._send_telegram(summary_text)

    async def _send_telegram(self, message: str) -> bool:
        """Send message via alerts service"""
        url = f"{self.base_url}/send"

        payload = {
            "channel": "telegram",
            "recipient": "default",  # Will use TELEGRAM_STEWARD_CHAT_ID from alerts .env
            "message": message,
            "priority": "normal"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                logger.info("Sent notification via alerts service")
                return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to send notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending notification: {e}")
            return False

    def _format_urgent_message(self, signal: Signal) -> str:
        """Format urgent signal for Telegram"""
        lines = []

        # Header
        lines.append(f"🔴 *URGENT* - {signal.title}")
        lines.append("")

        # Description
        lines.append(signal.description)
        lines.append("")

        # Impact
        if "impact" in signal.data:
            lines.append(f"*Impact:* {signal.data['impact']}")
            lines.append("")

        # Action needed
        if "action_needed" in signal.data:
            lines.append("*Action needed:*")
            lines.append(signal.data['action_needed'])
        else:
            lines.append("*Action needed:* Immediate attention required")

        # Quick actions
        if "quick_actions" in signal.data:
            lines.append("")
            lines.append("*Quick actions:*")
            for action in signal.data['quick_actions']:
                lines.append(f"• {action}")

        # Source
        lines.append("")
        lines.append(f"_Source: {signal.source}_")

        return "\n".join(lines)

    async def test_connection(self) -> bool:
        """Test connection to alerts service"""
        url = f"{self.base_url}/health"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                response.raise_for_status()
                logger.info("Alerts service connection OK")
                return True
        except Exception as e:
            logger.error(f"Alerts service not reachable: {e}")
            return False


# Global client instance
alerts_client = AlertsClient()
