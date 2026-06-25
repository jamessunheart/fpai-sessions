"""Base interface for Hermes channel adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..schema import HermesMessage, HermesResponse


class ChannelAdapter(ABC):
    """Translate one external channel into and out of Hermes."""

    @abstractmethod
    def normalize(self, raw: dict) -> HermesMessage:
        """Convert a platform payload into a channel-agnostic message."""

    @abstractmethod
    async def send(self, response: HermesResponse) -> None:
        """Send a Hermes response through the channel."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return whether the channel is configured/reachable."""
