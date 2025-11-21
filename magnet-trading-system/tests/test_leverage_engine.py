"""
Tests for Leverage Engine
Tests the magnet-aware leverage formula: L = (D × S) / (1 + C + V)
"""

import pytest
from backend.core.leverage_engine import LeverageEngine, MagnetState, LeverageConfig


class TestLeverageEngine:
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = LeverageEngine()
    
    def test_perfect_setup_high_tension(self):
        """Test high-tension scenario: far from magnet, strong, low friction"""
        state = MagnetState(
            primary_magnet_price=44000.0,
            current_price=43000.0,
            magnet_strength=85.0,
            conflict_index=0.1,
            volatility_pressure=0.2,
            atr=250.0
        )
        
        result = self.engine.calculate_leverage(state)
        
        # Should trigger high-tension override
        assert result['is_high_tension'] is True
        assert result['leverage'] >= 2.5
        assert result['leverage'] <= 3.0
        assert 'PERFECT SETUP' in result['reasoning']
    
    def test_low_leverage_high_conflict(self):
        """Test scenario with high conflict (competing magnets)"""
        state = MagnetState(
            primary_magnet_price=44000.0,
            current_price=43800.0,
            magnet_strength=60.0,
            conflict_index=0.8,  # High conflict
            volatility_pressure=0.3,
            atr=250.0
        )
        
        result = self.engine.calculate_leverage(state)
        
        # High conflict should reduce leverage
        assert result['leverage'] < 2.0
        assert 'High conflict' in result['reasoning']
    
    def test_low_leverage_high_volatility(self):
        """Test scenario with high volatility (market stress)"""
        state = MagnetState(
            primary_magnet_price=44000.0,
            current_price=43500.0,
            magnet_strength=70.0,
            conflict_index=0.2,
            volatility_pressure=1.8,  # High volatility
            atr=250.0
        )
        
        result = self.engine.calculate_leverage(state)
        
        # High volatility should reduce leverage
        assert result['leverage'] < 2.0
        assert 'High volatility' in result['reasoning']
    
    def test_close_to_magnet_low_distance(self):
        """Test scenario close to magnet (low distance)"""
        state = MagnetState(
            primary_magnet_price=43100.0,
            current_price=43080.0,  # Very close
            magnet_strength=80.0,
            conflict_index=0.2,
            volatility_pressure=0.4,
            atr=250.0
        )
        
        result = self.engine.calculate_leverage(state)
        
        # Low distance means low tension, should reduce leverage
        assert result['components']['distance'] < 0.5
        assert result['leverage'] < 1.5
    
    def test_weak_magnet_low_strength(self):
        """Test scenario with weak magnet"""
        state = MagnetState(
            primary_magnet_price=44000.0,
            current_price=43000.0,
            magnet_strength=40.0,  # Weak magnet
            conflict_index=0.2,
            volatility_pressure=0.3,
            atr=250.0
        )
        
        result = self.engine.calculate_leverage(state)
        
        # Weak magnet should reduce leverage
        assert result['components']['strength'] < 0.5
        assert result['leverage'] < 2.0
    
    def test_leverage_bounds(self):
        """Test that leverage stays within configured bounds"""
        config = LeverageConfig(min_leverage=1.0, max_leverage=2.5)
        engine = LeverageEngine(config)
        
        # Test extreme high case
        state_high = MagnetState(
            primary_magnet_price=50000.0,
            current_price=43000.0,
            magnet_strength=100.0,
            conflict_index=0.0,
            volatility_pressure=0.0,
            atr=250.0
        )
        
        result_high = engine.calculate_leverage(state_high)
        assert result_high['leverage'] >= 1.0
        assert result_high['leverage'] <= 3.0  # High-tension max
        
        # Test extreme low case
        state_low = MagnetState(
            primary_magnet_price=43000.0,
            current_price=43000.0,
            magnet_strength=0.0,
            conflict_index=10.0,
            volatility_pressure=10.0,
            atr=250.0
        )
        
        result_low = engine.calculate_leverage(state_low)
        assert result_low['leverage'] >= 1.0
    
    def test_distance_calculation(self):
        """Test distance normalization by ATR"""
        state = MagnetState(
            primary_magnet_price=44000.0,
            current_price=43000.0,
            magnet_strength=70.0,
            conflict_index=0.2,
            volatility_pressure=0.3,
            atr=250.0
        )
        
        distance = self.engine.calculate_distance(state)
        
        # Distance should be |44000 - 43000| / 250 = 4.0
        assert distance == pytest.approx(4.0, rel=0.01)
    
    def test_components_returned(self):
        """Test that all components are returned correctly"""
        state = MagnetState(
            primary_magnet_price=44000.0,
            current_price=43000.0,
            magnet_strength=80.0,
            conflict_index=0.3,
            volatility_pressure=0.5,
            atr=250.0
        )
        
        result = self.engine.calculate_leverage(state)
        
        assert 'leverage' in result
        assert 'components' in result
        assert 'distance' in result['components']
        assert 'strength' in result['components']
        assert 'conflict' in result['components']
        assert 'volatility' in result['components']
        assert 'raw_leverage' in result
        assert 'is_high_tension' in result
        assert 'reasoning' in result
