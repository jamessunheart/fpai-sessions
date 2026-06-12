"""
Coracle Prediction Engine - Data Models
=======================================
Pydantic models for signals, contracts, and API responses.
"""
from pydantic import BaseModel, Field, computed_field
from typing import Optional, Dict, List, Any, Literal
from datetime import datetime
from enum import Enum
from uuid import uuid4


# ============================================================================
# ENUMS
# ============================================================================

class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class ContractGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class TradeOutcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    PENDING = "PENDING"


class VolatilityRegime(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class LatencyTier(str, Enum):
    FAST = "FAST"      # 100ms-1s updates
    MEDIUM = "MEDIUM"  # 1-5min updates
    SLOW = "SLOW"      # 1-24hr updates


# ============================================================================
# SIGNAL MODELS
# ============================================================================

class SignalValue(BaseModel):
    """Individual signal with metadata."""
    name: str
    value: float
    signal: str  # BULLISH, BEARISH, NEUTRAL, etc.
    strength: float = Field(ge=0, le=100)
    tier: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = "computed"
    raw_data: Optional[Dict[str, Any]] = None


class SignalSnapshot(BaseModel):
    """Complete signal snapshot for an asset."""
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    price: float
    
    # Liquidity Signals
    bai: Optional[SignalValue] = None  # Bid/Ask Imbalance
    obs: Optional[SignalValue] = None  # Order Book Slope
    lcp: Optional[SignalValue] = None  # Liquidity Cascade Potential
    
    # Whale Signals
    wadi: Optional[SignalValue] = None  # Whale Accumulation/Distribution Index
    wc: Optional[SignalValue] = None    # Whale Confidence
    
    # Derivatives Signals
    cvd: Optional[SignalValue] = None   # Cumulative Volume Delta
    oi: Optional[SignalValue] = None    # Open Interest
    
    # Funding Signals
    fr: Optional[SignalValue] = None    # Funding Rate
    
    # On-Chain Signals (when available)
    sopr: Optional[SignalValue] = None  # Spent Output Profit Ratio
    mvrv: Optional[SignalValue] = None  # Market Value to Realized Value
    nupl: Optional[SignalValue] = None  # Net Unrealized Profit/Loss
    
    # Technical Signals
    vrc: Optional[SignalValue] = None   # Volatility Regime Classifier
    
    # Sentiment Signals
    fgi: Optional[SignalValue] = None   # Fear & Greed Index
    ls_ratio: Optional[SignalValue] = None  # Long/Short Ratio
    spot_premium: Optional[SignalValue] = None  # Spot Premium
    
    # Options/Gamma (when available)
    gex: Optional[SignalValue] = None   # Gamma Exposure
    pcr: Optional[SignalValue] = None   # Put/Call Ratio


# ============================================================================
# SACRED GATE MODELS
# ============================================================================

class GateKeyStatus(BaseModel):
    """Status of a single sacred gate key."""
    name: str
    passed: bool
    value: float
    threshold: float
    description: str


class SacredGateResult(BaseModel):
    """Result of sacred three-key gate validation."""
    passed: bool
    whale_key: GateKeyStatus
    liquidity_key: GateKeyStatus
    gamma_key: GateKeyStatus
    
    @computed_field
    @property
    def keys_passed(self) -> int:
        return sum([self.whale_key.passed, self.liquidity_key.passed, self.gamma_key.passed])


# ============================================================================
# CONFLUENCE MODELS
# ============================================================================

class TierScore(BaseModel):
    """Score for a signal tier."""
    tier: str
    weight: float
    signals_aligned: int
    signals_total: int
    raw_score: float
    weighted_score: float


class ConfluenceResult(BaseModel):
    """Result of confluence calculation."""
    direction: Direction
    base_probability: float = Field(ge=0, le=1)
    confluence_multiplier: float
    final_probability: float = Field(ge=0, le=1)
    tier_scores: List[TierScore]
    danger_penalty: float = 0.0
    aligned_tiers: int


# ============================================================================
# CONTRACT MODELS
# ============================================================================

class StopLoss(BaseModel):
    """Dynamic stop loss specification."""
    price: float
    distance_pct: float
    protection_logic: str
    volatility_regime: VolatilityRegime
    atr_value: float
    liquidation_buffer: bool = False


class TakeProfit(BaseModel):
    """Take profit level specification."""
    level: int = Field(ge=1, le=3)
    price: float
    size: float = Field(ge=0, le=1)  # Position percentage
    rr_ratio: float
    probability: float = Field(ge=0, le=1)


class TradingContract(BaseModel):
    """Complete trading contract with entry, exit, and risk parameters."""
    contract_id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    direction: Direction
    
    # Entry
    entry_price: float
    entry_type: Literal["MOMENTUM", "RETRACE", "REVERSAL"] = "MOMENTUM"
    
    # Risk Management
    stop_loss: StopLoss
    take_profits: List[TakeProfit]
    
    # Scoring
    confidence_score: float = Field(ge=0, le=1)
    grade: ContractGrade
    confluence_multiplier: float
    
    # Gate Validation
    sacred_gate: SacredGateResult
    
    # Signals Snapshot
    signals_snapshot: Dict[str, Any]
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # Outcome Tracking
    outcome: TradeOutcome = TradeOutcome.PENDING
    actual_exit_price: Optional[float] = None
    actual_pnl_pct: Optional[float] = None
    resolved_at: Optional[datetime] = None


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request for market analysis and contract generation."""
    ticker: str = Field(..., description="Asset symbol (BTC, ETH, XRP, SOL)")
    direction: Optional[Direction] = Field(default=None, description="Force direction or auto-detect")
    entry_type: Literal["MOMENTUM", "RETRACE", "REVERSAL"] = "MOMENTUM"
    capital: Optional[float] = Field(default=None, description="Capital for position sizing")


class AnalysisResponse(BaseModel):
    """Response from market analysis."""
    success: bool
    contract: Optional[TradingContract] = None
    signals: Optional[SignalSnapshot] = None
    gate_status: Optional[SacredGateResult] = None
    confluence: Optional[ConfluenceResult] = None
    error: Optional[str] = None
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class ContractListResponse(BaseModel):
    """List of contracts response."""
    contracts: List[TradingContract]
    total: int
    page: int = 1
    page_size: int = 50


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    uptime_seconds: float
    data_sources: Dict[str, bool]
    tracked_assets: List[str]
    active_contracts: int


# ============================================================================
# COMPOUNDING MODELS
# ============================================================================

class CompoundingState(BaseModel):
    """State of the compounding engine."""
    capital: float
    initial_capital: float
    preservation_mode: bool = False
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    total_trades: int = 0
    win_rate: float = 0.0


class CompoundingDecision(BaseModel):
    """Compounding engine decision."""
    action: Literal["COMPOUND_FULL", "COMPOUND_PROFIT_ONLY", "PRESERVATION_MODE", "WAIT"]
    capital_to_deploy: float
    next_setup: Optional[TradingContract] = None
    reason: str


# ============================================================================
# CAPACITY MODELS
# ============================================================================

class CapacityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    PAUSED = "paused"


class CapacityState(BaseModel):
    """Capacity oracle state for an asset."""
    asset: str
    level: CapacityLevel
    updated_at: datetime
    contributing_signals: Dict[str, float]
    max_position_pct: float  # Maximum position as % of capital


