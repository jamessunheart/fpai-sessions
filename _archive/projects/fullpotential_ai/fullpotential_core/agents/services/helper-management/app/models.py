"""Data models for Helper Management"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

Base = declarative_base()


class TaskStatus(str, Enum):
    """Task statuses"""
    DRAFT = "draft"
    POSTED = "posted"
    REVIEWING = "reviewing"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    PAID = "paid"
    FAILED = "failed"


class PaymentMethod(str, Enum):
    """Payment methods"""
    CRYPTO = "crypto"
    UPWORK = "upwork"
    PAYPAL = "paypal"
    WIRE = "wire"


class HelperStatus(str, Enum):
    """Helper statuses"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


# Database Models

class Task(Base):
    """Task to be completed by helper"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    requirements = Column(JSON)  # Skills, experience needed
    budget = Column(Float)
    currency = Column(String, default="USD")
    payment_method = Column(String)
    duration_hours = Column(Integer)

    # Credentials needed
    credential_ids = Column(JSON, default=[])
    access_scope = Column(String, default="read_only")

    # Status
    status = Column(String)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)

    # Assignment
    helper_id = Column(Integer, nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)

    # Completion
    completed_at = Column(DateTime(timezone=True), nullable=True)
    verification_details = Column(JSON, nullable=True)

    # Payment
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_transaction = Column(String, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    metadata = Column(JSON, default={})


class Helper(Base):
    """Contractor/helper profile"""
    __tablename__ = "helpers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, nullable=True)
    platform = Column(String)  # upwork, fiverr, crypto_board
    platform_profile_url = Column(String, nullable=True)

    # Skills and ratings
    skills = Column(JSON, default=[])
    rating = Column(Float, nullable=True)
    completed_tasks = Column(Integer, default=0)

    # Payment
    crypto_wallet = Column(String, nullable=True)
    payment_preference = Column(String)

    # Access
    current_access_token = Column(String, nullable=True)
    access_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String)
    hired_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), nullable=True)

    # Performance
    average_completion_time = Column(Float, nullable=True)
    success_rate = Column(Float, default=1.0)

    metadata = Column(JSON, default={})


class Application(Base):
    """Job application from helper"""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer)
    helper_name = Column(String)
    helper_email = Column(String, nullable=True)
    platform = Column(String)

    # Application details
    cover_letter = Column(Text)
    proposed_rate = Column(Float)
    estimated_hours = Column(Float)

    # Screening
    ai_score = Column(Float, nullable=True)
    ai_reasoning = Column(Text, nullable=True)

    # Status
    status = Column(String)  # pending, accepted, rejected
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    metadata = Column(JSON, default={})


# Pydantic Models

class TaskCreate(BaseModel):
    """Create task request"""
    title: str
    description: str
    requirements: Dict[str, Any] = Field(default_factory=dict)
    budget: float
    currency: str = "USD"
    payment_method: PaymentMethod = PaymentMethod.CRYPTO
    duration_hours: int = 24
    credential_ids: List[int] = Field(default_factory=list)
    access_scope: str = "read_only"


class TaskResponse(BaseModel):
    """Task response"""
    id: int
    title: str
    description: str
    budget: float
    currency: str
    status: TaskStatus
    helper_id: Optional[int]
    created_at: datetime
    deadline: Optional[datetime]


class HelperCreate(BaseModel):
    """Create helper profile"""
    name: str
    email: Optional[str]
    platform: str
    platform_profile_url: Optional[str]
    skills: List[str] = Field(default_factory=list)
    crypto_wallet: Optional[str]
    payment_preference: PaymentMethod = PaymentMethod.CRYPTO


class HelperResponse(BaseModel):
    """Helper response"""
    id: int
    name: str
    platform: str
    skills: List[str]
    rating: Optional[float]
    completed_tasks: int
    status: HelperStatus


class ApplicationCreate(BaseModel):
    """Submit application"""
    task_id: int
    helper_name: str
    helper_email: Optional[str]
    platform: str
    cover_letter: str
    proposed_rate: float
    estimated_hours: float


class ApplicationResponse(BaseModel):
    """Application response"""
    id: int
    task_id: int
    helper_name: str
    platform: str
    ai_score: Optional[float]
    ai_reasoning: Optional[str]
    status: str
    applied_at: datetime


class HireRequest(BaseModel):
    """Hire helper for task"""
    task_id: int
    application_id: int


class TaskCompletionRequest(BaseModel):
    """Mark task as completed"""
    task_id: int
    verification_details: Dict[str, Any] = Field(default_factory=dict)


class PaymentRequest(BaseModel):
    """Process payment"""
    task_id: int
    amount: float
    payment_method: PaymentMethod
