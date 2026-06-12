"""
Coracle Contract Generator
===========================
Generates complete trading contracts with:
- Dynamic stop-loss (ATR-adjusted with liquidity buffer)
- Multi-target take profit (3 levels with probability decay)
- Position sizing based on risk management rules
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
import logging

from app.config import Settings, GRADE_THRESHOLDS
from app.models import (
    SignalSnapshot, Direction, TradingContract, StopLoss, TakeProfit,
    SacredGateResult, ConfluenceResult, ContractGrade, VolatilityRegime
)

logger = logging.getLogger(__name__)


class ContractGenerator:
    """
    Generates probability-weighted trading contracts.
    
    Key features:
    - Dynamic SL based on volatility regime and ATR
    - SL always beyond nearest liquidation cluster
    - Multi-target TP with probability decay
    - Grade assignment based on confluence score
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.vol_regimes = settings.volatility_regimes
    
    def generate(
        self,
        symbol: str,
        direction: Direction,
        entry_type: Literal["MOMENTUM", "RETRACE", "REVERSAL"],
        signals: SignalSnapshot,
        gate_result: SacredGateResult,
        confluence_result: ConfluenceResult,
        capital: Optional[float] = None
    ) -> TradingContract:
        """
        Generate a complete trading contract.
        """
        entry_price = signals.price
        
        # Calculate stop loss
        stop_loss = self._calculate_stop_loss(
            entry_price=entry_price,
            direction=direction,
            signals=signals,
            confluence=confluence_result
        )
        
        # Calculate take profit levels
        take_profits = self._calculate_take_profits(
            entry_price=entry_price,
            stop_loss=stop_loss,
            direction=direction,
            signals=signals,
            win_probability=confluence_result.final_probability
        )
        
        # Determine grade
        grade = self._calculate_grade(confluence_result.final_probability)
        
        # Build signals snapshot for storage
        signals_snapshot = self._build_signals_snapshot(signals)
        
        # Create contract
        contract = TradingContract(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            entry_type=entry_type,
            stop_loss=stop_loss,
            take_profits=take_profits,
            confidence_score=confluence_result.final_probability,
            grade=grade,
            confluence_multiplier=confluence_result.confluence_multiplier,
            sacred_gate=gate_result,
            signals_snapshot=signals_snapshot,
            generated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        
        logger.info(
            f"Contract generated: {symbol} {direction.value} | "
            f"Grade {grade.value} | Confidence {confluence_result.final_probability:.2%} | "
            f"Entry: {entry_price:.2f} | SL: {stop_loss.price:.2f} | "
            f"TP1: {take_profits[0].price:.2f}"
        )
        
        # Store contract (via router)
        from app.routers.contracts import store_contract
        store_contract(contract)
        
        return contract
    
    def _calculate_stop_loss(
        self,
        entry_price: float,
        direction: Direction,
        signals: SignalSnapshot,
        confluence: ConfluenceResult
    ) -> StopLoss:
        """
        Calculate dynamic stop loss.
        
        Formula:
        1. Start with base SL % from volatility regime
        2. Add ATR adjustment
        3. Add order book slope buffer
        4. Adjust based on whale confidence
        5. Ensure beyond liquidation cluster
        """
        # 1. Get volatility regime
        regime = self._get_volatility_regime(signals)
        base_sl_pct = self.vol_regimes[regime.value]
        
        # 2. ATR adjustment
        atr_value = self._estimate_atr(signals)
        atr_pct = atr_value / entry_price if entry_price > 0 else 0
        
        # 3. Order book slope buffer (0-50% buffer)
        obs_buffer = 1.0
        if signals.obs:
            # Lower slope = easier to push through = need wider SL
            slope = signals.obs.value
            obs_buffer = 1.0 + (1 - slope) * 0.5  # 1.0 to 1.5
        
        # Calculate base SL distance
        sl_distance_pct = base_sl_pct + (atr_pct * obs_buffer)
        
        # 4. Cascade risk adjustment
        if signals.lcp and signals.lcp.value > 2.0:
            sl_distance_pct *= 1.3  # +30% wider for cascade risk
        
        # 5. Whale confidence adjustment
        if signals.wc:
            wc = signals.wc.value
            if wc > 80:
                sl_distance_pct *= 0.9  # 10% tighter
            elif wc < 40:
                sl_distance_pct *= 1.1  # 10% wider
        
        # Calculate SL price
        if direction == Direction.LONG:
            sl_price = entry_price * (1 - sl_distance_pct)
        else:
            sl_price = entry_price * (1 + sl_distance_pct)
        
        # Ensure beyond nearest liquidation cluster (simplified)
        # In production, this would query actual liquidation data
        liq_buffer_pct = 0.005  # 0.5% beyond
        if direction == Direction.LONG:
            sl_price = sl_price * (1 - liq_buffer_pct)
        else:
            sl_price = sl_price * (1 + liq_buffer_pct)
        
        return StopLoss(
            price=round(sl_price, 2),
            distance_pct=round(abs((sl_price - entry_price) / entry_price) * 100, 4),
            protection_logic="ATR-Adjusted + OBS Buffer + Liquidation Buffer",
            volatility_regime=regime,
            atr_value=round(atr_value, 2),
            liquidation_buffer=True
        )
    
    def _calculate_take_profits(
        self,
        entry_price: float,
        stop_loss: StopLoss,
        direction: Direction,
        signals: SignalSnapshot,
        win_probability: float
    ) -> list[TakeProfit]:
        """
        Calculate multi-target take profit levels.
        
        TP1: 30% position at 1:1 R:R
        TP2: 40% position at 1.5:1 R:R
        TP3: 30% position at 2.5:1 R:R
        
        Each level has probability decay applied.
        """
        take_profits = []
        
        # Calculate risk (distance to SL)
        risk_distance = abs(entry_price - stop_loss.price)
        
        # TP configurations
        tp_configs = [
            {"level": 1, "rr": self.settings.tp1_rr, "size": self.settings.tp1_size, "decay": 1.0},
            {"level": 2, "rr": self.settings.tp2_rr, "size": self.settings.tp2_size, "decay": 0.85},
            {"level": 3, "rr": self.settings.tp3_rr, "size": self.settings.tp3_size, "decay": 0.65},
        ]
        
        for tp in tp_configs:
            # Calculate TP price based on R:R
            reward_distance = risk_distance * tp["rr"]
            
            if direction == Direction.LONG:
                tp_price = entry_price + reward_distance
            else:
                tp_price = entry_price - reward_distance
            
            # Apply probability decay
            tp_probability = win_probability * tp["decay"]
            
            take_profits.append(TakeProfit(
                level=tp["level"],
                price=round(tp_price, 2),
                size=tp["size"],
                rr_ratio=tp["rr"],
                probability=round(tp_probability, 4)
            ))
        
        return take_profits
    
    def _get_volatility_regime(self, signals: SignalSnapshot) -> VolatilityRegime:
        """Determine volatility regime from signals."""
        if signals.vrc and signals.vrc.raw_data:
            regime_str = signals.vrc.raw_data.get("regime", "NORMAL")
            try:
                return VolatilityRegime(regime_str)
            except ValueError:
                pass
        
        # Default to NORMAL
        return VolatilityRegime.NORMAL
    
    def _estimate_atr(self, signals: SignalSnapshot) -> float:
        """
        Estimate ATR from available data.
        
        In production, this would use actual candle data.
        For now, estimate from volatility and price.
        """
        price = signals.price
        
        # Use VRC value as volatility proxy
        if signals.vrc:
            vol_pct = signals.vrc.value / 100  # Convert to decimal
            return price * vol_pct * 1.5  # Rough ATR estimate
        
        # Default: 1.5% of price
        return price * 0.015
    
    def _calculate_grade(self, probability: float) -> ContractGrade:
        """Convert probability to contract grade."""
        if probability >= GRADE_THRESHOLDS["A"]:
            return ContractGrade.A
        elif probability >= GRADE_THRESHOLDS["B"]:
            return ContractGrade.B
        elif probability >= GRADE_THRESHOLDS["C"]:
            return ContractGrade.C
        elif probability >= GRADE_THRESHOLDS["D"]:
            return ContractGrade.D
        else:
            return ContractGrade.F
    
    def _build_signals_snapshot(self, signals: SignalSnapshot) -> dict:
        """Build signals snapshot dictionary for storage."""
        snapshot = {
            "symbol": signals.symbol,
            "price": signals.price,
            "timestamp": signals.timestamp.isoformat(),
            "signals": {}
        }
        
        # Add each signal if present
        signal_fields = [
            "bai", "obs", "lcp", "wadi", "wc", "cvd", "oi",
            "fr", "ls_ratio", "spot_premium", "fgi", "vrc"
        ]
        
        for field in signal_fields:
            sig = getattr(signals, field, None)
            if sig:
                snapshot["signals"][field] = {
                    "name": sig.name,
                    "value": sig.value,
                    "signal": sig.signal,
                    "strength": sig.strength,
                    "tier": sig.tier
                }
        
        return snapshot
    
    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        risk_percent: float = 2.0,
        max_leverage: float = 5.0,
        grade: ContractGrade = ContractGrade.C
    ) -> dict:
        """
        Calculate position size based on risk management.
        
        Args:
            capital: Total account capital
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_percent: Max risk per trade (% of capital)
            max_leverage: Maximum allowed leverage
            grade: Contract grade (affects sizing)
        
        Returns:
            Position sizing recommendation
        """
        # Grade-based risk multiplier
        grade_multipliers = {
            ContractGrade.A: 1.0,   # Full risk
            ContractGrade.B: 0.75,  # 75% risk
            ContractGrade.C: 0.5,   # 50% risk
            ContractGrade.D: 0.25,  # 25% risk
            ContractGrade.F: 0.0    # No trade
        }
        
        grade_mult = grade_multipliers.get(grade, 0.5)
        effective_risk_pct = risk_percent * grade_mult
        
        # Calculate risk amount
        risk_amount = capital * (effective_risk_pct / 100)
        
        # Calculate distance to SL
        sl_distance = abs(entry_price - stop_loss_price)
        sl_distance_pct = sl_distance / entry_price
        
        if sl_distance_pct == 0:
            return {"safe_to_trade": False, "reason": "Stop loss too close"}
        
        # Calculate position size
        # Position = Risk Amount / SL Distance %
        position_size = risk_amount / sl_distance_pct
        
        # Calculate implied leverage
        leverage = position_size / capital
        
        # Cap leverage
        if leverage > max_leverage:
            leverage = max_leverage
            position_size = capital * leverage
            risk_amount = position_size * sl_distance_pct
        
        return {
            "position_size_usd": round(position_size, 2),
            "leverage": round(leverage, 2),
            "risk_amount_usd": round(risk_amount, 2),
            "risk_percent": round((risk_amount / capital) * 100, 2),
            "sl_distance_pct": round(sl_distance_pct * 100, 2),
            "grade_multiplier": grade_mult,
            "safe_to_trade": position_size > 0 and grade != ContractGrade.F
        }


