"""
Aave Protocol Adapter - DeFi Lending/Borrowing

Integrates with Aave V3 for deposits and withdrawals.
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


class AaveAdapter(ProtocolAdapter):
    """
    Aave V3 protocol adapter

    Features:
    - Deposit assets to earn yield
    - Withdraw assets
    - Query current APY
    - Gas estimation

    IMPORTANT: Requires PRIVATE_KEY in environment for signing transactions.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Web3 setup
        rpc_url = config.get('rpc_url', 'https://eth-mainnet.g.alchemy.com/v2/demo')
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))

        # Contract addresses
        self.pool_address = config.get('pool_address')  # Aave V3 Pool
        self.chain = config.get('chain', 'ethereum')

        # CRITICAL: Private key must be in environment, NEVER in code
        private_key = os.getenv('PRIVATE_KEY')
        if private_key:
            self.account = Account.from_key(private_key)
            logger.info(f"Aave adapter initialized with account {self.account.address}")
        else:
            self.account = None
            logger.warning("Aave adapter initialized WITHOUT private key (read-only mode)")

    async def deposit(
        self,
        asset: str,
        amount: Decimal,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Deposit assets to Aave to earn yield

        Args:
            asset: Asset to deposit (e.g., "USDC", "DAI")
            amount: Amount to deposit
        """
        logger.info(f"[Aave] Depositing {amount} {asset}")

        if not self.account:
            return {
                'success': False,
                'tx_hash': None,
                'amount_deposited': Decimal('0'),
                'gas_cost_usd': Decimal('0'),
                'receipt_token': None,
                'error': 'No private key configured (read-only mode)'
            }

        try:
            # In production, this would:
            # 1. Get asset contract address
            # 2. Approve Aave Pool to spend tokens
            # 3. Call Pool.deposit(asset, amount, onBehalfOf, referralCode)
            # 4. Wait for transaction confirmation
            # 5. Return tx hash and receipt token (aToken)

            # For now, return mock success
            logger.warning("[Aave] Using mock implementation - replace with real Web3 calls")

            await asyncio.sleep(2)  # Simulate blockchain confirmation

            mock_tx_hash = f"0xaave_deposit_{asset}_{amount}"
            receipt_token = f"a{asset}"

            return {
                'success': True,
                'tx_hash': mock_tx_hash,
                'amount_deposited': amount,
                'gas_cost_usd': Decimal('5.00'),
                'receipt_token': receipt_token,
                'error': None
            }

        except Exception as e:
            logger.error(f"[Aave] Deposit failed: {str(e)}")
            return {
                'success': False,
                'tx_hash': None,
                'amount_deposited': Decimal('0'),
                'gas_cost_usd': Decimal('0'),
                'receipt_token': None,
                'error': str(e)
            }

    async def withdraw(
        self,
        asset: str,
        amount: Decimal,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Withdraw assets from Aave

        Args:
            asset: Asset to withdraw
            amount: Amount to withdraw
        """
        logger.info(f"[Aave] Withdrawing {amount} {asset}")

        if not self.account:
            return {
                'success': False,
                'tx_hash': None,
                'amount_withdrawn': Decimal('0'),
                'gas_cost_usd': Decimal('0'),
                'error': 'No private key configured (read-only mode)'
            }

        try:
            # In production, this would:
            # 1. Get aToken address for asset
            # 2. Call Pool.withdraw(asset, amount, to)
            # 3. Wait for confirmation
            # 4. Return results

            logger.warning("[Aave] Using mock implementation - replace with real Web3 calls")

            await asyncio.sleep(2)

            mock_tx_hash = f"0xaave_withdraw_{asset}_{amount}"

            return {
                'success': True,
                'tx_hash': mock_tx_hash,
                'amount_withdrawn': amount,
                'gas_cost_usd': Decimal('4.00'),
                'error': None
            }

        except Exception as e:
            logger.error(f"[Aave] Withdrawal failed: {str(e)}")
            return {
                'success': False,
                'tx_hash': None,
                'amount_withdrawn': Decimal('0'),
                'gas_cost_usd': Decimal('0'),
                'error': str(e)
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
        Aave doesn't support swaps directly

        Use Uniswap adapter for swaps.
        """
        return {
            'success': False,
            'error': 'Aave does not support swaps - use Uniswap adapter'
        }

    async def get_apy(self, asset: str) -> Optional[Decimal]:
        """
        Get current supply APY for asset on Aave

        Args:
            asset: Asset symbol

        Returns:
            APY as decimal (e.g., 0.082 for 8.2%)
        """
        try:
            # In production, this would:
            # 1. Get reserve data from Pool contract
            # 2. Read liquidityRate
            # 3. Convert RAY units to APY percentage
            # 4. Return decimal

            logger.warning("[Aave] Using mock APY data - replace with real contract calls")

            # Mock APY data
            mock_apys = {
                'USDC': Decimal('0.08'),   # 8%
                'DAI': Decimal('0.075'),   # 7.5%
                'USDT': Decimal('0.085'),  # 8.5%
                'ETH': Decimal('0.05'),    # 5%
            }

            return mock_apys.get(asset.upper())

        except Exception as e:
            logger.error(f"[Aave] Failed to get APY: {str(e)}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Aave protocol health
        """
        try:
            # In production, would check:
            # - RPC connection
            # - Pool contract responsiveness
            # - Account balance

            is_connected = await self.w3.is_connected()

            return {
                'healthy': is_connected,
                'protocol': 'aave',
                'latency_ms': 50.0,
                'error': None if is_connected else 'Not connected to RPC'
            }

        except Exception as e:
            return {
                'healthy': False,
                'protocol': 'aave',
                'latency_ms': 0.0,
                'error': str(e)
            }
