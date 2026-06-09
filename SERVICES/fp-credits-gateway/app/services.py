"""
FP Credits Gateway - Business Logic Services
Handles credit operations with proper transaction management.
"""

from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import hashlib
import asyncio

from .database import (
    Account, Transaction, APIKey, Webhook,
    AccountRepository, TransactionRepository,
    AccountType, CreditType, TransactionType, TransactionStatus
)


# ============================================================
# CONFIGURATION
# ============================================================

class ExchangeRates:
    """Current exchange rates between credit types"""
    FP_TO_USD = 1.0       # 1 FP Credit = $1 USD
    FP_TO_CORA = 10.0     # 1 FP Credit = 10 Cora Credits
    CORA_TO_USD = 0.1     # 1 Cora Credit = $0.10 USD
    
    @classmethod
    def get_rate(cls, from_type: CreditType, to_type: CreditType) -> float:
        """Get exchange rate between two credit types"""
        if from_type == to_type:
            return 1.0
        
        rates = {
            (CreditType.FP_CREDITS, CreditType.USD): cls.FP_TO_USD,
            (CreditType.USD, CreditType.FP_CREDITS): 1.0 / cls.FP_TO_USD,
            (CreditType.FP_CREDITS, CreditType.CORA_CREDITS): cls.FP_TO_CORA,
            (CreditType.CORA_CREDITS, CreditType.FP_CREDITS): 1.0 / cls.FP_TO_CORA,
            (CreditType.CORA_CREDITS, CreditType.USD): cls.CORA_TO_USD,
            (CreditType.USD, CreditType.CORA_CREDITS): 1.0 / cls.CORA_TO_USD,
        }
        
        return rates.get((from_type, to_type), 0.0)


# ============================================================
# CREDITS SERVICE
# ============================================================

class CreditsService:
    """
    Main service for credit operations.
    Handles all credit/debit/transfer/exchange logic with proper transactions.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.accounts = AccountRepository(session)
        self.transactions = TransactionRepository(session)
        self._webhook_queue: List[dict] = []
    
    async def get_balance(self, account_id: str) -> Dict[str, Any]:
        """Get account balance for all credit types"""
        account = await self.accounts.get_by_id(account_id)
        
        if not account:
            return {
                "account_id": account_id,
                "balances": {
                    "fp_credits": 0.0,
                    "cora_credits": 0.0,
                    "usd": 0.0
                },
                "pending": {
                    "fp_credits": 0.0,
                    "cora_credits": 0.0,
                    "usd": 0.0
                },
                "exists": False
            }
        
        return {
            "account_id": account_id,
            "balances": {
                "fp_credits": account.balance_fp,
                "cora_credits": account.balance_cora,
                "usd": account.balance_usd
            },
            "pending": {
                "fp_credits": account.pending_fp,
                "cora_credits": account.pending_cora,
                "usd": account.pending_usd
            },
            "exists": True,
            "last_activity": account.last_activity.isoformat() if account.last_activity else None
        }
    
    async def credit(
        self,
        account_id: str,
        amount: float,
        credit_type: CreditType,
        reason: str,
        reference_id: str = None,
        metadata: dict = None,
        source_service: str = None
    ) -> Transaction:
        """Add credits to an account"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Get or create account
        account = await self.accounts.get_or_create(account_id)
        balance_before = account.get_balance(credit_type)
        
        # Update balance
        account = await self.accounts.update_balance(account_id, credit_type, amount)
        balance_after = account.get_balance(credit_type)
        
        # Create transaction record
        transaction = await self.transactions.create(
            account_id=account_id,
            transaction_type=TransactionType.CREDIT,
            credit_type=credit_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            reference_id=reference_id,
            metadata=metadata,
            source_service=source_service
        )
        
        # Queue webhook notification
        self._queue_webhook("credit", account_id, transaction)
        
        return transaction
    
    async def debit(
        self,
        account_id: str,
        amount: float,
        credit_type: CreditType,
        reason: str,
        reference_id: str = None,
        metadata: dict = None,
        source_service: str = None
    ) -> Transaction:
        """Remove credits from an account"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Get account (must exist for debit)
        account = await self.accounts.get_by_id(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        balance_before = account.get_balance(credit_type)
        
        if balance_before < amount:
            raise ValueError(f"Insufficient balance. Has {balance_before}, needs {amount}")
        
        # Update balance
        account = await self.accounts.update_balance(account_id, credit_type, -amount)
        balance_after = account.get_balance(credit_type)
        
        # Create transaction record
        transaction = await self.transactions.create(
            account_id=account_id,
            transaction_type=TransactionType.DEBIT,
            credit_type=credit_type,
            amount=-amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            reference_id=reference_id,
            metadata=metadata,
            source_service=source_service
        )
        
        # Queue webhook notification
        self._queue_webhook("debit", account_id, transaction)
        
        return transaction
    
    async def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: float,
        credit_type: CreditType,
        reason: str = "",
        metadata: dict = None,
        source_service: str = None
    ) -> Tuple[Transaction, Transaction]:
        """Transfer credits between accounts"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if from_account == to_account:
            raise ValueError("Cannot transfer to same account")
        
        # Debit from source
        debit_tx = await self.debit(
            account_id=from_account,
            amount=amount,
            credit_type=credit_type,
            reason=f"Transfer to {to_account}: {reason}",
            metadata={**(metadata or {}), "transfer_to": to_account},
            source_service=source_service
        )
        
        # Credit to destination
        credit_tx = await self.credit(
            account_id=to_account,
            amount=amount,
            credit_type=credit_type,
            reason=f"Transfer from {from_account}: {reason}",
            metadata={**(metadata or {}), "transfer_from": from_account},
            source_service=source_service
        )
        
        return debit_tx, credit_tx
    
    async def exchange(
        self,
        account_id: str,
        from_type: CreditType,
        to_type: CreditType,
        amount: float,
        source_service: str = None
    ) -> Tuple[Transaction, Transaction, float]:
        """Exchange between credit types"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if from_type == to_type:
            raise ValueError("Cannot exchange to same credit type")
        
        # Get exchange rate
        rate = ExchangeRates.get_rate(from_type, to_type)
        if rate == 0:
            raise ValueError(f"Unsupported exchange: {from_type} -> {to_type}")
        
        converted_amount = amount * rate
        
        # Debit source currency
        debit_tx = await self.debit(
            account_id=account_id,
            amount=amount,
            credit_type=from_type,
            reason=f"Exchange to {to_type.value}",
            metadata={"exchange_rate": rate, "to_type": to_type.value},
            source_service=source_service
        )
        
        # Credit destination currency
        credit_tx = await self.credit(
            account_id=account_id,
            amount=converted_amount,
            credit_type=to_type,
            reason=f"Exchange from {from_type.value}",
            metadata={"exchange_rate": rate, "from_type": from_type.value},
            source_service=source_service
        )
        
        return debit_tx, credit_tx, rate
    
    async def get_transactions(
        self,
        account_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Transaction]:
        """Get transaction history for an account"""
        return await self.transactions.get_by_account(account_id, limit, offset)
    
    async def check_balance(
        self,
        account_id: str,
        amount: float,
        credit_type: CreditType
    ) -> bool:
        """Check if account has sufficient balance"""
        account = await self.accounts.get_by_id(account_id)
        if not account:
            return False
        return account.get_balance(credit_type) >= amount
    
    def _queue_webhook(self, event_type: str, account_id: str, transaction: Transaction):
        """Queue a webhook notification for later delivery"""
        self._webhook_queue.append({
            "event_type": event_type,
            "account_id": account_id,
            "transaction": transaction.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })


# ============================================================
# API KEY SERVICE
# ============================================================

class APIKeyService:
    """Service for API key management"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_key(
        self,
        service_name: str,
        description: str = "",
        permissions: List[str] = None,
        rate_limit: int = 100
    ) -> Tuple[str, APIKey]:
        """Create a new API key. Returns (raw_key, key_record)"""
        key_id = f"fpk_{secrets.token_hex(8)}"
        raw_key = f"fps_{secrets.token_hex(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            service_name=service_name,
            description=description,
            permissions=permissions or ["read", "debit"],
            rate_limit_per_minute=rate_limit
        )
        
        self.session.add(api_key)
        await self.session.flush()
        
        return raw_key, api_key
    
    async def verify_key(self, raw_key: str) -> Optional[APIKey]:
        """Verify an API key and return its record"""
        from sqlalchemy import select
        
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True
            )
        )
        api_key = result.scalar_one_or_none()
        
        if api_key:
            api_key.last_used = datetime.utcnow()
            api_key.usage_count += 1
            await self.session.flush()
        
        return api_key
    
    async def list_keys(self) -> List[APIKey]:
        """List all API keys"""
        from sqlalchemy import select
        result = await self.session.execute(select(APIKey))
        return result.scalars().all()
    
    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key"""
        from sqlalchemy import select
        result = await self.session.execute(
            select(APIKey).where(APIKey.key_id == key_id)
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            api_key.is_active = False
            await self.session.flush()
            return True
        return False


# ============================================================
# BATCH OPERATIONS SERVICE
# ============================================================

class BatchService:
    """Service for batch credit operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.credits = CreditsService(session)
    
    async def batch_credit(
        self,
        operations: List[Dict[str, Any]],
        source_service: str = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple credit operations in a batch.
        
        operations: [
            {"account_id": "user:1", "amount": 10.0, "reason": "Bonus"},
            {"account_id": "user:2", "amount": 20.0, "reason": "Reward"},
        ]
        """
        results = []
        
        for op in operations:
            try:
                tx = await self.credits.credit(
                    account_id=op["account_id"],
                    amount=op["amount"],
                    credit_type=CreditType(op.get("credit_type", "fp_credits")),
                    reason=op.get("reason", "Batch credit"),
                    reference_id=op.get("reference_id"),
                    metadata=op.get("metadata"),
                    source_service=source_service
                )
                results.append({
                    "account_id": op["account_id"],
                    "success": True,
                    "transaction_id": tx.transaction_id,
                    "balance_after": tx.balance_after
                })
            except Exception as e:
                results.append({
                    "account_id": op["account_id"],
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def batch_debit(
        self,
        operations: List[Dict[str, Any]],
        source_service: str = None
    ) -> List[Dict[str, Any]]:
        """Process multiple debit operations in a batch"""
        results = []
        
        for op in operations:
            try:
                tx = await self.credits.debit(
                    account_id=op["account_id"],
                    amount=op["amount"],
                    credit_type=CreditType(op.get("credit_type", "fp_credits")),
                    reason=op.get("reason", "Batch debit"),
                    reference_id=op.get("reference_id"),
                    metadata=op.get("metadata"),
                    source_service=source_service
                )
                results.append({
                    "account_id": op["account_id"],
                    "success": True,
                    "transaction_id": tx.transaction_id,
                    "balance_after": tx.balance_after
                })
            except Exception as e:
                results.append({
                    "account_id": op["account_id"],
                    "success": False,
                    "error": str(e)
                })
        
        return results


# ============================================================
# STATS SERVICE
# ============================================================

class StatsService:
    """Service for system statistics"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        from sqlalchemy import select, func
        
        # Count accounts (excluding system accounts)
        result = await self.session.execute(
            select(func.count(Account.id)).where(
                Account.account_type != AccountType.SYSTEM
            )
        )
        total_accounts = result.scalar() or 0
        
        # Total transactions
        result = await self.session.execute(
            select(func.count(Transaction.id))
        )
        total_transactions = result.scalar() or 0
        
        # Total credits in circulation
        result = await self.session.execute(
            select(func.sum(Account.balance_fp)).where(
                Account.account_type != AccountType.SYSTEM
            )
        )
        total_fp = result.scalar() or 0
        
        result = await self.session.execute(
            select(func.sum(Account.balance_cora)).where(
                Account.account_type != AccountType.SYSTEM
            )
        )
        total_cora = result.scalar() or 0
        
        # Active API keys
        result = await self.session.execute(
            select(func.count(APIKey.id)).where(APIKey.is_active == True)
        )
        active_keys = result.scalar() or 0
        
        # Transactions today
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(func.count(Transaction.id)).where(
                Transaction.created_at >= today
            )
        )
        transactions_today = result.scalar() or 0
        
        return {
            "total_accounts": total_accounts,
            "total_transactions": total_transactions,
            "transactions_today": transactions_today,
            "active_api_keys": active_keys,
            "credits_in_circulation": {
                "fp_credits": total_fp,
                "cora_credits": total_cora
            },
            "exchange_rates": {
                "fp_to_usd": ExchangeRates.FP_TO_USD,
                "fp_to_cora": ExchangeRates.FP_TO_CORA
            }
        }


