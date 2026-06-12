from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .database import Base

# --- DB Models ---

class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    wallet_id = Column(String, nullable=True) # Linked to Credits Manager
    trust_score = Column(Integer, default=50) # 0-100
    skills = Column(JSON, default=list)
    
    # New Profile Fields
    avatar_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    whatsapp = Column(String, nullable=True)
    telegram = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    
    # Recruiting
    source = Column(String, default="direct") # referral, upwork_scout, direct
    scouted_by = Column(String, nullable=True)
    
    # Context & Status
    context_level = Column(Integer, default=0)
    status = Column(String, default="active") # active, inactive, pending
    
    # Role & Auth
    role = Column(String, default="member") # admin, member, observer
    is_admin = Column(Boolean, default=False)
    
    assignments = relationship("WorkAssignment", back_populates="assignee")

class WorkAssignment(Base):
    __tablename__ = "assignments"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    type = Column(String) # mission, api_procurement, code_review, support
    status = Column(String, default="pending") # pending, in_progress, completed, verified
    
    assignee_id = Column(String, ForeignKey("team_members.id"))
    assignee = relationship("TeamMember", back_populates="assignments")
    
    # Integration Refs
    mission_id = Column(String, nullable=True)
    procurement_id = Column(String, nullable=True)
    
    # Context
    context_summary = Column(String, nullable=True)
    relevant_docs = Column(JSON, default=list)
    
    # Economics
    uc_reward = Column(Float, default=0.0)
    cora_points = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class Invitation(Base):
    __tablename__ = "invitations"
    
    token = Column(String, primary_key=True)
    email = Column(String)
    role = Column(String, default="member")
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MagicLink(Base):
    """Passwordless login tokens."""
    __tablename__ = "magic_links"
    
    token = Column(String, primary_key=True)
    email = Column(String, index=True)
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    """Active user sessions for tracking."""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True)
    member_id = Column(String, ForeignKey("team_members.id"))
    token_hash = Column(String, index=True)  # Hash of JWT for revocation
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)

class VaultItem(Base):
    """Secure storage for credentials and docs."""
    __tablename__ = "vault_items"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    category = Column(String) # openai, stripe, legal
    type = Column(String) # text, file
    content_encrypted = Column(String) # Fernet token
    filename = Column(String, nullable=True)
    
    created_by_id = Column(String, ForeignKey("team_members.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Access Control
    min_role = Column(String, default="member") # admin, developer, assistant, strategist
    allowed_users = Column(JSON, default=list) # specific user IDs

class VaultShare(Base):
    """Shareable links for vault items."""
    __tablename__ = "vault_shares"
    
    token = Column(String, primary_key=True)
    vault_item_id = Column(String, ForeignKey("vault_items.id"))
    created_by_id = Column(String, ForeignKey("team_members.id"))
    expires_at = Column(DateTime)
    one_time_use = Column(Boolean, default=True)
    password_hash = Column(String, nullable=True) # Optional password protection
    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)

class ComplianceDoc(Base):
    """Legal templates (NDA, Contracts) and Library Docs."""
    __tablename__ = "compliance_docs"
    
    id = Column(String, primary_key=True)
    title = Column(String)
    description = Column(String, nullable=True)
    category = Column(String, default="legal") # legal, research, log, process
    file_path = Column(String) # Path to template PDF
    created_at = Column(DateTime, default=datetime.utcnow)
    
    signatures = relationship("Signature", back_populates="document")

class Signature(Base):
    """Signature requests and proofs."""
    __tablename__ = "signatures"
    
    id = Column(String, primary_key=True)
    doc_id = Column(String, ForeignKey("compliance_docs.id"))
    member_id = Column(String, ForeignKey("team_members.id"))
    status = Column(String, default="pending") # pending, signed
    
    signed_at = Column(DateTime, nullable=True)
    signature_text = Column(String, nullable=True) # Typed name
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Link to the secure vault item containing the "Signed Copy"
    vault_item_id = Column(String, ForeignKey("vault_items.id"), nullable=True)
    
    document = relationship("ComplianceDoc", back_populates="signatures")
    member = relationship("TeamMember")

# --- Pydantic Schemas ---

class TeamMemberBase(BaseModel):
    name: str
    email: str
    skills: List[str] = []
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    telegram: Optional[str] = None
    timezone: Optional[str] = None
    bio: Optional[str] = None

class TeamMemberCreate(TeamMemberBase):
    pass

class TeamMemberResponse(TeamMemberBase):
    id: str
    trust_score: int
    status: str
    
    class Config:
        from_attributes = True

class AssignmentCreate(BaseModel):
    title: str
    description: str
    type: str
    uc_reward: float
    mission_id: Optional[str] = None
    procurement_id: Optional[str] = None

class AssignmentResponse(AssignmentCreate):
    id: str
    status: str
    assignee_id: Optional[str]
    context_summary: Optional[str]
    relevant_docs: List[Any] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AssignmentCompleteRequest(BaseModel):
    notes: Optional[str] = None
    credentials: List[Dict[str, Any]] = []


# --- Auth Schemas ---

class MagicLinkRequest(BaseModel):
    email: str


class MagicLinkResponse(BaseModel):
    message: str
    expires_in_minutes: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int
    member: Optional[dict] = None


class InviteRequest(BaseModel):
    email: str
    role: str = "member"


class InviteResponse(BaseModel):
    token: str
    email: str
    role: str
    expires_at: datetime
    invite_url: str


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    skills: Optional[List[str]] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    telegram: Optional[str] = None
    timezone: Optional[str] = None
    bio: Optional[str] = None


class ClaimTaskRequest(BaseModel):
    pass  # Just POST to claim


class VaultItemCreate(BaseModel):
    name: str
    category: str
    type: str = "text" # text or file
    content: str # Plaintext (will be encrypted)
    filename: Optional[str] = None
    min_role: str = "member"

class VaultItemResponse(BaseModel):
    id: str
    name: str
    category: str
    type: str
    created_at: datetime
    min_role: str
    
    class Config:
        from_attributes = True

class VaultShareCreate(BaseModel):
    expires_in_hours: int = 24
    one_time_use: bool = True
    password: Optional[str] = None # Plaintext password from client

class ComplianceDocCreate(BaseModel):
    title: str
    description: Optional[str] = None

class SignatureResponse(BaseModel):
    id: str
    doc_title: str
    status: str
    signed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


