"""
SOL Treasury SSOT - Data Models
Tracks treasury health and path to 2x growth
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum


class TreasuryStatus(str, Enum):
    """Treasury health status"""
    ACCUMULATING = "accumulating"  # Below tipping point
    LEVERAGEABLE = "leverageable"  # At tipping point, can use as collateral
    SOVEREIGN = "sovereign"  # Beyond tipping point, fully autonomous


class SOLDeposit(BaseModel):
    """Track SOL deposits"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    user_id: str
    sol_amount: float
    sol_price_usd: float  # Price at deposit time
    pot_issued: float  # POT credits given
    conversion_rate: float  # SOL → POT rate
    timestamp: datetime = Field(default_factory=datetime.now)
    tx_signature: Optional[str] = None  # Solana transaction


class POTSpending(BaseModel):
    """Track POT spending across services"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    user_id: str
    service: str  # i-match, jobs, membership
    pot_spent: float
    value_created_usd: Optional[float] = None  # Measured value from spending
    roi_multiplier: Optional[float] = None  # value_created / pot_spent
    description: str
    timestamp: datetime = Field(default_factory=datetime.now)


class TreasuryMetrics(BaseModel):
    """Real-time treasury health metrics"""

    # SOL Reserves
    sol_balance: float  # Current SOL held
    sol_price_usd: float  # Current SOL price
    sol_value_usd: float  # Total USD value

    # POT Economy
    pot_total_issued: float  # Total POT ever issued
    pot_total_redeemed: float  # Total POT redeemed
    pot_outstanding: float  # Currently in circulation

    # Reserve Ratio (Path to Tipping Point)
    reserve_ratio: float  # sol_value / (pot_outstanding * redemption_value)
    tipping_point_ratio: float = 0.40  # 40% = can leverage instead of sell
    sol_needed_for_tipping_point: float
    days_to_tipping_point: Optional[float] = None  # At current growth rate

    # Value Creation (2x Proof)
    total_value_created_usd: float
    total_pot_spent: float
    overall_roi_multiplier: float  # Must be ≥ 2.0 to maintain trust

    # Liquidation Tracking
    sol_held_percent: float  # % of SOL still held
    sol_liquidated_percent: float  # % converted to USD (for vendors)
    sol_in_private_contracts: float  # SOL in off-market deals

    # Treasury Status
    status: TreasuryStatus
    can_leverage: bool  # True when reserve_ratio >= tipping_point_ratio

    # Growth Metrics
    weekly_growth_rate: Optional[float] = None  # % growth per week
    monthly_projection: Optional[float] = None  # Projected SOL in 30 days

    timestamp: datetime = Field(default_factory=datetime.now)


class ValueCreationProof(BaseModel):
    """Proof that spending creates 2x+ value"""
    service: str
    period: str  # "daily", "weekly", "monthly", "all-time"

    pot_spent: float
    value_created_usd: float
    roi_multiplier: float

    # Breakdown by category
    examples: List[Dict] = Field(default_factory=list)  # Specific examples of value

    # Verification
    verified: bool = False
    verified_by: Optional[str] = None
    verification_method: Optional[str] = None

    timestamp: datetime = Field(default_factory=datetime.now)


class GrowthStrategy(BaseModel):
    """Active strategies for 2x growth"""

    # Treasury Arena (AI Competition)
    arena_allocated: float  # SOL in arena
    arena_apy_target: float  # Target APY from arena
    arena_current_performance: Optional[float] = None

    # Treasury Manager (DeFi)
    defi_allocated: float  # SOL in DeFi protocols
    defi_apy_target: float  # Target APY
    defi_current_performance: Optional[float] = None

    # POT Economy Growth
    active_users: int
    pot_velocity: float  # How fast POT circulates
    new_deposits_this_week: float

    # Combined Strategy
    target_growth_rate: float  # Target weekly % growth
    actual_growth_rate: Optional[float] = None
    days_to_2x: Optional[int] = None  # Days to double treasury

    # Next Actions
    recommended_actions: List[str] = Field(default_factory=list)

    timestamp: datetime = Field(default_factory=datetime.now)


class LiquidationEvent(BaseModel):
    """Track when SOL is converted to USD"""
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    sol_amount: float
    usd_received: float
    reason: str  # "vendor_payment", "emergency", "user_redemption"
    vendor_name: Optional[str] = None
    can_accept_sol: bool = False  # Could this vendor accept SOL?

    # Impact on treasury
    impact_on_reserve_ratio: float

    timestamp: datetime = Field(default_factory=datetime.now)
