"""
Simulation Protocol Adapter - For testing and Phase 1

Executes virtual trades without blockchain interaction.
Returns realistic mock results for testing the trading engine.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
import logging
import asyncio
from datetime import datetime
import random

from .base import ProtocolAdapter

logger = logging.getLogger(__name__)


class SimulationAdapter(ProtocolAdapter):
    """
    Simulation protocol adapter for testing without blockchain

    Features:
    - Instant execution (no blockchain wait time)
    - Configurable success/failure rates
    - Realistic slippage simulation
    - Mock gas costs
    - APY data for common assets
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mock_apys = config.get('mock_apys', {
            'USDC': Decimal('0.08'),  # 8% APY
            'ETH': Decimal('0.05'),   # 5% APY
            'BTC': Decimal('0.03'),   # 3% APY
            'DAI': Decimal('0.075'),  # 7.5% APY
        })
        self.success_rate = config.get('success_rate', 0.95)  # 95% success by default
        self.simulate_delay = config.get('simulate_delay', False)
        logger.info("Simulation adapter initialized (no blockchain required)")

    async def deposit(
        self,
        asset: str,
        amount: Decimal,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Simulate deposit to DeFi protocol

        Args:
            asset: Asset symbol
            amount: Amount to deposit
        """
        logger.info(f"[SIMULATION] Depositing {amount} {asset}")

        # Simulate network delay if configured
        if self.simulate_delay:
            await asyncio.sleep(random.uniform(0.5, 2.0))

        # Random failure simulation
        if random.random() > self.success_rate:
            return {
                'success': False,
                'tx_hash': None,
                'amount_deposited': Decimal('0'),
                'gas_cost_usd': Decimal('0'),
                'receipt_token': None,
                'error': 'Simulated network failure'
            }

        # Successful deposit
        mock_tx_hash = f"0xsim_{datetime.utcnow().timestamp()}_{asset}_{amount}"
        receipt_token = f"a{asset}"  # e.g., aUSDC for Aave

        return {
            'success': True,
            'tx_hash': mock_tx_hash,
            'amount_deposited': amount,
            'gas_cost_usd': Decimal('3.50'),  # Mock gas cost
            'receipt_token': receipt_token,
            'error': None
        }

    async def withdraw(
        self,
        asset: str,
        amount: Decimal,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Simulate withdrawal from DeFi protocol

        Args:
            asset: Asset symbol
            amount: Amount to withdraw
        """
        logger.info(f"[SIMULATION] Withdrawing {amount} {asset}")

        if self.simulate_delay:
            await asyncio.sleep(random.uniform(0.5, 2.0))

        if random.random() > self.success_rate:
            return {
                'success': False,
                'tx_hash': None,
                'amount_withdrawn': Decimal('0'),
                'gas_cost_usd': Decimal('0'),
                'error': 'Simulated insufficient liquidity'
            }

        mock_tx_hash = f"0xsim_withdraw_{datetime.utcnow().timestamp()}_{asset}"

        return {
            'success': True,
            'tx_hash': mock_tx_hash,
            'amount_withdrawn': amount,
            'gas_cost_usd': Decimal('4.00'),
            'error': None
        }

    async def swap(
        self,
        input_asset: str,
        output_asset: str,
        input_amount: Decimal,
        min_output_amount: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Simulate token swap on DEX

        Args:
            input_asset: Asset to sell
            output_asset: Asset to buy
            input_amount: Amount of input asset
            min_output_amount: Minimum acceptable output
        """
        logger.info(f"[SIMULATION] Swapping {input_amount} {input_asset} -> {output_asset}")

        if self.simulate_delay:
            await asyncio.sleep(random.uniform(1.0, 3.0))

        if random.random() > self.success_rate:
            return {
                'success': False,
                'tx_hash': None,
                'input_amount': input_amount,
                'output_amount': Decimal('0'),
                'execution_price': Decimal('0'),
                'slippage': Decimal('0'),
                'gas_cost_usd': Decimal('0'),
                'error': 'Simulated slippage exceeded tolerance'
            }

        # Mock exchange rate (simplified)
        mock_rates = {
            ('USDC', 'ETH'): Decimal('0.0004'),   # 1 USDC = 0.0004 ETH (~$2500 ETH)
            ('ETH', 'USDC'): Decimal('2500'),      # 1 ETH = 2500 USDC
            ('USDC', 'BTC'): Decimal('0.000011'),  # 1 USDC = 0.000011 BTC (~$90K BTC)
            ('BTC', 'USDC'): Decimal('90000'),     # 1 BTC = 90K USDC
            ('DAI', 'USDC'): Decimal('0.9995'),    # Nearly 1:1
            ('USDC', 'DAI'): Decimal('1.0005'),
        }

        rate_key = (input_asset, output_asset)
        base_rate = mock_rates.get(rate_key, Decimal('1.0'))

        # Simulate realistic slippage (0.1% - 0.5%)
        slippage_factor = Decimal(1) - Decimal(random.uniform(0.001, 0.005))
        execution_rate = base_rate * slippage_factor

        output_amount = input_amount * execution_rate
        actual_slippage = (base_rate - execution_rate) / base_rate * Decimal('100')

        # Check minimum output
        if min_output_amount and output_amount < min_output_amount:
            return {
                'success': False,
                'tx_hash': None,
                'input_amount': input_amount,
                'output_amount': Decimal('0'),
                'execution_price': Decimal('0'),
                'slippage': actual_slippage,
                'gas_cost_usd': Decimal('0'),
                'error': f'Output {output_amount} below minimum {min_output_amount}'
            }

        mock_tx_hash = f"0xsim_swap_{datetime.utcnow().timestamp()}_{input_asset}_{output_asset}"

        return {
            'success': True,
            'tx_hash': mock_tx_hash,
            'input_amount': input_amount,
            'output_amount': output_amount,
            'execution_price': execution_rate,
            'slippage': actual_slippage,
            'gas_cost_usd': Decimal('12.50'),
            'error': None
        }

    async def get_apy(self, asset: str) -> Optional[Decimal]:
        """
        Get mock APY for asset

        Args:
            asset: Asset symbol

        Returns:
            Mock APY as decimal
        """
        return self.mock_apys.get(asset.upper())

    async def estimate_gas(self, operation: str) -> Decimal:
        """
        Estimate gas cost (mocked)

        Args:
            operation: Operation type

        Returns:
            Mock gas cost in USD
        """
        gas_costs = {
            'deposit': Decimal('3.50'),
            'withdraw': Decimal('4.00'),
            'swap': Decimal('12.50'),
            'stake': Decimal('8.00')
        }
        return gas_costs.get(operation, Decimal('5.00'))

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check (always healthy for simulation)
        """
        return {
            'healthy': True,
            'protocol': 'simulation',
            'latency_ms': 0.1,
            'error': None
        }
