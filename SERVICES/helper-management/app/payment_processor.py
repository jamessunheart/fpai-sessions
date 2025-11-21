"""Payment processing for crypto and fiat"""

from web3 import Web3
from typing import Optional, Dict, Any
import httpx

from .config import settings
from .models import PaymentMethod


class PaymentProcessor:
    """Process payments to helpers"""

    def __init__(self):
        """Initialize payment providers"""
        # Web3 for crypto payments
        if settings.crypto_wallet_address and settings.web3_provider_url:
            self.w3 = Web3(Web3.HTTPProvider(settings.web3_provider_url))
        else:
            self.w3 = None

    async def process_payment(
        self,
        amount: float,
        recipient: str,
        payment_method: PaymentMethod,
        currency: str = "USD",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process payment to helper.

        Returns:
        {
            "success": True,
            "transaction_id": "0xabc...",
            "amount": 50.0,
            "fee": 0.5,
            "total": 50.5
        }
        """
        if payment_method == PaymentMethod.CRYPTO:
            return await self._process_crypto_payment(amount, recipient, currency)
        elif payment_method == PaymentMethod.UPWORK:
            return await self._process_upwork_payment(amount, recipient, metadata)
        elif payment_method == PaymentMethod.PAYPAL:
            return await self._process_paypal_payment(amount, recipient)
        else:
            return {
                "success": False,
                "error": f"Unsupported payment method: {payment_method}"
            }

    async def _process_crypto_payment(
        self,
        amount: float,
        wallet_address: str,
        currency: str = "USDC"
    ) -> Dict[str, Any]:
        """
        Send crypto payment (USDC, BTC, ETH).

        For USDC on Ethereum mainnet.
        """
        if not self.w3:
            return {"success": False, "error": "Web3 not configured"}

        try:
            # USDC contract on Ethereum (example)
            usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

            # Convert USD amount to USDC (1:1, but in wei)
            usdc_amount = int(amount * 1e6)  # USDC has 6 decimals

            # Estimate gas
            gas_estimate = 100000  # Standard ERC20 transfer

            # Build transaction
            # (Simplified - production would use proper contract interaction)
            transaction = {
                'from': settings.crypto_wallet_address,
                'to': wallet_address,
                'value': usdc_amount,
                'gas': gas_estimate,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(settings.crypto_wallet_address),
            }

            # Sign transaction
            # (In production, use hardware wallet or secure key management)
            # signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)

            # Send transaction
            # tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # For now, return simulated response
            return {
                "success": True,
                "transaction_id": "0xabc123...",  # Simulated
                "amount": amount,
                "currency": currency,
                "fee": 0.50,  # Gas fees
                "total": amount + 0.50,
                "network": "ethereum",
                "confirmation_time": "10-30 seconds"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Crypto payment failed: {str(e)}"
            }

    async def _process_upwork_payment(
        self,
        amount: float,
        helper_id: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Release escrow payment via Upwork.

        Uses Upwork API to release funds.
        """
        if not settings.upwork_api_key:
            return {"success": False, "error": "Upwork API not configured"}

        try:
            # Upwork API endpoint (example)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.upwork.com/api/hr/v2/contracts/payments",
                    headers={
                        "Authorization": f"Bearer {settings.upwork_api_key}"
                    },
                    json={
                        "amount": amount,
                        "helper_id": helper_id,
                        "memo": metadata.get("memo", "Task completed")
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "transaction_id": data.get("payment_id"),
                        "amount": amount,
                        "currency": "USD",
                        "fee": amount * 0.03,  # Upwork 3% fee
                        "total": amount * 1.03,
                        "platform": "upwork"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Upwork payment failed: {response.status_code}"
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"Upwork payment error: {str(e)}"
            }

    async def _process_paypal_payment(
        self,
        amount: float,
        email: str
    ) -> Dict[str, Any]:
        """Send PayPal payment"""
        # Placeholder for PayPal integration
        return {
            "success": False,
            "error": "PayPal integration not implemented"
        }

    def estimate_payment_cost(
        self,
        amount: float,
        payment_method: PaymentMethod
    ) -> Dict[str, Any]:
        """
        Estimate total cost including fees.

        Returns:
        {
            "amount": 50.0,
            "fee": 1.5,
            "total": 51.5,
            "fee_percentage": 3.0
        }
        """
        if payment_method == PaymentMethod.CRYPTO:
            fee = 0.50  # Flat gas fee estimate
            fee_pct = (fee / amount) * 100 if amount > 0 else 0
        elif payment_method == PaymentMethod.UPWORK:
            fee = amount * 0.03  # 3%
            fee_pct = 3.0
        elif payment_method == PaymentMethod.PAYPAL:
            fee = amount * 0.029 + 0.30  # 2.9% + $0.30
            fee_pct = 2.9
        else:
            fee = 0
            fee_pct = 0

        return {
            "amount": amount,
            "fee": round(fee, 2),
            "total": round(amount + fee, 2),
            "fee_percentage": fee_pct
        }


# Global instance
payment_processor = PaymentProcessor()
