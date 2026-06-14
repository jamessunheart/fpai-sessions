"""
Autonomy Optimizer Integration Adapter
Bridges the contributor credits system to the unified FP Credits Gateway.

This adapter allows the Autonomy Optimizer's contributor rewards system
to use the gateway while maintaining its existing interface.

Usage:
    from integrations.autonomy_adapter import ContributorCreditsAdapter
    
    credits = ContributorCreditsAdapter()
    
    # Same interface as the original credit_ledger
    credits.award_credits("contributor_123", 100, "API key used")
"""

import os
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CreditRate:
    """Credit earning rates for different contributions."""
    API_CALL_SUCCESS = 1
    API_CALL_CACHED = 0.1
    SERVER_TASK_COMPLETE = 10
    SERVER_HOUR_ACTIVE = 2
    SERVER_UPTIME_BONUS = 5
    GPU_HOUR = 100
    GPU_TRAINING_JOB = 500
    FIRST_CONTRIBUTION = 100
    REFERRAL_BONUS = 50
    STREAK_BONUS = 10
    VALIDATION_BONUS = 25


@dataclass
class RedemptionCost:
    """Credit costs for services."""
    AI_CHAT_SESSION = 100
    AI_CODE_REVIEW = 200
    AI_DOCUMENT_ANALYSIS = 150
    PRIORITY_QUEUE = 500
    DEDICATED_SUPPORT = 1000
    CUSTOM_INTEGRATION = 2000
    WHITE_LABEL = 5000
    REVENUE_SHARE = 10000


class ContributorCreditsAdapter:
    """
    Adapter that bridges Autonomy Optimizer's CreditLedger to FP Credits Gateway.
    
    Provides the same interface as the original CreditLedger but routes
    operations through the unified gateway.
    """
    
    def __init__(
        self,
        gateway_url: str = None,
        api_key: str = None
    ):
        self.gateway_url = gateway_url or os.environ.get(
            "FP_CREDITS_GATEWAY_URL",
            "http://198.54.123.234:8760"
        )
        self.api_key = api_key or os.environ.get("FP_CREDITS_API_KEY")
        self._client = httpx.AsyncClient(
            base_url=self.gateway_url,
            headers={"X-API-Key": self.api_key} if self.api_key else {},
            timeout=10.0
        )
    
    def _contributor_account_id(self, contributor_id: str) -> str:
        """Convert contributor ID to gateway account ID"""
        return f"autonomy:contributor:{contributor_id}"
    
    async def get_or_create_account(
        self,
        contributor_id: str,
        display_name: str = None,
        referred_by: str = None
    ) -> Dict[str, Any]:
        """Get existing account or create new one with welcome bonus"""
        account_id = self._contributor_account_id(contributor_id)
        
        try:
            # Check if account exists
            response = await self._client.get(f"/api/balance/{account_id}")
            data = response.json()
            
            if not data.get("exists", False):
                # New account - award welcome bonus
                await self.award_credits(
                    contributor_id=contributor_id,
                    amount=CreditRate.FIRST_CONTRIBUTION,
                    reason="Welcome bonus for first contribution!"
                )
                
                # Award referral bonus if applicable
                if referred_by:
                    await self.award_credits(
                        contributor_id=referred_by,
                        amount=CreditRate.REFERRAL_BONUS,
                        reason=f"Referral bonus: {display_name or contributor_id} joined"
                    )
            
            return await self.get_account_summary(contributor_id)
        except Exception as e:
            print(f"[AutonomyAdapter] Error: {e}")
            return {"contributor_id": contributor_id, "balance": 0}
    
    async def award_credits(
        self,
        contributor_id: str,
        amount: float,
        reason: str,
        resource_id: str = None
    ) -> Dict[str, Any]:
        """Award credits to a contributor"""
        try:
            account_id = self._contributor_account_id(contributor_id)
            response = await self._client.post("/api/credit", json={
                "account_id": account_id,
                "amount": amount,
                "credit_type": "fp_credits",
                "reason": reason,
                "reference_id": resource_id,
                "metadata": {
                    "source": "autonomy-optimizer",
                    "contributor_id": contributor_id,
                    "resource_id": resource_id
                }
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[AutonomyAdapter] Award failed: {e}")
            raise
    
    async def spend_credits(
        self,
        contributor_id: str,
        amount: float,
        reason: str
    ) -> tuple:
        """Spend credits from a contributor's balance"""
        try:
            account_id = self._contributor_account_id(contributor_id)
            
            # Check balance first
            balance_response = await self._client.get(f"/api/balance/{account_id}")
            balance_data = balance_response.json()
            current_balance = balance_data.get("balances", {}).get("fp_credits", 0)
            
            if current_balance < amount:
                return False, f"Insufficient credits. Balance: {current_balance}, Required: {amount}", None
            
            response = await self._client.post("/api/debit", json={
                "account_id": account_id,
                "amount": amount,
                "credit_type": "fp_credits",
                "reason": reason,
                "metadata": {
                    "source": "autonomy-optimizer",
                    "contributor_id": contributor_id
                }
            })
            response.raise_for_status()
            return True, "Credits redeemed successfully", response.json()
        except Exception as e:
            return False, str(e), None
    
    async def record_api_usage(
        self,
        contributor_id: str,
        key_id: str,
        calls: int = 1
    ):
        """Record API key usage and award credits"""
        credits = calls * CreditRate.API_CALL_SUCCESS
        await self.award_credits(
            contributor_id=contributor_id,
            amount=credits,
            reason=f"API key used {calls} time(s)",
            resource_id=key_id
        )
    
    async def record_task_completion(
        self,
        contributor_id: str,
        server_id: str,
        task_type: str = "standard"
    ):
        """Record server task completion and award credits"""
        await self.award_credits(
            contributor_id=contributor_id,
            amount=CreditRate.SERVER_TASK_COMPLETE,
            reason="Task completed on contributed server",
            resource_id=server_id
        )
    
    async def get_balance(self, contributor_id: str) -> float:
        """Get current credit balance"""
        try:
            account_id = self._contributor_account_id(contributor_id)
            response = await self._client.get(f"/api/balance/{account_id}")
            data = response.json()
            return data.get("balances", {}).get("fp_credits", 0.0)
        except:
            return 0.0
    
    async def get_account_summary(self, contributor_id: str) -> Optional[Dict]:
        """Get full account summary for a contributor"""
        try:
            account_id = self._contributor_account_id(contributor_id)
            
            # Get balance
            balance_response = await self._client.get(f"/api/balance/{account_id}")
            balance_data = balance_response.json()
            
            # Get transactions
            tx_response = await self._client.get(f"/api/transactions/{account_id}")
            tx_data = tx_response.json()
            
            balance = balance_data.get("balances", {}).get("fp_credits", 0.0)
            
            return {
                "contributor_id": contributor_id,
                "account_id": account_id,
                "balance": balance,
                "recent_transactions": tx_data.get("transactions", [])[:20],
                "available_redemptions": self._get_available_redemptions(balance)
            }
        except Exception as e:
            print(f"[AutonomyAdapter] Get summary failed: {e}")
            return None
    
    def _get_available_redemptions(self, balance: float) -> List[Dict]:
        """Get list of services the user can afford"""
        redemptions = [
            {"name": "AI Chat Session", "cost": RedemptionCost.AI_CHAT_SESSION, "description": "One-on-one AI assistant session"},
            {"name": "AI Document Analysis", "cost": RedemptionCost.AI_DOCUMENT_ANALYSIS, "description": "AI analyzes your documents"},
            {"name": "AI Code Review", "cost": RedemptionCost.AI_CODE_REVIEW, "description": "AI reviews your code"},
            {"name": "Priority Queue", "cost": RedemptionCost.PRIORITY_QUEUE, "description": "Skip to front of queue"},
            {"name": "Dedicated Support", "cost": RedemptionCost.DEDICATED_SUPPORT, "description": "Human + AI support team"},
            {"name": "Custom Integration", "cost": RedemptionCost.CUSTOM_INTEGRATION, "description": "Custom API integration"},
            {"name": "White Label", "cost": RedemptionCost.WHITE_LABEL, "description": "White-label a Full Potential service"},
            {"name": "Revenue Share", "cost": RedemptionCost.REVENUE_SHARE, "description": "Unlock revenue sharing tier"},
        ]
        
        for r in redemptions:
            r["affordable"] = balance >= r["cost"]
        
        return redemptions
    
    async def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top contributors by balance"""
        # This would require a gateway endpoint for leaderboards
        # For now, return empty list
        return []
    
    async def get_economy_stats(self) -> Dict:
        """Get overall economy statistics"""
        try:
            response = await self._client.get("/api/stats")
            return response.json()
        except:
            return {}
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()


# ============================================================
# HELPER FUNCTIONS (Same interface as original)
# ============================================================

_adapter: Optional[ContributorCreditsAdapter] = None

def get_adapter() -> ContributorCreditsAdapter:
    global _adapter
    if _adapter is None:
        _adapter = ContributorCreditsAdapter()
    return _adapter


async def on_key_contributed(contributor_id: str, key_id: str, provider: str):
    """Called when a new API key is contributed"""
    adapter = get_adapter()
    await adapter.get_or_create_account(contributor_id)
    await adapter.award_credits(
        contributor_id=contributor_id,
        amount=CreditRate.VALIDATION_BONUS,
        reason=f"Contributed {provider} API key",
        resource_id=key_id
    )


async def on_key_used(contributor_id: str, key_id: str, calls: int = 1):
    """Called when a contributed API key is used"""
    adapter = get_adapter()
    await adapter.record_api_usage(contributor_id, key_id, calls)


async def on_server_contributed(contributor_id: str, server_id: str):
    """Called when a server is contributed"""
    adapter = get_adapter()
    await adapter.get_or_create_account(contributor_id)
    await adapter.award_credits(
        contributor_id=contributor_id,
        amount=CreditRate.VALIDATION_BONUS,
        reason="Contributed server resource",
        resource_id=server_id
    )


async def on_task_completed(contributor_id: str, server_id: str):
    """Called when a task completes on a contributed server"""
    adapter = get_adapter()
    await adapter.record_task_completion(contributor_id, server_id)


