"""
Tests for Survival Fuse System
Tests the circuit breaker that protects capital
"""

import pytest
from backend.core.survival_fuse import SurvivalFuse, MarketConditions, FuseConfig, FuseState, FuseTrigger


class TestSurvivalFuse:
    
    def setup_method(self):
        """Setup test fixtures"""
        self.fuse = SurvivalFuse()
    
    def test_normal_conditions_no_trigger(self):
        """Test that fuse doesn't trigger under normal conditions"""
        conditions = MarketConditions(
            volatility_pressure=1.0,
            account_drawdown_pct=2.0,
            conflict_index=0.3,
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=True,
            liquidity_score=70.0
        )
        
        result = self.fuse.check_triggers(conditions)
        
        assert result['triggered'] is False
        assert result['current_state'] == 'active'
        assert len(result['triggers']) == 0
    
    def test_volatility_spike_triggers(self):
        """Test fuse triggers on volatility spike"""
        conditions = MarketConditions(
            volatility_pressure=2.5,  # Above threshold (2.0)
            account_drawdown_pct=2.0,
            conflict_index=0.3,
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=True,
            liquidity_score=70.0
        )
        
        result = self.fuse.check_triggers(conditions)
        
        assert result['triggered'] is True
        assert 'volatility_spike' in result['triggers']
        assert self.fuse.state == FuseState.TRIGGERED
    
    def test_drawdown_breach_triggers(self):
        """Test fuse triggers on max drawdown breach"""
        conditions = MarketConditions(
            volatility_pressure=1.0,
            account_drawdown_pct=6.0,  # Above threshold (5.0%)
            conflict_index=0.3,
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=True,
            liquidity_score=70.0
        )
        
        result = self.fuse.check_triggers(conditions)
        
        assert result['triggered'] is True
        assert 'drawdown_breach' in result['triggers']
    
    def test_magnet_conflict_triggers(self):
        """Test fuse triggers on magnet conflict"""
        conditions = MarketConditions(
            volatility_pressure=1.0,
            account_drawdown_pct=2.0,
            conflict_index=0.9,  # Above threshold (0.8)
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=True,
            liquidity_score=70.0
        )
        
        result = self.fuse.check_triggers(conditions)
        
        assert result['triggered'] is True
        assert 'magnet_conflict' in result['triggers']
    
    def test_secondary_magnet_stronger_triggers(self):
        """Test fuse triggers when secondary magnet is stronger"""
        conditions = MarketConditions(
            volatility_pressure=1.0,
            account_drawdown_pct=2.0,
            conflict_index=0.3,
            primary_magnet_strength=60.0,
            secondary_magnet_strength=80.0,  # Stronger than primary
            trend_aligned=True,
            liquidity_score=70.0
        )
        
        result = self.fuse.check_triggers(conditions)
        
        assert result['triggered'] is True
        assert 'magnet_conflict' in result['triggers']
    
    def test_trend_flip_triggers(self):
        """Test fuse triggers on trend flip"""
        conditions = MarketConditions(
            volatility_pressure=1.0,
            account_drawdown_pct=2.0,
            conflict_index=0.3,
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=False,  # Trend flipped
            liquidity_score=70.0
        )
        
        result = self.fuse.check_triggers(conditions)
        
        assert result['triggered'] is True
        assert 'trend_flip' in result['triggers']
    
    def test_liquidity_dry_triggers(self):
        """Test fuse triggers on low liquidity"""
        conditions = MarketConditions(
            volatility_pressure=1.0,
            account_drawdown_pct=2.0,
            conflict_index=0.3,
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=True,
            liquidity_score=20.0  # Below threshold (30)
        )
        
        result = self.fuse.check_triggers(conditions)
        
        assert result['triggered'] is True
        assert 'liquidity_dry' in result['triggers']
    
    def test_multiple_triggers(self):
        """Test that multiple conditions can trigger simultaneously"""
        conditions = MarketConditions(
            volatility_pressure=2.5,  # Trigger 1
            account_drawdown_pct=6.0,  # Trigger 2
            conflict_index=0.9,  # Trigger 3
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=False,  # Trigger 4
            liquidity_score=20.0  # Trigger 5
        )
        
        result = self.fuse.check_triggers(conditions)
        
        assert result['triggered'] is True
        assert len(result['triggers']) >= 3
    
    def test_actions_returned_on_trigger(self):
        """Test that actions are returned when triggered"""
        conditions = MarketConditions(
            volatility_pressure=2.5,
            account_drawdown_pct=2.0,
            conflict_index=0.3,
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=True,
            liquidity_score=70.0
        )
        
        result = self.fuse.check_triggers(conditions)
        
        assert result['triggered'] is True
        assert len(result['actions']) > 0
        assert any('Reduce position' in action for action in result['actions'])
        assert any('leverage to 1.0x' in action for action in result['actions'])
    
    def test_manual_reset(self):
        """Test manual reset functionality"""
        # Trigger the fuse
        conditions = MarketConditions(
            volatility_pressure=2.5,
            account_drawdown_pct=2.0,
            conflict_index=0.3,
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=True,
            liquidity_score=70.0
        )
        
        self.fuse.check_triggers(conditions)
        assert self.fuse.state == FuseState.TRIGGERED
        
        # Manual reset
        self.fuse.manual_reset()
        assert self.fuse.state == FuseState.ACTIVE
        assert self.fuse.triggered_at is None
    
    def test_custom_config(self):
        """Test fuse with custom configuration"""
        custom_config = FuseConfig(
            max_volatility=1.5,
            max_drawdown_pct=3.0,
            max_conflict_index=0.5
        )
        fuse = SurvivalFuse(custom_config)
        
        conditions = MarketConditions(
            volatility_pressure=1.6,  # Above custom threshold (1.5)
            account_drawdown_pct=2.0,
            conflict_index=0.3,
            primary_magnet_strength=80.0,
            secondary_magnet_strength=40.0,
            trend_aligned=True,
            liquidity_score=70.0
        )
        
        result = fuse.check_triggers(conditions)
        assert result['triggered'] is True
