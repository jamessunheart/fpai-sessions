"""Pydantic models for Zend Payments.

Per docs/protocols/ZEND_REGENERATIVE_SPEC.md Part 2: Core Primitives
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class RailPolicy(str, Enum):
    """Settlement rail policy"""
    STRIPE_FIRST = "stripe_first"
    SOLANA_FIRST = "solana_first"
    USER_CHOICE = "user_choice"


class IntentStatus(str, Enum):
    """Payment intent status"""
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SETTLED = "settled"
    EXPIRED = "expired"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfirmLevel(str, Enum):
    """Confirmation level required"""
    NONE = "none"
    LIGHT = "light"
    FULL = "full"
    HUMAN_REVIEW = "human_review"


# ============================================================
# PAYMENT INTENT
# ============================================================

class CreateIntentRequest(BaseModel):
    """Request to create a payment intent"""
    payer_id: Optional[str] = Field(None, description="Payer member ID (optional for requests)")
    recipient_id: str = Field(..., min_length=1, max_length=120)
    amount: float = Field(..., gt=0, le=10000)
    currency: str = Field("USD", pattern="^(USD|USDC)$")
    rail_policy: RailPolicy = Field(RailPolicy.STRIPE_FIRST)
    commons_contribution_pct: float = Field(0, ge=0, le=5)
    note: Optional[str] = Field(None, max_length=500)
    expires_in_minutes: int = Field(30, ge=5, le=1440)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaymentIntent(BaseModel):
    """Payment intent response"""
    intent_id: str
    payer_id: Optional[str]
    recipient_id: str
    amount: float
    currency: str
    rail_policy: RailPolicy
    commons_contribution_pct: float
    note: Optional[str]
    risk_score: float
    confirm_level: ConfirmLevel
    status: IntentStatus
    created_at: datetime
    expires_at: datetime
    settled_at: Optional[datetime]
    
    # ZendLink
    zend_link: Optional[str]
    zend_link_code: Optional[str]
    
    # Rail-specific details
    stripe_checkout_url: Optional[str]
    stripe_payment_intent_id: Optional[str]
    solana_payment_request: Optional[str]
    solana_tx_signature: Optional[str]


class ConfirmIntentRequest(BaseModel):
    """Request to confirm a payment intent"""
    intent_id: str
    rail: str = Field("stripe", pattern="^(stripe|solana)$")
    # For Solana: tx_signature
    tx_signature: Optional[str] = None


class IntentResponse(BaseModel):
    """Generic intent operation response"""
    success: bool
    intent_id: str
    status: IntentStatus
    message: str
    zend_link: Optional[str] = None


# ============================================================
# ZENDLINK
# ============================================================

class ZendLinkResponse(BaseModel):
    """ZendLink resolution response"""
    code: str
    intent_id: str
    recipient_id: str
    recipient_name: Optional[str]
    amount: float
    currency: str
    note: Optional[str]
    commons_badge: bool  # True if recipient opted into Commons
    status: IntentStatus
    expires_at: datetime
    
    # Available rails
    stripe_available: bool
    solana_available: bool


# ============================================================
# RECEIPT
# ============================================================

class ZendReceipt(BaseModel):
    """Immutable proof of settlement"""
    receipt_id: str
    intent_id: str
    rail: str  # "stripe" | "solana"
    external_ref: str  # stripe_payment_intent_id or solana_tx_signature
    amount_settled: float
    commons_contributed: float
    settled_at: datetime
    blessing_message: Optional[str]
    
    # Verification
    payer_id: Optional[str]
    recipient_id: str


# ============================================================
# MERCHANT / POS
# ============================================================

class CreateInvoiceRequest(BaseModel):
    """Create a merchant invoice/payment request"""
    merchant_id: str = Field(..., min_length=1)
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: float = Field(..., gt=0)
    currency: str = Field("USD")
    note: Optional[str] = None
    commons_tithe_pct: float = Field(0, ge=0, le=5)
    expires_in_minutes: int = Field(30)


class InvoiceResponse(BaseModel):
    """Invoice creation response"""
    invoice_id: str
    intent_id: str
    zend_link: str
    qr_code_url: Optional[str]
    amount: float
    currency: str
    status: IntentStatus
    expires_at: datetime




