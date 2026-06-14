"""
Pydantic models for zend-ton API.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TonWalletInfo(BaseModel):
    """User's connected TON wallet information."""
    member_id: str
    ton_address: str
    connected: bool = True
    balances: Dict[str, float] = Field(default_factory=dict)  # {"USDT": 1250.00, "TON": 45.3}
    connected_at: Optional[str] = None
    last_verified: Optional[str] = None


class TonConnectRequest(BaseModel):
    """Request to initiate TON Connect flow."""
    member_id: str
    callback_url: Optional[str] = None


class TonConnectResponse(BaseModel):
    """Response with TON Connect session."""
    member_id: str
    connect_url: str
    session_id: str
    expires_at: str


class TonTransferRequest(BaseModel):
    """Request to generate a USDT transfer."""
    from_member_id: str
    to_address: str
    amount_usdt: float = Field(..., gt=0)
    comment: str = ""
    purpose: str = "direct_send"  # direct_send | p2p_settlement | merchant


class TonTransferResponse(BaseModel):
    """Response with transfer deep link."""
    transfer_id: str
    from_member_id: str
    to_address: str
    amount_usdt: float
    comment: str
    deep_link: str  # ton://transfer/... URL
    qr_data: str  # Data for QR code
    expires_at: str
    status: str = "pending"


class TonTxVerifyRequest(BaseModel):
    """Request to verify a TON transaction."""
    tx_hash: str
    expected_amount: Optional[float] = None
    expected_to: Optional[str] = None


class TonTxVerification(BaseModel):
    """Transaction verification result."""
    tx_hash: str
    verified: bool
    amount_usdt: float
    from_address: str
    to_address: str
    comment: Optional[str] = None
    confirmed_at: Optional[str] = None
    block_height: Optional[int] = None
    error: Optional[str] = None


class TonBalanceResponse(BaseModel):
    """TON wallet balance response."""
    member_id: str
    ton_address: Optional[str] = None
    connected: bool = False
    balances: Dict[str, float] = Field(default_factory=dict)
    usdt_balance: float = 0.0
    ton_balance: float = 0.0
    usdt_yield_apy: float = 2.86  # Current USDT staking APY
    timestamp: str


class SaveConnectionRequest(BaseModel):
    """Request to save a wallet connection."""
    member_id: str
    ton_address: str


class WebhookPayload(BaseModel):
    """TON blockchain webhook payload."""
    tx_hash: str
    direction: str  # in | out
    amount: float
    asset: str  # USDT | TON
    from_address: str
    to_address: str
    comment: Optional[str] = None
    timestamp: str




