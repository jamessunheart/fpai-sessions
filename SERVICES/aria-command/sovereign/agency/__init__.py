#!/usr/bin/env python3
"""
ARIA ASCENSION - REAL-WORLD AGENCY
==================================

Take actions beyond the codebase:
- Communication: Email, calendar, SMS, Slack
- Financial: Payments, invoices, expenses
- Social: Posts, scheduling, monitoring

Approval Levels:
- Read operations: Auto
- Notify James: Auto
- External communication: Requires approval
- Financial: Requires approval + confirmation
"""

from .communication import (
    CommunicationHub,
    get_communication_hub,
    send_email,
    send_sms,
    create_calendar_event
)

from .financial import (
    FinancialHub,
    get_financial_hub,
    get_balances,
    request_payment
)

__all__ = [
    "CommunicationHub",
    "get_communication_hub",
    "send_email",
    "send_sms",
    "create_calendar_event",
    "FinancialHub",
    "get_financial_hub",
    "get_balances",
    "request_payment"
]


