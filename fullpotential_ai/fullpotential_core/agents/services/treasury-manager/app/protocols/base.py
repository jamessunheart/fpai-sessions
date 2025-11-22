"""
Protocol Adapter Base Class

Abstract interface for all DeFi protocol integrations
Ensures consistent API across Aave, Pendle, Curve, etc.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional, Dict, List
from datetime import datetime
import logging

from app.core.models import Transaction, ProtocolName, AssetType

logger = logging.getLogger(__name__)


class ProtocolAdapter(ABC):
    """
    Base class for all DeFi protocol adapters

    Each protocol (Aave, Pendle, Curve) implements this interface
    This ensures consistent operations across all protocols
    """

    def __init__(self, protocol_name: ProtocolName):
        self.protocol_name = protocol_name
        self.last_sync: Optional[datetime] = None

    # ========================================================================
    # CORE OPERATIONS (Must Implement)
    # ========================================================================

    @abstractmethod
    async def deposit(
        self,
        asset: AssetType,
        amount: Decimal,
        simulate: bool = False
    ) -> Transaction:
        """
        Deposit asset into protocol

        Args:
            asset: Asset to deposit (USDC, BTC, ETH, etc.)
            amount: Amount to deposit
            simulate: If True, don't execute (for testing)

        Returns:
            Transaction record with details
        """
        pass

    @abstractmethod
    async def withdraw(
        self,
        asset: AssetType,
        amount: Decimal,
        simulate: bool = False
    ) -> Transaction:
        """
        Withdraw asset from protocol

        Args:
            asset: Asset to withdraw
            amount: Amount to withdraw (or "max" for all)
            simulate: If True, don't execute

        Returns:
            Transaction record
        """
        pass

    @abstractmethod
    async def get_balance(self, asset: AssetType) -> Decimal:
        """
        Get current balance in protocol

        Args:
            asset: Asset to check

        Returns:
            Current balance
        """
        pass

    @abstractmethod
    async def get_current_apy(self, asset: AssetType) -> float:
        """
        Get current APY for depositing asset

        Args:
            asset: Asset to check

        Returns:
            Current APY as percentage (e.g., 3.9 for 3.9%)
        """
        pass

    # ========================================================================
    # OPTIONAL OPERATIONS (Protocol-Specific)
    # ========================================================================

    async def claim_rewards(self) -> Optional[Transaction]:
        """
        Claim any pending rewards (CRV, AAVE tokens, etc.)
        Optional - not all protocols have rewards
        """
        return None

    async def get_rewards_balance(self) -> Dict[str, Decimal]:
        """
        Get pending rewards

        Returns:
            Dict of {token: amount}
        """
        return {}

    # ========================================================================
    # INFORMATION & HEALTH CHECKS
    # ========================================================================

    async def get_protocol_info(self) -> Dict:
        """
        Get general protocol information

        Returns:
            {
                "name": str,
                "tvl": Decimal,
                "health": str,
                "available_assets": List[AssetType]
            }
        """
        return {
            "name": self.protocol_name.value,
            "tvl": Decimal("0"),
            "health": "unknown",
            "available_assets": []
        }

    async def health_check(self) -> bool:
        """
        Check if protocol is operational

        Returns:
            True if healthy, False if issues detected
        """
        try:
            # Basic check: can we query APY?
            apy = await self.get_current_apy(AssetType.USDC)
            return apy > 0
        except Exception as e:
            logger.error(f"Health check failed for {self.protocol_name.value}: {e}")
            return False

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def _create_transaction_record(
        self,
        tx_type: str,
        from_asset: AssetType,
        to_asset: AssetType,
        amount_from: Decimal,
        amount_to: Decimal,
        tx_hash: Optional[str] = None,
        status: str = "pending"
    ) -> Transaction:
        """Helper to create transaction records"""
        from app.core.models import TransactionType

        return Transaction(
            timestamp=datetime.utcnow(),
            tx_type=TransactionType(tx_type),
            protocol=self.protocol_name,
            from_asset=from_asset,
            to_asset=to_asset,
            amount_from=amount_from,
            amount_to=amount_to,
            tx_hash=tx_hash,
            status=status
        )

    def __repr__(self):
        return f"<{self.__class__.__name__} protocol={self.protocol_name.value}>"
