#!/usr/bin/env python3
"""
AI-to-AI Protocol Module
========================
Enables AI-to-AI communication for coordination without human involvement.

Components:
- engine.py: Core protocol engine
- negotiation.py: Scheduling negotiation
- exchange.py: Information exchange
- escalation.py: Human escalation triggers
"""
from .engine import (
    AIProtocolEngine, AIConversation, AIMessage,
    ConversationStatus, MessageType,
    get_protocol_engine
)
from .negotiation import (
    ScheduleNegotiator, get_negotiator
)
from .exchange import (
    InfoExchanger, get_exchanger
)
from .escalation import (
    AIEscalation, AIEscalationReason, get_ai_escalation
)

__all__ = [
    # Engine
    'AIProtocolEngine', 'AIConversation', 'AIMessage',
    'ConversationStatus', 'MessageType',
    'get_protocol_engine',
    # Negotiation
    'ScheduleNegotiator', 'get_negotiator',
    # Exchange
    'InfoExchanger', 'get_exchanger',
    # Escalation
    'AIEscalation', 'AIEscalationReason', 'get_ai_escalation'
]








