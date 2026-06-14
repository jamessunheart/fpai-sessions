"""Solana USDC connector for Zend Payments.

Per docs/protocols/ZEND_REGENERATIVE_SPEC.md Part 7.2:
- Mode: Wallet-signed payment request
- Flow: Generate payment request → user signs in wallet → verify tx signature
"""
import logging
import json
import base64
from typing import Optional, Dict, Any
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)


class SolanaConnector:
    """Solana USDC payment request connector."""

    def __init__(self):
        self.enabled = settings.SOLANA_ENABLED
        self.rpc_url = settings.SOLANA_RPC_URL
        self.usdc_mint = settings.SOLANA_USDC_MINT

    async def create_payment_request(
        self,
        intent_id: str,
        amount: float,
        recipient_wallet: str,
        note: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Solana Pay payment request URL.
        Returns payment request URL (can be encoded as QR).
        """
        if not self.enabled:
            return None

        if not recipient_wallet:
            logger.warning("No recipient wallet provided for Solana payment")
            return None

        try:
            # Convert amount to USDC (6 decimals)
            usdc_amount = amount  # USDC uses 6 decimals, but Solana Pay handles this

            # Build Solana Pay URL
            # Format: solana:<recipient>?amount=<amount>&spl-token=<mint>&reference=<ref>&label=<label>&message=<message>
            reference = intent_id  # Use intent_id as reference for tracking

            params = [
                f"amount={usdc_amount}",
                f"spl-token={self.usdc_mint}",
                f"reference={reference}",
                f"label=Zend%20Money",
            ]

            if note:
                # URL encode the note
                encoded_note = note.replace(" ", "%20").replace("&", "%26")
                params.append(f"message={encoded_note}")

            payment_url = f"solana:{recipient_wallet}?{'&'.join(params)}"

            return {
                "payment_request": payment_url,
                "recipient_wallet": recipient_wallet,
                "amount_usdc": usdc_amount,
                "reference": reference,
            }

        except Exception as e:
            logger.error(f"Solana payment request creation failed: {e}")
            return None

    async def verify_transaction(self, tx_signature: str, expected_amount: float, expected_recipient: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Solana transaction signature.
        Returns transaction details if valid.
        """
        if not self.enabled:
            return None

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                # Get transaction details from RPC
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [
                        tx_signature,
                        {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
                    ]
                }

                resp = await client.post(self.rpc_url, json=payload, timeout=10.0)
                if resp.status_code != 200:
                    return None

                result = resp.json().get("result")
                if not result:
                    return None

                # Parse transaction for USDC transfer
                # This is simplified - production would need full SPL token parsing
                meta = result.get("meta", {})
                if meta.get("err"):
                    return {"status": "failed", "error": str(meta["err"])}

                return {
                    "status": "confirmed",
                    "tx_signature": tx_signature,
                    "block_time": result.get("blockTime"),
                    "slot": result.get("slot"),
                }

        except Exception as e:
            logger.error(f"Solana transaction verification failed: {e}")
            return None

    async def get_wallet_balance(self, wallet_address: str) -> Optional[float]:
        """Get USDC balance for a wallet."""
        if not self.enabled:
            return None

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                # Get token accounts
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        wallet_address,
                        {"mint": self.usdc_mint},
                        {"encoding": "jsonParsed"}
                    ]
                }

                resp = await client.post(self.rpc_url, json=payload, timeout=10.0)
                if resp.status_code != 200:
                    return None

                result = resp.json().get("result", {}).get("value", [])
                if not result:
                    return 0.0

                # Sum USDC balance across all token accounts
                total = 0.0
                for account in result:
                    parsed = account.get("account", {}).get("data", {}).get("parsed", {})
                    info = parsed.get("info", {})
                    token_amount = info.get("tokenAmount", {})
                    total += float(token_amount.get("uiAmount", 0))

                return total

        except Exception as e:
            logger.error(f"Solana balance fetch failed: {e}")
            return None


# Singleton
solana_connector = SolanaConnector()




