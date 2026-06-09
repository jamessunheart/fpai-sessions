"""
Coracle Compounding Engine (Snowball Strategy)
===============================================
Manages capital compounding logic for consecutive wins.

Strategy:
- Win → Roll principal + profit into next Grade A setup
- Loss → Enter preservation mode (risk only profits)
- Grade A required for full compounding
"""
from datetime import datetime, timezone
from typing import Optional, List
import logging

from app.config import Settings
from app.models import (
    CompoundingState, CompoundingDecision, TradingContract,
    TradeOutcome, ContractGrade
)

logger = logging.getLogger(__name__)


class CompoundingEngine:
    """
    Snowball compounding engine.
    
    Manages capital growth through intelligent compounding:
    - Full compounding on Grade A wins
    - Profit-only compounding in preservation mode
    - Cross-asset scanning for best setups
    """
    
    def __init__(self, settings: Settings, initial_capital: float = 10000.0):
        self.settings = settings
        
        # State
        self.state = CompoundingState(
            capital=initial_capital,
            initial_capital=initial_capital,
            preservation_mode=False,
            consecutive_wins=0,
            consecutive_losses=0,
            total_trades=0,
            win_rate=0.0
        )
        
        # Trade history for win rate calculation
        self._trade_history: List[dict] = []
    
    def process_trade_outcome(
        self,
        contract: TradingContract,
        outcome: TradeOutcome,
        pnl_usd: float
    ) -> CompoundingDecision:
        """
        Process a trade outcome and decide on compounding action.
        
        Args:
            contract: The completed contract
            outcome: WIN, LOSS, or BREAKEVEN
            pnl_usd: Actual P&L in USD
        
        Returns:
            CompoundingDecision with action and reasoning
        """
        # Update state
        self.state.total_trades += 1
        
        if outcome == TradeOutcome.WIN:
            return self._handle_win(contract, pnl_usd)
        elif outcome == TradeOutcome.LOSS:
            return self._handle_loss(contract, pnl_usd)
        else:
            return self._handle_breakeven(contract)
    
    def _handle_win(
        self, 
        contract: TradingContract, 
        pnl_usd: float
    ) -> CompoundingDecision:
        """Handle winning trade."""
        # Update state
        self.state.capital += pnl_usd
        self.state.consecutive_wins += 1
        self.state.consecutive_losses = 0
        self._update_win_rate(won=True)
        
        logger.info(
            f"WIN: +${pnl_usd:.2f} | Capital: ${self.state.capital:.2f} | "
            f"Streak: {self.state.consecutive_wins}"
        )
        
        # Exit preservation mode after 2 consecutive wins
        if self.state.preservation_mode and self.state.consecutive_wins >= 2:
            self.state.preservation_mode = False
            logger.info("Exiting preservation mode after 2 consecutive wins")
        
        # Look for next Grade A setup
        # In production, this would scan all assets
        
        if self.state.preservation_mode:
            # Preservation mode: only risk the profit
            return CompoundingDecision(
                action="COMPOUND_PROFIT_ONLY",
                capital_to_deploy=pnl_usd,
                reason=(
                    f"Preservation mode active. Risking profit only: ${pnl_usd:.2f}. "
                    f"Win {self.state.consecutive_wins - 1} more to exit preservation."
                )
            )
        else:
            # Full compounding
            return CompoundingDecision(
                action="COMPOUND_FULL",
                capital_to_deploy=self.state.capital,
                reason=(
                    f"Full compounding enabled. Capital: ${self.state.capital:.2f}. "
                    f"Win streak: {self.state.consecutive_wins}. "
                    "Scanning for Grade A setups..."
                )
            )
    
    def _handle_loss(
        self, 
        contract: TradingContract, 
        pnl_usd: float
    ) -> CompoundingDecision:
        """Handle losing trade."""
        # Update state
        self.state.capital += pnl_usd  # pnl_usd is negative
        self.state.consecutive_wins = 0
        self.state.consecutive_losses += 1
        self._update_win_rate(won=False)
        
        logger.info(
            f"LOSS: ${pnl_usd:.2f} | Capital: ${self.state.capital:.2f} | "
            f"Loss streak: {self.state.consecutive_losses}"
        )
        
        # Enter preservation mode
        self.state.preservation_mode = True
        
        return CompoundingDecision(
            action="PRESERVATION_MODE",
            capital_to_deploy=0,
            reason=(
                f"Loss of ${abs(pnl_usd):.2f}. Entering preservation mode. "
                f"Capital now: ${self.state.capital:.2f}. "
                "Will only risk profits until 2 consecutive wins."
            )
        )
    
    def _handle_breakeven(self, contract: TradingContract) -> CompoundingDecision:
        """Handle breakeven trade."""
        logger.info(f"BREAKEVEN | Capital: ${self.state.capital:.2f}")
        
        return CompoundingDecision(
            action="WAIT",
            capital_to_deploy=0,
            reason="Breakeven trade. Waiting for next setup."
        )
    
    def scan_for_setups(
        self, 
        contracts: List[TradingContract]
    ) -> Optional[TradingContract]:
        """
        Scan contracts for best Grade A setup.
        
        Used for compounding decision - finds the highest confidence
        Grade A setup across all assets.
        """
        # Filter to Grade A only
        grade_a = [c for c in contracts if c.grade == ContractGrade.A]
        
        if not grade_a:
            return None
        
        # Sort by confidence descending
        grade_a.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return grade_a[0]
    
    def get_state(self) -> CompoundingState:
        """Get current compounding state."""
        return self.state
    
    def reset_state(self, initial_capital: Optional[float] = None):
        """Reset compounding state."""
        if initial_capital is None:
            initial_capital = self.state.initial_capital
        
        self.state = CompoundingState(
            capital=initial_capital,
            initial_capital=initial_capital,
            preservation_mode=False,
            consecutive_wins=0,
            consecutive_losses=0,
            total_trades=0,
            win_rate=0.0
        )
        self._trade_history = []
        
        logger.info(f"Compounding state reset. Capital: ${initial_capital:.2f}")
    
    def _update_win_rate(self, won: bool):
        """Update running win rate."""
        self._trade_history.append({
            "won": won,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Keep last 100 trades
        if len(self._trade_history) > 100:
            self._trade_history = self._trade_history[-100:]
        
        wins = sum(1 for t in self._trade_history if t["won"])
        self.state.win_rate = wins / len(self._trade_history) if self._trade_history else 0
    
    def get_recommended_risk(self, grade: ContractGrade) -> float:
        """
        Get recommended risk % based on grade and state.
        
        Returns risk percentage of capital to use.
        """
        # Base risk by grade
        base_risk = {
            ContractGrade.A: 5.0,   # 5%
            ContractGrade.B: 3.0,   # 3%
            ContractGrade.C: 2.0,   # 2%
            ContractGrade.D: 1.0,   # 1%
            ContractGrade.F: 0.0    # No trade
        }
        
        risk = base_risk.get(grade, 2.0)
        
        # Reduce risk in preservation mode
        if self.state.preservation_mode:
            risk *= 0.5
        
        # Reduce risk after loss streak
        if self.state.consecutive_losses >= 2:
            risk *= 0.75
        
        # Increase risk on win streak (Kelly-ish)
        if self.state.consecutive_wins >= 3 and not self.state.preservation_mode:
            risk *= 1.2
        
        # Cap at 10%
        return min(10.0, risk)
    
    def get_summary(self) -> dict:
        """Get human-readable summary of compounding state."""
        profit = self.state.capital - self.state.initial_capital
        roi = (profit / self.state.initial_capital) * 100 if self.state.initial_capital > 0 else 0
        
        return {
            "initial_capital": self.state.initial_capital,
            "current_capital": round(self.state.capital, 2),
            "profit": round(profit, 2),
            "roi_pct": round(roi, 2),
            "total_trades": self.state.total_trades,
            "win_rate": round(self.state.win_rate * 100, 1),
            "consecutive_wins": self.state.consecutive_wins,
            "consecutive_losses": self.state.consecutive_losses,
            "preservation_mode": self.state.preservation_mode,
            "mode": "PRESERVATION" if self.state.preservation_mode else "FULL_COMPOUND"
        }


