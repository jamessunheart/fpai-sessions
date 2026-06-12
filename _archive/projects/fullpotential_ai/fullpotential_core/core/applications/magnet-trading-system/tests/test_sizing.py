"""
Tests for position sizing
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.position_sizing import PositionSizer, AccountState, TradeSetup, SizingConfig


def test_tier_limits():
    """Test position sizing respects tier limits"""
    sizer = PositionSizer()

    account = AccountState(
        equity=100000.0,
        available_margin=90000.0,
        open_positions_value=0
    )

    # Tier 1: 15% max
    trade_tier1 = TradeSetup(
        entry_price=43200.0,
        stop_price=42800.0,
        magnet_price=44000.0,
        magnet_tier=1,
        leverage=2.0
    )

    result_tier1 = sizer.calculate_position_size(account, trade_tier1)
    assert result_tier1['position_pct'] <= 15.0

    # Tier 2: 10% max
    trade_tier2 = TradeSetup(
        entry_price=43200.0,
        stop_price=42800.0,
        magnet_price=44000.0,
        magnet_tier=2,
        leverage=2.0
    )

    result_tier2 = sizer.calculate_position_size(account, trade_tier2)
    assert result_tier2['position_pct'] <= 10.0

    # Tier 3: 5% max
    trade_tier3 = TradeSetup(
        entry_price=43200.0,
        stop_price=42800.0,
        magnet_price=44000.0,
        magnet_tier=3,
        leverage=2.0
    )

    result_tier3 = sizer.calculate_position_size(account, trade_tier3)
    assert result_tier3['position_pct'] <= 5.0


def test_exposure_limit():
    """Test total exposure limit"""
    sizer = PositionSizer()

    account = AccountState(
        equity=100000.0,
        available_margin=90000.0,
        open_positions_value=45000.0  # Already at 45%
    )

    trade = TradeSetup(
        entry_price=43200.0,
        stop_price=42800.0,
        magnet_price=44000.0,
        magnet_tier=1,
        leverage=2.0
    )

    result = sizer.calculate_position_size(account, trade)

    # Should be limited to prevent exceeding 50% total exposure
    total_exposure_pct = (account.open_positions_value + result['position_size']) / account.equity * 100
    assert total_exposure_pct <= 50.0


def test_risk_calculation():
    """Test risk and reward calculations"""
    sizer = PositionSizer()

    account = AccountState(
        equity=100000.0,
        available_margin=90000.0,
        open_positions_value=0
    )

    trade = TradeSetup(
        entry_price=43200.0,
        stop_price=42800.0,  # 0.93% stop
        magnet_price=44000.0,  # 1.85% target
        magnet_tier=1,
        leverage=2.0
    )

    result = sizer.calculate_position_size(account, trade)

    assert 'actual_risk' in result
    assert 'potential_reward' in result
    assert 'risk_reward_ratio' in result
    assert result['risk_reward_ratio'] > 1.0  # Target > Stop


if __name__ == "__main__":
    test_tier_limits()
    test_exposure_limit()
    test_risk_calculation()
    print("✅ All position sizing tests passed!")
