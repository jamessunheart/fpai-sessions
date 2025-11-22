"""
Tokenization Models for Treasury Arena

Provides dataclasses and database models for:
- Strategy Tokens (tokenized AI agent strategies)
- AI Wallets (user portfolios with AI management)
- Token Holdings (ownership records)
- Transactions (audit trail)
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ============================================================================
# ENUMS
# ============================================================================

class TokenStatus(Enum):
    """Strategy token lifecycle states"""
    PROVING = "proving"      # In paper trading (30 days)
    ACTIVE = "active"        # Live and tradeable
    PAUSED = "paused"        # Temporarily disabled
    RETIRED = "retired"      # Permanently closed


class WalletMode(Enum):
    """AI wallet management modes"""
    FULL_AI = "full_ai"      # AI decides everything
    HYBRID = "hybrid"        # AI suggests, user approves
    MANUAL = "manual"        # User controls all decisions


class RiskTolerance(Enum):
    """User risk preferences"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class TransactionType(Enum):
    """Token transaction types"""
    BUY = "buy"
    SELL = "sell"
    MINT = "mint"           # Create new tokens
    BURN = "burn"           # Destroy tokens


# ============================================================================
# STRATEGY TOKEN
# ============================================================================

@dataclass
class StrategyToken:
    """
    Represents a tokenized treasury strategy.

    Each strategy that passes backtesting and proving grounds
    becomes a tradeable token that users can purchase.
    """

    # Identity
    id: Optional[int] = None
    token_symbol: str = ""                    # STRAT-AAVE-MOMENTUM-001
    strategy_id: int = 0                       # Reference to TreasuryAgent
    strategy_name: str = ""
    strategy_description: str = ""

    # Token economics
    total_supply: int = 0                      # Fixed at creation
    circulating_supply: int = 0                # Currently in circulation
    reserved_supply: int = 0                   # Team/insurance reserve

    # Pricing
    current_nav: float = 0.0                   # Net Asset Value per token
    initial_nav: float = 1.0                   # Starting NAV
    total_aum: float = 0.0                     # Assets Under Management

    # Lifecycle
    status: TokenStatus = TokenStatus.PROVING
    creation_date: datetime = field(default_factory=datetime.now)
    tokenization_date: Optional[datetime] = None
    retirement_date: Optional[datetime] = None

    # Performance metrics (cached)
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_return_pct: Optional[float] = None
    last_30d_return_pct: Optional[float] = None
    last_7d_return_pct: Optional[float] = None

    # Constraints
    min_purchase: float = 1.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "token_symbol": self.token_symbol,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_description": self.strategy_description,
            "total_supply": self.total_supply,
            "circulating_supply": self.circulating_supply,
            "current_nav": self.current_nav,
            "initial_nav": self.initial_nav,
            "total_aum": self.total_aum,
            "status": self.status.value,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "total_return_pct": self.total_return_pct,
            "last_30d_return_pct": self.last_30d_return_pct,
            "last_7d_return_pct": self.last_7d_return_pct,
            "min_purchase": self.min_purchase,
        }

    def save(self, db_path: str = "treasury_arena.db") -> int:
        """Save token to database, returns token ID"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if self.id is None:
            # Insert new token
            cursor.execute("""
                INSERT INTO strategy_tokens (
                    token_symbol, strategy_id, strategy_name, strategy_description,
                    total_supply, circulating_supply, reserved_supply,
                    current_nav, initial_nav, total_aum,
                    status, creation_date, tokenization_date, retirement_date,
                    sharpe_ratio, max_drawdown, total_return_pct,
                    last_30d_return_pct, last_7d_return_pct,
                    min_purchase, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.token_symbol, self.strategy_id, self.strategy_name, self.strategy_description,
                self.total_supply, self.circulating_supply, self.reserved_supply,
                self.current_nav, self.initial_nav, self.total_aum,
                self.status.value, self.creation_date, self.tokenization_date, self.retirement_date,
                self.sharpe_ratio, self.max_drawdown, self.total_return_pct,
                self.last_30d_return_pct, self.last_7d_return_pct,
                self.min_purchase, self.created_at, self.updated_at
            ))
            self.id = cursor.lastrowid
        else:
            # Update existing token
            self.updated_at = datetime.now()
            cursor.execute("""
                UPDATE strategy_tokens SET
                    circulating_supply = ?, current_nav = ?, total_aum = ?,
                    status = ?, sharpe_ratio = ?, max_drawdown = ?,
                    total_return_pct = ?, last_30d_return_pct = ?, last_7d_return_pct = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                self.circulating_supply, self.current_nav, self.total_aum,
                self.status.value, self.sharpe_ratio, self.max_drawdown,
                self.total_return_pct, self.last_30d_return_pct, self.last_7d_return_pct,
                self.updated_at, self.id
            ))

        conn.commit()
        conn.close()
        return self.id

    @staticmethod
    def load(token_id: int, db_path: str = "treasury_arena.db") -> Optional['StrategyToken']:
        """Load token from database by ID"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM strategy_tokens WHERE id = ?", (token_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return StrategyToken._from_row(row)

    @staticmethod
    def load_by_symbol(symbol: str, db_path: str = "treasury_arena.db") -> Optional['StrategyToken']:
        """Load token from database by symbol"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM strategy_tokens WHERE token_symbol = ?", (symbol,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return StrategyToken._from_row(row)

    @staticmethod
    def list_active(db_path: str = "treasury_arena.db") -> List['StrategyToken']:
        """List all active tokens"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM strategy_tokens WHERE status = 'active' ORDER BY total_aum DESC")
        rows = cursor.fetchall()
        conn.close()

        return [StrategyToken._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row) -> 'StrategyToken':
        """Create StrategyToken from database row"""
        return StrategyToken(
            id=row[0],
            token_symbol=row[1],
            strategy_id=row[2],
            strategy_name=row[3],
            strategy_description=row[4],
            total_supply=row[5],
            circulating_supply=row[6],
            reserved_supply=row[7],
            current_nav=row[8],
            initial_nav=row[9],
            total_aum=row[10],
            status=TokenStatus(row[11]),
            creation_date=datetime.fromisoformat(row[12]) if row[12] else None,
            tokenization_date=datetime.fromisoformat(row[13]) if row[13] else None,
            retirement_date=datetime.fromisoformat(row[14]) if row[14] else None,
            sharpe_ratio=row[15],
            max_drawdown=row[16],
            total_return_pct=row[17],
            last_30d_return_pct=row[18],
            last_7d_return_pct=row[19],
            min_purchase=row[20],
            created_at=datetime.fromisoformat(row[21]),
            updated_at=datetime.fromisoformat(row[22])
        )


# ============================================================================
# AI WALLET
# ============================================================================

@dataclass
class AIWallet:
    """
    AI-powered wallet that manages user capital across strategy tokens.

    Modes:
    - FULL_AI: AI makes all allocation decisions automatically
    - HYBRID: AI suggests, user approves
    - MANUAL: User makes all decisions
    """

    # Identity
    id: Optional[int] = None
    wallet_address: str = field(default_factory=lambda: str(uuid.uuid4()))

    # User info
    user_id: str = ""
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    # Wallet mode
    mode: WalletMode = WalletMode.HYBRID
    ai_optimizer_active: bool = True

    # Capital
    total_capital: float = 0.0
    cash_balance: float = 0.0
    invested_balance: float = 0.0

    # Performance tracking
    initial_capital: float = 0.0
    all_time_high: float = 0.0
    total_return_pct: float = 0.0
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None

    # Risk preferences
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    max_single_strategy_pct: float = 20.0
    min_diversification: int = 5

    # Compliance
    church_verified: bool = False
    attestation_signed: bool = False
    attestation_date: Optional[datetime] = None

    # Lifecycle
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_rebalance_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "wallet_address": self.wallet_address,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "mode": self.mode.value,
            "ai_optimizer_active": self.ai_optimizer_active,
            "total_capital": self.total_capital,
            "cash_balance": self.cash_balance,
            "invested_balance": self.invested_balance,
            "total_return_pct": self.total_return_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "risk_tolerance": self.risk_tolerance.value,
            "church_verified": self.church_verified,
            "attestation_signed": self.attestation_signed,
        }

    def save(self, db_path: str = "treasury_arena.db") -> int:
        """Save wallet to database, returns wallet ID"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if self.id is None:
            # Insert new wallet
            cursor.execute("""
                INSERT INTO ai_wallets (
                    wallet_address, user_id, user_email, user_name,
                    mode, ai_optimizer_active,
                    total_capital, cash_balance, invested_balance,
                    initial_capital, all_time_high, total_return_pct,
                    sharpe_ratio, max_drawdown,
                    risk_tolerance, max_single_strategy_pct, min_diversification,
                    church_verified, attestation_signed, attestation_date,
                    status, created_at, updated_at, last_rebalance_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.wallet_address, self.user_id, self.user_email, self.user_name,
                self.mode.value, self.ai_optimizer_active,
                self.total_capital, self.cash_balance, self.invested_balance,
                self.initial_capital, self.all_time_high, self.total_return_pct,
                self.sharpe_ratio, self.max_drawdown,
                self.risk_tolerance.value, self.max_single_strategy_pct, self.min_diversification,
                self.church_verified, self.attestation_signed, self.attestation_date,
                self.status, self.created_at, self.updated_at, self.last_rebalance_at
            ))
            self.id = cursor.lastrowid
        else:
            # Update existing wallet
            self.updated_at = datetime.now()
            cursor.execute("""
                UPDATE ai_wallets SET
                    mode = ?, ai_optimizer_active = ?,
                    total_capital = ?, cash_balance = ?, invested_balance = ?,
                    all_time_high = ?, total_return_pct = ?,
                    sharpe_ratio = ?, max_drawdown = ?,
                    risk_tolerance = ?, max_single_strategy_pct = ?, min_diversification = ?,
                    church_verified = ?, attestation_signed = ?, attestation_date = ?,
                    status = ?, updated_at = ?, last_rebalance_at = ?
                WHERE id = ?
            """, (
                self.mode.value, self.ai_optimizer_active,
                self.total_capital, self.cash_balance, self.invested_balance,
                self.all_time_high, self.total_return_pct,
                self.sharpe_ratio, self.max_drawdown,
                self.risk_tolerance.value, self.max_single_strategy_pct, self.min_diversification,
                self.church_verified, self.attestation_signed, self.attestation_date,
                self.status, self.updated_at, self.last_rebalance_at,
                self.id
            ))

        conn.commit()
        conn.close()
        return self.id

    @staticmethod
    def load(wallet_id: int, db_path: str = "treasury_arena.db") -> Optional['AIWallet']:
        """Load wallet from database by ID"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ai_wallets WHERE id = ?", (wallet_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return AIWallet._from_row(row)

    @staticmethod
    def load_by_address(address: str, db_path: str = "treasury_arena.db") -> Optional['AIWallet']:
        """Load wallet from database by address"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ai_wallets WHERE wallet_address = ?", (address,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return AIWallet._from_row(row)

    @staticmethod
    def _from_row(row) -> 'AIWallet':
        """Create AIWallet from database row"""
        return AIWallet(
            id=row[0],
            wallet_address=row[1],
            user_id=row[2],
            user_email=row[3],
            user_name=row[4],
            mode=WalletMode(row[5]),
            ai_optimizer_active=bool(row[6]),
            total_capital=row[7],
            cash_balance=row[8],
            invested_balance=row[9],
            initial_capital=row[10],
            all_time_high=row[11],
            total_return_pct=row[12],
            sharpe_ratio=row[13],
            max_drawdown=row[14],
            risk_tolerance=RiskTolerance(row[15]),
            max_single_strategy_pct=row[16],
            min_diversification=row[17],
            church_verified=bool(row[18]),
            attestation_signed=bool(row[19]),
            attestation_date=datetime.fromisoformat(row[20]) if row[20] else None,
            status=row[21],
            created_at=datetime.fromisoformat(row[22]),
            updated_at=datetime.fromisoformat(row[23]),
            last_rebalance_at=datetime.fromisoformat(row[24]) if row[24] else None
        )


# ============================================================================
# TOKEN HOLDING
# ============================================================================

@dataclass
class TokenHolding:
    """Represents ownership of strategy tokens by a wallet"""

    id: Optional[int] = None
    wallet_id: int = 0
    token_id: int = 0

    # Position details
    quantity: float = 0.0
    avg_cost_basis: float = 0.0
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

    # Timing
    first_acquired_at: datetime = field(default_factory=datetime.now)
    last_updated_at: datetime = field(default_factory=datetime.now)

    def update_value(self, current_nav: float):
        """Update current value and P&L based on current NAV"""
        self.current_value = self.quantity * current_nav
        cost = self.quantity * self.avg_cost_basis
        self.unrealized_pnl = self.current_value - cost
        self.unrealized_pnl_pct = (self.unrealized_pnl / cost * 100) if cost > 0 else 0.0
        self.last_updated_at = datetime.now()

    def save(self, db_path: str = "treasury_arena.db") -> int:
        """Save holding to database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if self.id is None:
            cursor.execute("""
                INSERT INTO token_holdings (
                    wallet_id, token_id, quantity, avg_cost_basis,
                    current_value, unrealized_pnl, unrealized_pnl_pct,
                    first_acquired_at, last_updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.wallet_id, self.token_id, self.quantity, self.avg_cost_basis,
                self.current_value, self.unrealized_pnl, self.unrealized_pnl_pct,
                self.first_acquired_at, self.last_updated_at
            ))
            self.id = cursor.lastrowid
        else:
            cursor.execute("""
                UPDATE token_holdings SET
                    quantity = ?, avg_cost_basis = ?,
                    current_value = ?, unrealized_pnl = ?, unrealized_pnl_pct = ?,
                    last_updated_at = ?
                WHERE id = ?
            """, (
                self.quantity, self.avg_cost_basis,
                self.current_value, self.unrealized_pnl, self.unrealized_pnl_pct,
                self.last_updated_at, self.id
            ))

        conn.commit()
        conn.close()
        return self.id

    @staticmethod
    def get_wallet_holdings(wallet_id: int, db_path: str = "treasury_arena.db") -> List['TokenHolding']:
        """Get all holdings for a wallet"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM token_holdings WHERE wallet_id = ?", (wallet_id,))
        rows = cursor.fetchall()
        conn.close()

        return [TokenHolding._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row) -> 'TokenHolding':
        """Create TokenHolding from database row"""
        return TokenHolding(
            id=row[0],
            wallet_id=row[1],
            token_id=row[2],
            quantity=row[3],
            avg_cost_basis=row[4],
            current_value=row[5],
            unrealized_pnl=row[6],
            unrealized_pnl_pct=row[7],
            first_acquired_at=datetime.fromisoformat(row[8]),
            last_updated_at=datetime.fromisoformat(row[9])
        )


# ============================================================================
# TRANSACTION
# ============================================================================

@dataclass
class TokenTransaction:
    """Records token buy/sell transactions"""

    id: Optional[int] = None
    wallet_id: int = 0
    token_id: int = 0

    # Transaction details
    transaction_type: TransactionType = TransactionType.BUY
    quantity: float = 0.0
    price_per_token: float = 0.0
    total_value: float = 0.0

    # Fees
    platform_fee: float = 0.0
    performance_fee: float = 0.0

    # Context
    triggered_by: str = "user"  # user, ai_optimizer, admin
    notes: Optional[str] = None

    # Timing
    executed_at: datetime = field(default_factory=datetime.now)

    def save(self, db_path: str = "treasury_arena.db") -> int:
        """Save transaction to database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO token_transactions (
                wallet_id, token_id, transaction_type,
                quantity, price_per_token, total_value,
                platform_fee, performance_fee,
                triggered_by, notes, executed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.wallet_id, self.token_id, self.transaction_type.value,
            self.quantity, self.price_per_token, self.total_value,
            self.platform_fee, self.performance_fee,
            self.triggered_by, self.notes, self.executed_at
        ))

        self.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return self.id

    @staticmethod
    def get_wallet_transactions(wallet_id: int, limit: int = 100, db_path: str = "treasury_arena.db") -> List['TokenTransaction']:
        """Get transaction history for a wallet"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM token_transactions
            WHERE wallet_id = ?
            ORDER BY executed_at DESC
            LIMIT ?
        """, (wallet_id, limit))
        rows = cursor.fetchall()
        conn.close()

        return [TokenTransaction._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row) -> 'TokenTransaction':
        """Create TokenTransaction from database row"""
        return TokenTransaction(
            id=row[0],
            wallet_id=row[1],
            token_id=row[2],
            transaction_type=TransactionType(row[3]),
            quantity=row[4],
            price_per_token=row[5],
            total_value=row[6],
            platform_fee=row[7],
            performance_fee=row[8],
            triggered_by=row[9],
            notes=row[10],
            executed_at=datetime.fromisoformat(row[11])
        )
