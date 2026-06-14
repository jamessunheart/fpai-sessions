"""
Aave Protocol Adapter

Aave is a lending protocol - you deposit USDC and earn interest.
This is the foundation of our base yield layer ($100K target).

Aave V3 on Ethereum mainnet:
- Pool contract: 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2
- USDC on Ethereum: 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
- aUSDC (receipt token): 0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c

APY as of Nov 2025: ~3.9%
"""
from decimal import Decimal
from typing import Optional, Dict
import logging
from web3 import Web3
from web3.contract import Contract
import aiohttp

from app.config import settings
from app.core.models import AssetType, ProtocolName, Transaction
from app.protocols.base import ProtocolAdapter

logger = logging.getLogger(__name__)


class AaveAdapter(ProtocolAdapter):
    """
    Adapter for Aave V3 lending protocol

    Operations:
    - Deposit USDC to earn yield
    - Withdraw USDC (instant liquidity)
    - Query balance and APY
    """

    # Aave V3 Mainnet Addresses
    POOL_ADDRESS = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
    USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    AUSDC_ADDRESS = "0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c"

    # Aave Pool ABI (simplified - just what we need)
    POOL_ABI = [
        {
            "inputs": [
                {"name": "asset", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "onBehalfOf", "type": "address"},
                {"name": "referralCode", "type": "uint16"}
            ],
            "name": "supply",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                {"name": "asset", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "to", "type": "address"}
            ],
            "name": "withdraw",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [{"name": "asset", "type": "address"}],
            "name": "getReserveData",
            "outputs": [
                {
                    "components": [
                        {"name": "configuration", "type": "uint256"},
                        {"name": "liquidityIndex", "type": "uint128"},
                        {"name": "currentLiquidityRate", "type": "uint128"},
                        {"name": "variableBorrowIndex", "type": "uint128"},
                        {"name": "currentVariableBorrowRate", "type": "uint128"},
                        {"name": "currentStableBorrowRate", "type": "uint128"},
                        {"name": "lastUpdateTimestamp", "type": "uint40"},
                        {"name": "id", "type": "uint16"},
                        {"name": "aTokenAddress", "type": "address"},
                        {"name": "stableDebtTokenAddress", "type": "address"},
                        {"name": "variableDebtTokenAddress", "type": "address"},
                        {"name": "interestRateStrategyAddress", "type": "address"},
                        {"name": "accruedToTreasury", "type": "uint128"},
                        {"name": "unbacked", "type": "uint128"},
                        {"name": "isolationModeTotalDebt", "type": "uint128"}
                    ],
                    "name": "",
                    "type": "tuple"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]

    # ERC20 ABI (for aUSDC balance checking)
    ERC20_ABI = [
        {
            "inputs": [{"name": "account", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]

    def __init__(self):
        super().__init__(ProtocolName.AAVE)

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(settings.ethereum_rpc_url))

        # Initialize contracts
        self.pool_contract: Optional[Contract] = None
        self.ausdc_contract: Optional[Contract] = None

        if self.w3.is_connected():
            self.pool_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.POOL_ADDRESS),
                abi=self.POOL_ABI
            )
            self.ausdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.AUSDC_ADDRESS),
                abi=self.ERC20_ABI
            )
            logger.info("✅ Connected to Aave V3 on Ethereum")
        else:
            logger.warning("⚠️ Web3 not connected - check RPC URL")

    # ========================================================================
    # CORE OPERATIONS
    # ========================================================================

    async def deposit(
        self,
        asset: AssetType,
        amount: Decimal,
        simulate: bool = False
    ) -> Transaction:
        """
        Deposit USDC to Aave to earn yield

        Process:
        1. Approve Aave Pool to spend USDC
        2. Call pool.supply(usdc, amount, user, 0)
        3. Receive aUSDC (interest-bearing token)
        """
        if asset != AssetType.USDC:
            raise ValueError(f"Aave adapter only supports USDC deposits, got {asset}")

        logger.info(f"💰 Depositing {amount} USDC to Aave...")

        if simulate:
            logger.info("   (SIMULATION - not executing)")
            return self._create_transaction_record(
                tx_type="deposit",
                from_asset=AssetType.USDC,
                to_asset=AssetType.AUSDC,
                amount_from=amount,
                amount_to=amount,  # 1:1 initially
                status="simulated"
            )

        # TODO: Actual blockchain execution
        # For now, return simulated transaction

        logger.info(f"✅ Deposit simulated: {amount} USDC → aUSDC")

        return self._create_transaction_record(
            tx_type="deposit",
            from_asset=AssetType.USDC,
            to_asset=AssetType.AUSDC,
            amount_from=amount,
            amount_to=amount,
            tx_hash="0x" + "0" * 64,  # Placeholder
            status="simulated"
        )

    async def withdraw(
        self,
        asset: AssetType,
        amount: Decimal,
        simulate: bool = False
    ) -> Transaction:
        """
        Withdraw USDC from Aave

        Process:
        1. Call pool.withdraw(usdc, amount, user)
        2. Burn aUSDC, receive USDC
        """
        if asset != AssetType.USDC:
            raise ValueError(f"Aave adapter only supports USDC withdrawals, got {asset}")

        logger.info(f"💸 Withdrawing {amount} USDC from Aave...")

        if simulate:
            logger.info("   (SIMULATION - not executing)")
            return self._create_transaction_record(
                tx_type="withdraw",
                from_asset=AssetType.AUSDC,
                to_asset=AssetType.USDC,
                amount_from=amount,
                amount_to=amount,
                status="simulated"
            )

        # TODO: Actual blockchain execution

        logger.info(f"✅ Withdrawal simulated: {amount} aUSDC → USDC")

        return self._create_transaction_record(
            tx_type="withdraw",
            from_asset=AssetType.AUSDC,
            to_asset=AssetType.USDC,
            amount_from=amount,
            amount_to=amount,
            tx_hash="0x" + "0" * 64,
            status="simulated"
        )

    async def get_balance(self, asset: AssetType) -> Decimal:
        """
        Get current aUSDC balance (which represents USDC deposited + interest)

        aUSDC balance grows over time as interest accrues
        """
        if asset != AssetType.USDC:
            return Decimal("0")

        # For MVP without wallet connected, return simulated balance
        # In production, query actual blockchain balance

        if not settings.treasury_wallet_address:
            # Return target allocation for testing
            return Decimal("100000")  # $100K target

        try:
            # Query actual balance from blockchain
            wallet_address = Web3.to_checksum_address(settings.treasury_wallet_address)
            balance_wei = self.ausdc_contract.functions.balanceOf(wallet_address).call()

            # Convert from wei to USDC (6 decimals)
            balance_usdc = Decimal(balance_wei) / Decimal(10 ** 6)

            logger.info(f"📊 Aave balance: {balance_usdc} aUSDC")
            return balance_usdc

        except Exception as e:
            logger.error(f"Error querying Aave balance: {e}")
            return Decimal("0")

    async def get_current_apy(self, asset: AssetType) -> float:
        """
        Get current USDC lending APY on Aave

        This queries the Aave reserve data to get real-time APY
        """
        if asset != AssetType.USDC:
            return 0.0

        try:
            # Method 1: Query on-chain reserve data
            if self.pool_contract and self.w3.is_connected():
                reserve_data = self.pool_contract.functions.getReserveData(
                    Web3.to_checksum_address(self.USDC_ADDRESS)
                ).call()

                # Extract liquidity rate (index 2)
                # Aave uses Ray (27 decimals) for rates
                liquidity_rate_ray = reserve_data[2]

                # Convert Ray to APY percentage
                # Formula: APY = (liquidityRate / 10^27) * 100
                apy = float(liquidity_rate_ray) / (10 ** 27) * 100

                logger.info(f"📈 Aave USDC APY: {apy:.2f}%")
                return apy

            # Method 2: Fallback to API query
            return await self._get_apy_from_api()

        except Exception as e:
            logger.error(f"Error fetching Aave APY: {e}")
            # Fallback to recent known APY
            return 3.9  # Nov 2025 approximate

    async def _get_apy_from_api(self) -> float:
        """
        Fallback: Get APY from Aave API or external data source
        """
        try:
            # Aave V3 Subgraph or API endpoint
            # For MVP, return approximate current rate
            url = "https://aave-api-v2.aave.com/data/liquidity/v2"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Parse APY from response
                        # TODO: Implement actual parsing
                        pass

            # Fallback to known approximate
            return 3.9

        except Exception as e:
            logger.error(f"Error fetching APY from API: {e}")
            return 3.9

    # ========================================================================
    # INFORMATION
    # ========================================================================

    async def get_protocol_info(self) -> Dict:
        """Get Aave protocol information"""
        return {
            "name": "Aave V3",
            "network": "Ethereum Mainnet",
            "tvl": Decimal("10000000000"),  # ~$10B approximate
            "health": "healthy" if await self.health_check() else "issues",
            "available_assets": [AssetType.USDC],
            "pool_address": self.POOL_ADDRESS,
            "ausdc_address": self.AUSDC_ADDRESS
        }

    async def health_check(self) -> bool:
        """Check if Aave is operational"""
        try:
            # Check 1: Can we get APY?
            apy = await self.get_current_apy(AssetType.USDC)
            if apy <= 0:
                logger.warning("Aave health check: APY is 0 or negative")
                return False

            # Check 2: Is Web3 connected?
            if not self.w3.is_connected():
                logger.warning("Aave health check: Web3 not connected")
                return False

            logger.info("✅ Aave health check passed")
            return True

        except Exception as e:
            logger.error(f"Aave health check failed: {e}")
            return False


# Global instance
aave_adapter = AaveAdapter()
