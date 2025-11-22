"""
Pydantic models for API requests/responses
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# Request Models
class DepositRequest(BaseModel):
    wallet_address: str = Field(..., description="Solana wallet address")
    amount_sol: float = Field(..., gt=0, description="Amount of SOL to deposit")
    signature: Optional[str] = Field(None, description="Transaction signature from wallet")

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                "amount_sol": 10.5,
                "signature": "3Bxs..."
            }
        }


class WithdrawRequest(BaseModel):
    wallet_address: str
    amount_sol: float = Field(..., gt=0)
    authorization: str = Field(..., description="Authorization signature from redemption-algorithm")

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                "amount_sol": 5.0,
                "authorization": "auth_sig_from_redemption_service"
            }
        }


# Response Models
class DepositResponse(BaseModel):
    transaction_id: str
    tie_contract_value: float = Field(..., description="2x the deposited amount")
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "5J7Yx...",
                "tie_contract_value": 21.0,
                "status": "pending"
            }
        }


class WithdrawResponse(BaseModel):
    transaction_id: str
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "2K8Zx...",
                "status": "processing"
            }
        }


class TreasuryBalance(BaseModel):
    total_deposited: float = Field(..., description="Total SOL deposited all-time")
    current_balance: float = Field(..., description="Current SOL in treasury")
    treasury_ratio: float = Field(..., description="current_balance / total_deposited")

    class Config:
        json_schema_extra = {
            "example": {
                "total_deposited": 1000.0,
                "current_balance": 1840.5,
                "treasury_ratio": 1.84
            }
        }


class TreasuryControl(BaseModel):
    holder_control_pct: float = Field(..., description="% of voting power held by holders")
    status: str = Field(..., description="green|yellow_low|yellow_high|orange|red")
    threshold: float = Field(51.0, description="Minimum control threshold")

    class Config:
        json_schema_extra = {
            "example": {
                "holder_control_pct": 75.3,
                "status": "green",
                "threshold": 51.0
            }
        }


class TreasuryTransaction(BaseModel):
    id: int
    transaction_id: str
    wallet_address: str
    type: str  # deposit or withdrawal
    amount_sol: float
    status: str  # pending, confirmed, failed
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    tie_contract_value: Optional[float] = None

    class Config:
        from_attributes = True


class TransactionHistory(BaseModel):
    transactions: List[TreasuryTransaction]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "transactions": [],
                "total": 0
            }
        }
