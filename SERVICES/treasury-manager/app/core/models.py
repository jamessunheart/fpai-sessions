"""
Data models for Treasury Manager
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MarketPhase(str, Enum):
    """Current market cycle phase"""
    ACCUMULATION = "accumulation"  # MVRV 2-3, building positions
    EUPHORIA = "euphoria"  # MVRV 3-5, approaching top
    TOP = "top"  # MVRV 5-7+, peak zone
    BEAR = "bear"  # MVRV <2, correction/bear market
    UNKNOWN = "unknown"


class AllocationMode(str, Enum):
    """Portfolio allocation strategy mode"""
    CONSERVATIVE = "conservative"  # 100% yield
    TACTICAL = "tactical"  # 60% yield, 40% BTC/ETH spot
    AGGRESSIVE = "aggressive"  # Leveraged positions
    HEDGE = "hedge"  # Defensive, mostly stablecoins


class ProtocolName(str, Enum):
    """Supported DeFi protocols"""
    AAVE = "aave"
    PENDLE = "pendle"
    CURVE = "curve"
    ONEINCH = "1inch"


class AssetType(str, Enum):
    """Asset types in portfolio"""
    USDC = "USDC"
    BTC = "BTC"
    ETH = "ETH"
    AUSDC = "aUSDC"  # Aave interest-bearing USDC
    PT = "PT"  # Pendle Principal Token
    LP = "LP"  # Curve LP token


# ============================================================================
# MARKET DATA MODELS
# ============================================================================


class MarketData(BaseModel):
    """Real-time market indicators"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Cycle Indicators
    mvrv_z_score: Optional[float] = None
    btc_price: Decimal
    eth_price: Decimal

    # Sentiment
    fear_greed_index: Optional[int] = None  # 0-100
    btc_funding_rate: Optional[float] = None  # Perpetual futures funding
    eth_funding_rate: Optional[float] = None

    # Derived
    market_phase: MarketPhase
    recommended_mode: AllocationMode


class AllocationSignal(BaseModel):
    """Signal for allocation changes"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    market_phase: MarketPhase
    recommended_mode: AllocationMode
    confidence: float = Field(ge=0.0, le=1.0)  # 0-1

    target_allocations: Dict[str, float]  # asset -> percentage
    reasoning: str

    # Triggers
    mvrv_threshold_crossed: bool = False
    funding_rate_extreme: bool = False
    quarterly_expiry_approaching: bool = False


# ============================================================================
# PORTFOLIO STATE MODELS
# ============================================================================


class Position(BaseModel):
    """Individual position in portfolio"""
    asset_type: AssetType
    protocol: Optional[ProtocolName] = None
    amount: Decimal
    value_usd: Decimal
    entry_price: Optional[Decimal] = None
    current_apy: Optional[float] = None

    opened_at: datetime
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PortfolioState(BaseModel):
    """Complete portfolio state"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Total Value
    total_value_usd: Decimal

    # Positions
    positions: List[Position]

    # Base Yield Layer ($240K target)
    aave_balance_usd: Decimal = Decimal("0")
    pendle_balance_usd: Decimal = Decimal("0")
    curve_balance_usd: Decimal = Decimal("0")

    # Tactical Layer ($160K target)
    btc_balance: Decimal = Decimal("0")  # in BTC
    eth_balance: Decimal = Decimal("0")  # in ETH
    usdc_cash: Decimal = Decimal("0")  # in USDC

    # Allocation Percentages (actual)
    base_yield_percent: float
    tactical_percent: float
    cash_percent: float

    # Target vs Actual
    target_allocation: Dict[str, float]
    allocation_drift: Dict[str, float]  # Difference from target

    # Metadata
    current_phase: MarketPhase
    current_mode: AllocationMode
    last_rebalance: Optional[datetime] = None


# ============================================================================
# TRANSACTION MODELS
# ============================================================================


class TransactionType(str, Enum):
    """Types of transactions"""
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    SWAP = "swap"
    STAKE = "stake"
    UNSTAKE = "unstake"
    CLAIM_REWARDS = "claim_rewards"


class Transaction(BaseModel):
    """Record of a transaction"""
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    tx_type: TransactionType
    protocol: ProtocolName
    from_asset: AssetType
    to_asset: AssetType
    amount_from: Decimal
    amount_to: Decimal

    tx_hash: Optional[str] = None  # Blockchain transaction hash
    gas_used: Optional[Decimal] = None
    gas_price_gwei: Optional[int] = None
    gas_cost_usd: Optional[Decimal] = None

    status: str = "pending"  # pending, confirmed, failed
    error: Optional[str] = None


class RebalanceResult(BaseModel):
    """Result of a rebalancing operation"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    success: bool
    transactions: List[Transaction]

    # Before/After
    state_before: PortfolioState
    state_after: Optional[PortfolioState] = None

    # Costs
    total_gas_cost_usd: Decimal
    slippage_percent: float

    # Metadata
    reasoning: str
    error: Optional[str] = None


# ============================================================================
# RISK MODELS
# ============================================================================


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class RiskAssessment(BaseModel):
    """Risk analysis of proposed action"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    approved: bool
    risk_level: RiskLevel
    risk_score: float = Field(ge=0.0, le=100.0)  # 0-100

    # Specific Checks
    position_size_ok: bool
    concentration_ok: bool
    liquidity_ok: bool
    protocol_safe: bool

    issues: List[str] = []
    warnings: List[str] = []
    reasoning: str


class ProtocolRiskScore(BaseModel):
    """Risk assessment for a DeFi protocol"""
    protocol: ProtocolName
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    tvl_usd: Decimal
    audited: bool
    audit_firms: List[str] = []
    time_in_operation_days: int
    exploit_history: List[str] = []

    risk_score: float = Field(ge=0.0, le=100.0)
    risk_level: RiskLevel
    approved_for_use: bool


# ============================================================================
# PERFORMANCE MODELS
# ============================================================================


class PerformanceMetrics(BaseModel):
    """Portfolio performance analytics"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    period: str  # "daily", "weekly", "monthly", "all_time"

    # Returns
    total_return_usd: Decimal
    total_return_percent: float
    annualized_apy: float

    # Risk-Adjusted
    sharpe_ratio: Optional[float] = None
    max_drawdown_percent: float
    current_drawdown_percent: float

    # Components
    base_yield_return: Decimal
    tactical_return: Decimal
    gas_costs_total: Decimal

    # Comparison
    btc_buy_hold_return: float  # What if we just bought BTC?
    eth_buy_hold_return: float
    static_yield_return: float  # What if we did 6.5% APY?


class Decision(BaseModel):
    """Record of an AI decision"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    decision_type: str  # "rebalance", "hold", "emergency_exit"
    approved: bool
    confidence: float = Field(ge=0.0, le=1.0)

    # Context
    market_data: MarketData
    portfolio_state: PortfolioState

    # Decision
    action_taken: str
    reasoning: str

    # Outcome (filled in later)
    outcome_success: Optional[bool] = None
    outcome_return: Optional[Decimal] = None
    outcome_notes: Optional[str] = None


class Insight(BaseModel):
    """Learning from historical decisions"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    category: str  # "pattern", "mistake", "success_factor"
    insight_text: str
    confidence: float
    supporting_decisions: List[str]  # Decision IDs

    actionable: bool
    recommendation: Optional[str] = None


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    market_data_healthy: bool
    protocols_healthy: bool


class DashboardData(BaseModel):
    """Data for dashboard display"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    portfolio: PortfolioState
    market: MarketData
    performance: PerformanceMetrics
    recent_decisions: List[Decision]
    recent_transactions: List[Transaction]

    # Alerts
    active_alerts: List[str] = []
    needs_rebalancing: bool = False
