"""
Orchestrator Domain Models - UPDATED WITH UDC EXAMPLES
Pydantic models for task and droplet management with UDC-compliant examples
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    """Valid task status values"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Common task types"""
    VERIFY = "verify"
    BUILD = "build"
    DEPLOY = "deploy"
    MONITOR = "monitor"
    PROVISION = "provision"
    CUSTOM = "custom"


# ============================================================================
# TASK MODELS
# ============================================================================

class TaskCreate(BaseModel):
    """Request model for creating a new task"""
    task_type: str = Field(..., min_length=1, max_length=50, description="Type of task")
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Detailed task description")
    required_capability: Optional[str] = Field(None, max_length=100, description="Required droplet capability")
    priority: int = Field(5, ge=1, le=10, description="Task priority (1=highest, 10=lowest)")
    payload: Dict[str, Any] = Field(..., description="Task-specific data")
    deadline: Optional[datetime] = Field(None, description="Task deadline")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    created_by: Optional[str] = Field(None, description="Creator identifier")

    @field_validator('payload')
    @classmethod
    def validate_payload_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure payload is not too large"""
        import json
        payload_str = json.dumps(v)
        if len(payload_str) > 1_000_000:  # 1MB limit
            raise ValueError("Payload exceeds 1MB limit")
        return v

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
                    "task_type": "verify",
                    "title": "Verify Droplet #14 code",
                    "description": "UDC compliance check",
                    "required_capability": "code_verification",
                    "priority": 3,
                    "payload": {
                        "spec_url": "https://github.com/fullpotential-ai/specs/droplet-14.md",
                        "code_url": "https://github.com/fullpotential-ai/droplet-14"
                    },
                    "deadline": "2025-11-14T12:00:00Z",
                    "max_retries": 3
                }
            }
        }


class TaskUpdate(BaseModel):
    """Request model for updating task status"""
    status: TaskStatus = Field(..., description="New task status")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-8",
                "target": "droplet-10",
                "message_type": "command",
                "timestamp": "2025-11-14T10:35:00Z",
                "payload": {
                    "status": "in_progress",
                    "result": None,
                    "error_message": None
                }
            }
        }


class TaskResponse(BaseModel):
    """Response model for task details"""
    id: int
    trace_id: UUID
    task_type: str
    title: str
    description: Optional[str]
    payload: Dict[str, Any]
    status: TaskStatus
    priority: int
    required_capability: Optional[str]
    assigned_droplet_id: Optional[int]
    assigned_droplet_name: Optional[str]
    created_at: datetime
    assigned_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    deadline: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    created_by: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-10",
                "target": "droplet-5",
                "message_type": "response",
                "timestamp": "2025-11-14T10:30:01Z",
                "payload": {
                    "id": 123,
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                    "task_type": "verify",
                    "title": "Verify Droplet #14",
                    "description": "UDC compliance check",
                    "payload": {"spec_url": "https://..."},
                    "status": "in_progress",
                    "priority": 3,
                    "required_capability": "code_verification",
                    "assigned_droplet_id": 8,
                    "assigned_droplet_name": "Verifier",
                    "created_at": "2025-11-13T10:30:00Z",
                    "assigned_at": "2025-11-13T10:30:15Z",
                    "started_at": "2025-11-13T10:31:00Z",
                    "completed_at": None,
                    "deadline": "2025-11-14T12:00:00Z",
                    "result": None,
                    "error_message": None,
                    "retry_count": 0,
                    "max_retries": 3,
                    "created_by": "dashboard",
                    "updated_at": "2025-11-13T10:31:00Z"
                }
            }
        }


class TaskCreateResponse(BaseModel):
    """Response model for task creation"""
    task_id: int
    trace_id: UUID
    status: TaskStatus
    created_at: datetime
    estimated_assignment_seconds: int = Field(10, description="Estimated time until assignment")

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
                    "task_id": 123,
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "pending",
                    "created_at": "2025-11-13T10:30:00Z",
                    "estimated_assignment_seconds": 10
                }
            }
        }


class TaskListResponse(BaseModel):
    """Response model for task list"""
    tasks: List[TaskResponse]
    total: int
    limit: int
    offset: int

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
                    "tasks": [
                        {
                            "id": 123,
                            "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                            "task_type": "verify",
                            "title": "Verify Droplet #14",
                            "status": "pending",
                            "priority": 3
                        }
                    ],
                    "total": 1,
                    "limit": 50,
                    "offset": 0
                }
            }
        }


class TaskStateHistory(BaseModel):
    """Task state change history"""
    from_status: Optional[TaskStatus]
    to_status: TaskStatus
    changed_by: Optional[str]
    reason: Optional[str]
    changed_at: datetime


class TaskDetailedResponse(TaskResponse):
    """Detailed task response with state history"""
    state_history: List[TaskStateHistory]


# ============================================================================
# DROPLET MODELS
# ============================================================================

class DropletRegister(BaseModel):
    """Request model for droplet registration"""
    droplet_id: int = Field(..., gt=0, description="Unique droplet ID")
    name: str = Field(..., min_length=1, max_length=100, description="Droplet name")
    steward: Optional[str] = Field(None, max_length=100, description="Droplet steward")
    endpoint: str = Field(..., description="Droplet base URL")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities")

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-14",
                "target": "droplet-10",
                "message_type": "command",
                "timestamp": "2025-11-14T10:30:00Z",
                "payload": {
                    "droplet_id": 14,
                    "name": "Visibility Deck",
                    "steward": "Haythem",
                    "endpoint": "https://visibility.fullpotential.ai",
                    "capabilities": ["monitoring", "alerts", "snapshots"]
                }
            }
        }


class DropletRegisterResponse(BaseModel):
    """Response model for droplet registration"""
    registered: bool
    droplet_id: int
    registered_at: datetime
    heartbeat_required_every_seconds: int = 60

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-10",
                "target": "droplet-14",
                "message_type": "response",
                "timestamp": "2025-11-14T10:30:01Z",
                "payload": {
                    "registered": True,
                    "droplet_id": 14,
                    "registered_at": "2025-11-14T10:30:00Z",
                    "heartbeat_required_every_seconds": 60
                }
            }
        }


class DropletHeartbeat(BaseModel):
    """Request model for droplet heartbeat"""
    status: str = Field(..., description="Current droplet status")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-14",
                "target": "droplet-10",
                "message_type": "heartbeat",
                "timestamp": "2025-11-14T10:31:00Z",
                "payload": {
                    "status": "active",
                    "metrics": {
                        "cpu_percent": 23.4,
                        "memory_mb": 512,
                        "requests_per_minute": 42
                    }
                }
            }
        }


class DropletHeartbeatResponse(BaseModel):
    """Response model for heartbeat acknowledgment"""
    received: bool
    next_heartbeat_deadline: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-10",
                "target": "droplet-14",
                "message_type": "response",
                "timestamp": "2025-11-14T10:31:01Z",
                "payload": {
                    "received": True,
                    "next_heartbeat_deadline": "2025-11-14T10:32:00Z"
                }
            }
        }


class DropletInfo(BaseModel):
    """Droplet information"""
    id: int
    droplet_id: int
    name: str
    steward: Optional[str]
    endpoint: str
    capabilities: List[str]
    status: str
    last_heartbeat: Optional[datetime]
    registered_at: datetime
    seconds_since_heartbeat: Optional[float] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "udc_version": "1.0",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "droplet-10",
                "target": "droplet-5",
                "message_type": "response",
                "timestamp": "2025-11-14T10:30:01Z",
                "payload": {
                    "id": 5,
                    "droplet_id": 14,
                    "name": "Visibility Deck",
                    "steward": "Haythem",
                    "endpoint": "https://visibility.fullpotential.ai",
                    "capabilities": ["monitoring", "alerts", "snapshots"],
                    "status": "active",
                    "last_heartbeat": "2025-11-14T10:30:00Z",
                    "registered_at": "2025-11-13T09:00:00Z",
                    "seconds_since_heartbeat": 1.5
                }
            }
        }


class DropletListResponse(BaseModel):
    """Response model for droplet list"""
    droplets: List[DropletInfo]
    total: int

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
                    "droplets": [
                        {
                            "droplet_id": 14,
                            "name": "Visibility Deck",
                            "status": "active",
                            "capabilities": ["monitoring"]
                        }
                    ],
                    "total": 1
                }
            }
        }


class DropletTaskSummary(BaseModel):
    """Task summary for a droplet"""
    task_id: int
    status: TaskStatus
    task_type: str
    created_at: datetime


class DropletHealthHistory(BaseModel):
    """Health check history"""
    time: datetime
    status: str


class DropletDetailedResponse(DropletInfo):
    """Detailed droplet response with task history"""
    recent_tasks: List[DropletTaskSummary]
    health_history_24h: List[DropletHealthHistory]
    active_tasks_count: int
    completed_tasks_count: int
    failed_tasks_count: int


# ============================================================================
# METRICS MODELS
# ============================================================================

class MetricsSummary(BaseModel):
    """System-wide metrics summary"""
    tasks: Dict[str, Any]
    droplets: Dict[str, Any]
    system: Dict[str, Any]

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
                    "tasks": {
                        "total_created": 1523,
                        "completed": 1420,
                        "failed": 23,
                        "pending": 5,
                        "in_progress": 12,
                        "average_completion_seconds": 180,
                        "success_rate_percent": 98.4
                    },
                    "droplets": {
                        "total_registered": 10,
                        "active": 8,
                        "inactive": 1,
                        "error": 1
                    },
                    "system": {
                        "uptime_seconds": 432000,
                        "requests_per_minute": 150
                    }
                }
            }
        }


class TaskPerformanceMetrics(BaseModel):
    """Task performance metrics by type"""
    task_type: str
    time_range: str
    metrics: Dict[str, Any]

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
                    "task_type": "verify",
                    "time_range": "24h",
                    "metrics": {
                        "count": 50,
                        "success_rate": 96.0,
                        "average_duration_seconds": 120,
                        "p50_duration_seconds": 100,
                        "p95_duration_seconds": 180,
                        "p99_duration_seconds": 240
                    }
                }
            }
        }


class DropletPerformanceMetrics(BaseModel):
    """Droplet performance metrics"""
    droplet_id: int
    droplet_name: str
    time_range: str
    tasks_completed: int
    tasks_failed: int
    average_response_time_ms: float
    uptime_percent: float

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
                    "droplet_id": 14,
                    "droplet_name": "Visibility Deck",
                    "time_range": "24h",
                    "tasks_completed": 45,
                    "tasks_failed": 2,
                    "average_response_time_ms": 1250.5,
                    "uptime_percent": 99.8
                }
            }
        }