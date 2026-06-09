"""
Base channel handler interface
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseChannel(ABC):
    """Abstract base class for notification channels"""

    @abstractmethod
    async def send(self, recipient: str, message: str) -> bool:
        """
        Send a notification

        Args:
            recipient: Recipient identifier (chat ID, phone, email)
            message: Message content

        Returns:
            True if sent successfully, False otherwise

        Raises:
            Exception: If sending fails
        """
        pass

    @abstractmethod
    async def test(self) -> bool:
        """
        Test channel connectivity

        Returns:
            True if channel is operational, False otherwise
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if channel is properly configured

        Returns:
            True if configured, False otherwise
        """
        pass
