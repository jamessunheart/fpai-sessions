"""
Tests for leverage engine
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.leverage_engine import LeverageEngine, MagnetState, LeverageConfig


def test_leverage_calculation_normal():
    """Test leverage calculation under normal conditions"""
    engine = LeverageEngine()

    state = MagnetState(
        primary_magnet_price=44000.0,
        current_price=43200.0,
        magnet_strength=70.0,
        conflict_index=0.3,
        volatility_pressure=1.0,
        atr=450.0
    )

    result = engine.calculate_leverage(state)

    assert 'leverage' in result
    assert 1.0 <= result['leverage'] <= 3.0
    assert 'components' in result
    assert 'is_high_tension' in result


def test_leverage_high_tension():
    """Test high-tension override"""
    engine = LeverageEngine()

    state = MagnetState(
        primary_magnet_price=45000.0,
        current_price=43200.0,
        magnet_strength=85.0,  # High strength
        conflict_index=0.05,   # Low conflict
        volatility_pressure=0.05,  # Low volatility
        atr=450.0
    )

    result = engine.calculate_leverage(state)

    assert result['is_high_tension'] == True
    assert result['leverage'] >= 2.0  # Should be boosted


def test_leverage_bounds():
    """Test leverage stays within bounds"""
    engine = LeverageEngine()

    # Test minimum bound
    state_min = MagnetState(
        primary_magnet_price=43200.0,  # No distance
        current_price=43200.0,
        magnet_strength=30.0,  # Low strength
        conflict_index=0.8,    # High conflict
        volatility_pressure=2.0,  # High volatility
        atr=450.0
    )

    result_min = engine.calculate_leverage(state_min)
    assert result_min['leverage'] >= 1.0

    # Test maximum bound
    state_max = MagnetState(
        primary_magnet_price=50000.0,  # Large distance
        current_price=43200.0,
        magnet_strength=95.0,  # Very high strength
        conflict_index=0.01,   # Minimal conflict
        volatility_pressure=0.01,  # Minimal volatility
        atr=450.0
    )

    result_max = engine.calculate_leverage(state_max)
    assert result_max['leverage'] <= 3.0


if __name__ == "__main__":
    test_leverage_calculation_normal()
    test_leverage_high_tension()
    test_leverage_bounds()
    print("✅ All leverage tests passed!")
