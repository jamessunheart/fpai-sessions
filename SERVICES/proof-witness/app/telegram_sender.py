"""
Proof Witness - Telegram Sender

Sends daily proof summary to Telegram with interactive buttons.
The 15-second confirmation flow.
"""
import logging
import httpx
from typing import List
from datetime import datetime

from app.models import ProofCandidate
from app.storage import storage
from app.config import settings

logger = logging.getLogger(__name__)


class TelegramProofSender:
    """Sends proof candidates to Telegram for human confirmation"""

    def __init__(self):
        self.alerts_url = "http://localhost:8766"  # Alerts service with Telegram bot

    async def send_daily_summary(self, max_items: int = 10) -> dict:
        """
        Send daily proof summary to Telegram

        This is the end-of-day notification:
        "I saw 3 events today. Confirm?"

        Returns:
            {
                "sent": 3,
                "pending": 3,
                "message": "Sent 3 proof items for confirmation"
            }
        """
        # Get pending proof candidates
        candidates = storage.get_pending_candidates(limit=max_items)

        if not candidates:
            logger.info("No pending proof to send")
            return {
                "sent": 0,
                "pending": 0,
                "message": "No pending proof"
            }

        # Send each candidate as a separate message with buttons
        sent_count = 0

        for candidate in candidates:
            try:
                await self._send_candidate(candidate)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send candidate {candidate.id}: {e}")

        logger.info(f"Sent {sent_count}/{len(candidates)} proof items to Telegram")

        return {
            "sent": sent_count,
            "pending": len(candidates),
            "message": f"Sent {sent_count} proof items for confirmation"
        }

    async def _send_candidate(self, candidate: ProofCandidate):
        """Send a single proof candidate to Telegram with inline buttons"""

        # Format the message
        message = self._format_candidate_message(candidate)

        # Create inline buttons
        buttons = self._create_buttons(candidate)

        # Send via Alerts service (which has the Telegram bot)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.alerts_url}/send/telegram/buttons",
                json={
                    "recipient": "default",  # Steward chat
                    "message": message,
                    "buttons": buttons
                },
                timeout=10.0
            )

            if response.status_code != 200:
                raise Exception(f"Failed to send to Telegram: {response.text}")

            logger.info(f"Sent proof candidate {candidate.id} to Telegram")

    def _format_candidate_message(self, candidate: ProofCandidate) -> str:
        """Format proof candidate as Telegram message"""

        # Type emoji
        type_emoji = {
            "code": "💻",
            "photo": "📸",
            "metric": "📊",
            "event": "✅",
            "knowledge": "📚",
            "content": "📱"
        }.get(candidate.type.value, "•")

        # Build message
        lines = [f"{type_emoji} *{candidate.owner}*: {candidate.title}"]

        # Add description if short
        if candidate.description and len(candidate.description) < 100:
            lines.append(f"_{candidate.description}_")

        # Add suggested tag with confidence
        if candidate.tags:
            tag = candidate.tags[0]
            confidence_pct = int(candidate.confidence * 100)
            lines.append(f"Tag: `{tag}` ({confidence_pct}% confident)")

        # Add timestamp
        time_str = candidate.occurred_at.strftime("%I:%M%p").lower()
        lines.append(f"_Occurred at {time_str}_")

        return "\n".join(lines)

    def _create_buttons(self, candidate: ProofCandidate) -> List[List[dict]]:
        """Create inline keyboard buttons for proof candidate"""

        # Single row with 3 buttons
        return [[
            {"text": "✅ Yes", "callback_data": f"confirm:{candidate.id}"},
            {"text": "✏️ Edit", "callback_data": f"edit:{candidate.id}"},
            {"text": "❌ Skip", "callback_data": f"reject:{candidate.id}"}
        ]]


# Global instance
telegram_sender = TelegramProofSender()
