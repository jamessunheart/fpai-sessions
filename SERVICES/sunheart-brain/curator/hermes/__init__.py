"""Hermes channel gateway package.

Hermes normalizes each external door into one internal message shape. Telegram
remains the live bot path; this package adds the translation layer for the next
channels while preserving the legacy probe send helper.
"""
from __future__ import annotations

from .gateway import ChannelNotRegistered, HermesDisabled, HermesGateway, send_message
from .schema import HermesMessage, HermesResponse

__all__ = [
    "ChannelNotRegistered",
    "HermesDisabled",
    "HermesGateway",
    "HermesMessage",
    "HermesResponse",
    "send_message",
]
