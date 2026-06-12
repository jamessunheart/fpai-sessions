"""Data models for Credentials Manager"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

Base = declarative_base()


class CredentialType(str, Enum):
    """Types of credentials"""
    API_KEY = "api_key"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    PASSWORD = "password"
    TOKEN = "token"
    OAUTH = "oauth"


class AccessScope(str, Enum):
    """Access permission scopes"""
    READ_ONLY = "read_only"
    WRITE = "write"
    ADMIN = "admin"


# Database Models

class Credential(Base):
    """Stored credential (encrypted)"""
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    type = Column(String)  # CredentialType
    encrypted_value = Column(Text)  # AES-256 encrypted
    service = Column(String)  # e.g., "sendgrid", "stripe"
    metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)


class AccessToken(Base):
    """Helper access tokens (scoped)"""
    __tablename__ = "access_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True)
    helper_name = Column(String)
    credential_ids = Column(JSON)  # List of credential IDs accessible
    scope = Column(String)  # AccessScope
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """Access audit trail"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    credential_id = Column(Integer)
    token_id = Column(Integer, nullable=True)
    action = Column(String)  # "access", "create", "update", "delete"
    accessor = Column(String)  # "admin" or helper name
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean)
    details = Column(JSON, default={})


# Pydantic Models (API)

class CredentialCreate(BaseModel):
    """Create credential request"""
    name: str
    type: CredentialType
    value: str  # Will be encrypted before storage
    service: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None


class CredentialResponse(BaseModel):
    """Credential response (without value)"""
    id: int
    name: str
    type: CredentialType
    service: str
    metadata: Dict[str, Any]
    created_at: datetime
    is_active: bool


class CredentialValue(BaseModel):
    """Decrypted credential value"""
    name: str
    value: str
    service: str
    type: CredentialType


class AccessTokenCreate(BaseModel):
    """Create helper access token"""
    helper_name: str
    credential_ids: List[int]
    scope: AccessScope = AccessScope.READ_ONLY
    expires_hours: int = 24


class AccessTokenResponse(BaseModel):
    """Access token response"""
    token: str  # JWT token
    helper_name: str
    credential_ids: List[int]
    scope: AccessScope
    expires_at: datetime


class AuditLogResponse(BaseModel):
    """Audit log entry"""
    id: int
    credential_id: int
    action: str
    accessor: str
    ip_address: Optional[str]
    timestamp: datetime
    success: bool
    details: Dict[str, Any]


class CredentialUpdate(BaseModel):
    """Update credential"""
    value: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
