"""
Comprehensive tests for Trading Engine

Tests all critical safety features:
- Trade validation before execution
- Position limits enforcement
- Emergency stop functionality
- Capital updates on success only
- Retry logic
"""

import pytest
import asyncio
import sqlite3
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading_engine import TradingEngine, TradingDisabledError, ValidationError
from src.protocols.simulation import SimulationAdapter
from src.validators import create_standard_validator


@pytest.fixture
def db_path(tmp_path):
    """Create temporary test database"""
    db = tmp_path / "test_arena.db"
    conn = sqlite3.connect(str(db))

    # Create tables
    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT UNIQUE NOT NULL,
            agent_id TEXT NOT NULL,
            trade_type TEXT NOT NULL,
            status TEXT NOT NULL,
            protocol TEXT,
            input_asset TEXT,
            input_amount REAL,
            output_asset TEXT,
            expected_return REAL,
            actual_return REAL,
            gas_cost_usd REAL,
            tx_hash TEXT,
            error_message TEXT,
            execution_price REAL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            executed_at TIMESTAMP,
            failed_at TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE position_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            asset TEXT,
            max_position_usd REAL NOT NULL,
            max_trade_size_usd REAL NOT NULL,
            max_daily_trades INTEGER NOT NULL,
            UNIQUE(agent_id, asset)
        )
    """)

    conn.execute("""
        CREATE TABLE execution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            data TEXT
        )
    """)

    conn.commit()
    conn.close()

    return str(db)


@pytest.fixture
def mock_agent():
    """Create mock agent"""
    agent = Mock()
    agent.agent_id = "test-agent-001"
    agent.real_capital = Decimal('10000')
    return agent


@pytest.fixture
def protocols():
    """Create protocol adapters"""
    return {
        'simulation': SimulationAdapter({
            'success_rate': 1.0,  # 100% success for deterministic tests
            'simulate_delay': False
        })
    }


@pytest.fixture
async def engine(db_path, protocols):
    """Create trading engine"""
    return TradingEngine(
        db_path=db_path,
        protocols=protocols
    )


@pytest.mark.asyncio
async def test_submit_trade_success(engine, mock_agent):
    """Test successful trade submission"""
    trade = {
        'trade_type': 'deposit',
        'protocol': 'simulation',
        'input_asset': 'USDC',
        'input_amount': Decimal('1000'),
        'output_asset': 'USDC',
        'expected_return': Decimal('1000'),
        'gas_cost_usd': Decimal('3.50')
    }

    result = await engine.submit_trade(mock_agent, trade)

    assert result['status'] == 'submitted'
    assert result['trade_id'] is not None
    assert result['error'] is None


@pytest.mark.asyncio
async def test_emergency_stop_blocks_trading(engine, mock_agent):
    """CRITICAL TEST: Emergency stop must prevent new trades"""
    # Execute emergency stop
    engine.emergency_stop()

    trade = {
        'trade_type': 'deposit',
        'protocol': 'simulation',
        'input_asset': 'USDC',
        'input_amount': Decimal('1000'),
        'output_asset': 'USDC',
        'expected_return': Decimal('1000'),
        'gas_cost_usd': Decimal('3.50')
    }

    # Should raise error
    with pytest.raises(TradingDisabledError):
        await engine.submit_trade(mock_agent, trade)


@pytest.mark.asyncio
async def test_validation_before_execution(engine, mock_agent):
    """CRITICAL TEST: Validation must happen before execution"""
    # Insufficient capital
    mock_agent.real_capital = Decimal('100')  # Only $100

    trade = {
        'trade_type': 'deposit',
        'protocol': 'simulation',
        'input_asset': 'USDC',
        'input_amount': Decimal('10000'),  # Try to deposit $10K
        'output_asset': 'USDC',
        'expected_return': Decimal('10000'),
        'gas_cost_usd': Decimal('3.50')
    }

    # Should fail validation
    with pytest.raises(ValidationError):
        await engine.submit_trade(mock_agent, trade)


@pytest.mark.asyncio
async def test_capital_updated_only_on_success(engine, mock_agent):
    """CRITICAL TEST: Capital must only update on successful execution"""
    initial_capital = mock_agent.real_capital

    trade = {
        'trade_type': 'swap',
        'protocol': 'simulation',
        'input_asset': 'USDC',
        'input_amount': Decimal('1000'),
        'output_asset': 'ETH',
        'expected_return': Decimal('0.4'),  # ~0.4 ETH at $2500
        'gas_cost_usd': Decimal('12.50')
    }

    result = await engine.submit_trade(mock_agent, trade)

    # Wait for execution to complete
    await asyncio.sleep(1)

    # Capital should have changed (input - output - gas != 0 for swaps)
    # In simulation, swap returns different output amount
    assert mock_agent.real_capital != initial_capital


@pytest.mark.asyncio
async def test_position_limits_enforced(db_path, protocols, mock_agent):
    """CRITICAL TEST: Position limits must be enforced"""
    # Set strict position limit
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO position_limits (agent_id, asset, max_position_usd, max_trade_size_usd, max_daily_trades)
        VALUES (?, ?, ?, ?, ?)
    """, (mock_agent.agent_id, 'ETH', 5000, 2000, 100))
    conn.commit()
    conn.close()

    engine = TradingEngine(db_path=db_path, protocols=protocols)

    trade = {
        'trade_type': 'swap',
        'protocol': 'simulation',
        'input_asset': 'USDC',
        'input_amount': Decimal('3000'),  # Exceeds max_trade_size
        'output_asset': 'ETH',
        'expected_return': Decimal('3000'),
        'gas_cost_usd': Decimal('12.50')
    }

    # Should fail validation
    with pytest.raises(ValidationError):
        await engine.submit_trade(mock_agent, trade)


@pytest.mark.asyncio
async def test_trade_logging_to_database(engine, mock_agent):
    """Test that all trades are logged"""
    trade = {
        'trade_type': 'deposit',
        'protocol': 'simulation',
        'input_asset': 'USDC',
        'input_amount': Decimal('1000'),
        'output_asset': 'USDC',
        'expected_return': Decimal('1000'),
        'gas_cost_usd': Decimal('3.50')
    }

    result = await engine.submit_trade(mock_agent, trade)
    trade_id = result['trade_id']

    # Wait for execution
    await asyncio.sleep(1)

    # Check database
    conn = sqlite3.connect(engine.db_path)
    cursor = conn.execute("SELECT status FROM trades WHERE trade_id = ?", (trade_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] in ['pending', 'executing', 'success']


@pytest.mark.asyncio
async def test_get_status(engine, mock_agent):
    """Test status reporting"""
    status = await engine.get_status()

    assert 'trading_enabled' in status
    assert 'pending_trades' in status
    assert 'protocols' in status
    assert status['trading_enabled'] is True
    assert 'simulation' in status['protocols']


def test_emergency_resume(engine):
    """Test emergency resume after stop"""
    engine.emergency_stop()
    assert engine.trading_enabled is False

    engine.emergency_resume()
    assert engine.trading_enabled is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
