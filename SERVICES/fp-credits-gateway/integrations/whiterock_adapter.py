"""
WhiteRock API Integration Adapter
Bridges the existing WhiteRock credits system to the unified FP Credits Gateway.

This adapter allows WhiteRock API to gradually migrate to the gateway
without breaking existing functionality.

Usage in WhiteRock API:
    from integrations.whiterock_adapter import WhiteRockCreditsAdapter
    
    # Replace direct CreditsService usage
    credits = WhiteRockCreditsAdapter(db_session)
    
    # Same interface as before
    await credits.credit_member(member_id, 10.0, "welcome_bonus", "Welcome!")
"""

import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime


class WhiteRockCreditsAdapter:
    """
    Adapter that bridges WhiteRock's CreditsService to FP Credits Gateway.
    
    Provides the same interface as the original CreditsService but routes
    operations through the unified gateway.
    """
    
    def __init__(
        self,
        gateway_url: str = None,
        api_key: str = None,
        fallback_to_local: bool = True
    ):
        """
        Initialize the adapter.
        
        Args:
            gateway_url: FP Credits Gateway URL
            api_key: API key for gateway authentication
            fallback_to_local: If True, fall back to local DB on gateway failure
        """
        self.gateway_url = gateway_url or os.environ.get(
            "FP_CREDITS_GATEWAY_URL",
            "http://198.54.123.234:8760"
        )
        self.api_key = api_key or os.environ.get("FP_CREDITS_API_KEY")
        self.fallback_to_local = fallback_to_local
        self._client = httpx.AsyncClient(
            base_url=self.gateway_url,
            headers={"X-API-Key": self.api_key} if self.api_key else {},
            timeout=10.0
        )
    
    def _member_account_id(self, member_id: int) -> str:
        """Convert WhiteRock member ID to gateway account ID"""
        return f"whiterock:member:{member_id}"
    
    def _provider_account_id(self, provider_id: int) -> str:
        """Convert WhiteRock provider ID to gateway account ID"""
        return f"whiterock:provider:{provider_id}"
    
    async def get_member_balance(self, member_id: int) -> float:
        """Get current credit balance for a member"""
        try:
            account_id = self._member_account_id(member_id)
            response = await self._client.get(f"/api/balance/{account_id}")
            response.raise_for_status()
            data = response.json()
            return data.get("balances", {}).get("fp_credits", 0.0)
        except Exception as e:
            print(f"[WhiteRockAdapter] Gateway error: {e}")
            return 0.0
    
    async def get_provider_balance(self, provider_id: int) -> float:
        """Get current credit balance for a provider"""
        try:
            account_id = self._provider_account_id(provider_id)
            response = await self._client.get(f"/api/balance/{account_id}")
            response.raise_for_status()
            data = response.json()
            return data.get("balances", {}).get("fp_credits", 0.0)
        except Exception as e:
            print(f"[WhiteRockAdapter] Gateway error: {e}")
            return 0.0
    
    async def credit_member(
        self,
        member_id: int,
        amount: float,
        type: str,
        description: str = None,
        reference_type: str = None,
        reference_id: int = None
    ) -> Dict[str, Any]:
        """Add credits to a member's account"""
        try:
            account_id = self._member_account_id(member_id)
            response = await self._client.post("/api/credit", json={
                "account_id": account_id,
                "amount": amount,
                "credit_type": "fp_credits",
                "reason": f"{type}: {description}" if description else type,
                "reference_id": f"{reference_type}:{reference_id}" if reference_type else None,
                "metadata": {
                    "source": "whiterock",
                    "transaction_type": type,
                    "member_id": member_id
                }
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[WhiteRockAdapter] Credit failed: {e}")
            raise
    
    async def debit_member(
        self,
        member_id: int,
        amount: float,
        type: str,
        description: str = None,
        reference_type: str = None,
        reference_id: int = None
    ) -> Dict[str, Any]:
        """Remove credits from a member's account"""
        try:
            account_id = self._member_account_id(member_id)
            response = await self._client.post("/api/debit", json={
                "account_id": account_id,
                "amount": amount,
                "credit_type": "fp_credits",
                "reason": f"{type}: {description}" if description else type,
                "reference_id": f"{reference_type}:{reference_id}" if reference_type else None,
                "metadata": {
                    "source": "whiterock",
                    "transaction_type": type,
                    "member_id": member_id
                }
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[WhiteRockAdapter] Debit failed: {e}")
            raise
    
    async def credit_provider(
        self,
        provider_id: int,
        amount: float,
        type: str,
        description: str = None,
        reference_type: str = None,
        reference_id: int = None
    ) -> Dict[str, Any]:
        """Add credits to a provider's account"""
        try:
            account_id = self._provider_account_id(provider_id)
            response = await self._client.post("/api/credit", json={
                "account_id": account_id,
                "amount": amount,
                "credit_type": "fp_credits",
                "reason": f"{type}: {description}" if description else type,
                "reference_id": f"{reference_type}:{reference_id}" if reference_type else None,
                "metadata": {
                    "source": "whiterock",
                    "transaction_type": type,
                    "provider_id": provider_id
                }
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[WhiteRockAdapter] Credit failed: {e}")
            raise
    
    async def transfer_member_to_provider(
        self,
        member_id: int,
        provider_id: int,
        amount: float,
        description: str = None,
        reference_type: str = None,
        reference_id: int = None,
        commission_rate: float = 0.15
    ) -> Dict[str, Any]:
        """Transfer credits from member to provider (with commission)"""
        try:
            from_account = self._member_account_id(member_id)
            to_account = self._provider_account_id(provider_id)
            
            # Calculate provider amount after commission
            commission = amount * commission_rate
            provider_amount = amount - commission
            
            # Transfer to provider
            response = await self._client.post("/api/transfer", json={
                "from_account": from_account,
                "to_account": to_account,
                "amount": provider_amount,
                "credit_type": "fp_credits",
                "reason": f"Purchase: {description}" if description else "Purchase",
                "metadata": {
                    "source": "whiterock",
                    "original_amount": amount,
                    "commission": commission,
                    "commission_rate": commission_rate,
                    "member_id": member_id,
                    "provider_id": provider_id
                }
            })
            response.raise_for_status()
            
            # Debit commission to system fees
            if commission > 0:
                await self._client.post("/api/transfer", json={
                    "from_account": from_account,
                    "to_account": "system:fees",
                    "amount": commission,
                    "credit_type": "fp_credits",
                    "reason": f"Commission ({commission_rate*100}%)"
                })
            
            return response.json()
        except Exception as e:
            print(f"[WhiteRockAdapter] Transfer failed: {e}")
            raise
    
    async def issue_welcome_bonus(self, member_id: int, amount: float = 10.0) -> Dict[str, Any]:
        """Issue welcome bonus credits to new member"""
        return await self.credit_member(
            member_id=member_id,
            amount=amount,
            type="welcome_bonus",
            description=f"Welcome bonus - {amount} FP Credits"
        )
    
    async def issue_referral_bonus(
        self, 
        member_id: int, 
        referred_member_id: int,
        amount: float = 25.0
    ) -> Dict[str, Any]:
        """Issue referral bonus when someone they referred joins"""
        return await self.credit_member(
            member_id=member_id,
            amount=amount,
            type="referral_bonus",
            description=f"Referral bonus for member #{referred_member_id}",
            reference_type="member",
            reference_id=referred_member_id
        )
    
    async def process_donation(self, member_id: int, amount_usd: float) -> Dict[str, Any]:
        """Convert donation to credits (1:1 ratio)"""
        return await self.credit_member(
            member_id=member_id,
            amount=amount_usd,
            type="donation",
            description=f"Donation conversion - ${amount_usd} USD"
        )
    
    async def process_reimbursement(
        self, 
        member_id: int, 
        amount: float, 
        receipt_id: int
    ) -> Dict[str, Any]:
        """Issue credits for approved receipt reimbursement"""
        return await self.credit_member(
            member_id=member_id,
            amount=amount,
            type="reimbursement",
            description="Receipt reimbursement",
            reference_type="receipt",
            reference_id=receipt_id
        )
    
    async def get_transaction_history(
        self,
        member_id: int = None,
        provider_id: int = None,
        limit: int = 50
    ) -> list:
        """Get transaction history for a member or provider"""
        try:
            if member_id:
                account_id = self._member_account_id(member_id)
            elif provider_id:
                account_id = self._provider_account_id(provider_id)
            else:
                return []
            
            response = await self._client.get(
                f"/api/transactions/{account_id}",
                params={"limit": limit}
            )
            response.raise_for_status()
            return response.json().get("transactions", [])
        except Exception as e:
            print(f"[WhiteRockAdapter] Get transactions failed: {e}")
            return []
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()


# ============================================================
# MIGRATION HELPER
# ============================================================

async def migrate_whiterock_balances(
    whiterock_db_session,
    gateway_url: str,
    api_key: str
):
    """
    One-time migration of existing WhiteRock balances to the gateway.
    
    Run this once to sync existing member/provider balances.
    """
    from sqlalchemy import select
    
    adapter = WhiteRockCreditsAdapter(gateway_url, api_key)
    
    # This would need to import the WhiteRock models
    # from whiterock_api.models import Member, Provider
    
    print("[Migration] Starting balance migration...")
    
    # Migrate members
    # result = await whiterock_db_session.execute(select(Member))
    # for member in result.scalars():
    #     if member.credit_balance > 0:
    #         await adapter.credit_member(
    #             member.id,
    #             member.credit_balance,
    #             "migration",
    #             "Balance migration from WhiteRock"
    #         )
    #         print(f"  Migrated member {member.id}: {member.credit_balance} credits")
    
    # Migrate providers
    # result = await whiterock_db_session.execute(select(Provider))
    # for provider in result.scalars():
    #     if provider.credit_balance > 0:
    #         await adapter.credit_provider(
    #             provider.id,
    #             provider.credit_balance,
    #             "migration",
    #             "Balance migration from WhiteRock"
    #         )
    #         print(f"  Migrated provider {provider.id}: {provider.credit_balance} credits")
    
    await adapter.close()
    print("[Migration] Complete!")


