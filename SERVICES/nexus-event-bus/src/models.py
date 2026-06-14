"""Data models for NEXUS event bus"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class EventType(str, Enum):
    """Event type enumeration"""
    SESSION_CONNECTED = "session.connected"
    SESSION_DISCONNECTED = "session.disconnected"
    WORK_CLAIMED = "work.claimed"
    WORK_COMPLETED = "work.completed"
    WORK_RELEASED = "work.released"
    HELP_NEEDED = "help.needed"
    CAPABILITY_BROADCAST = "capability.broadcast"
    STATUS_UPDATE = "status.update"
    MESSAGE_BROADCAST = "message.broadcast"
    MESSAGE_DIRECT = "message.direct"


class Event(BaseModel):
    """Event model for pub/sub system"""
    event_id: str = Field(description="Unique event identifier")
    event_type: EventType = Field(description="Type of event")
    session_id: str = Field(description="Session that published the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    ttl: int = Field(default=3600, description="Time to live in seconds")


class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    OFFLINE = "offline"


class ConnectedSession(BaseModel):
    """Model for a connected session"""
    session_id: str
    role: str
    subscribed_topics: List[str] = Field(default_factory=list)
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_event: Optional[datetime] = None
    current_work: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE


class WorkClaimStatus(str, Enum):
    """Work claim status"""
    CLAIMED = "claimed"
    COMPLETED = "completed"
    RELEASED = "released"


class WorkClaim(BaseModel):
    """Model for work claims"""
    work_id: str
    claimed_by: str
    claimed_at: datetime = Field(default_factory=datetime.utcnow)
    description: str
    status: WorkClaimStatus = WorkClaimStatus.CLAIMED
    completed_at: Optional[datetime] = None


class SubscribeRequest(BaseModel):
    """WebSocket subscribe request"""
    action: str = "subscribe"
    topics: List[str] = Field(description="Topics to subscribe to (supports wildcards)")


class PublishRequest(BaseModel):
    """WebSocket publish request"""
    action: str = "publish"
    event_type: EventType
    payload: Dict[str, Any] = Field(default_factory=dict)


class EventHistoryQuery(BaseModel):
    """Query parameters for event history"""
    since: Optional[datetime] = None
    event_type: Optional[str] = None
    limit: int = Field(default=100, le=1000)


class HealthResponse(BaseModel):
    """UDC /health response"""
    status: str = "active"
    service: str = "nexus-event-bus"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CapabilitiesResponse(BaseModel):
    """UDC /capabilities response"""
    version: str = "1.0.0"
    features: List[str]
    dependencies: List[str]
    udc_version: str = "1.0"
    metadata: Dict[str, Any]


class StateResponse(BaseModel):
    """UDC /state response"""
    uptime_seconds: int
    connected_sessions: int
    events_total: int
    events_per_second: float
    errors_last_hour: int
    last_restart: datetime
    event_latency_ms: float


class DependencyStatus(BaseModel):
    """Dependency status model"""
    name: str
    status: str
    url: Optional[str] = None
    path: Optional[str] = None


class DependenciesResponse(BaseModel):
    """UDC /dependencies response"""
    required: List[DependencyStatus]
    optional: List[DependencyStatus]
    missing: List[str]


class InterDropletMessage(BaseModel):
    """UDC /message request"""
    trace_id: str
    source: str
    target: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime


class HelpRequest(BaseModel):
    """Help request model"""
    task: str
    capabilities_needed: List[str] = Field(default_factory=list)
    priority: str = "normal"
    context: Optional[str] = None


class WorkClaimRequest(BaseModel):
    """Work claim request"""
    session_id: str
    work_id: str
    work_description: str
