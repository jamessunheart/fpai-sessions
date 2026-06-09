"""
TON blockchain client for wallet operations.
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlencode

import httpx

from app.config import settings


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TonClient:
    """
    Client for TON blockchain operations.
    Handles balance queries, transfer generation, and transaction verification.
    """

    def __init__(self):
        self.rpc_url = settings.ton_rpc_url
        self.api_key = settings.ton_api_key
        self.usdt_master = settings.usdt_jetton_master
        self.network = settings.ton_network

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def get_ton_balance(self, address: str) -> float:
        """Get native TON balance for an address."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use toncenter API
                url = f"https://toncenter.com/api/v2/getAddressBalance"
                params = {"address": address}
                if self.api_key:
                    params["api_key"] = self.api_key

                r = await client.get(url, params=params)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("ok"):
                        # Balance is in nanoTON (10^-9)
                        balance_nano = int(data.get("result", 0))
                        return balance_nano / 1e9
        except Exception as e:
            print(f"TON balance error: {e}")
        return 0.0

    async def get_usdt_balance(self, address: str) -> float:
        """Get USDT (Jetton) balance for an address."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use toncenter jetton API
                url = f"https://toncenter.com/api/v2/getJettonWalletBalance"
                params = {
                    "address": address,
                    "jetton_master": self.usdt_master
                }
                if self.api_key:
                    params["api_key"] = self.api_key

                r = await client.get(url, params=params)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("ok"):
                        # USDT has 6 decimals
                        balance_raw = int(data.get("result", 0))
                        return balance_raw / 1e6
        except Exception as e:
            print(f"USDT balance error: {e}")
        return 0.0

    async def get_all_balances(self, address: str) -> Dict[str, float]:
        """Get all balances for an address."""
        ton = await self.get_ton_balance(address)
        usdt = await self.get_usdt_balance(address)
        return {
            "TON": round(ton, 4),
            "USDT": round(usdt, 2)
        }

    def generate_transfer_deep_link(
        self,
        to_address: str,
        amount_usdt: float,
        comment: str = ""
    ) -> Tuple[str, str]:
        """
        Generate a TON transfer deep link for USDT.

        Returns (deep_link_url, qr_data)
        """
        # For USDT transfers, we need to use Jetton transfer format
        # Amount in smallest units (6 decimals for USDT)
        amount_raw = int(amount_usdt * 1e6)

        # Build transfer URL
        # Format: ton://transfer/<address>?amount=<nanotons>&text=<comment>&jetton=<jetton_master>
        params = {
            "jetton": self.usdt_master,
            "amount": str(amount_raw),
        }
        if comment:
            params["text"] = comment

        # Deep link format
        deep_link = f"ton://transfer/{to_address}?" + urlencode(params)

        # QR data is same as deep link
        qr_data = deep_link

        return deep_link, qr_data

    async def verify_transaction(
        self,
        tx_hash: str,
        expected_amount: Optional[float] = None,
        expected_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a TON transaction on-chain.

        Returns verification result with transaction details.
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Query transaction by hash
                url = "https://toncenter.com/api/v2/getTransactions"
                params = {
                    "hash": tx_hash,
                    "limit": 1
                }
                if self.api_key:
                    params["api_key"] = self.api_key

                r = await client.get(url, params=params)
                if r.status_code != 200:
                    return {
                        "verified": False,
                        "error": f"API error: {r.status_code}"
                    }

                data = r.json()
                if not data.get("ok") or not data.get("result"):
                    return {
                        "verified": False,
                        "error": "Transaction not found"
                    }

                tx = data["result"][0]

                # Extract transaction details
                from_addr = tx.get("in_msg", {}).get("source", "")
                to_addr = tx.get("in_msg", {}).get("destination", "")
                value = int(tx.get("in_msg", {}).get("value", 0))
                comment = tx.get("in_msg", {}).get("message", "")
                utime = tx.get("utime", 0)

                # For Jetton transfers, we need to parse the message
                # This is simplified - production would parse Jetton transfer payload
                amount_usdt = value / 1e6  # Assuming USDT decimals

                # Verification checks
                verified = True
                if expected_amount and abs(amount_usdt - expected_amount) > 0.01:
                    verified = False
                if expected_to and to_addr.lower() != expected_to.lower():
                    verified = False

                return {
                    "verified": verified,
                    "tx_hash": tx_hash,
                    "amount_usdt": amount_usdt,
                    "from_address": from_addr,
                    "to_address": to_addr,
                    "comment": comment,
                    "confirmed_at": datetime.fromtimestamp(utime, tz=timezone.utc).isoformat() if utime else None,
                    "block_height": tx.get("block_id", {}).get("seqno")
                }

        except Exception as e:
            return {
                "verified": False,
                "error": str(e)
            }

    async def get_address_transactions(
        self,
        address: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent transactions for an address."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://toncenter.com/api/v2/getTransactions"
                params = {
                    "address": address,
                    "limit": limit
                }
                if self.api_key:
                    params["api_key"] = self.api_key

                r = await client.get(url, params=params)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("ok"):
                        return data.get("result", [])
        except Exception as e:
            print(f"Get transactions error: {e}")
        return []


# Singleton
_ton_client: Optional[TonClient] = None


def get_ton_client() -> TonClient:
    global _ton_client
    if _ton_client is None:
        _ton_client = TonClient()
    return _ton_client




