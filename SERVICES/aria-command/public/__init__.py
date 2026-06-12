#!/usr/bin/env python3
"""
Public Interface Module
=======================
"Talk to my AI" - public interface for reaching James through JAI.

Components:
- handler.py: Request processing
- responder.py: AI response generation
- escalation.py: Escalation logic
- interface.py: FastAPI routes and chat UI
"""
from .handler import (
    PublicHandler, PublicRequest, RequestType, RequestPriority,
    get_handler
)
from .responder import (
    PublicResponder, get_responder, generate_response
)
from .escalation import (
    EscalationEngine, EscalationReason, get_escalation_engine
)
from .interface import router as public_router

__all__ = [
    # Handler
    'PublicHandler', 'PublicRequest', 'RequestType', 'RequestPriority',
    'get_handler',
    # Responder
    'PublicResponder', 'get_responder', 'generate_response',
    # Escalation
    'EscalationEngine', 'EscalationReason', 'get_escalation_engine',
    # API
    'public_router'
]








