"""
SQLAlchemy ORM Models
Database table definitions matching schema.sql
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, CheckConstraint, DECIMAL, Index
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Droplet(Base):
    """Droplet registration table"""
    __tablename__ = "droplets"

    id = Column(Integer, primary_key=True)
    droplet_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    steward = Column(String(100))
    endpoint = Column(String(255), nullable=False)
    capabilities = Column(JSONB, default=[], nullable=False)
    status = Column(
        String(20), 
        CheckConstraint("status IN ('active', 'inactive', 'error')"),
        nullable=False,
        index=True
    )
    last_heartbeat = Column(DateTime, index=True)
    registered_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    tasks = relationship("Task", back_populates="assigned_droplet", foreign_keys="Task.assigned_droplet_id")
    heartbeats = relationship("Heartbeat", back_populates="droplet", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_droplets_status', 'status'),
        Index('idx_droplets_heartbeat', 'last_heartbeat'),
        Index('idx_droplets_capabilities', 'capabilities', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<Droplet(id={self.droplet_id}, name='{self.name}', status='{self.status}')>"


class Task(Base):
    """Task management table"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    trace_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    task_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    payload = Column(JSONB, nullable=False)
    
    # Routing
    required_capability = Column(String(100), index=True)
    assigned_droplet_id = Column(Integer, ForeignKey('droplets.id', ondelete='SET NULL'), index=True)
    
    # State machine
    status = Column(
        String(20),
        CheckConstraint("status IN ('pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled')"),
        nullable=False,
        default='pending',
        index=True
    )
    
    # Priority & timing
    priority = Column(
        Integer,
        CheckConstraint("priority BETWEEN 1 AND 10"),
        default=5,
        index=True
    )
    created_at = Column(DateTime, default=func.now(), index=True)
    assigned_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    deadline = Column(DateTime)
    
    # Results
    result = Column(JSONB)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Metadata
    created_by = Column(String(100))
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    assigned_droplet = relationship("Droplet", back_populates="tasks", foreign_keys=[assigned_droplet_id])
    state_history = relationship("TaskStateHistory", back_populates="task", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_tasks_status', 'status'),
        Index('idx_tasks_trace_id', 'trace_id'),
        Index('idx_tasks_priority', 'priority'),
        Index('idx_tasks_assigned_droplet', 'assigned_droplet_id'),
        Index('idx_tasks_created_at', 'created_at', postgresql_ops={'created_at': 'DESC'}),
        Index('idx_tasks_capability', 'required_capability'),
        Index('idx_tasks_type', 'task_type'),
    )

    def __repr__(self):
        return f"<Task(id={self.id}, type='{self.task_type}', status='{self.status}')>"


class TaskStateHistory(Base):
    """Task state change audit trail"""
    __tablename__ = "task_state_history"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    from_status = Column(String(20))
    to_status = Column(String(20), nullable=False)
    changed_by = Column(String(100))
    reason = Column(Text)
    metadata = Column(JSONB)
    changed_at = Column(DateTime, default=func.now(), index=True)

    # Relationships
    task = relationship("Task", back_populates="state_history")

    # Indexes
    __table_args__ = (
        Index('idx_task_history_task_id', 'task_id'),
        Index('idx_task_history_changed_at', 'changed_at'),
    )

    def __repr__(self):
        return f"<TaskStateHistory(task_id={self.task_id}, {self.from_status} -> {self.to_status})>"


class Heartbeat(Base):
    """Droplet heartbeat history"""
    __tablename__ = "heartbeats"

    id = Column(Integer, primary_key=True)
    droplet_id = Column(Integer, ForeignKey('droplets.id', ondelete='CASCADE'), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    metrics = Column(JSONB)
    received_at = Column(DateTime, default=func.now(), index=True)

    # Relationships
    droplet = relationship("Droplet", back_populates="heartbeats")

    # Indexes
    __table_args__ = (
        Index('idx_heartbeats_droplet_id', 'droplet_id'),
        Index('idx_heartbeats_received_at', 'received_at', postgresql_ops={'received_at': 'DESC'}),
    )

    def __repr__(self):
        return f"<Heartbeat(droplet_id={self.droplet_id}, status='{self.status}')>"


class OrchestratorMetric(Base):
    """System-wide performance metrics"""
    __tablename__ = "orchestrator_metrics"

    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(DECIMAL, nullable=False)
    labels = Column(JSONB)
    recorded_at = Column(DateTime, default=func.now(), index=True)

    # Indexes
    __table_args__ = (
        Index('idx_metrics_name_time', 'metric_name', 'recorded_at', postgresql_ops={'recorded_at': 'DESC'}),
        Index('idx_metrics_recorded_at', 'recorded_at', postgresql_ops={'recorded_at': 'DESC'}),
        Index('idx_metrics_name', 'metric_name'),
    )

    def __repr__(self):
        return f"<OrchestratorMetric(name='{self.metric_name}', value={self.metric_value})>"


class SchemaVersion(Base):
    """Database schema version tracking"""
    __tablename__ = "schema_version"

    version = Column(String(10), primary_key=True)
    applied_at = Column(DateTime, default=func.now())
    description = Column(Text)

    def __repr__(self):
        return f"<SchemaVersion(version='{self.version}')>"
    