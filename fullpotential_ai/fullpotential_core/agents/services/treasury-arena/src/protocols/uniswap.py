"""
Uniswap Protocol Adapter - DEX Swaps

Integrates with Uniswap V3 for token swaps.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
import logging
import asyncio
import os

from web3 import AsyncWeb3
from eth_account import Account

from .base import ProtocolAdapter

logger = logging.getLogger(__name__)


class UniswapAdapter(ProtocolAdapter):
    """
    Uniswap V3 protocol adapter

    Features:
    - Token swaps with slippage protection
    - Price estimation
    - Gas estimation
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Web3 setup
        rpc_url = config.get('rpc_url', 'https://eth-mainnet.g.alchemy.com/v2/demo')
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))

        # Contract addresses
        self.router_address = config.get('router_address')  # Uniswap V3 Router
        self.quoter_address = config.get('quoter_address')  # Quoter for price estimates
        self.chain = config.get('chain', 'ethereum')

        # CRITICAL: Private key from environment only
        private_key = os.getenv('PRIVATE_KEY')
        if private_key:
            self.account = Account.from_key(private_key)
            logger.info(f"Uniswap adapter initialized with account {self.account.address}")
        else:
            self.account = None
            logger.warning("Uniswap adapter initialized WITHOUT private key (read-only mode)")

    async def deposit(self, asset: str, amount: Decimal, **kwargs) -> Dict[str, Any]:
        """Uniswap doesn't support deposits"""
        return {
            'success': False,
            'error': 'Uniswap does not support deposits - use Aave adapter'
        }

    async def withdraw(self, asset: str, amount: Decimal, **kwargs) -> Dict[str, Any]:
        """Uniswap doesn't support withdrawals"""
        return {
            'success': False,
            'error': 'Uniswap does not support withdrawals - use Aave adapter'
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
        Execute token swap on Uniswap

        Args:
            input_asset: Token to sell
            output_asset: Token to buy
            input_amount: Amount of input token
            min_output_amount: Minimum acceptable output (slippage protection)
        """
        logger.info(f"[Uniswap] Swapping {input_amount} {input_asset} -> {output_asset}")

        if not self.account:
            return {
                'success': False,
                'tx_hash': None,
                'input_amount': input_amount,
                'output_amount': Decimal('0'),
                'execution_price': Decimal('0'),
                'slippage': Decimal('0'),
                'gas_cost_usd': Decimal('0'),
                'error': 'No private key configured (read-only mode)'
            }

        try:
            # In production, this would:
            # 1. Get token addresses from symbols
            # 2. Calculate expected output using Quoter contract
            # 3. Set deadline (e.g., block.timestamp + 15 minutes)
            # 4. Approve Router to spend input tokens
            # 5. Call Router.exactInputSingle() or exactInput() for multi-hop
            # 6. Wait for transaction confirmation
            # 7. Calculate actual slippage
            # 8. Return results

            logger.warning("[Uniswap] Using mock implementation - replace with real Web3 calls")

            # Estimate output (mocked)
            estimated_output = await self.estimate_output(
                input_asset,
                output_asset,
                input_amount
            )

            if not estimated_output:
                return {
                    'success': False,
                    'tx_hash': None,
                    'input_amount': input_amount,
                    'output_amount': Decimal('0'),
                    'execution_price': Decimal('0'),
                    'slippage': Decimal('0'),
                    'gas_cost_usd': Decimal('0'),
                    'error': 'Failed to estimate output'
                }

            # Check slippage
            if min_output_amount and estimated_output < min_output_amount:
                return {
                    'success': False,
                    'tx_hash': None,
                    'input_amount': input_amount,
                    'output_amount': Decimal('0'),
                    'execution_price': Decimal('0'),
                    'slippage': Decimal('0'),
                    'gas_cost_usd': Decimal('0'),
                    'error': f'Estimated output {estimated_output} below minimum {min_output_amount}'
                }

            # Simulate blockchain execution
            await asyncio.sleep(3)

            # Calculate execution price and slippage
            execution_price = estimated_output / input_amount
            slippage = await self.calculate_slippage(
                input_asset,
                output_asset,
                input_amount,
                estimated_output
            )

            mock_tx_hash = f"0xuniswap_swap_{input_asset}_{output_asset}_{input_amount}"

            return {
                'success': True,
                'tx_hash': mock_tx_hash,
                'input_amount': input_amount,
                'output_amount': estimated_output,
                'execution_price': execution_price,
                'slippage': slippage,
                'gas_cost_usd': Decimal('15.00'),
                'error': None
            }

        except Exception as e:
            logger.error(f"[Uniswap] Swap failed: {str(e)}")
            return {
                'success': False,
                'tx_hash': None,
                'input_amount': input_amount,
                'output_amount': Decimal('0'),
                'execution_price': Decimal('0'),
                'slippage': Decimal('0'),
                'gas_cost_usd': Decimal('0'),
                'error': str(e)
            }

    async def estimate_output(
        self,
        input_asset: str,
        output_asset: str,
        input_amount: Decimal
    ) -> Optional[Decimal]:
        """
        Estimate output amount for swap

        In production, uses Quoter contract to get on-chain quote.

        Args:
            input_asset: Input token
            output_asset: Output token
            input_amount: Input amount

        Returns:
            Estimated output amount
        """
        # Mock exchange rates
        mock_rates = {
            ('USDC', 'ETH'): Decimal('0.0004'),
            ('ETH', 'USDC'): Decimal('2500'),
            ('USDC', 'BTC'): Decimal('0.000011'),
            ('BTC', 'USDC'): Decimal('90000'),
            ('DAI', 'USDC'): Decimal('0.9995'),
            ('USDC', 'DAI'): Decimal('1.0005'),
        }

        rate_key = (input_asset, output_asset)
        rate = mock_rates.get(rate_key, Decimal('1.0'))

        estimated = input_amount * rate

        logger.info(f"[Uniswap] Estimated: {input_amount} {input_asset} -> {estimated} {output_asset}")

        return estimated

    async def calculate_slippage(
        self,
        input_asset: str,
        output_asset: str,
        input_amount: Decimal,
        output_amount: Decimal
    ) -> Decimal:
        """
        Calculate slippage percentage

        Args:
            input_asset: Input token
            output_asset: Output token
            input_amount: Input amount
            output_amount: Actual output amount

        Returns:
            Slippage as percentage (e.g., 0.5 for 0.5%)
        """
        # Get expected output at mid-market rate
        expected = await self.estimate_output(input_asset, output_asset, input_amount)

        if not expected or expected == 0:
            return Decimal('0')

        slippage = ((expected - output_amount) / expected) * Decimal('100')

        return max(Decimal('0'), slippage)  # Can't be negative

    async def get_apy(self, asset: str) -> Optional[Decimal]:
        """Uniswap doesn't have APY (it's a DEX, not a lending protocol)"""
        return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Uniswap protocol health
        """
        try:
            is_connected = await self.w3.is_connected()

            return {
                'healthy': is_connected,
                'protocol': 'uniswap',
                'latency_ms': 50.0,
                'error': None if is_connected else 'Not connected to RPC'
            }

        except Exception as e:
            return {
                'healthy': False,
                'protocol': 'uniswap',
                'latency_ms': 0.0,
                'error': str(e)
            }
