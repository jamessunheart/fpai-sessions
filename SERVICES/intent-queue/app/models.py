"""Data models for intent-queue service"""
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from uuid import uuid4

class LifecycleEvent(BaseModel):
    phase: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str  # running, completed, failed
    duration_seconds: Optional[int] = None
    details: Dict = {}

class Intent(BaseModel):
    intent_id: str = Field(default_factory=lambda: str(uuid4()))
    submitted_by: str
    submitted_at: datetime = Field(default_factory=datetime.now)
    source: str  # unified-chat, api, autonomous-agent
    
    # Service details
    service_name: str
    service_type: str  # infrastructure, sacred_loop, domain, api_gateway, data
    priority: str = "medium"  # critical, high, medium, low
    purpose: str
    key_features: List[str]
    dependencies: List[str] = []
    port: int
    target_tier: int
    
    # Governance
    blueprint_context: str = ""
    blueprint_aligned: Optional[bool] = None
    alignment_score: Optional[float] = None
    governance_decision: Optional[str] = None
    governance_reasoning: Optional[str] = None
    
    # Build settings
    auto_build: bool = True
    auto_deploy: bool = False
    
    # Status tracking
    status: str = "queued"
    queue_position: Optional[int] = None
    
    # Pipeline references
    spec_path: Optional[str] = None
    spec_score: Optional[int] = None
    build_id: Optional[str] = None
    deployment_url: Optional[str] = None
    
    # Lifecycle
    lifecycle: List[LifecycleEvent] = []
    
    # Metadata
    metadata: Dict = {}
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

class IntentSubmitRequest(BaseModel):
    submitted_by: str
    source: str = "api"
    service_name: str
    service_type: str
    priority: str = "medium"
    purpose: str
    key_features: List[str]
    dependencies: List[str] = []
    port: int
    target_tier: int = 2
    blueprint_context: str = ""
    auto_build: bool = True
    auto_deploy: bool = False
    metadata: Dict = {}

class IntentResponse(BaseModel):
    intent_id: str
    status: str
    queue_position: int
    priority: str
    estimated_start: Optional[str] = None
    governance_status: str
    track_url: str
    subscribe_url: str

class QueueStatus(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    next_processing: List[Dict]
    processing_rate: Dict
