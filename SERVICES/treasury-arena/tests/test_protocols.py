"""
Tests for Protocol Adapters

Tests simulation, Aave, and Uniswap adapters with mocked external calls.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.protocols.simulation import SimulationAdapter
from src.protocols.aave import AaveAdapter
from src.protocols.uniswap import UniswapAdapter


# Simulation Adapter Tests

@pytest.mark.asyncio
async def test_simulation_deposit():
    """Test simulation deposit"""
    adapter = SimulationAdapter({
        'success_rate': 1.0,
        'simulate_delay': False
    })

    result = await adapter.deposit('USDC', Decimal('1000'))

    assert result['success'] is True
    assert result['amount_deposited'] == Decimal('1000')
    assert result['receipt_token'] == 'aUSDC'
    assert result['gas_cost_usd'] > 0


@pytest.mark.asyncio
async def test_simulation_withdraw():
    """Test simulation withdrawal"""
    adapter = SimulationAdapter({
        'success_rate': 1.0,
        'simulate_delay': False
    })

    result = await adapter.withdraw('USDC', Decimal('500'))

    assert result['success'] is True
    assert result['amount_withdrawn'] == Decimal('500')


@pytest.mark.asyncio
async def test_simulation_swap():
    """Test simulation swap"""
    adapter = SimulationAdapter({
        'success_rate': 1.0,
        'simulate_delay': False
    })

    result = await adapter.swap('USDC', 'ETH', Decimal('2500'))

    assert result['success'] is True
    assert result['input_amount'] == Decimal('2500')
    assert result['output_amount'] > 0
    assert result['slippage'] >= 0


@pytest.mark.asyncio
async def test_simulation_swap_min_output():
    """Test simulation swap with minimum output requirement"""
    adapter = SimulationAdapter({
        'success_rate': 1.0,
        'simulate_delay': False
    })

    # Set unreasonably high minimum output
    result = await adapter.swap(
        'USDC',
        'ETH',
        Decimal('1000'),
        min_output_amount=Decimal('10000')  # Impossible to achieve
    )

    assert result['success'] is False
    assert 'below minimum' in result['error']


@pytest.mark.asyncio
async def test_simulation_get_apy():
    """Test APY retrieval"""
    adapter = SimulationAdapter({'mock_apys': {'USDC': Decimal('0.08')}})

    apy = await adapter.get_apy('USDC')

    assert apy == Decimal('0.08')


@pytest.mark.asyncio
async def test_simulation_random_failure():
    """Test simulated failures"""
    adapter = SimulationAdapter({
        'success_rate': 0.0,  # 0% success = always fail
        'simulate_delay': False
    })

    result = await adapter.deposit('USDC', Decimal('1000'))

    # Should fail due to 0% success rate
    assert result['success'] is False
    assert result['error'] is not None


# Aave Adapter Tests (Mocked)

@pytest.mark.asyncio
async def test_aave_deposit_without_private_key():
    """Test Aave adapter fails gracefully without private key"""
    with patch('os.getenv', return_value=None):
        adapter = AaveAdapter({
            'pool_address': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'
        })

        result = await adapter.deposit('USDC', Decimal('1000'))

        assert result['success'] is False
        assert 'read-only mode' in result['error']


@pytest.mark.asyncio
async def test_aave_withdraw_without_private_key():
    """Test Aave withdrawal without private key"""
    with patch('os.getenv', return_value=None):
        adapter = AaveAdapter({
            'pool_address': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'
        })

        result = await adapter.withdraw('USDC', Decimal('500'))

        assert result['success'] is False
        assert 'read-only mode' in result['error']


@pytest.mark.asyncio
async def test_aave_swap_not_supported():
    """Test that Aave doesn't support swaps"""
    with patch('os.getenv', return_value=None):
        adapter = AaveAdapter({})

        result = await adapter.swap('USDC', 'ETH', Decimal('1000'))

        assert result['success'] is False
        assert 'does not support swaps' in result['error']


@pytest.mark.asyncio
async def test_aave_get_apy():
    """Test Aave APY retrieval (mocked)"""
    with patch('os.getenv', return_value=None):
        adapter = AaveAdapter({})

        apy = await adapter.get_apy('USDC')

        # Mock implementation returns value
        assert apy is not None
        assert apy > 0


# Uniswap Adapter Tests (Mocked)

@pytest.mark.asyncio
async def test_uniswap_deposit_not_supported():
    """Test that Uniswap doesn't support deposits"""
    with patch('os.getenv', return_value=None):
        adapter = UniswapAdapter({})

        result = await adapter.deposit('USDC', Decimal('1000'))

        assert result['success'] is False
        assert 'does not support deposits' in result['error']


@pytest.mark.asyncio
async def test_uniswap_withdraw_not_supported():
    """Test that Uniswap doesn't support withdrawals"""
    with patch('os.getenv', return_value=None):
        adapter = UniswapAdapter({})

        result = await adapter.withdraw('USDC', Decimal('500'))

        assert result['success'] is False
        assert 'does not support withdrawals' in result['error']


@pytest.mark.asyncio
async def test_uniswap_swap_without_private_key():
    """Test Uniswap swap without private key"""
    with patch('os.getenv', return_value=None):
        adapter = UniswapAdapter({})

        result = await adapter.swap('USDC', 'ETH', Decimal('2500'))

        assert result['success'] is False
        assert 'read-only mode' in result['error']


@pytest.mark.asyncio
async def test_uniswap_estimate_output():
    """Test output estimation"""
    with patch('os.getenv', return_value=None):
        adapter = UniswapAdapter({})

        estimated = await adapter.estimate_output('USDC', 'ETH', Decimal('2500'))

        assert estimated is not None
        assert estimated > 0


@pytest.mark.asyncio
async def test_uniswap_calculate_slippage():
    """Test slippage calculation"""
    with patch('os.getenv', return_value=None):
        adapter = UniswapAdapter({})

        slippage = await adapter.calculate_slippage(
            'USDC',
            'ETH',
            Decimal('2500'),
            Decimal('0.99')  # Got slightly less than expected
        )

        assert slippage >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
