"""
Proof Witness - Data Models

The Witness runs silently, capturing ambient evidence and creating proof candidates.
Humans spend 15 seconds/day confirming, not creating.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ProofSource(str, Enum):
    """Where the proof came from"""
    GITHUB = "github"           # Commit, PR, deploy
    TELEGRAM = "telegram"       # Photo, message, voice note
    CALENDAR = "calendar"       # Meeting happened
    REVENUE = "revenue"         # Transaction, payment
    SERVICE = "service"         # Health check, metric
    AI_CHAT = "ai_chat"        # Question answered, learning
    MANUAL = "manual"          # Human submitted


class ProofType(str, Enum):
    """What kind of proof this is"""
    CODE = "code"              # Commit, deploy
    PHOTO = "photo"            # Visual evidence
    METRIC = "metric"          # Number changed
    EVENT = "event"            # Something happened
    KNOWLEDGE = "knowledge"    # Learning captured
    CONTENT = "content"        # Posted to social


class ProofStatus(str, Enum):
    """Lifecycle of a proof candidate"""
    PENDING = "pending"        # Waiting for human confirm
    CONFIRMED = "confirmed"    # Human said "yes, real"
    REJECTED = "rejected"      # Human said "no, ignore"
    EXPIRED = "expired"        # Too old, auto-archived


class ProofCandidate(BaseModel):
    """
    A proof candidate - something that might be proof, waiting for 15 seconds of human attention
    """
    id: str = Field(..., description="Unique ID")
    source: ProofSource = Field(..., description="Where this came from")
    type: ProofType = Field(..., description="What kind of proof")
    status: ProofStatus = Field(default=ProofStatus.PENDING)

    # Who did the work
    owner: str = Field(..., description="Person who did this (github username, telegram username, etc)")

    # What happened
    title: str = Field(..., description="One-line summary")
    description: Optional[str] = Field(None, description="Details if needed")

    # Evidence
    url: Optional[str] = Field(None, description="Link to commit, photo, etc")
    media: Optional[List[str]] = Field(None, description="Photos, videos")
    data: Optional[Dict[str, Any]] = Field(None, description="Structured data (metrics, etc)")

    # Auto-tagging
    tags: List[str] = Field(default_factory=list, description="Keywords (greenhouse, revenue, etc)")
    suggested_question: Optional[str] = Field(None, description="Which question does this solve?")
    confidence: float = Field(default=0.5, description="AI confidence in tagging (0-1)")

    # Timestamps
    occurred_at: datetime = Field(..., description="When the work happened")
    captured_at: datetime = Field(default_factory=datetime.utcnow, description="When we saw it")
    confirmed_at: Optional[datetime] = Field(None, description="When human confirmed")

    # Generated content
    content_draft: Optional[str] = Field(None, description="Auto-generated tweet/post")


class ConfirmedProof(BaseModel):
    """
    Confirmed proof - the human said "yes, this is real"

    This goes into the digest, becomes content, shows in progress tracking
    """
    id: str
    candidate_id: str  # Link back to original candidate

    # From candidate
    source: ProofSource
    type: ProofType
    owner: str
    title: str
    description: Optional[str]
    url: Optional[str]
    media: Optional[List[str]]
    data: Optional[Dict[str, Any]]

    # Human-confirmed tagging
    tags: List[str]
    question_id: Optional[str] = Field(None, description="Which question this solves")

    # Impact
    impact: Optional[str] = Field(None, description="What changed because of this")
    progress_delta: Optional[float] = Field(None, description="How much closer to done (0-100%)")

    # Timestamps
    occurred_at: datetime
    confirmed_at: datetime

    # Content
    content_published: Optional[str] = Field(None, description="Final published content")
    content_url: Optional[str] = Field(None, description="Where it was posted")


class DailyProofSummary(BaseModel):
    """
    Summary of all proof from one day

    This goes into the morning digest
    """
    date: str  # YYYY-MM-DD
    total_candidates: int
    total_confirmed: int
    total_rejected: int

    by_owner: Dict[str, int] = Field(default_factory=dict, description="Proof count per person")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Proof count by type")
    by_tag: Dict[str, int] = Field(default_factory=dict, description="Proof count by tag")

    # For digest
    highlights: List[ConfirmedProof] = Field(default_factory=list, description="Top 5 proof items")


class ConfirmationRequest(BaseModel):
    """
    What the bot sends to get human confirmation

    Designed for Telegram inline buttons - one tap to confirm
    """
    candidate_id: str
    summary: str  # "Atlas uploaded photo at greenhouse (2:14pm)"
    suggested_tag: str  # "greenhouse_electrical"
    confidence: float  # 0.85

    # Actions
    quick_confirm: str = "✅ Yes"  # Confirms with suggested tag
    edit: str = "✏️ Edit"          # Let human change tag/details
    reject: str = "❌ Skip"        # Ignore this proof
