"""
Data models for Alerts Service
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class NotificationChannel(str, Enum):
    """Supported notification channels"""
    TELEGRAM = "telegram"
    SMS = "sms"
    EMAIL = "email"


class SendNotificationRequest(BaseModel):
    """Request to send a notification"""
    channel: NotificationChannel
    recipient: str = Field(..., description="Chat ID, phone number, or email")
    message: str = Field(..., description="Message content")
    priority: NotificationPriority = NotificationPriority.NORMAL


class SendTemplateRequest(BaseModel):
    """Request to send a templated notification"""
    template: str = Field(..., description="Template name")
    recipient: str = Field(..., description="Chat ID, phone number, or email")
    data: Dict[str, Any] = Field(default_factory=dict, description="Template data")
    channel: NotificationChannel = NotificationChannel.TELEGRAM
    priority: NotificationPriority = NotificationPriority.NORMAL


class NotificationResponse(BaseModel):
    """Response after queuing a notification"""
    message_id: str
    status: NotificationStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UDCMessage(BaseModel):
    """UDC-compliant message format"""
    from_service: str
    message_type: str
    payload: Dict[str, Any]


class QueuedNotification(BaseModel):
    """Internal representation of a queued notification"""
    message_id: str
    channel: NotificationChannel
    recipient: str
    message: str
    priority: NotificationPriority
    status: NotificationStatus
    created_at: datetime
    retry_count: int = 0
    last_error: Optional[str] = None
