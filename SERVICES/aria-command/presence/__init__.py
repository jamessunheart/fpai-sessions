#!/usr/bin/env python3
"""
Presence Module
===============
The "green dot" - JAI is visibly alive and working.

Components:
- engine.py: Core presence state machine
- status.py: Status display formatting
- api.py: FastAPI endpoints
"""
from .engine import (
    PresenceEngine, PresenceState, PresenceStatus, Activity,
    get_presence_engine, get_presence_status,
    log_activity, set_current_activity, queue_item
)
from .status import (
    get_state_emoji, get_state_label,
    format_status_text, format_status_short, format_status_json, format_status_card,
    get_status_for_telegram, get_status_for_api, get_status_short
)
from .api import router as presence_router

__all__ = [
    # Engine
    'PresenceEngine', 'PresenceState', 'PresenceStatus', 'Activity',
    'get_presence_engine', 'get_presence_status',
    'log_activity', 'set_current_activity', 'queue_item',
    # Status
    'get_state_emoji', 'get_state_label',
    'format_status_text', 'format_status_short', 'format_status_json', 'format_status_card',
    'get_status_for_telegram', 'get_status_for_api',
    # API
    'presence_router'
]








