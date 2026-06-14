"""Test suite for simulation engine"""
import pytest
import asyncio
from datetime import datetime, timedelta
from src.simulation_engine import SimulationEngine, quick_backtest
from src.data_sources import CoinGeckoAPI, DeFiLlamaAPI, SimulationDataCache


@pytest.mark.asyncio
async def test_data_fetching():
    """Test market data fetching"""
    async with CoinGeckoAPI() as gecko:
        end = datetime.now()
        start = end - timedelta(days=7)
        
        data = await gecko.fetch_historical_prices('BTC', start, end)
        assert len(data) > 0
        assert all(d.asset == 'BTC' for d in data)


@pytest.mark.asyncio
async def test_quick_backtest():
    """Test 30-day backtest integration"""
    results = await quick_backtest(days=30, agents=5)
    
    assert results is not None
    assert results.final_agents > 0
    assert results.total_return is not None


def test_data_cache():
    """Test SQLite caching"""
    cache = SimulationDataCache("test_simulation.db")
    
    # Test cache functionality
    data_points = cache.get_market_data('BTC', '2024-01-01', '2024-01-07')
    assert isinstance(data_points, list)


@pytest.mark.asyncio
async def test_time_progression():
    """Test simulation time progression"""
    engine = SimulationEngine(time_multiplier=10.0)
    
    start = datetime.now() - timedelta(days=10)
    end = datetime.now()
    
    results = await engine.backtest(start, end, initial_agents=3)
    
    assert results.snapshots is not None
    assert len(results.snapshots) > 0
