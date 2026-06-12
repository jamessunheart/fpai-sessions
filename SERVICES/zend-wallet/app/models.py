"""Pydantic models for Zend Wallet API."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class WalletUnlocks(BaseModel):
    """Derived UX unlocks based on UC balance and internal perks."""
    send_for_me: str  # "locked" | "light_approval" | "full_approval"
    sponsored_sends_remaining: int = 0
    human_concierge: bool = False


class WalletResponse(BaseModel):
    member_id: str
    uc_balance: float
    unlocks: WalletUnlocks
    timestamp: datetime


class DraftSendRequest(BaseModel):
    member_id: str
    prompt: str = Field(..., min_length=2, max_length=500)


class DraftSendResponse(BaseModel):
    member_id: str
    to: Optional[str] = None  # parsed recipient handle/contact
    amount_uc: Optional[float] = None
    note: Optional[str] = None
    risk_flags: List[str] = []
    confirm_level: str = "full"  # "light" | "full"
    ai_used: bool = False
    raw: Dict[str, Any] = {}


class SendRequest(BaseModel):
    from_member_id: str
    # Either to_member_id OR invite_contact must be provided
    to_member_id: Optional[str] = None
    invite_contact: Optional[str] = None  # phone/email/name

    amount_uc: float = Field(..., gt=0, le=1000)
    note: Optional[str] = Field(default=None, max_length=500)
    extra: Optional[Dict[str, Any]] = None


class SendResponse(BaseModel):
    status: str  # "sent" | "escrowed"
    amount_uc: float
    from_member_id: str
    to_member_id: Optional[str] = None
    invite_code: Optional[str] = None
    transfer_tx_from: Optional[str] = None
    transfer_tx_to: Optional[str] = None
    timestamp: datetime


class ClaimInviteRequest(BaseModel):
    invite_code: str = Field(..., min_length=6, max_length=32)
    claimer_member_id: str


class ClaimInviteResponse(BaseModel):
    status: str  # "claimed"
    invite_code: str
    amount_uc: float
    claimer_member_id: str
    transfer_tx_from: Optional[str] = None
    transfer_tx_to: Optional[str] = None
    timestamp: datetime








