"""Spine Validator — memory integrity checks (Phase 1: lightweight)."""

import json


def validate_memory(memory):
    """Validate that memory has required Phase 1 fields."""
    required = ["cycle_number", "status", "sunheart_steering", "history"]
    missing = [f for f in required if f not in memory]
    if missing:
        raise ValueError(f"Memory missing required fields: {missing}")

    if not isinstance(memory.get("cycle_number"), int):
        raise ValueError("cycle_number must be an integer")

    if not isinstance(memory.get("sunheart_steering"), list):
        raise ValueError("sunheart_steering must be a list")

    if not isinstance(memory.get("history"), list):
        raise ValueError("history must be a list")

    return True


def validate_lock(memory):
    """Check if memory is currently locked by another process."""
    locked_by = memory.get("locked_by")
    if locked_by is not None:
        return False, locked_by
    return True, None


def trim_history(memory, max_cycles=20):
    """Keep only the last N cycles in history."""
    history = memory.get("history", [])
    if len(history) > max_cycles:
        memory["history"] = history[-max_cycles:]
    return memory
