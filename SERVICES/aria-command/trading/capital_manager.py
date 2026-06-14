#!/usr/bin/env python3
"""
💵 CAPITAL MANAGEMENT SYSTEM
==============================

Manages capital growth and withdrawals:
- Minimum balance buffer (never trade below)
- Compounding rules (when to increase size)
- Withdrawal thresholds (take profits off table)
- Risk allocation rules

Ensures sustainable long-term capital growth.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger("aria.trading.capital")

DATA_DIR = Path(os.getenv("ARIA_DATA_DIR", "/opt/fpai/aria-command/data"))
STEWARD_CHAT_ID = int(os.getenv("STEWARD_CHAT_ID", "1759822075"))


@dataclass
class CapitalRules:
    """Capital management rules."""
    # Safety buffer
    min_balance: float = 200.0         # Never trade below this
    
    # Compounding
    compound_above: float = 500.0      # Start compounding above this
    compound_rate: float = 0.7         # Reinvest 70% of profits above threshold
    
    # Withdrawals
    profit_reinvest_pct: float = 0.7   # Reinvest 70% of profits
    withdrawal_threshold: float = 100.0 # Suggest withdrawal after $100 profit
    
    # Position limits
    max_single_trade_pct: float = 0.25 # Max 25% of trading capital per trade
    reserve_pct: float = 0.1           # Keep 10% as reserve


@dataclass
class WithdrawalSuggestion:
    """A suggested withdrawal."""
    amount: float
    reason: str
    current_balance: float
    profit_since_start: float
    pending: bool = True


class CapitalManager:
    """
    Manages capital growth and withdrawals.
    
    Features:
    - Tracks initial capital and current balance
    - Enforces minimum balance buffer
    - Suggests withdrawals at profit targets
    - Manages compounding rules
    """
    
    def __init__(self, initial_capital: float, rules: Optional[CapitalRules] = None):
        self._initial = initial_capital
        self._rules = rules or CapitalRules()
        self._current_balance: float = initial_capital
        self._total_withdrawn: float = 0.0
        self._realized_profit: float = 0.0
        self._pending_withdrawals: list[WithdrawalSuggestion] = []
        
        # Load state
        self._load_state()
    
    def _state_file(self) -> Path:
        """Get state file path."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / "capital_state.json"
    
    def _load_state(self):
        """Load persisted state."""
        try:
            path = self._state_file()
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                
                self._initial = data.get("initial_capital", self._initial)
                self._total_withdrawn = data.get("total_withdrawn", 0)
                self._realized_profit = data.get("realized_profit", 0)
                
                logger.info(f"💵 Loaded capital state: initial=${self._initial:,.2f}")
        except Exception as e:
            logger.warning(f"Failed to load capital state: {e}")
    
    def _save_state(self):
        """Save state to file."""
        try:
            data = {
                "initial_capital": self._initial,
                "total_withdrawn": self._total_withdrawn,
                "realized_profit": self._realized_profit,
                "current_balance": self._current_balance,
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self._state_file(), "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save capital state: {e}")
    
    def update_balance(self, new_balance: float):
        """Update current balance."""
        self._current_balance = new_balance
        self._save_state()
    
    def record_profit(self, pnl: float, new_balance: float):
        """Record a realized profit/loss."""
        self._realized_profit += pnl
        self._current_balance = new_balance
        
        # Check for withdrawal suggestion
        if self._should_suggest_withdrawal():
            self._create_withdrawal_suggestion()
        
        self._save_state()
    
    def get_trading_capital(self, current_balance: Optional[float] = None) -> float:
        """
        Calculate capital available for trading.
        
        Rules:
        1. Never risk the min_balance buffer
        2. Keep reserve percentage
        3. Apply compounding rules
        """
        balance = current_balance or self._current_balance
        
        # 1. Subtract minimum buffer
        available = balance - self._rules.min_balance
        if available <= 0:
            return 0.0
        
        # 2. Keep reserve
        reserve = available * self._rules.reserve_pct
        available -= reserve
        
        # 3. Apply compounding
        if balance > self._rules.compound_above:
            # Only compound a portion of profits above threshold
            excess = balance - self._rules.compound_above
            compounded_portion = excess * self._rules.compound_rate
            base_trading = self._rules.compound_above - self._rules.min_balance
            base_trading -= self._rules.compound_above * self._rules.reserve_pct
            available = base_trading + compounded_portion
        
        return max(0, available)
    
    def get_max_position_size(self, current_balance: Optional[float] = None) -> float:
        """
        Calculate max position size based on rules.
        """
        trading_capital = self.get_trading_capital(current_balance)
        return trading_capital * self._rules.max_single_trade_pct
    
    def _should_suggest_withdrawal(self) -> bool:
        """Check if we should suggest a withdrawal."""
        profit = self._current_balance - self._initial
        
        # Don't suggest if we haven't reached threshold
        if profit < self._rules.withdrawal_threshold:
            return False
        
        # Don't suggest if there's already a pending suggestion
        if self._pending_withdrawals:
            return False
        
        return True
    
    def _create_withdrawal_suggestion(self):
        """Create a withdrawal suggestion."""
        profit = self._current_balance - self._initial
        
        # Suggest withdrawing the non-reinvest portion
        withdrawal_pct = 1 - self._rules.profit_reinvest_pct
        suggested_amount = profit * withdrawal_pct
        
        if suggested_amount < 50:  # Min withdrawal threshold
            return
        
        suggestion = WithdrawalSuggestion(
            amount=round(suggested_amount, 2),
            reason=f"Take ${suggested_amount:.2f} profit off the table",
            current_balance=self._current_balance,
            profit_since_start=profit
        )
        
        self._pending_withdrawals.append(suggestion)
        
        logger.info(f"💰 Withdrawal suggested: ${suggested_amount:,.2f}")
        
        # Notify steward
        self._notify_withdrawal_suggestion(suggestion)
    
    def check_withdrawal(self, current_balance: Optional[float] = None) -> Optional[float]:
        """
        Check if withdrawal should be made.
        
        Returns withdrawal amount if threshold reached.
        """
        balance = current_balance or self._current_balance
        profit = balance - self._initial - self._total_withdrawn
        
        if profit >= self._rules.withdrawal_threshold:
            withdrawal_pct = 1 - self._rules.profit_reinvest_pct
            return profit * withdrawal_pct
        
        return None
    
    def confirm_withdrawal(self, amount: float):
        """Confirm a withdrawal was made."""
        self._total_withdrawn += amount
        self._current_balance -= amount
        
        # Clear pending suggestions
        self._pending_withdrawals = [
            s for s in self._pending_withdrawals
            if not s.pending or s.amount != amount
        ]
        
        self._save_state()
        logger.info(f"💸 Withdrawal confirmed: ${amount:,.2f}")
    
    def dismiss_withdrawal_suggestion(self):
        """Dismiss pending withdrawal suggestion."""
        self._pending_withdrawals = []
    
    def can_trade(self, current_balance: Optional[float] = None) -> tuple[bool, str]:
        """Check if trading is allowed based on capital rules."""
        balance = current_balance or self._current_balance
        
        if balance < self._rules.min_balance:
            return False, f"Balance ${balance:.2f} below minimum ${self._rules.min_balance:.2f}"
        
        trading_capital = self.get_trading_capital(balance)
        if trading_capital < 50:  # Minimum practical trading capital
            return False, f"Trading capital ${trading_capital:.2f} too low"
        
        return True, "OK"
    
    def get_status(self) -> Dict:
        """Get current capital management status."""
        profit = self._current_balance - self._initial
        return_pct = profit / self._initial * 100 if self._initial > 0 else 0
        
        return {
            "initial_capital": self._initial,
            "current_balance": self._current_balance,
            "total_withdrawn": self._total_withdrawn,
            "realized_profit": self._realized_profit,
            "current_profit": round(profit, 2),
            "return_pct": round(return_pct, 2),
            "trading_capital": round(self.get_trading_capital(), 2),
            "max_position_size": round(self.get_max_position_size(), 2),
            "can_trade": self.can_trade()[0],
            "pending_withdrawals": [
                {"amount": s.amount, "reason": s.reason}
                for s in self._pending_withdrawals
            ],
            "rules": {
                "min_balance": self._rules.min_balance,
                "compound_above": self._rules.compound_above,
                "withdrawal_threshold": self._rules.withdrawal_threshold,
                "max_single_trade_pct": self._rules.max_single_trade_pct
            }
        }
    
    async def _notify_withdrawal_suggestion(self, suggestion: WithdrawalSuggestion):
        """Notify steward of withdrawal suggestion."""
        try:
            from telegram.bot import send_message
            
            profit_pct = (suggestion.profit_since_start / self._initial) * 100
            
            message = f"""💰 **WITHDRAWAL SUGGESTED**

**Suggestion:** Take ${suggestion.amount:,.2f} off the table

**Account Status:**
• Initial Capital: ${self._initial:,.2f}
• Current Balance: ${suggestion.current_balance:,.2f}
• Total Profit: ${suggestion.profit_since_start:,.2f} (+{profit_pct:.1f}%)
• Already Withdrawn: ${self._total_withdrawn:,.2f}

**After Withdrawal:**
• Remaining Balance: ${suggestion.current_balance - suggestion.amount:,.2f}
• Still +${suggestion.profit_since_start - suggestion.amount:,.2f} profit

_Locking in profits reduces risk while keeping gains working_"""
            
            await send_message(STEWARD_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Failed to notify: {e}")


# Singleton
_capital_manager: Optional[CapitalManager] = None


def get_capital_manager(initial_capital: float = 500.0) -> CapitalManager:
    """Get or create global capital manager."""
    global _capital_manager
    if _capital_manager is None:
        _capital_manager = CapitalManager(initial_capital)
    return _capital_manager









