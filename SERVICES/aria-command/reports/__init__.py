#!/usr/bin/env python3
"""
Reports Module
==============
Proactive reporting system for Full Potential.

Report Types:
- Morning Brief: Start of day summary
- Progress: Task completed notification
- Status: Periodic check-in
- Heads Up: Upcoming event reminder
- Decision: Needs human input
- Digest: End of day summary
"""
from .engine import (
    ReportEngine, get_report_engine,
    send_morning_brief, send_status, send_digest,
    send_progress, send_quick, check_scheduled_reports
)
from .templates import (
    ReportData,
    format_morning_brief, format_progress_report, format_status_report,
    format_heads_up, format_decision_request, format_digest,
    quick_status, quick_progress, quick_alert
)
from .scheduler import (
    ReportScheduler, ReportType, get_scheduler
)
from .delivery import (
    ReportDelivery, get_delivery,
    deliver_report, deliver_report_sync
)

__all__ = [
    # Engine
    'ReportEngine', 'get_report_engine',
    'send_morning_brief', 'send_status', 'send_digest',
    'send_progress', 'send_quick', 'check_scheduled_reports',
    # Templates
    'ReportData',
    'format_morning_brief', 'format_progress_report', 'format_status_report',
    'format_heads_up', 'format_decision_request', 'format_digest',
    'quick_status', 'quick_progress', 'quick_alert',
    # Scheduler
    'ReportScheduler', 'ReportType', 'get_scheduler',
    # Delivery
    'ReportDelivery', 'get_delivery',
    'deliver_report', 'deliver_report_sync'
]








