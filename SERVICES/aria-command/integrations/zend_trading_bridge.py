# SERVICES/aria-command/integrations/zend_trading_bridge.py
"""
Zend-Trading Bridge
Cross-service integration for converting trading profits to UC credits.

Commands enabled:
- "convert trading profit to UC" - Withdraw from Hyperliquid → Zend Marketplace → UC
- "fund trading from Zend" - Transfer UC to trading margin

Per ZEND_REGENERATIVE_SPEC.md:
- External: Real money (USDC) moves via Hyperliquid
- Internal: UC Credits for friction-free value transfer
"""

import os
import logging
import httpx
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversionStatus(Enum):
    """Status of a conversion operation."""
    PENDING = "pending"
    WITHDRAWING = "withdrawing"
    IN_MARKETPLACE = "in_marketplace"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ConversionOrder:
    """A conversion order (profit → UC or UC → margin)."""
    id: str
    user_id: str
    direction: str  # "profit_to_uc" or "uc_to_margin"
    amount_usd: float
    amount_uc: float
    status: ConversionStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    marketplace_order_id: Optional[str] = None
    withdraw_tx_hash: Optional[str] = None
    error_message: Optional[str] = None


class ZendTradingBridge:
    """
    Bridge between Aria Trading and Zend payment system.
    
    Enables:
    - Converting trading profits to UC credits
    - Funding trading margin from Zend UC balance
    - Cross-service balance management
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        # Zend service URLs
        self.zend_wallet_url = os.getenv(
            "ZEND_WALLET_URL",
            "http://198.54.123.234:8580"
        )
        self.zend_marketplace_url = os.getenv(
            "ZEND_MARKETPLACE_URL",
            "http://198.54.123.234:8584"
        )
        self.credits_gateway_url = os.getenv(
            "FP_CREDITS_GATEWAY_URL",
            "https://fullpotential.ai/services/credits/api"
        )
        
        # API keys
        self.api_key = os.getenv("ZEND_API_KEY", "")
        
        # UC rate (1:1 with USD per protocol)
        self.uc_rate = 1.0
        
        # Active conversions
        self.active_conversions: Dict[str, ConversionOrder] = {}
        
        self._initialized = True
        logger.info("Zend Trading Bridge initialized")
    
    async def convert_profit_to_uc(
        self,
        user_id: str,
        amount_usd: float,
        source: str = "hyperliquid"
    ) -> Dict[str, Any]:
        """
        Convert trading profit to UC credits.
        
        Flow:
        1. Verify withdrawable balance on exchange
        2. Initiate withdrawal from Hyperliquid to user's wallet
        3. Create sell order on Zend Marketplace (USDT → UC)
        4. Credit UC upon P2P settlement
        
        Args:
            user_id: User requesting conversion
            amount_usd: Amount in USD to convert
            source: Source exchange
            
        Returns:
            Conversion order details
        """
        try:
            # Step 1: Verify trading balance
            from trading.hyperliquid_live import get_hyperliquid_client
            client = get_hyperliquid_client()
            
            if not client or not client.connected:
                return {"success": False, "error": "Trading not connected"}
            
            account = await client.get_account_state()
            withdrawable = float(account.get("marginSummary", {}).get("withdrawable", 0))
            
            if withdrawable < amount_usd:
                return {
                    "success": False,
                    "error": f"Insufficient withdrawable balance. Available: ${withdrawable:.2f}"
                }
            
            # Calculate UC amount (1:1 rate per protocol)
            amount_uc = amount_usd * self.uc_rate
            
            # Step 2: Create conversion order
            order_id = f"conv_{user_id}_{int(datetime.now().timestamp())}"
            order = ConversionOrder(
                id=order_id,
                user_id=user_id,
                direction="profit_to_uc",
                amount_usd=amount_usd,
                amount_uc=amount_uc,
                status=ConversionStatus.PENDING,
                created_at=datetime.now()
            )
            self.active_conversions[order_id] = order
            
            # Step 3: Initiate withdrawal from Hyperliquid
            # Note: This requires implementation of withdrawal functionality
            logger.info(f"Initiating withdrawal of ${amount_usd:.2f} for user {user_id}")
            order.status = ConversionStatus.WITHDRAWING
            
            # For now, simulate the withdrawal (actual implementation would call exchange API)
            # In production: result = await client.withdraw(amount_usd, destination_address)
            
            # Step 4: Create Zend Marketplace order
            marketplace_result = await self._create_marketplace_order(
                user_id=user_id,
                order_type="sell_usdt",
                amount_usdt=amount_usd,
                amount_uc=amount_uc
            )
            
            if not marketplace_result.get("success"):
                order.status = ConversionStatus.FAILED
                order.error_message = marketplace_result.get("error")
                return {
                    "success": False,
                    "error": f"Failed to create marketplace order: {marketplace_result.get('error')}"
                }
            
            order.marketplace_order_id = marketplace_result.get("order_id")
            order.status = ConversionStatus.IN_MARKETPLACE
            
            logger.info(f"Created conversion order {order_id}: ${amount_usd:.2f} → {amount_uc:.2f} UC")
            
            return {
                "success": True,
                "order_id": order_id,
                "amount_usd": amount_usd,
                "amount_uc": amount_uc,
                "status": order.status.value,
                "message": f"Converting ${amount_usd:.2f} to {amount_uc:.2f} UC. Settlement pending in marketplace.",
                "estimated_time": "1-24 hours (P2P settlement)"
            }
            
        except Exception as e:
            logger.error(f"Error in profit to UC conversion: {e}")
            return {"success": False, "error": str(e)}
    
    async def fund_trading_from_zend(
        self,
        user_id: str,
        amount_uc: float
    ) -> Dict[str, Any]:
        """
        Fund trading margin from Zend UC balance.
        
        Flow:
        1. Check Zend UC balance
        2. Create buy order on Zend Marketplace (UC → USDT)
        3. After settlement, deposit USDT to Hyperliquid
        
        Args:
            user_id: User requesting funding
            amount_uc: Amount in UC to convert to trading margin
            
        Returns:
            Funding order details
        """
        try:
            # Step 1: Check Zend balance
            zend_balance = await self._get_zend_balance(user_id)
            
            if zend_balance < amount_uc:
                return {
                    "success": False,
                    "error": f"Insufficient UC balance. Available: {zend_balance:.2f} UC"
                }
            
            # Calculate USD amount (1:1 rate)
            amount_usd = amount_uc / self.uc_rate
            
            # Step 2: Create conversion order
            order_id = f"fund_{user_id}_{int(datetime.now().timestamp())}"
            order = ConversionOrder(
                id=order_id,
                user_id=user_id,
                direction="uc_to_margin",
                amount_usd=amount_usd,
                amount_uc=amount_uc,
                status=ConversionStatus.PENDING,
                created_at=datetime.now()
            )
            self.active_conversions[order_id] = order
            
            # Step 3: Debit UC from user's balance
            debit_result = await self._debit_uc(user_id, amount_uc, f"Trading margin funding: {order_id}")
            
            if not debit_result.get("success"):
                order.status = ConversionStatus.FAILED
                order.error_message = debit_result.get("error")
                return {
                    "success": False,
                    "error": f"Failed to debit UC: {debit_result.get('error')}"
                }
            
            # Step 4: Create marketplace order (UC → USDT)
            marketplace_result = await self._create_marketplace_order(
                user_id=user_id,
                order_type="buy_usdt",
                amount_usdt=amount_usd,
                amount_uc=amount_uc
            )
            
            if not marketplace_result.get("success"):
                # Refund UC
                await self._credit_uc(user_id, amount_uc, f"Refund: Failed funding {order_id}")
                order.status = ConversionStatus.FAILED
                order.error_message = marketplace_result.get("error")
                return {
                    "success": False,
                    "error": f"Failed to create marketplace order: {marketplace_result.get('error')}"
                }
            
            order.marketplace_order_id = marketplace_result.get("order_id")
            order.status = ConversionStatus.IN_MARKETPLACE
            
            logger.info(f"Created funding order {order_id}: {amount_uc:.2f} UC → ${amount_usd:.2f}")
            
            return {
                "success": True,
                "order_id": order_id,
                "amount_uc": amount_uc,
                "amount_usd": amount_usd,
                "status": order.status.value,
                "message": f"Funding trading with {amount_uc:.2f} UC (${amount_usd:.2f}). Settlement pending.",
                "estimated_time": "1-24 hours (P2P settlement)"
            }
            
        except Exception as e:
            logger.error(f"Error in UC to margin funding: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_conversion_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a conversion order."""
        order = self.active_conversions.get(order_id)
        
        if not order:
            return None
        
        return {
            "order_id": order.id,
            "user_id": order.user_id,
            "direction": order.direction,
            "amount_usd": order.amount_usd,
            "amount_uc": order.amount_uc,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "completed_at": order.completed_at.isoformat() if order.completed_at else None,
            "marketplace_order_id": order.marketplace_order_id,
            "error": order.error_message
        }
    
    async def get_user_conversions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all conversions for a user."""
        user_orders = [
            await self.get_conversion_status(order_id)
            for order_id, order in self.active_conversions.items()
            if order.user_id == user_id
        ]
        return [o for o in user_orders if o is not None]
    
    async def check_pending_conversions(self):
        """Check and update status of pending conversions."""
        for order_id, order in list(self.active_conversions.items()):
            if order.status in (ConversionStatus.WITHDRAWING, ConversionStatus.IN_MARKETPLACE):
                # Check marketplace order status
                if order.marketplace_order_id:
                    status = await self._check_marketplace_order(order.marketplace_order_id)
                    
                    if status.get("completed"):
                        order.status = ConversionStatus.COMPLETED
                        order.completed_at = datetime.now()
                        
                        # If funding trading, deposit to exchange
                        if order.direction == "uc_to_margin":
                            await self._deposit_to_exchange(order.user_id, order.amount_usd)
                        
                        # If converting profit, credit UC
                        elif order.direction == "profit_to_uc":
                            await self._credit_uc(
                                order.user_id, 
                                order.amount_uc,
                                f"Trading profit conversion: {order_id}"
                            )
                        
                        logger.info(f"Conversion {order_id} completed")
    
    # =========================================================================
    # Private helper methods
    # =========================================================================
    
    async def _get_zend_balance(self, user_id: str) -> float:
        """Get user's Zend UC balance."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.zend_wallet_url}/api/zend/wallet/{user_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if response.status_code == 200:
                    return response.json().get("balance", 0)
        except Exception as e:
            logger.warning(f"Failed to get Zend balance: {e}")
        
        # Fallback to credits gateway
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.credits_gateway_url}/balance/{user_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if response.status_code == 200:
                    return response.json().get("balance", 0)
        except Exception:
            pass
        
        return 0
    
    async def _create_marketplace_order(
        self,
        user_id: str,
        order_type: str,
        amount_usdt: float,
        amount_uc: float
    ) -> Dict[str, Any]:
        """Create a marketplace order."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.zend_marketplace_url}/api/marketplace/orders",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "member_id": user_id,
                        "order_type": order_type,
                        "amount_usdt": amount_usdt,
                        "amount_uc": amount_uc,
                        "source": "trading_bridge"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "order_id": data.get("order_id")
                    }
                
                return {
                    "success": False,
                    "error": f"Marketplace returned {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Failed to create marketplace order: {e}")
            return {"success": False, "error": str(e)}
    
    async def _check_marketplace_order(self, order_id: str) -> Dict[str, Any]:
        """Check status of a marketplace order."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.zend_marketplace_url}/api/marketplace/orders/{order_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": data.get("status"),
                        "completed": data.get("status") == "completed"
                    }
                    
        except Exception as e:
            logger.warning(f"Failed to check marketplace order: {e}")
        
        return {"status": "unknown", "completed": False}
    
    async def _debit_uc(self, user_id: str, amount: float, description: str) -> Dict[str, Any]:
        """Debit UC from user's balance."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.credits_gateway_url}/debit",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "user_id": user_id,
                        "amount": amount,
                        "description": description,
                        "source": "trading_bridge"
                    }
                )
                
                if response.status_code == 200:
                    return {"success": True}
                
                return {"success": False, "error": f"Gateway returned {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Failed to debit UC: {e}")
            return {"success": False, "error": str(e)}
    
    async def _credit_uc(self, user_id: str, amount: float, description: str) -> Dict[str, Any]:
        """Credit UC to user's balance."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.credits_gateway_url}/credit",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "user_id": user_id,
                        "amount": amount,
                        "description": description,
                        "source": "trading_bridge"
                    }
                )
                
                if response.status_code == 200:
                    return {"success": True}
                
                return {"success": False, "error": f"Gateway returned {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Failed to credit UC: {e}")
            return {"success": False, "error": str(e)}
    
    async def _deposit_to_exchange(self, user_id: str, amount_usd: float) -> Dict[str, Any]:
        """Deposit to exchange after marketplace settlement."""
        # This would be implemented when we have deposit functionality
        # For now, log the intent
        logger.info(f"Pending deposit to exchange for {user_id}: ${amount_usd:.2f}")
        return {"success": True, "pending": True}


# Singleton instance
_bridge: Optional[ZendTradingBridge] = None


def get_zend_trading_bridge() -> ZendTradingBridge:
    """Get the singleton bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = ZendTradingBridge()
    return _bridge


async def convert_profit_to_uc(user_id: str, amount_usd: float) -> Dict[str, Any]:
    """Convert trading profit to UC credits."""
    return await get_zend_trading_bridge().convert_profit_to_uc(user_id, amount_usd)


async def fund_trading_from_zend(user_id: str, amount_uc: float) -> Dict[str, Any]:
    """Fund trading margin from Zend UC balance."""
    return await get_zend_trading_bridge().fund_trading_from_zend(user_id, amount_uc)









