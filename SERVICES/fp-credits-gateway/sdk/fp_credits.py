"""
FP Credits SDK - Python Client Library
Easy integration for any service to use the FP Credits system.

Usage:
    from fp_credits import FPCredits
    
    # Initialize with your API key
    credits = FPCredits(api_key="fps_your_api_key_here")
    
    # Check balance
    balance = credits.get_balance("user:123")
    print(f"FP Credits: {balance.fp_credits}")
    
    # Debit credits for a service
    result = credits.debit("user:123", 10.0, "AI Chat Session")
    
    # Credit rewards
    credits.credit("user:123", 5.0, "Referral bonus")
"""

import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import os


class CreditType(str, Enum):
    FP_CREDITS = "fp_credits"
    CORA_CREDITS = "cora_credits"
    USD = "usd"


@dataclass
class Balance:
    """Account balance information"""
    account_id: str
    fp_credits: float = 0.0
    cora_credits: float = 0.0
    usd: float = 0.0
    
    @classmethod
    def from_response(cls, data: dict) -> "Balance":
        balances = data.get("balances", {})
        return cls(
            account_id=data.get("account_id", ""),
            fp_credits=balances.get("fp_credits", 0.0),
            cora_credits=balances.get("cora_credits", 0.0),
            usd=balances.get("usd", 0.0)
        )


@dataclass
class Transaction:
    """Transaction record"""
    transaction_id: str
    account_id: str
    type: str
    amount: float
    credit_type: str
    balance_after: float
    reason: str
    reference_id: Optional[str]
    created_at: str


class FPCreditsError(Exception):
    """Exception for FP Credits API errors"""
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class FPCredits:
    """
    FP Credits Python SDK Client
    
    Provides easy integration with the FP Credits Gateway for:
    - Balance checking
    - Credits/debits
    - Transfers
    - Currency exchange
    - Transaction history
    """
    
    # Default gateway URLs
    PRODUCTION_URL = "https://fullpotential.ai/services/credits"
    SERVER_URL = "http://198.54.123.234:8765"
    LOCAL_URL = "http://localhost:8765"
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        timeout: int = 30
    ):
        """
        Initialize the FP Credits client.
        
        Args:
            api_key: Your service API key (or set FP_CREDITS_API_KEY env var)
            base_url: Gateway URL (defaults to production)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.environ.get("FP_CREDITS_API_KEY")
        if not self.api_key:
            raise FPCreditsError("API key required. Set api_key or FP_CREDITS_API_KEY env var")
        
        self.base_url = (base_url or os.environ.get("FP_CREDITS_URL", self.SERVER_URL)).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request"""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)
        
        try:
            response = self._session.request(method, url, **kwargs)
            
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    message = error_data.get("detail", response.text)
                except:
                    message = response.text
                raise FPCreditsError(message, response.status_code)
            
            return response.json()
        except requests.RequestException as e:
            raise FPCreditsError(f"Request failed: {str(e)}")
    
    # ================================================================
    # BALANCE OPERATIONS
    # ================================================================
    
    def get_balance(self, account_id: str) -> Balance:
        """
        Get the current balance for an account.
        
        Args:
            account_id: The account identifier (e.g., "user:123", "service:myapp")
            
        Returns:
            Balance object with fp_credits, cora_credits, and usd
        """
        data = self._request("GET", f"/api/balance/{account_id}")
        return Balance.from_response(data)
    
    def has_sufficient_balance(
        self,
        account_id: str,
        amount: float,
        credit_type: CreditType = CreditType.FP_CREDITS
    ) -> bool:
        """
        Check if an account has sufficient balance.
        
        Args:
            account_id: The account identifier
            amount: Amount to check
            credit_type: Type of credits to check
            
        Returns:
            True if balance is sufficient
        """
        balance = self.get_balance(account_id)
        current = getattr(balance, credit_type.value.replace("_credits", "_credits"), 0)
        return current >= amount
    
    # ================================================================
    # CREDIT OPERATIONS
    # ================================================================
    
    def credit(
        self,
        account_id: str,
        amount: float,
        reason: str,
        credit_type: CreditType = CreditType.FP_CREDITS,
        reference_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Transaction:
        """
        Add credits to an account.
        
        Args:
            account_id: The account to credit
            amount: Amount to add (must be positive)
            reason: Description of why credits are being added
            credit_type: Type of credits
            reference_id: Optional reference (e.g., order ID)
            metadata: Optional additional data
            
        Returns:
            Transaction record
        """
        data = self._request("POST", "/api/credit", json={
            "account_id": account_id,
            "amount": amount,
            "credit_type": credit_type.value,
            "reason": reason,
            "reference_id": reference_id,
            "metadata": metadata or {}
        })
        return Transaction(**data)
    
    def debit(
        self,
        account_id: str,
        amount: float,
        reason: str,
        credit_type: CreditType = CreditType.FP_CREDITS,
        reference_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Transaction:
        """
        Deduct credits from an account.
        
        Args:
            account_id: The account to debit
            amount: Amount to deduct (must be positive)
            reason: Description of why credits are being deducted
            credit_type: Type of credits
            reference_id: Optional reference (e.g., service usage ID)
            metadata: Optional additional data
            
        Returns:
            Transaction record
            
        Raises:
            FPCreditsError: If insufficient balance
        """
        data = self._request("POST", "/api/debit", json={
            "account_id": account_id,
            "amount": amount,
            "credit_type": credit_type.value,
            "reason": reason,
            "reference_id": reference_id,
            "metadata": metadata or {}
        })
        return Transaction(**data)
    
    def charge(
        self,
        account_id: str,
        amount: float,
        service_name: str,
        description: str = "",
        reference_id: str = None
    ) -> Transaction:
        """
        Convenience method to charge a user for a service.
        
        Args:
            account_id: The user's account
            amount: Amount to charge
            service_name: Name of the service being used
            description: Additional description
            reference_id: Optional reference ID
            
        Returns:
            Transaction record
        """
        reason = f"{service_name}: {description}" if description else service_name
        return self.debit(account_id, amount, reason, reference_id=reference_id)
    
    # ================================================================
    # TRANSFER OPERATIONS
    # ================================================================
    
    def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: float,
        reason: str = "",
        credit_type: CreditType = CreditType.FP_CREDITS,
        metadata: Dict[str, Any] = None
    ) -> dict:
        """
        Transfer credits between accounts.
        
        Args:
            from_account: Source account
            to_account: Destination account
            amount: Amount to transfer
            reason: Description of the transfer
            credit_type: Type of credits
            metadata: Optional additional data
            
        Returns:
            Transfer result with transaction IDs
        """
        return self._request("POST", "/api/transfer", json={
            "from_account": from_account,
            "to_account": to_account,
            "amount": amount,
            "credit_type": credit_type.value,
            "reason": reason,
            "metadata": metadata or {}
        })
    
    # ================================================================
    # EXCHANGE OPERATIONS
    # ================================================================
    
    def exchange(
        self,
        account_id: str,
        from_type: CreditType,
        to_type: CreditType,
        amount: float
    ) -> dict:
        """
        Exchange between credit types.
        
        Args:
            account_id: The account performing the exchange
            from_type: Credit type to exchange from
            to_type: Credit type to exchange to
            amount: Amount to exchange
            
        Returns:
            Exchange result with amounts and rate
        """
        return self._request("POST", "/api/exchange", json={
            "account_id": account_id,
            "from_type": from_type.value,
            "to_type": to_type.value,
            "amount": amount
        })
    
    def fp_to_cora(self, account_id: str, fp_amount: float) -> dict:
        """Convert FP Credits to Cora Credits"""
        return self.exchange(account_id, CreditType.FP_CREDITS, CreditType.CORA_CREDITS, fp_amount)
    
    def cora_to_fp(self, account_id: str, cora_amount: float) -> dict:
        """Convert Cora Credits to FP Credits"""
        return self.exchange(account_id, CreditType.CORA_CREDITS, CreditType.FP_CREDITS, cora_amount)
    
    # ================================================================
    # TRANSACTION HISTORY
    # ================================================================
    
    def get_transactions(
        self,
        account_id: str,
        limit: int = 50
    ) -> List[dict]:
        """
        Get transaction history for an account.
        
        Args:
            account_id: The account to get history for
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction records
        """
        data = self._request("GET", f"/api/transactions/{account_id}", params={"limit": limit})
        return data.get("transactions", [])
    
    # ================================================================
    # UTILITY METHODS
    # ================================================================
    
    def health_check(self) -> dict:
        """Check if the credits gateway is healthy"""
        return self._request("GET", "/health")
    
    def get_account(self, account_id: str) -> dict:
        """Get full account details"""
        return self._request("GET", f"/api/accounts/{account_id}")


# ================================================================
# DECORATOR FOR SERVICE INTEGRATION
# ================================================================

def require_credits(amount: float, credit_type: CreditType = CreditType.FP_CREDITS):
    """
    Decorator to require credits before executing a function.
    
    Usage:
        @require_credits(10.0)
        def my_expensive_operation(user_id: str, ...):
            # This only runs if user has 10+ FP credits
            pass
    
    The decorated function must have 'user_id' or 'account_id' as first argument.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get account ID from first arg or kwargs
            account_id = kwargs.get("account_id") or kwargs.get("user_id") or args[0]
            
            # Get credits client from environment or create one
            api_key = os.environ.get("FP_CREDITS_API_KEY")
            if not api_key:
                raise FPCreditsError("FP_CREDITS_API_KEY environment variable required")
            
            client = FPCredits(api_key=api_key)
            
            # Check balance
            if not client.has_sufficient_balance(account_id, amount, credit_type):
                raise FPCreditsError(f"Insufficient credits. Required: {amount} {credit_type.value}")
            
            # Debit credits
            client.debit(
                account_id,
                amount,
                f"Service charge: {func.__name__}",
                credit_type
            )
            
            # Execute function
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ================================================================
# QUICK START EXAMPLES
# ================================================================

if __name__ == "__main__":
    # Example usage
    print("FP Credits SDK - Example Usage")
    print("=" * 50)
    
    # Initialize client (use environment variable or pass directly)
    # export FP_CREDITS_API_KEY=fps_your_key_here
    
    try:
        client = FPCredits(
            api_key="fpai_master_key_change_in_production",  # Use your real key
            base_url="http://localhost:8760"  # Use production URL in real apps
        )
        
        # Health check
        health = client.health_check()
        print(f"Gateway Status: {health['status']}")
        
        # Get balance
        balance = client.get_balance("user:demo")
        print(f"Demo User Balance: {balance.fp_credits} FP Credits")
        
        # Credit some credits
        tx = client.credit("user:demo", 100.0, "SDK test credit")
        print(f"Credited 100 FP Credits. New balance: {tx.balance_after}")
        
        # Debit for a service
        tx = client.charge("user:demo", 10.0, "AI Chat", "Test session")
        print(f"Charged 10 FP Credits. New balance: {tx.balance_after}")
        
        # Get transactions
        transactions = client.get_transactions("user:demo", limit=5)
        print(f"Recent transactions: {len(transactions)}")
        
    except FPCreditsError as e:
        print(f"Error: {e.message}")

