"""Hermes channel gateway.

Hermes normalizes each external door into one internal message shape. Telegram
remains the live bot path; this package adds the translation layer for the
next channels.
"""
from __future__ import annotations

from .gateway import ChannelNotRegistered, HermesGateway
from .schema import HermesMessage, HermesResponse

__all__ = [
    "ChannelNotRegistered",
    "HermesGateway",
    "HermesMessage",
    "HermesResponse",
]
