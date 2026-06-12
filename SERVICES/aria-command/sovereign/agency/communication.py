#!/usr/bin/env python3
"""
ARIA ASCENSION - COMMUNICATION HUB
==================================

Handle external communications:
- Email (SMTP/API)
- SMS (Twilio)
- Calendar (Google Calendar API)
- Slack/Discord messages

Approval Levels:
- Read calendar: Auto
- Notify James: Auto
- External email: Requires approval
"""

import os
import json
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.agency.communication")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Email
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "aria@fullpotential.ai")

# Twilio
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM_NUMBER", "")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
JAMES_CHAT_ID = os.getenv("JAMES_CHAT_ID", "")


class ApprovalLevel(str, Enum):
    """Approval levels for actions."""
    AUTO = "auto"            # No approval needed
    NOTIFY = "notify"        # Send, notify James after
    APPROVE = "approve"      # Requires approval before
    CONFIRM = "confirm"      # Requires approval + confirmation


@dataclass
class CommunicationAction:
    """A pending or completed communication action."""
    id: str
    action_type: str  # email, sms, calendar, slack
    recipient: str
    subject: str
    content: str
    approval_level: ApprovalLevel
    status: str = "pending"  # pending, approved, sent, rejected
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: datetime = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "recipient": self.recipient,
            "subject": self.subject,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "approval_level": self.approval_level.value,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }


# ============================================================================
# COMMUNICATION HUB
# ============================================================================

class CommunicationHub:
    """
    Central hub for all external communications.
    """
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.pending_actions: Dict[str, CommunicationAction] = {}
        self._approval_callback: Optional[callable] = None
    
    def set_approval_callback(self, callback: callable):
        """Set callback for requesting approvals."""
        self._approval_callback = callback
    
    # ========================================================================
    # EMAIL
    # ========================================================================
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Approval rules:
        - To James: Auto
        - To external: Requires approval
        """
        # Determine approval level
        is_internal = to.endswith("@fullpotential.ai") or "james" in to.lower()
        approval_level = ApprovalLevel.AUTO if (is_internal and not require_approval) else ApprovalLevel.APPROVE
        
        action = CommunicationAction(
            id=f"email-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            action_type="email",
            recipient=to,
            subject=subject,
            content=body,
            approval_level=approval_level
        )
        
        if approval_level == ApprovalLevel.APPROVE:
            self.pending_actions[action.id] = action
            
            if self._approval_callback:
                await self._approval_callback(action)
            
            return {
                "status": "pending_approval",
                "action_id": action.id,
                "message": f"Email to {to} requires approval"
            }
        
        # Send immediately
        return await self._send_email_now(action)
    
    async def _send_email_now(self, action: CommunicationAction) -> Dict[str, Any]:
        """Actually send the email."""
        if not SMTP_USER:
            return {"status": "error", "message": "SMTP not configured"}
        
        try:
            msg = MIMEMultipart()
            msg['From'] = DEFAULT_FROM_EMAIL
            msg['To'] = action.recipient
            msg['Subject'] = action.subject
            msg.attach(MIMEText(action.content, 'plain'))
            
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            
            action.status = "sent"
            action.sent_at = datetime.now()
            
            return {
                "status": "sent",
                "action_id": action.id,
                "message": f"Email sent to {action.recipient}"
            }
        
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return {"status": "error", "message": str(e)}
    
    # ========================================================================
    # SMS (TWILIO)
    # ========================================================================
    
    async def send_sms(
        self,
        to: str,
        message: str,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Send an SMS via Twilio.
        """
        # SMS always requires approval unless to James's number
        is_james = to.endswith(os.getenv("JAMES_PHONE", "0000")[-4:])
        approval_level = ApprovalLevel.AUTO if is_james else ApprovalLevel.APPROVE
        
        action = CommunicationAction(
            id=f"sms-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            action_type="sms",
            recipient=to,
            subject="SMS",
            content=message,
            approval_level=approval_level
        )
        
        if approval_level == ApprovalLevel.APPROVE and require_approval:
            self.pending_actions[action.id] = action
            
            if self._approval_callback:
                await self._approval_callback(action)
            
            return {
                "status": "pending_approval",
                "action_id": action.id
            }
        
        return await self._send_sms_now(action)
    
    async def _send_sms_now(self, action: CommunicationAction) -> Dict[str, Any]:
        """Actually send SMS via Twilio."""
        if not TWILIO_SID or not TWILIO_TOKEN:
            return {"status": "error", "message": "Twilio not configured"}
        
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
            
            response = await self.http_client.post(
                url,
                auth=(TWILIO_SID, TWILIO_TOKEN),
                data={
                    "To": action.recipient,
                    "From": TWILIO_FROM,
                    "Body": action.content
                }
            )
            
            if response.status_code in [200, 201]:
                action.status = "sent"
                action.sent_at = datetime.now()
                return {"status": "sent", "action_id": action.id}
            else:
                return {"status": "error", "message": response.text}
        
        except Exception as e:
            logger.error(f"SMS send error: {e}")
            return {"status": "error", "message": str(e)}
    
    # ========================================================================
    # CALENDAR
    # ========================================================================
    
    async def create_calendar_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime = None,
        description: str = "",
        attendees: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a calendar event.
        
        Note: Requires Google Calendar API integration.
        Currently returns placeholder response.
        """
        if end_time is None:
            end_time = start_time + timedelta(hours=1)
        
        action = CommunicationAction(
            id=f"cal-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            action_type="calendar",
            recipient=",".join(attendees or []),
            subject=title,
            content=description,
            approval_level=ApprovalLevel.APPROVE if attendees else ApprovalLevel.AUTO,
            metadata={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "attendees": attendees or []
            }
        )
        
        # If has external attendees, require approval
        if attendees and action.approval_level == ApprovalLevel.APPROVE:
            self.pending_actions[action.id] = action
            
            if self._approval_callback:
                await self._approval_callback(action)
            
            return {
                "status": "pending_approval",
                "action_id": action.id,
                "message": "Calendar event with attendees requires approval"
            }
        
        # Would integrate with Google Calendar API here
        return {
            "status": "created",
            "action_id": action.id,
            "message": f"Event '{title}' scheduled for {start_time.strftime('%Y-%m-%d %H:%M')}",
            "note": "Calendar API integration pending"
        }
    
    async def get_calendar_events(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[Dict]:
        """Get calendar events (read-only, auto-approved)."""
        # Would integrate with Google Calendar API
        return {
            "status": "success",
            "events": [],
            "note": "Calendar API integration pending"
        }
    
    # ========================================================================
    # TELEGRAM (INTERNAL)
    # ========================================================================
    
    async def send_telegram(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = "Markdown"
    ) -> Dict[str, Any]:
        """
        Send a Telegram message.
        Internal communication - auto-approved.
        """
        if not TELEGRAM_BOT_TOKEN:
            return {"status": "error", "message": "Telegram not configured"}
        
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            
            response = await self.http_client.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            })
            
            if response.status_code == 200:
                return {"status": "sent", "message": "Telegram message sent"}
            else:
                return {"status": "error", "message": response.text}
        
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return {"status": "error", "message": str(e)}
    
    # ========================================================================
    # APPROVAL MANAGEMENT
    # ========================================================================
    
    async def approve_action(self, action_id: str) -> Dict[str, Any]:
        """Approve a pending action."""
        if action_id not in self.pending_actions:
            return {"status": "error", "message": "Action not found"}
        
        action = self.pending_actions[action_id]
        
        # Execute based on type
        if action.action_type == "email":
            result = await self._send_email_now(action)
        elif action.action_type == "sms":
            result = await self._send_sms_now(action)
        else:
            result = {"status": "error", "message": f"Unknown action type: {action.action_type}"}
        
        # Remove from pending
        if result.get("status") == "sent":
            del self.pending_actions[action_id]
        
        return result
    
    async def reject_action(self, action_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a pending action."""
        if action_id not in self.pending_actions:
            return {"status": "error", "message": "Action not found"}
        
        action = self.pending_actions[action_id]
        action.status = "rejected"
        
        del self.pending_actions[action_id]
        
        return {"status": "rejected", "action_id": action_id, "reason": reason}
    
    def get_pending_actions(self) -> List[Dict]:
        """Get all pending actions."""
        return [action.to_dict() for action in self.pending_actions.values()]


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_hub: Optional[CommunicationHub] = None


def get_communication_hub() -> CommunicationHub:
    """Get global communication hub."""
    global _hub
    if _hub is None:
        _hub = CommunicationHub()
    return _hub


async def send_email(to: str, subject: str, body: str, **kwargs) -> Dict:
    """Send an email."""
    return await get_communication_hub().send_email(to, subject, body, **kwargs)


async def send_sms(to: str, message: str, **kwargs) -> Dict:
    """Send an SMS."""
    return await get_communication_hub().send_sms(to, message, **kwargs)


async def create_calendar_event(title: str, start_time: datetime, **kwargs) -> Dict:
    """Create a calendar event."""
    return await get_communication_hub().create_calendar_event(title, start_time, **kwargs)


