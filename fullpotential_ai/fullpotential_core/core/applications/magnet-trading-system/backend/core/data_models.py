"""
Core data structures for the Magnet Protocol
Complete production-ready implementation
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from datetime import datetime


class MagnetType(Enum):
    """Types of market magnets"""
    STRUCTURAL = "structural"      # Swing highs/lows
    LIQUIDITY = "liquidity"        # Stop clusters, equal highs/lows, FVGs
    ORDERFLOW = "orderflow"        # Liquidations, imbalances
    VOLUME = "volume"              # Volume voids, POCs
    TIMEFRAME = "timeframe"        # Multi-TF confluence


class MagnetTier(Enum):
    """Magnet quality tiers"""
    TIER_1 = 1  # Strongest - full position sizing
    TIER_2 = 2  # Supporting - reduced sizing
    TIER_3 = 3  # Traps - minimal sizing
    TIER_4 = 4  # Phantom - avoid


@dataclass
class Magnet:
    """Represents a detected market magnet"""
    level: float
    magnet_type: MagnetType
    strength: float                 # S: 0-100 score
    conflict: float                 # C: competing magnets
    distance_atr: float             # D: normalized distance
    volatility_pressure: float      # V: market stress
    tier: MagnetTier
    timeframe: str                  # "1h", "4h", "1d"
    detected_at: datetime


@dataclass
class MarketState:
    """Current market conditions"""
    symbol: str
    timestamp: datetime
    price: float
    atr: float
    volume: float
    trend_direction: str            # "up", "down", "neutral"
    liquidity_score: float          # 0-100


@dataclass
class Position:
    """Open or proposed trading position"""
    symbol: str
    direction: str                  # "long", "short"
    size_usd: float
    leverage: float
    entry_price: float
    stop_price: float
    target_price: float
    magnet_tier: MagnetTier
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    pnl: Optional[float] = None


@dataclass
class AccountState:
    """Current account state"""
    equity: float
    available_margin: float
    open_positions_value: float
    unrealized_pnl: float
    daily_pnl: float
