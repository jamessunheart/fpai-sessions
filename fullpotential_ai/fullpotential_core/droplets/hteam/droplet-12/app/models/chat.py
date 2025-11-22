"""
Chat-Specific Models
Per Spec requirements
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import uuid


class ChatRequest(BaseModel):
    """
    Direct chat request from web/mobile clients.
    Per Spec - POST /chat endpoint.
    """
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator("message")
    def validate_message(cls, v):
        """Ensure message is not empty"""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class ChatResponse(BaseModel):
    """
    Response to chat request.
    Per Spec - POST /chat endpoint response.
    """
    response: str
    session_id: str
    trace_id: str
    timestamp: str
    
    @validator("timestamp", pre=True, always=True)
    def set_timestamp(cls, v):
        if v is None or v == "":
            return datetime.utcnow().isoformat() + "Z"
        return v
    
    @validator("trace_id", pre=True, always=True)
    def set_trace_id(cls, v):
        if v is None or v == "":
            return str(uuid.uuid4())
        return v


class ProcessRequest(BaseModel):
    """
    Process request from Voice Droplet (via Orchestrator).
    Per Spec - POST /process endpoint (MessageEnvelope format).
    """
    trace_id: str
    source: str  # Source droplet ID (e.g., "18" for Voice)
    target: str  # Target droplet ID (always "12" for this droplet)
    message_type: Literal["command", "query", "response"]
    payload: Dict[str, Any]
    timestamp: str
    route_back: Optional[str] = None  # Where to send response
    
    @validator("trace_id")
    def validate_trace_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("trace_id must be valid UUID")
        return v


class ProcessResponse(BaseModel):
    """
    Response to process request.
    Per Spec - returns MessageEnvelope format.
    """
    trace_id: str
    source: str  # This droplet ("12")
    target: str  # Where response goes
    message_type: Literal["response"] = "response"
    payload: Dict[str, Any]
    timestamp: str
    
    @validator("timestamp", pre=True, always=True)
    def set_timestamp(cls, v):
        if v is None or v == "":
            return datetime.utcnow().isoformat() + "Z"
        return v


class AnalyzeRequest(BaseModel):
    """
    Text analysis request (stateless).
    Per Spec - POST /analyze endpoint.
    """
    text: str = Field(..., min_length=1, max_length=5000)
    
    @validator("text")
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()


class AnalyzeResponse(BaseModel):
    """
    Analysis result.
    Per Spec - POST /analyze endpoint response.
    """
    analysis: Dict[str, Any]
    timestamp: str
    
    @validator("timestamp", pre=True, always=True)
    def set_timestamp(cls, v):
        if v is None or v == "":
            return datetime.utcnow().isoformat() + "Z"
        return v


class WebSocketMessage(BaseModel):
    """
    WebSocket message format.
    Per Spec - WebSocket communication.
    """
    type: Literal["message", "typing", "error", "welcome"]
    content: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    @validator("timestamp", pre=True, always=True)
    def set_timestamp(cls, v):
        if v is None or v == "":
            return datetime.utcnow().isoformat() + "Z"
        return v


class SessionInfo(BaseModel):
    """
    Session information.
    Per Spec - session management.
    """
    session_id: str
    source: Literal["chat", "voice"]
    created_at: str
    last_activity: str
    message_count: int
    metadata: Optional[Dict[str, Any]] = None


class SessionListResponse(BaseModel):
    """
    List of active sessions.
    Per Spec - GET /sessions endpoint.
    """
    sessions: List[SessionInfo]
    total: int


class ReasoningResult(BaseModel):
    """
    AI reasoning result from Gemini.
    Internal model for reasoning engine.
    """
    reasoning: str
    action_type: Literal["single_query", "multiple_queries", "needs_clarification", "error"]
    needs_clarification: bool
    clarification_message: Optional[str] = None
    queries: List[Dict[str, Any]] = []


class Query(BaseModel):
    """
    Single query to execute via Orchestrator.
    Internal model for query execution.
    """
    droplet: str  # e.g., "droplet_1"
    endpoint: str  # e.g., "getAll"
    method: Literal["GET", "POST"]
    needs_data: bool
    extracted_data: Dict[str, Any] = {}
    confidence: float = 0.0