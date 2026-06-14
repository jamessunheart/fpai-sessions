#!/usr/bin/env python3
"""
ARIA ASCENSION - FINANCIAL HUB
==============================

Handle financial actions:
- View account balances
- Request payments (with approval)
- Generate invoices
- Track expenses

Approval Levels:
- View balances: Auto
- Request payment: Requires approval + confirmation
- Generate invoice: Requires approval
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.agency.financial")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Hyperliquid
HYPERLIQUID_API_URL = os.getenv("HYPERLIQUID_API_URL", "http://198.54.123.234:8601")

# Credits
CREDITS_API_URL = os.getenv("CREDITS_API_URL", "http://198.54.123.234:8765")

# Payment limits
MAX_AUTO_PAYMENT = float(os.getenv("MAX_AUTO_PAYMENT", "0"))  # 0 = always approve
DAILY_PAYMENT_LIMIT = float(os.getenv("DAILY_PAYMENT_LIMIT", "1000"))


class PaymentStatus(str, Enum):
    """Status of a payment."""
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class PaymentRequest:
    """A payment request."""
    id: str
    amount: float
    currency: str
    recipient: str
    description: str
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    approved_at: datetime = None
    completed_at: datetime = None
    transaction_id: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "amount": self.amount,
            "currency": self.currency,
            "recipient": self.recipient,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "transaction_id": self.transaction_id
        }


@dataclass
class Invoice:
    """An invoice."""
    id: str
    client_name: str
    amount: float
    currency: str
    items: List[Dict]
    due_date: datetime
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "client_name": self.client_name,
            "amount": self.amount,
            "currency": self.currency,
            "items": self.items,
            "due_date": self.due_date.isoformat(),
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }


# ============================================================================
# FINANCIAL HUB
# ============================================================================

class FinancialHub:
    """
    Central hub for financial operations.
    """
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.pending_payments: Dict[str, PaymentRequest] = {}
        self.pending_invoices: Dict[str, Invoice] = {}
        self._approval_callback: Optional[callable] = None
        self._daily_total: float = 0
        self._daily_reset_date: datetime = datetime.now().date()
    
    def set_approval_callback(self, callback: callable):
        """Set callback for requesting approvals."""
        self._approval_callback = callback
    
    # ========================================================================
    # BALANCES (READ-ONLY)
    # ========================================================================
    
    async def get_trading_balance(self) -> Dict[str, Any]:
        """
        Get trading account balance.
        Read-only - auto-approved.
        """
        try:
            response = await self.http_client.get(
                f"{HYPERLIQUID_API_URL}/api/live/balance"
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "balance": data.get("balance", 0),
                    "equity": data.get("equity", 0),
                    "available": data.get("available", 0),
                    "currency": "USDC"
                }
            else:
                return {"status": "error", "message": "Failed to fetch balance"}
        
        except Exception as e:
            logger.error(f"Balance fetch error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_credits_balance(self) -> Dict[str, Any]:
        """
        Get UC credits balance.
        Read-only - auto-approved.
        """
        try:
            response = await self.http_client.get(
                f"{CREDITS_API_URL}/api/balance"
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "balance": data.get("balance", 0),
                    "currency": "UC"
                }
            else:
                return {"status": "unavailable", "note": "Credits service not running"}
        
        except Exception as e:
            return {"status": "unavailable", "note": str(e)}
    
    async def get_all_balances(self) -> Dict[str, Any]:
        """Get all account balances."""
        trading = await self.get_trading_balance()
        credits = await self.get_credits_balance()
        
        return {
            "trading": trading,
            "credits": credits,
            "timestamp": datetime.now().isoformat()
        }
    
    # ========================================================================
    # PAYMENTS
    # ========================================================================
    
    async def request_payment(
        self,
        amount: float,
        currency: str,
        recipient: str,
        description: str,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        Request a payment.
        
        Always requires approval + confirmation for safety.
        """
        # Check daily limit
        self._check_daily_reset()
        if self._daily_total + amount > DAILY_PAYMENT_LIMIT:
            return {
                "status": "rejected",
                "message": f"Would exceed daily limit of ${DAILY_PAYMENT_LIMIT}",
                "daily_remaining": DAILY_PAYMENT_LIMIT - self._daily_total
            }
        
        payment = PaymentRequest(
            id=f"pay-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            amount=amount,
            currency=currency,
            recipient=recipient,
            description=description,
            metadata=metadata or {}
        )
        
        self.pending_payments[payment.id] = payment
        
        # Request approval
        if self._approval_callback:
            await self._approval_callback({
                "type": "payment",
                "payment": payment.to_dict()
            })
        
        return {
            "status": "pending_approval",
            "payment_id": payment.id,
            "message": f"Payment of {amount} {currency} to {recipient} requires approval",
            "approval_required": True,
            "confirmation_required": True
        }
    
    async def approve_payment(self, payment_id: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Approve a payment.
        
        Two-step process:
        1. approve_payment(id) - Marks as approved
        2. approve_payment(id, confirm=True) - Actually sends
        """
        if payment_id not in self.pending_payments:
            return {"status": "error", "message": "Payment not found"}
        
        payment = self.pending_payments[payment_id]
        
        if payment.status == PaymentStatus.PENDING:
            if not confirm:
                payment.status = PaymentStatus.APPROVED
                payment.approved_at = datetime.now()
                return {
                    "status": "approved",
                    "message": "Payment approved. Send CONFIRM to execute.",
                    "payment": payment.to_dict()
                }
        
        if payment.status == PaymentStatus.APPROVED and confirm:
            # Execute the payment
            result = await self._execute_payment(payment)
            
            if result.get("status") == "completed":
                self._daily_total += payment.amount
                del self.pending_payments[payment_id]
            
            return result
        
        return {"status": "error", "message": f"Payment in invalid state: {payment.status.value}"}
    
    async def _execute_payment(self, payment: PaymentRequest) -> Dict[str, Any]:
        """Execute an approved payment."""
        payment.status = PaymentStatus.PROCESSING
        
        # This would integrate with actual payment system
        # For now, simulate success
        
        try:
            # Simulate payment processing
            payment.status = PaymentStatus.COMPLETED
            payment.completed_at = datetime.now()
            payment.transaction_id = f"tx-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            logger.info(f"Payment executed: {payment.id} - {payment.amount} {payment.currency}")
            
            return {
                "status": "completed",
                "payment": payment.to_dict(),
                "message": f"Payment of {payment.amount} {payment.currency} sent to {payment.recipient}",
                "note": "Payment integration pending - simulated success"
            }
        
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            return {"status": "failed", "message": str(e)}
    
    async def reject_payment(self, payment_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a payment request."""
        if payment_id not in self.pending_payments:
            return {"status": "error", "message": "Payment not found"}
        
        payment = self.pending_payments[payment_id]
        payment.status = PaymentStatus.REJECTED
        
        del self.pending_payments[payment_id]
        
        return {"status": "rejected", "payment_id": payment_id, "reason": reason}
    
    def _check_daily_reset(self):
        """Reset daily total if new day."""
        today = datetime.now().date()
        if today > self._daily_reset_date:
            self._daily_total = 0
            self._daily_reset_date = today
    
    # ========================================================================
    # INVOICES
    # ========================================================================
    
    async def create_invoice(
        self,
        client_name: str,
        items: List[Dict],
        due_date: datetime = None,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Create an invoice.
        Requires approval before sending.
        """
        if due_date is None:
            due_date = datetime.now() + timedelta(days=30)
        
        total = sum(item.get("amount", 0) * item.get("quantity", 1) for item in items)
        
        invoice = Invoice(
            id=f"inv-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            client_name=client_name,
            amount=total,
            currency=currency,
            items=items,
            due_date=due_date
        )
        
        self.pending_invoices[invoice.id] = invoice
        
        return {
            "status": "draft",
            "invoice_id": invoice.id,
            "invoice": invoice.to_dict(),
            "message": "Invoice created as draft. Approve to send."
        }
    
    async def approve_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Approve and send an invoice."""
        if invoice_id not in self.pending_invoices:
            return {"status": "error", "message": "Invoice not found"}
        
        invoice = self.pending_invoices[invoice_id]
        invoice.status = "sent"
        
        # Would integrate with invoicing system
        
        return {
            "status": "sent",
            "invoice": invoice.to_dict(),
            "note": "Invoice integration pending"
        }
    
    # ========================================================================
    # EXPENSE TRACKING
    # ========================================================================
    
    async def track_expense(
        self,
        amount: float,
        category: str,
        description: str,
        date: datetime = None
    ) -> Dict[str, Any]:
        """
        Track an expense.
        Read/write to internal tracking - auto-approved.
        """
        expense = {
            "id": f"exp-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "amount": amount,
            "category": category,
            "description": description,
            "date": (date or datetime.now()).isoformat()
        }
        
        # Would store in database
        
        return {
            "status": "tracked",
            "expense": expense
        }
    
    async def get_expense_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get expense summary."""
        # Would query database
        return {
            "status": "success",
            "period_days": days,
            "total": 0,
            "by_category": {},
            "note": "Expense tracking integration pending"
        }
    
    # ========================================================================
    # PENDING ITEMS
    # ========================================================================
    
    def get_pending_payments(self) -> List[Dict]:
        """Get all pending payments."""
        return [p.to_dict() for p in self.pending_payments.values()]
    
    def get_pending_invoices(self) -> List[Dict]:
        """Get all pending invoices."""
        return [i.to_dict() for i in self.pending_invoices.values()]


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_hub: Optional[FinancialHub] = None


def get_financial_hub() -> FinancialHub:
    """Get global financial hub."""
    global _hub
    if _hub is None:
        _hub = FinancialHub()
    return _hub


async def get_balances() -> Dict:
    """Get all balances."""
    return await get_financial_hub().get_all_balances()


async def request_payment(amount: float, currency: str, recipient: str, description: str) -> Dict:
    """Request a payment."""
    return await get_financial_hub().request_payment(amount, currency, recipient, description)


