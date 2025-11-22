"""
Tests for survival fuse
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.survival_fuse import SurvivalFuse, MarketConditions, FuseConfig


def test_fuse_normal_conditions():
    """Test fuse doesn't trigger under normal conditions"""
    fuse = SurvivalFuse()

    conditions = MarketConditions(
        volatility_pressure=1.0,
        account_drawdown_pct=2.0,  # Below threshold
        conflict_index=0.4,
        primary_magnet_strength=70.0,
        secondary_magnet_strength=40.0,
        trend_aligned=True,
        liquidity_score=70.0
    )

    result = fuse.check_triggers(conditions)

    assert result['triggered'] == False
    assert len(result['triggers']) == 0


def test_fuse_drawdown_breach():
    """Test fuse triggers on drawdown breach"""
    fuse = SurvivalFuse()

    conditions = MarketConditions(
        volatility_pressure=1.0,
        account_drawdown_pct=6.0,  # Above 5% threshold
        conflict_index=0.4,
        primary_magnet_strength=70.0,
        secondary_magnet_strength=40.0,
        trend_aligned=True,
        liquidity_score=70.0
    )

    result = fuse.check_triggers(conditions)

    assert result['triggered'] == True
    assert 'drawdown_breach' in result['triggers']
    assert len(result['actions']) > 0


def test_fuse_volatility_spike():
    """Test fuse triggers on volatility spike"""
    fuse = SurvivalFuse()

    conditions = MarketConditions(
        volatility_pressure=2.5,  # Above 2.0 threshold
        account_drawdown_pct=1.0,
        conflict_index=0.4,
        primary_magnet_strength=70.0,
        secondary_magnet_strength=40.0,
        trend_aligned=True,
        liquidity_score=70.0
    )

    result = fuse.check_triggers(conditions)

    assert result['triggered'] == True
    assert 'volatility_spike' in result['triggers']


def test_fuse_manual_reset():
    """Test manual fuse reset"""
    fuse = SurvivalFuse()

    # Trigger fuse
    conditions = MarketConditions(
        volatility_pressure=3.0,
        account_drawdown_pct=1.0,
        conflict_index=0.4,
        primary_magnet_strength=70.0,
        secondary_magnet_strength=40.0,
        trend_aligned=True,
        liquidity_score=70.0
    )

    fuse.check_triggers(conditions)
    assert fuse.state.value == 'triggered'

    # Manual reset
    fuse.manual_reset()
    assert fuse.state.value == 'active'


if __name__ == "__main__":
    test_fuse_normal_conditions()
    test_fuse_drawdown_breach()
    test_fuse_volatility_spike()
    test_fuse_manual_reset()
    print("✅ All fuse tests passed!")
