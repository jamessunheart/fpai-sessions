#!/usr/bin/env python3
"""
Signal Consolidation Module
===========================
All inputs → one stream → what matters now.

Components:
- engine.py: Central signal processor
- priority.py: Priority framework
- contacts.py: Contact/relationship management
- gmail.py: Gmail integration
- calendar.py: Calendar integration
"""
from .engine import (
    SignalEngine, Signal, SignalStatus, SignalAction,
    get_signal_engine, process_signal, poll_channels
)
from .priority import (
    PriorityFramework, PriorityLevel, PriorityResult,
    get_priority_framework, calculate_priority
)
from .contacts import (
    ContactManager, Contact,
    get_contact_manager, find_contact, get_contact_info
)
from .gmail import (
    GmailClient, Email,
    get_gmail_client, fetch_unread_emails
)
from .calendar import (
    CalendarClient, CalendarEvent,
    get_calendar_client, get_upcoming_events, get_heads_up_events, check_availability
)

__all__ = [
    # Engine
    'SignalEngine', 'Signal', 'SignalStatus', 'SignalAction',
    'get_signal_engine', 'process_signal', 'poll_channels',
    # Priority
    'PriorityFramework', 'PriorityLevel', 'PriorityResult',
    'get_priority_framework', 'calculate_priority',
    # Contacts
    'ContactManager', 'Contact',
    'get_contact_manager', 'find_contact', 'get_contact_info',
    # Gmail
    'GmailClient', 'Email',
    'get_gmail_client', 'fetch_unread_emails',
    # Calendar
    'CalendarClient', 'CalendarEvent',
    'get_calendar_client', 'get_upcoming_events', 'get_heads_up_events', 'check_availability'
]








