"""
Coracle Sacred Three-Key Gate
==============================
Mandatory validation before contract generation.

All three conditions must be satisfied:
1. Whale Key: WADI alignment with direction
2. Liquidity Key: No cascade risk (LCP < threshold)
3. Gamma Key: Volatility expansion regime (GEX < 0)

If any key fails, no contract is generated.
"""
from typing import Tuple, Optional
import logging

from app.config import Settings
from app.models import (
    SignalSnapshot, Direction, SacredGateResult, GateKeyStatus
)

logger = logging.getLogger(__name__)


class SacredGate:
    """
    Sacred Three-Key Gate validator.
    
    This is the MANDATORY filter before any contract generation.
    All three keys must pass for a trade to be considered valid.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.whale_threshold = settings.whale_threshold  # 0.4
        self.liquidity_threshold = settings.liquidity_threshold  # 2.5
    
    def validate(
        self, 
        signals: SignalSnapshot, 
        direction: Direction
    ) -> SacredGateResult:
        """
        Validate all three sacred keys.
        
        Args:
            signals: Complete signal snapshot
            direction: Intended trade direction (LONG/SHORT)
        
        Returns:
            SacredGateResult with pass/fail status for each key
        """
        whale_key = self._check_whale_key(signals, direction)
        liquidity_key = self._check_liquidity_key(signals)
        gamma_key = self._check_gamma_key(signals)
        
        all_passed = whale_key.passed and liquidity_key.passed and gamma_key.passed
        
        if all_passed:
            logger.info(f"Sacred Gate PASSED for {signals.symbol} {direction.value}")
        else:
            failed_keys = []
            if not whale_key.passed:
                failed_keys.append("whale")
            if not liquidity_key.passed:
                failed_keys.append("liquidity")
            if not gamma_key.passed:
                failed_keys.append("gamma")
            logger.info(
                f"Sacred Gate FAILED for {signals.symbol} {direction.value}: "
                f"failed keys = {failed_keys}"
            )
        
        return SacredGateResult(
            passed=all_passed,
            whale_key=whale_key,
            liquidity_key=liquidity_key,
            gamma_key=gamma_key
        )
    
    def _check_whale_key(
        self, 
        signals: SignalSnapshot, 
        direction: Direction
    ) -> GateKeyStatus:
        """
        Check Whale Key: WADI must align with trade direction.
        
        For LONG: WADI > 0.4 (whales accumulating)
        For SHORT: WADI < -0.4 (whales distributing)
        """
        wadi_value = 0.0
        if signals.wadi:
            wadi_value = signals.wadi.value
        
        if direction == Direction.LONG:
            passed = wadi_value > self.whale_threshold
            threshold = self.whale_threshold
            description = (
                f"LONG requires whale accumulation (WADI > {threshold}). "
                f"Current WADI: {wadi_value:.4f}"
            )
        elif direction == Direction.SHORT:
            passed = wadi_value < -self.whale_threshold
            threshold = -self.whale_threshold
            description = (
                f"SHORT requires whale distribution (WADI < {threshold}). "
                f"Current WADI: {wadi_value:.4f}"
            )
        else:
            # Neutral direction - whale key passes by default
            passed = True
            threshold = 0
            description = "Neutral direction - whale key bypassed"
        
        return GateKeyStatus(
            name="whale",
            passed=passed,
            value=wadi_value,
            threshold=threshold,
            description=description
        )
    
    def _check_liquidity_key(self, signals: SignalSnapshot) -> GateKeyStatus:
        """
        Check Liquidity Key: LCP must be below cascade threshold.
        
        LCP < 2.5 indicates no significant cascade risk.
        High LCP means liquidations could cascade and move price against us.
        """
        lcp_value = 0.0
        if signals.lcp:
            lcp_value = signals.lcp.value
        
        passed = lcp_value < self.liquidity_threshold
        
        return GateKeyStatus(
            name="liquidity",
            passed=passed,
            value=lcp_value,
            threshold=self.liquidity_threshold,
            description=(
                f"Cascade risk must be low (LCP < {self.liquidity_threshold}). "
                f"Current LCP: {lcp_value:.4f}. "
                f"{'SAFE - No cascade risk' if passed else 'DANGER - High cascade risk'}"
            )
        )
    
    def _check_gamma_key(self, signals: SignalSnapshot) -> GateKeyStatus:
        """
        Check Gamma Key: GEX should indicate volatility expansion.
        
        GEX < 0 indicates negative gamma exposure (volatility expansion regime)
        GEX > 0 indicates positive gamma exposure (volatility compression)
        
        We want negative gamma for trending moves.
        
        NOTE: If GEX is not available, we default to PASS since this
        requires external options data (Deribit/Laevitas).
        """
        if signals.gex is None:
            # GEX not available - pass by default with note
            return GateKeyStatus(
                name="gamma",
                passed=True,
                value=0.0,
                threshold=0.0,
                description=(
                    "GEX data not available (requires Deribit/Laevitas integration). "
                    "Defaulting to PASS. Consider adding options data source."
                )
            )
        
        gex_value = signals.gex.value
        passed = gex_value < 0
        
        return GateKeyStatus(
            name="gamma",
            passed=passed,
            value=gex_value,
            threshold=0.0,
            description=(
                f"Volatility expansion regime required (GEX < 0). "
                f"Current GEX: {gex_value:.4f}. "
                f"{'Volatility expanding' if passed else 'Volatility compressing - avoid trending trades'}"
            )
        )
    
    def quick_check(
        self, 
        wadi: float, 
        lcp: float, 
        direction: Direction,
        gex: Optional[float] = None
    ) -> Tuple[bool, dict]:
        """
        Quick gate check without full signal snapshot.
        
        Useful for rapid screening across multiple assets.
        
        Returns:
            (passed, status_dict)
        """
        # Whale key
        if direction == Direction.LONG:
            whale_passed = wadi > self.whale_threshold
        elif direction == Direction.SHORT:
            whale_passed = wadi < -self.whale_threshold
        else:
            whale_passed = True
        
        # Liquidity key
        liquidity_passed = lcp < self.liquidity_threshold
        
        # Gamma key (default pass if not available)
        gamma_passed = gex < 0 if gex is not None else True
        
        all_passed = whale_passed and liquidity_passed and gamma_passed
        
        return all_passed, {
            "whale": {"passed": whale_passed, "value": wadi},
            "liquidity": {"passed": liquidity_passed, "value": lcp},
            "gamma": {"passed": gamma_passed, "value": gex}
        }
    
    def get_gate_summary(self, result: SacredGateResult) -> str:
        """Get human-readable summary of gate result."""
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        
        keys = [
            f"Whale: {'✓' if result.whale_key.passed else '✗'}",
            f"Liquidity: {'✓' if result.liquidity_key.passed else '✗'}",
            f"Gamma: {'✓' if result.gamma_key.passed else '✗'}"
        ]
        
        return f"Sacred Gate {status} ({result.keys_passed}/3): {', '.join(keys)}"


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def validate_sacred_gate(signals: dict, direction: str) -> 'GateStatus':
    """
    Convenience function to validate the Sacred Gate without instantiating the class.
    
    Args:
        signals: Dictionary of processed signals (from SignalProcessor)
        direction: "LONG" or "SHORT"
    
    Returns:
        GateStatus with pass/fail status
    """
    from app.models import GateStatus, GateKeyStatus
    from app.config import get_settings
    
    settings = get_settings()
    whale_threshold = settings.whale_threshold
    liquidity_threshold = settings.liquidity_threshold
    
    # Extract signal values
    wadi = signals.get("wadi", {})
    wadi_value = wadi.get("value", 0.0) if isinstance(wadi, dict) else 0.0
    
    lcp = signals.get("lcp", {})
    lcp_value = lcp.get("value", 0.0) if isinstance(lcp, dict) else 0.0
    
    gex = signals.get("gex")
    gex_value = gex.get("value", 0.0) if isinstance(gex, dict) and gex else None
    
    # Check Whale Key
    if direction == "LONG":
        whale_passed = wadi_value > whale_threshold
        whale_desc = f"LONG requires whale accumulation (WADI > {whale_threshold}). Current WADI: {wadi_value:.4f}"
    else:  # SHORT
        whale_passed = wadi_value < -whale_threshold
        whale_desc = f"SHORT requires whale distribution (WADI < -{whale_threshold}). Current WADI: {wadi_value:.4f}"
    
    whale_key = GateKeyStatus(
        name="whale",
        passed=whale_passed,
        value=wadi_value,
        threshold=whale_threshold,
        description=whale_desc
    )
    
    # Check Liquidity Key
    liquidity_passed = lcp_value < liquidity_threshold
    liquidity_key = GateKeyStatus(
        name="liquidity",
        passed=liquidity_passed,
        value=lcp_value,
        threshold=liquidity_threshold,
        description=f"Cascade risk must be low (LCP < {liquidity_threshold}). Current LCP: {lcp_value:.4f}. {'SAFE - No cascade risk' if liquidity_passed else 'DANGER - High cascade risk'}"
    )
    
    # Check Gamma Key (defaults to pass if not available)
    if gex_value is None:
        gamma_passed = True
        gamma_desc = "GEX data not available (requires Deribit/Laevitas integration). Defaulting to PASS. Consider adding options data source."
        gex_value = 0.0
    else:
        gamma_passed = gex_value < 0
        gamma_desc = f"Volatility expansion regime required (GEX < 0). Current GEX: {gex_value:.4f}."
    
    gamma_key = GateKeyStatus(
        name="gamma",
        passed=gamma_passed,
        value=gex_value,
        threshold=0.0,
        description=gamma_desc
    )
    
    # Count passed keys
    keys_passed = sum([whale_passed, liquidity_passed, gamma_passed])
    all_passed = keys_passed == 3
    
    return GateStatus(
        passed=all_passed,
        whale_key=whale_key,
        liquidity_key=liquidity_key,
        gamma_key=gamma_key,
        keys_passed=keys_passed
    )
