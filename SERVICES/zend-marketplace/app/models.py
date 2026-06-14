"""
Pydantic models for zend-marketplace API.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    """Request to create a sell or buy order."""
    order_type: str = Field(..., description="sell_uc or buy_uc")
    member_id: str = Field(..., min_length=1, max_length=120)
    entity_id: Optional[str] = Field(default=None, description="If order is from an entity")
    amount_uc: float = Field(..., gt=0)
    accepted_rails: List[str] = Field(default=["ton_usdt"], description="Payment rails: ton_usdt, zelle, venmo")
    ton_wallet_address: Optional[str] = None


class OrderResponse(BaseModel):
    """Market order response."""
    order_id: str
    order_type: str
    member_id: str
    entity_id: Optional[str] = None
    amount_uc: float
    rate: float = 1.0
    accepted_rails: List[str]
    ton_wallet_address: Optional[str] = None
    status: str
    created_at: str
    expires_at: str
    matched_with: Optional[str] = None
    matched_at: Optional[str] = None


class MatchResult(BaseModel):
    """Result of order matching."""
    matched: bool
    trade_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    buy_order_id: Optional[str] = None
    amount_uc: float = 0.0
    amount_usdt: float = 0.0
    seller_member_id: Optional[str] = None
    buyer_member_id: Optional[str] = None
    seller_ton_address: Optional[str] = None
    buyer_ton_address: Optional[str] = None
    next_step: str = ""
    message: str = ""


class ConfirmPaymentRequest(BaseModel):
    """Request to confirm payment received."""
    trade_id: str
    confirmer_member_id: str
    tx_hash: Optional[str] = None  # TON transaction hash for verification


class TradeResponse(BaseModel):
    """Trade details response."""
    trade_id: str
    sell_order_id: str
    buy_order_id: str
    amount_uc: float
    amount_usdt: float
    rail: str
    seller_member_id: str
    buyer_member_id: str
    seller_ton_address: Optional[str] = None
    buyer_ton_address: Optional[str] = None
    ton_tx_hash: Optional[str] = None
    seller_confirmed: bool = False
    buyer_confirmed: bool = False
    status: str
    created_at: str
    settled_at: Optional[str] = None


class RegisterLPRequest(BaseModel):
    """Request to register as liquidity provider."""
    entity_id: str
    max_buy_uc: float = Field(..., gt=0)
    daily_limit_uc: float = Field(..., gt=0)
    auto_buy_enabled: bool = True
    min_amount_uc: float = Field(default=10, ge=1)
    max_amount_uc: float = Field(default=500, le=5000)
    ton_wallet_address: str


class LPStatusResponse(BaseModel):
    """Liquidity provider status."""
    entity_id: str
    max_buy_uc: float
    daily_limit_uc: float
    daily_used_uc: float
    daily_remaining_uc: float
    auto_buy_enabled: bool
    min_amount_uc: float
    max_amount_uc: float
    ton_wallet_address: str
    is_active: bool
    last_reset_date: str


class MarketStats(BaseModel):
    """Marketplace statistics."""
    open_sell_orders: int
    open_buy_orders: int
    total_volume_24h_uc: float
    total_trades_24h: int
    active_liquidity_providers: int
    instant_liquidity_available_uc: float




