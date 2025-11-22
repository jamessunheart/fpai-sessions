"""
UDC (Universal Droplet Contract) Standard Models - UPDATED EXAMPLES
Pydantic models for UDC v1.0 compliance with comprehensive examples
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DropletStatus(str, Enum):
    """Valid droplet status values per UDC spec"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class MessageType(str, Enum):
    """UDC message types"""
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    EVENT = "event"
    HEARTBEAT = "heartbeat"


class HealthResponse(BaseModel):
    """GET /health response per UDC spec"""
    id: int = Field(..., description="Droplet ID")
    name: str = Field(..., description="Droplet name")
    steward: str = Field(..., description="Droplet steward")
    status: DropletStatus = Field(..., description="Current operational status")
    endpoint: str = Field(..., description="Droplet base URL")
    updated_at: datetime = Field(..., description="Last status update timestamp")
    message: Optional[str] = Field(None, description="Optional status message")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 10,
                "name": "Orchestrator",
                "steward": "Tnsae",
                "status": "active",
                "endpoint": "https://orchestrator.fullpotential.ai",
                "updated_at": "2025-11-14T10:30:00Z",
                "message": "All systems operational"
            }
        }


class CapabilitiesResponse(BaseModel):
    """GET /capabilities response per UDC spec"""
    version: str = Field(..., description="Droplet version")
    features: List[str] = Field(..., description="List of supported features")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    udc_version: str = Field("1.0", description="UDC specification version")

    class Config:
        json_schema_extra = {
            "example": {
                "version": "2.0.0",
                "features": [
                    "task_routing",
                    "droplet_discovery",
                    "health_monitoring",
                    "workflow_management",
                    "real_time_updates"
                ],
                "dependencies": ["registry", "dashboard"],
                "udc_version": "1.0"
            }
        }


class StateResponse(BaseModel):
    """GET /state response per UDC spec"""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_mb: int = Field(..., description="Memory usage in megabytes")
    uptime_seconds: int = Field(..., description="Uptime in seconds")
    custom_metrics: Dict[str, Any] = Field(default_factory=dict, description="Additional metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "cpu_percent": 15.3,
                "memory_mb": 768,
                "uptime_seconds": 432000,
                "custom_metrics": {
                    "tasks_active": 12,
                    "tasks_pending": 5,
                    "droplets_active": 8,
                    "droplets_total": 10
                }
            }
        }


class DependencyInfo(BaseModel):
    """Dependency information for GET /dependencies"""
    id: int = Field(..., description="Dependent droplet ID")
    name: str = Field(..., description="Dependent droplet name")
    status: str = Field(..., description="Connection status")
    last_check: Optional[datetime] = Field(None, description="Last health check")


class DependenciesResponse(BaseModel):
    """GET /dependencies response per UDC spec"""
    required: List[DependencyInfo] = Field(default_factory=list, description="Required dependencies")
    optional: List[DependencyInfo] = Field(default_factory=list, description="Optional dependencies")
    missing: List[str] = Field(default_factory=list, description="Missing dependencies")

    class Config:
        json_schema_extra = {
            "example": {
                "required": [
                    {"id": 3, "name": "Registry v2", "status": "connected", "last_check": "2025-11-14T10:30:00Z"}
                ],
                "optional": [
                    {"id": 5, "name": "Dashboard", "status": "connected", "last_check": "2025-11-14T10:29:00Z"},
                    {"id": 8, "name": "Verifier", "status": "connected", "last_check": "2025-11-14T10:28:00Z"}
                ],
                "missing": []
            }
        }


class UDCMessage(BaseModel):
    """POST /message request body per UDC spec"""
    trace_id: UUID = Field(..., description="Unique trace ID for request tracking")
    source: int = Field(..., description="Source droplet ID")
    target: int = Field(..., description="Target droplet ID")
    message_type: MessageType = Field(..., description="Type of message")
    payload: Dict[str, Any] = Field(..., description="Message payload")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": 5,
                "target": 10,
                "message_type": "command",
                "payload": {
                    "command": "create_task",
                    "task_data": {
                        "task_type": "verify",
                        "title": "Verify Droplet #14",
                        "priority": 3,
                        "payload": {
                            "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md",
                            "code_url": "https://github.com/fullpotential-ai/droplet-14"
                        }
                    }
                },
                "timestamp": "2025-11-14T10:30:00Z"
            }
        }


class UDCMessageResponse(BaseModel):
    """POST /message response per UDC spec"""
    received: bool = Field(..., description="Whether message was received")
    trace_id: UUID = Field(..., description="Original trace ID")
    processed_at: datetime = Field(..., description="Processing timestamp")
    result: Any = Field(None, description="Processing result")
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-10",
                "target": "droplet-5",
                "message_type": "response",
                "timestamp": "2025-11-14T10:30:01Z",
                "payload": {
                    "received": True,
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                    "processed_at": "2025-11-14T10:30:05Z",
                    "result": {
                        "command": "create_task",
                        "task_id": 123,
                        "status": "pending"
                    },
                    "error": None
                }
            }
        }


class SendMessageRequest(BaseModel):
    """POST /send request for sending messages to other droplets"""
    target_droplet_id: int = Field(..., description="Target droplet ID")
    message_type: MessageType = Field(..., description="Type of message")
    payload: Dict[str, Any] = Field(..., description="Message payload")

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-5",
                "target": "droplet-10",
                "message_type": "command",
                "timestamp": "2025-11-14T10:30:00Z",
                "payload": {
                    "target_droplet_id": 8,
                    "message_type": "command",
                    "payload": {
                        "command": "verify_code",
                        "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md",
                        "code_url": "https://github.com/fullpotential-ai/droplet-14"
                    }
                }
            }
        }


class SendMessageResponse(BaseModel):
    """POST /send response"""
    sent: bool = Field(..., description="Whether message was sent")
    trace_id: UUID = Field(..., description="Trace ID for tracking")
    target_droplet: str = Field(..., description="Target droplet name")
    timestamp: datetime = Field(..., description="Send timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-10",
                "target": "droplet-5",
                "message_type": "response",
                "timestamp": "2025-11-14T10:30:01Z",
                "payload": {
                    "sent": True,
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                    "target_droplet": "Verifier",
                    "target_droplet_id": 8,
                    "message_delivered_at": "2025-11-14T10:30:00Z"
                }
            }
        }


# ============================================================================
# UDC ENVELOPE WRAPPER (for documentation)
# ============================================================================

class UDCEnvelope(BaseModel):
    """
    Complete UDC message envelope structure
    
    This is the standard wrapper for ALL inter-droplet communication.
    """
    udc_version: str = Field("1.0", description="UDC protocol version")
    trace_id: str = Field(..., description="Unique trace ID (UUID)")
    source: str = Field(..., description="Source droplet identifier")
    target: str = Field(..., description="Target droplet identifier")
    message_type: str = Field(..., description="Message type (command, query, response, event, heartbeat)")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    payload: Dict[str, Any] = Field(..., description="Actual message content")

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-5",
                "target": "droplet-10",
                "message_type": "command",
                "timestamp": "2025-11-14T10:30:00.123456Z",
                "payload": {
                    "task_type": "verify",
                    "title": "Verify Droplet #14 code",
                    "description": "Full UDC compliance verification",
                    "required_capability": "code_verification",
                    "priority": 3,
                    "payload": {
                        "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md",
                        "code_url": "https://github.com/fullpotential-ai/droplet-14",
                        "verification_level": "strict"
                    },
                    "deadline": "2025-11-14T12:00:00Z",
                    "max_retries": 3,
                    "created_by": "droplet-5"
                }
            }
        }


class UDCErrorResponse(BaseModel):
    """
    Standard UDC error response structure
    """
    udc_version: str = Field("1.0", description="UDC protocol version")
    trace_id: str = Field(..., description="Original trace ID")
    source: str = Field(..., description="Source droplet identifier")
    target: str = Field(..., description="Target droplet identifier")
    message_type: str = Field("error", description="Always 'error' for error responses")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    payload: Dict[str, Any] = Field(..., description="Error details")

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-10",
                "target": "droplet-5",
                "message_type": "error",
                "timestamp": "2025-11-14T10:30:01.234567Z",
                "payload": {
                    "status": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Task 123 not found",
                        "details": {
                            "task_id": 123,
                            "searched_in": "tasks_table",
                            "suggestion": "Verify task ID is correct"
                        }
                    },
                    "timestamp": "2025-11-14T10:30:01.234567Z"
                }
            }
        }


# ============================================================================
# STANDARD ERROR CODES (for documentation)
# ============================================================================

class UDCErrorCodes:
    """
    Standard UDC error codes
    
    Use these consistently across all droplets for interoperability.
    """
    INVALID_REQUEST = "INVALID_REQUEST"  # Malformed request or missing required fields
    UNAUTHORIZED = "UNAUTHORIZED"  # Missing or invalid JWT token
    FORBIDDEN = "FORBIDDEN"  # Valid JWT but insufficient permissions
    NOT_FOUND = "NOT_FOUND"  # Requested resource doesn't exist
    CONFLICT = "CONFLICT"  # Resource already exists or state conflict
    RATE_LIMITED = "RATE_LIMITED"  # Too many requests
    INTERNAL_ERROR = "INTERNAL_ERROR"  # Server error
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"  # Required droplet offline
    TIMEOUT = "TIMEOUT"  # Operation timed out
    VALIDATION_ERROR = "VALIDATION_ERROR"  # Request validation failed


# ============================================================================
# USAGE EXAMPLES (for documentation)
# ============================================================================

class UDCUsageExamples:
    """
    Comprehensive examples of UDC message patterns
    """
    
    CREATE_TASK_REQUEST = {
        "udc_version": "1.0",
        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
        "source": "droplet-5",
        "target": "droplet-10",
        "message_type": "command",
        "timestamp": "2025-11-14T10:30:00Z",
        "payload": {
            "task_type": "verify",
            "title": "Verify Droplet #14 code",
            "priority": 3,
            "payload": {
                "spec_url": "https://...",
                "code_url": "https://..."
            }
        }
    }
    
    CREATE_TASK_RESPONSE = {
        "udc_version": "1.0",
        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
        "source": "droplet-10",
        "target": "droplet-5",
        "message_type": "response",
        "timestamp": "2025-11-14T10:30:01Z",
        "payload": {
            "task_id": 123,
            "trace_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "pending",
            "created_at": "2025-11-14T10:30:00Z"
        }
    }
    
    QUERY_TASK_STATUS = {
        "udc_version": "1.0",
        "trace_id": "550e8400-e29b-41d4-a716-446655440001",
        "source": "droplet-5",
        "target": "droplet-10",
        "message_type": "query",
        "timestamp": "2025-11-14T10:35:00Z",
        "payload": {
            "query": "task_status",
            "task_id": 123
        }
    }
    
    TASK_COMPLETED_EVENT = {
        "udc_version": "1.0",
        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
        "source": "droplet-10",
        "target": "broadcast",
        "message_type": "event",
        "timestamp": "2025-11-14T10:45:00Z",
        "payload": {
            "event": "task_completed",
            "task_id": 123,
            "result": {
                "compliant": True,
                "issues_found": 0
            }
        }
    }
    
    ERROR_RESPONSE = {
        "udc_version": "1.0",
        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
        "source": "droplet-10",
        "target": "droplet-5",
        "message_type": "error",
        "timestamp": "2025-11-14T10:30:01Z",
        "payload": {
            "status": "error",
            "error": {
                "code": "NOT_FOUND",
                "message": "Task 999 not found",
                "details": {"task_id": 999}
            }
        }
    }