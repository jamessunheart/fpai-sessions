"""
SMS notification channel via Twilio
"""
import httpx
import logging
import base64
from typing import Optional

from app.channels.base import BaseChannel
from app.config import settings

logger = logging.getLogger(__name__)


class SMSChannel(BaseChannel):
    """Twilio SMS channel handler"""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

    def is_configured(self) -> bool:
        """Check if Twilio is configured"""
        return bool(
            self.account_sid and self.auth_token and self.from_number
        )

    async def send(self, recipient: str, message: str) -> bool:
        """
        Send an SMS via Twilio

        Args:
            recipient: Phone number (E.164 format)
            message: Message text

        Returns:
            True if sent successfully

        Raises:
            Exception: If API call fails
        """
        if not self.is_configured():
            raise ValueError("Twilio credentials not configured")

        url = f"{self.base_url}/Messages.json"

        # Prepare basic auth
        auth_str = f"{self.account_sid}:{self.auth_token}"
        auth_bytes = auth_str.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "From": self.from_number,
            "To": recipient,
            "Body": message,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=headers, data=data, timeout=10.0
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") in ["queued", "sent", "sending"]:
                    logger.info(f"SMS sent to {recipient}")
                    return True
                else:
                    error = result.get("error_message", "Unknown error")
                    raise Exception(f"Twilio error: {error}")

            except httpx.HTTPStatusError as e:
                logger.error(f"Twilio HTTP error: {e}")
                raise
            except Exception as e:
                logger.error(f"SMS send failed: {e}")
                raise

    async def test(self) -> bool:
        """
        Test Twilio connectivity by fetching account info

        Returns:
            True if account is accessible
        """
        if not self.is_configured():
            return False

        url = f"{self.base_url}.json"

        auth_str = f"{self.account_sid}:{self.auth_token}"
        auth_bytes = auth_str.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        headers = {"Authorization": f"Basic {auth_b64}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=5.0)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Twilio test failed: {e}")
                return False
