#!/usr/bin/env python3
"""
Treasury Arena - Leverage Trading Engine

Provides leveraged trading platform where users can:
- Deposit capital
- Get 2-5x leverage
- Trade tokenized strategies
- Withdraw profits (with limits)
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Tuple
from decimal import Decimal


class LeverageTier(Enum):
    """Available leverage tiers"""
    CONSERVATIVE = 2  # 2x leverage
    MODERATE = 3      # 3x leverage
    AGGRESSIVE = 5    # 5x leverage


@dataclass
class LeverageAccount:
    """User account with leverage trading capabilities"""

    # Identity
    id: Optional[int] = None
    wallet_id: int = 0
    user_id: str = ""

    # Capital
    deposited_capital: float = 0.0    # User's actual deposit
    leverage_tier: LeverageTier = LeverageTier.MODERATE
    trading_power: float = 0.0         # Deposit × Leverage
    current_balance: float = 0.0       # Current value including P&L

    # P&L tracking
    total_profit: float = 0.0          # Lifetime profits
    total_loss: float = 0.0            # Lifetime losses
    unrealized_pnl: float = 0.0        # Open position P&L

    # Withdrawal limits
    withdrawable_amount: float = 0.0   # How much can be withdrawn now
    total_withdrawn: float = 0.0       # Total withdrawn to date
    last_withdrawal: Optional[datetime] = None
    monthly_withdrawal_limit_pct: float = 20.0  # Can withdraw 20% of profits/month

    # Risk management
    liquidation_threshold: float = -50.0  # Liquidate at -50% loss
    is_liquidated: bool = False

    # Timestamps
    created_at: datetime = None
    last_trade_at: Optional[datetime] = None

    def calculate_trading_power(self) -> float:
        """Calculate total trading power with leverage"""
        return self.deposited_capital * self.leverage_tier.value

    def calculate_withdrawable(self) -> float:
        """Calculate how much user can withdraw now"""
        # Can only withdraw profits, not principal
        net_profit = self.total_profit - self.total_loss

        if net_profit <= 0:
            return 0.0

        # Monthly limit: 20% of accumulated profits
        monthly_limit = net_profit * (self.monthly_withdrawal_limit_pct / 100)

        # Check if a month has passed since last withdrawal
        if self.last_withdrawal:
            days_since = (datetime.now() - self.last_withdrawal).days
            if days_since < 30:
                # Pro-rate the limit based on days
                monthly_limit *= (days_since / 30)

        return min(monthly_limit, net_profit)

    def check_liquidation(self) -> bool:
        """Check if account should be liquidated"""
        if self.deposited_capital <= 0:
            return False

        loss_pct = ((self.current_balance - self.deposited_capital) / self.deposited_capital) * 100

        if loss_pct <= self.liquidation_threshold:
            self.is_liquidated = True
            return True

        return False


class LeverageEngine:
    """Core leverage trading engine"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        """Create leverage trading tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Leverage accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leverage_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                deposited_capital REAL NOT NULL,
                leverage_tier INTEGER NOT NULL,
                trading_power REAL NOT NULL,
                current_balance REAL NOT NULL,
                total_profit REAL DEFAULT 0.0,
                total_loss REAL DEFAULT 0.0,
                unrealized_pnl REAL DEFAULT 0.0,
                withdrawable_amount REAL DEFAULT 0.0,
                total_withdrawn REAL DEFAULT 0.0,
                last_withdrawal TIMESTAMP,
                monthly_withdrawal_limit_pct REAL DEFAULT 20.0,
                liquidation_threshold REAL DEFAULT -50.0,
                is_liquidated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_trade_at TIMESTAMP,
                FOREIGN KEY (wallet_id) REFERENCES ai_wallets(id)
            )
        """)

        # Leverage trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leverage_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                trade_type TEXT NOT NULL,  -- 'OPEN' or 'CLOSE'
                token_symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                leverage_used REAL NOT NULL,
                position_size REAL NOT NULL,  -- quantity × leverage
                pnl REAL DEFAULT 0.0,
                fees_paid REAL NOT NULL,
                status TEXT NOT NULL,  -- 'OPEN', 'CLOSED', 'LIQUIDATED'
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES leverage_accounts(id)
            )
        """)

        # Fee collection table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS platform_fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                fee_type TEXT NOT NULL,  -- 'TRADING', 'LEVERAGE', 'WITHDRAWAL'
                amount REAL NOT NULL,
                description TEXT,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES leverage_accounts(id)
            )
        """)

        # Withdrawal history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                fee REAL NOT NULL,
                net_amount REAL NOT NULL,
                status TEXT NOT NULL,  -- 'PENDING', 'COMPLETED', 'REJECTED'
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES leverage_accounts(id)
            )
        """)

        conn.commit()
        conn.close()

    def create_account(
        self,
        wallet_id: int,
        user_id: str,
        deposit_amount: float,
        leverage_tier: LeverageTier = LeverageTier.MODERATE
    ) -> LeverageAccount:
        """Create a new leverage trading account"""

        trading_power = deposit_amount * leverage_tier.value

        account = LeverageAccount(
            wallet_id=wallet_id,
            user_id=user_id,
            deposited_capital=deposit_amount,
            leverage_tier=leverage_tier,
            trading_power=trading_power,
            current_balance=deposit_amount,
            created_at=datetime.now()
        )

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO leverage_accounts (
                wallet_id, user_id, deposited_capital, leverage_tier,
                trading_power, current_balance
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            account.wallet_id,
            account.user_id,
            account.deposited_capital,
            account.leverage_tier.value,
            account.trading_power,
            account.current_balance
        ))

        account.id = cursor.lastrowid
        conn.commit()
        conn.close()

        return account

    def open_leveraged_position(
        self,
        account_id: int,
        token_symbol: str,
        quantity: float,
        entry_price: float,
        leverage_multiplier: float
    ) -> Tuple[bool, str, float]:
        """
        Open a leveraged trading position

        Returns: (success, message, fees_charged)
        """

        # Get account
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM leverage_accounts WHERE id = ?", (account_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False, "Account not found", 0.0

        deposited_capital = row[3]
        leverage_tier = row[4]
        trading_power = row[5]
        current_balance = row[6]

        # Calculate position size
        position_size = quantity * entry_price
        effective_position = position_size * leverage_multiplier

        # Check if user has enough trading power
        if effective_position > trading_power:
            conn.close()
            return False, f"Insufficient trading power. Need ${effective_position:,.2f}, have ${trading_power:,.2f}", 0.0

        # Calculate fees
        trading_fee = position_size * 0.005  # 0.5% trading fee
        leverage_fee = effective_position * 0.001  # 0.1% leverage fee
        total_fees = trading_fee + leverage_fee

        # Deduct fees from balance
        new_balance = current_balance - total_fees

        # Create trade record
        cursor.execute("""
            INSERT INTO leverage_trades (
                account_id, trade_type, token_symbol, quantity,
                entry_price, leverage_used, position_size, fees_paid, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account_id, 'OPEN', token_symbol, quantity,
            entry_price, leverage_multiplier, effective_position, total_fees, 'OPEN'
        ))

        # Record fees
        cursor.execute("""
            INSERT INTO platform_fees (account_id, fee_type, amount, description)
            VALUES (?, ?, ?, ?)
        """, (account_id, 'TRADING', trading_fee, f"Trading fee for {token_symbol}"))

        cursor.execute("""
            INSERT INTO platform_fees (account_id, fee_type, amount, description)
            VALUES (?, ?, ?, ?)
        """, (account_id, 'LEVERAGE', leverage_fee, f"Leverage fee for {token_symbol}"))

        # Update account
        cursor.execute("""
            UPDATE leverage_accounts
            SET current_balance = ?, last_trade_at = ?
            WHERE id = ?
        """, (new_balance, datetime.now(), account_id))

        conn.commit()
        conn.close()

        return True, f"Position opened: {quantity} {token_symbol} @ ${entry_price} with {leverage_multiplier}x leverage", total_fees

    def close_position(
        self,
        trade_id: int,
        exit_price: float
    ) -> Tuple[bool, str, float]:
        """
        Close a leveraged position

        Returns: (success, message, pnl)
        """

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get trade
        cursor.execute("SELECT * FROM leverage_trades WHERE id = ? AND status = 'OPEN'", (trade_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False, "Trade not found or already closed", 0.0

        account_id = row[1]
        token_symbol = row[3]
        quantity = row[4]
        entry_price = row[5]
        leverage_used = row[7]
        position_size = row[8]

        # Calculate P&L
        price_change_pct = ((exit_price - entry_price) / entry_price)
        leveraged_pnl = position_size * price_change_pct

        # Trading fee on exit
        exit_value = quantity * exit_price
        exit_fee = exit_value * 0.005  # 0.5%
        net_pnl = leveraged_pnl - exit_fee

        # Update trade
        cursor.execute("""
            UPDATE leverage_trades
            SET exit_price = ?, pnl = ?, status = 'CLOSED', closed_at = ?
            WHERE id = ?
        """, (exit_price, net_pnl, datetime.now(), trade_id))

        # Record exit fee
        cursor.execute("""
            INSERT INTO platform_fees (account_id, fee_type, amount, description)
            VALUES (?, ?, ?, ?)
        """, (account_id, 'TRADING', exit_fee, f"Exit fee for {token_symbol}"))

        # Update account balance and profit/loss
        cursor.execute("SELECT current_balance, total_profit, total_loss FROM leverage_accounts WHERE id = ?", (account_id,))
        acc_row = cursor.fetchone()
        current_balance = acc_row[0]
        total_profit = acc_row[1]
        total_loss = acc_row[2]

        new_balance = current_balance + net_pnl

        if net_pnl > 0:
            total_profit += net_pnl
        else:
            total_loss += abs(net_pnl)

        cursor.execute("""
            UPDATE leverage_accounts
            SET current_balance = ?, total_profit = ?, total_loss = ?
            WHERE id = ?
        """, (new_balance, total_profit, total_loss, account_id))

        conn.commit()
        conn.close()

        direction = "profit" if net_pnl > 0 else "loss"
        return True, f"Position closed: {net_pnl:+.2f} {direction}", net_pnl

    def request_withdrawal(
        self,
        account_id: int,
        amount: float
    ) -> Tuple[bool, str]:
        """Request a withdrawal (subject to limits)"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get account
        cursor.execute("""
            SELECT deposited_capital, total_profit, total_loss, total_withdrawn,
                   last_withdrawal, monthly_withdrawal_limit_pct
            FROM leverage_accounts WHERE id = ?
        """, (account_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "Account not found"

        deposited = row[0]
        profit = row[1]
        loss = row[2]
        withdrawn = row[3]
        last_withdrawal = row[4]
        monthly_limit_pct = row[5]

        # Calculate withdrawable amount
        net_profit = profit - loss

        if net_profit <= 0:
            conn.close()
            return False, "No profits to withdraw"

        # Monthly limit
        monthly_limit = net_profit * (monthly_limit_pct / 100)

        # Check time since last withdrawal
        if last_withdrawal:
            last_dt = datetime.fromisoformat(last_withdrawal)
            days_since = (datetime.now() - last_dt).days
            if days_since < 30:
                monthly_limit *= (days_since / 30)

        available = min(monthly_limit, net_profit)

        if amount > available:
            conn.close()
            return False, f"Withdrawal exceeds limit. Max available: ${available:.2f}"

        # Calculate withdrawal fee (1%)
        fee = amount * 0.01
        net_amount = amount - fee

        # Create withdrawal record
        cursor.execute("""
            INSERT INTO withdrawals (account_id, amount, fee, net_amount, status)
            VALUES (?, ?, ?, ?, 'PENDING')
        """, (account_id, amount, fee, net_amount))

        # Record fee
        cursor.execute("""
            INSERT INTO platform_fees (account_id, fee_type, amount, description)
            VALUES (?, ?, ?, ?)
        """, (account_id, 'WITHDRAWAL', fee, f"Withdrawal fee"))

        # Update account
        cursor.execute("""
            UPDATE leverage_accounts
            SET total_withdrawn = total_withdrawn + ?, last_withdrawal = ?
            WHERE id = ?
        """, (amount, datetime.now(), account_id))

        conn.commit()
        conn.close()

        return True, f"Withdrawal requested: ${net_amount:.2f} (fee: ${fee:.2f})"

    def get_platform_stats(self) -> dict:
        """Get platform-wide statistics"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total accounts
        cursor.execute("SELECT COUNT(*) FROM leverage_accounts")
        total_accounts = cursor.fetchone()[0]

        # Total deposited
        cursor.execute("SELECT SUM(deposited_capital) FROM leverage_accounts")
        total_deposited = cursor.fetchone()[0] or 0.0

        # Total trading power
        cursor.execute("SELECT SUM(trading_power) FROM leverage_accounts")
        total_trading_power = cursor.fetchone()[0] or 0.0

        # Total fees collected
        cursor.execute("SELECT SUM(amount) FROM platform_fees")
        total_fees = cursor.fetchone()[0] or 0.0

        # Fees by type
        cursor.execute("SELECT fee_type, SUM(amount) FROM platform_fees GROUP BY fee_type")
        fees_by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # Active positions
        cursor.execute("SELECT COUNT(*) FROM leverage_trades WHERE status = 'OPEN'")
        active_positions = cursor.fetchone()[0]

        conn.close()

        return {
            "total_accounts": total_accounts,
            "total_deposited": total_deposited,
            "total_trading_power": total_trading_power,
            "total_fees_collected": total_fees,
            "fees_by_type": fees_by_type,
            "active_positions": active_positions,
            "leverage_multiplier": total_trading_power / total_deposited if total_deposited > 0 else 0
        }
