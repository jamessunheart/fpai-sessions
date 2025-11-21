"""
Base Protocol Adapter - Interface for all protocol integrations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ProtocolAdapter(ABC):
    """
    Base class for all protocol adapters (Aave, Uniswap, etc.)

    All protocol integrations must implement this interface to ensure
    consistent behavior across different DeFi protocols.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize protocol adapter with configuration

        Args:
            config: Protocol-specific configuration
                   (contract addresses, gas limits, slippage tolerance, etc.)
        """
        self.config = config
        self.protocol_name = self.__class__.__name__.replace('Adapter', '').lower()
        logger.info(f"Initialized {self.protocol_name} adapter")

    @abstractmethod
    async def deposit(
        self,
        asset: str,
        amount: Decimal,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Deposit assets to the protocol

        Args:
            asset: Asset symbol (e.g., "USDC", "ETH")
            amount: Amount to deposit
            **kwargs: Protocol-specific parameters

        Returns:
            {
                'success': bool,
                'tx_hash': str,
                'amount_deposited': Decimal,
                'gas_cost_usd': Decimal,
                'receipt_token': str,  # e.g., aUSDC
                'error': Optional[str]
            }
        """
        pass

    @abstractmethod
    async def withdraw(
        self,
        asset: str,
        amount: Decimal,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Withdraw assets from the protocol

        Args:
            asset: Asset symbol (e.g., "USDC", "ETH")
            amount: Amount to withdraw
            **kwargs: Protocol-specific parameters

        Returns:
            {
                'success': bool,
                'tx_hash': str,
                'amount_withdrawn': Decimal,
                'gas_cost_usd': Decimal,
                'error': Optional[str]
            }
        """
        pass

    @abstractmethod
    async def swap(
        self,
        input_asset: str,
        output_asset: str,
        input_amount: Decimal,
        min_output_amount: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute token swap

        Args:
            input_asset: Asset to sell (e.g., "USDC")
            output_asset: Asset to buy (e.g., "ETH")
            input_amount: Amount of input asset
            min_output_amount: Minimum acceptable output (slippage protection)
            **kwargs: Protocol-specific parameters

        Returns:
            {
                'success': bool,
                'tx_hash': str,
                'input_amount': Decimal,
                'output_amount': Decimal,
                'execution_price': Decimal,
                'slippage': Decimal,  # Actual slippage %
                'gas_cost_usd': Decimal,
                'error': Optional[str]
            }
        """
        pass

    async def stake(
        self,
        asset: str,
        amount: Decimal,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Stake assets (optional - not all protocols support)

        Args:
            asset: Asset to stake
            amount: Amount to stake
            **kwargs: Protocol-specific parameters

        Returns:
            {
                'success': bool,
                'tx_hash': str,
                'amount_staked': Decimal,
                'gas_cost_usd': Decimal,
                'error': Optional[str]
            }
        """
        return {
            'success': False,
            'error': f'{self.protocol_name} does not support staking'
        }

    @abstractmethod
    async def get_apy(self, asset: str) -> Optional[Decimal]:
        """
        Get current APY for an asset on this protocol

        Args:
            asset: Asset symbol

        Returns:
            APY as decimal (e.g., 0.082 for 8.2%) or None if unavailable
        """
        pass

    async def estimate_gas(self, operation: str) -> Decimal:
        """
        Estimate gas cost for an operation

        Args:
            operation: Operation type ('deposit', 'withdraw', 'swap', etc.)

        Returns:
            Estimated gas cost in USD
        """
        # Default implementation - can be overridden
        gas_estimates = {
            'deposit': Decimal('5.00'),
            'withdraw': Decimal('5.00'),
            'swap': Decimal('15.00'),
            'stake': Decimal('10.00')
        }
        return gas_estimates.get(operation, Decimal('10.00'))

    def validate_asset(self, asset: str) -> bool:
        """
        Validate if asset is supported by this protocol

        Args:
            asset: Asset symbol

        Returns:
            True if supported
        """
        supported_assets = self.config.get('supported_assets', [])
        if not supported_assets:
            return True  # No restrictions
        return asset.upper() in [a.upper() for a in supported_assets]

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if protocol adapter is operational

        Returns:
            {
                'healthy': bool,
                'protocol': str,
                'latency_ms': float,
                'error': Optional[str]
            }
        """
        return {
            'healthy': True,
            'protocol': self.protocol_name,
            'latency_ms': 0.0,
            'error': None
        }
