"""
Core semantic memory utilities shared across services.

This package currently exposes a ChromaDB-backed vector store along with
helper functions for adding new episodes and recalling memories by meaning.
"""

from .vector_store import add_episode, recall, get_client  # noqa: F401

__all__ = ["add_episode", "recall", "get_client"]


