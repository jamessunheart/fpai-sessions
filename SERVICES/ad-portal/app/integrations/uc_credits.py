"""
UC Credits Gateway Integration

Interface with the Universal Credits system for crypto payments.
UC Credits Gateway runs on primary server at port 8765.
"""
import httpx
from typing import Dict, List, Optional
from datetime import datetime
from app.config import settings


class UCCreditsClient:
    """
    Client for UC Credits Gateway
    
    Used for:
    - Checking UC balances
    - Processing UC payments
    - Fetching UC transactions for reconciliation
    """
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.UC_GATEWAY_URL
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make request to UC Gateway"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = await self.client.get(url, params=params)
            elif method == "POST":
                response = await self.client.post(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            raise UCCreditsError(
                message=error_data.get("error", str(e)),
                status_code=e.response.status_code
            )
        except httpx.RequestError as e:
            raise UCCreditsError(f"Connection error: {str(e)}")
    
    async def get_balance(self, user_id: str) -> Dict:
        """
        Get UC balance for a user
        
        Returns:
            Dict with balance_uc and balance_usd (1:1)
        """
        result = await self._request("GET", f"/api/balance/{user_id}")
        return {
            "user_id": user_id,
            "balance_uc": result.get("balance", 0),
            "balance_usd": result.get("balance", 0)  # 1 UC = $1 USD
        }
    
    async def create_payment(
        self,
        user_id: str,
        amount_uc: float,
        offer_id: str,
        campaign_id: str = None,
        metadata: Dict = None
    ) -> Dict:
        """
        Process UC payment for an offer
        
        Args:
            user_id: User making payment
            amount_uc: Amount in UC (= USD)
            offer_id: Offer being purchased
            campaign_id: Campaign for attribution
            metadata: Additional tracking data (UTM, fbclid, etc.)
            
        Returns:
            Transaction details
        """
        payment_data = {
            "user_id": user_id,
            "amount": amount_uc,
            "type": "purchase",
            "product_id": offer_id,
            "description": f"Ad Portal Purchase - Offer {offer_id}",
            "metadata": {
                "source": "ad_portal",
                "campaign_id": campaign_id,
                **(metadata or {})
            }
        }
        
        result = await self._request("POST", "/api/transactions/create", data=payment_data)
        
        return {
            "transaction_id": result.get("id"),
            "amount_uc": amount_uc,
            "amount_usd": amount_uc,  # 1:1
            "status": result.get("status", "completed"),
            "user_id": user_id,
            "offer_id": offer_id,
            "metadata": payment_data["metadata"]
        }
    
    async def get_transactions(
        self,
        since: datetime = None,
        product_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get UC transactions for reconciliation
        
        Args:
            since: Get transactions after this time
            product_id: Filter by product/offer ID
            limit: Max results
            
        Returns:
            List of transactions
        """
        params = {"limit": limit, "type": "purchase"}
        
        if since:
            params["since"] = since.isoformat()
        if product_id:
            params["product_id"] = product_id
        
        result = await self._request("GET", "/api/transactions", params=params)
        
        transactions = result.get("transactions", [])
        
        return [
            {
                "transaction_id": t.get("id"),
                "user_id": t.get("user_id"),
                "amount_uc": t.get("amount", 0),
                "amount_usd": t.get("amount", 0),  # 1:1
                "product_id": t.get("product_id"),
                "status": t.get("status"),
                "metadata": t.get("metadata", {}),
                "created_at": t.get("created_at")
            }
            for t in transactions
        ]
    
    async def get_exchange_rates(self) -> Dict:
        """
        Get current UC exchange rates
        
        Per UC Protocol: 1 UC = $1 USD (fixed)
        """
        # UC is fixed at 1:1 with USD
        return {
            "UC_USD": 1.0,
            "USD_UC": 1.0,
            "protocol_phase": "anchor",  # Anchor phase = fixed 1:1
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def verify_payment(self, transaction_id: str) -> Dict:
        """
        Verify a UC payment was successful
        
        Args:
            transaction_id: Transaction to verify
            
        Returns:
            Transaction details with verification status
        """
        result = await self._request("GET", f"/api/transactions/{transaction_id}")
        
        return {
            "transaction_id": transaction_id,
            "verified": result.get("status") == "completed",
            "amount_uc": result.get("amount", 0),
            "amount_usd": result.get("amount", 0),
            "status": result.get("status"),
            "product_id": result.get("product_id"),
            "metadata": result.get("metadata", {})
        }
    
    async def health_check(self) -> bool:
        """Check if UC Gateway is healthy"""
        try:
            result = await self._request("GET", "/health")
            return result.get("status") == "healthy"
        except:
            return False


class UCCreditsError(Exception):
    """Custom exception for UC Credits errors"""
    
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


